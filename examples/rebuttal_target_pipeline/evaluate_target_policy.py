#!/usr/bin/env python3
"""Evaluate one Target participant policy on the frozen ten paired specs."""

import argparse
import hashlib
import json
import math
import os
import random
import sys
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pybullet as pb


GROUP = "simulation_target_group"
PARTICIPANTS = [f"T{index:02d}" for index in range(1, 11)]
EXPECTED_RELEASE_Z = 0.08
ARCAP_ROOT = Path("/users/k23114984/code/arcap_policy/STEP2_train_policy")
EXAMPLES_DIR = Path(__file__).resolve().parents[1]
for extra in (EXAMPLES_DIR, ARCAP_ROOT):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

import main_obstacle_transport as task  # noqa: E402
from rebuttal_target_pipeline.target_protocol import (  # noqa: E402
    TARGET_SUCCESS_CRITERION,
    TARGET_XY_TOLERANCE,
    TargetObstacleTransportSim,
)


class InvalidPolicyAction(ValueError):
    pass


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(payload):
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def load_json(path):
    with Path(path).open("r", encoding="utf-8") as stream:
        return json.load(stream)


def write_json_exclusive(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=2, sort_keys=True)
        stream.write("\n")


def set_all_seeds(seed):
    np.random.seed(seed)
    random.seed(seed)
    import torch

    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def load_policy(checkpoint, cuda):
    import robomimic.utils.file_utils as FileUtils
    import robomimic.utils.torch_utils as TorchUtils

    device = TorchUtils.get_torch_device(try_to_use_cuda=bool(cuda))
    policy, _ = FileUtils.policy_from_checkpoint(
        ckpt_path=str(checkpoint), device=device, verbose=False
    )
    return policy, str(device)


def fixed_size_pointcloud(sim, num_points, rng):
    cloud = sim.get_system_virtual_pcd()
    cloud = sim.crop_pcd(cloud, sim.crop_min, sim.crop_max)
    if cloud.shape[0] == 0:
        raise RuntimeError("Cropped point cloud is empty")
    if cloud.shape[0] < num_points:
        repeats = num_points // cloud.shape[0] + 1
        cloud = np.tile(cloud, (repeats, 1))[:num_points]
    elif cloud.shape[0] > num_points:
        cloud = cloud[rng.choice(cloud.shape[0], num_points, replace=False)]
    cloud = np.asarray(cloud, dtype=np.float32)
    if cloud.shape != (num_points, 6) or not np.isfinite(cloud).all():
        raise RuntimeError(f"Invalid policy point cloud: {cloud.shape}")
    return cloud


def current_obs(sim, gripper_state, num_points, pointcloud_rng):
    return {
        "robot0_arm_joints": np.asarray(
            [pb.getJointState(sim.panda, joint)[0] for joint in sim.arm_joint_indices],
            dtype=np.float32,
        ),
        "robot0_hand_joints": np.asarray([gripper_state], dtype=np.float32),
        "pointcloud": fixed_size_pointcloud(sim, num_points, pointcloud_rng),
    }


def stacked_obs(history):
    return {
        key: np.stack([observation[key] for observation in history], axis=0)
        for key in history[0]
    }


def apply_policy_action(sim, action, duration):
    action = np.asarray(action, dtype=float).reshape(-1)
    if action.shape != (8,) or not np.isfinite(action).all():
        raise InvalidPolicyAction(f"Expected finite (8,) action, received {action.shape}")
    target_q = action[:7]
    gripper_state = float(np.clip(action[7], -1.0, 1.0))
    gripper_width = float(np.clip((1.0 - gripper_state) * 0.02, 0.0, 0.04))
    steps = max(1, int(round(float(duration) * sim.control_hz)))
    for _ in range(steps):
        sim._apply_arm(target_q, force=120, max_vel=1.5)
        sim._apply_gripper(gripper_width, force=120, max_vel=0.08)
        sim._step_simulation(sim.sim_dt)
    return gripper_state, action


def policy_start_state(sim):
    box_pos, box_quat = pb.getBasePositionAndOrientation(sim.cube_id)
    ee_state = pb.getLinkState(sim.panda, sim.ee_link_index, computeForwardKinematics=True)
    return {
        "phase": "policy_inference_start",
        "time": 0.0,
        "sim_step": int(sim._sim_step_count),
        "box_position": list(box_pos),
        "box_quaternion_xyzw": list(box_quat),
        "ee_position": list(ee_state[0]),
        "ee_quaternion_xyzw": list(ee_state[1]),
        "gripper_state": 1.0,
        "gripper_closed": True,
    }


def trace_snapshot(sim, step, gripper_state):
    box_pos = np.asarray(pb.getBasePositionAndOrientation(sim.cube_id)[0], dtype=float)
    ee_pos = np.asarray(sim.ee_pos(), dtype=float)
    obstacle_pos, obstacle_quat = pb.getBasePositionAndOrientation(sim.obstacle_id)
    return {
        "policy_step": int(step),
        "box_position": box_pos.tolist(),
        "ee_position": ee_pos.tolist(),
        "cylinder_position": list(obstacle_pos),
        "cylinder_tilt_degrees": task.quaternion_upright_error_degrees(obstacle_quat),
        "gripper_state": float(gripper_state),
        "box_obstacle_contact_steps_cumulative": int(sim._box_obstacle_contact_steps),
        "robot_obstacle_contact_steps_cumulative": int(sim._robot_obstacle_contact_steps),
    }


def route_behavior(trace):
    points = np.asarray([row["box_position"] for row in trace], dtype=float)
    if len(points) == 0:
        return {"realised_route": "indeterminate", "reason": "empty_policy_trace"}
    obstacle_y = float(task.OBSTACLE_XY[1])
    band_half_width = float(task.OBSTACLE_RADIUS + task.BOX_HALF_EXTENT)
    in_band = np.abs(points[:, 1] - obstacle_y) <= band_half_width
    closest_index = int(np.argmin(np.abs(points[:, 1] - obstacle_y)))
    x_reference = float(np.median(points[in_band, 0])) if np.any(in_band) else float(points[closest_index, 0])
    reached_band = bool(np.any(in_band))
    return {
        "realised_route": ("L" if x_reference < task.OBSTACLE_XY[0] else "R") if reached_band else "indeterminate",
        "crossed_obstacle_y_band": reached_band,
        "obstacle_y_band_half_width": band_half_width,
        "box_x_reference": x_reference,
        "box_x_at_closest_obstacle_y": float(points[closest_index, 0]),
        "box_y_at_closest_obstacle_y": float(points[closest_index, 1]),
        "minimum_box_cylinder_xy_distance": float(
            np.min(np.linalg.norm(points[:, :2] - np.asarray(task.OBSTACLE_XY), axis=1))
        ),
    }


def next_execution_index(participant_dir, eval_case_id):
    paths = list((participant_dir / "videos").glob(f"case_{eval_case_id:02d}_execution_*.mp4"))
    paths += list(
        (participant_dir / "infrastructure_failures").glob(
            f"case_{eval_case_id:02d}_execution_*.json"
        )
    )
    values = []
    for path in paths:
        try:
            values.append(int(path.stem.rsplit("_", 1)[1]))
        except ValueError:
            continue
    return max(values, default=-1) + 1


def run_case(sim, policy, participant, case, args, checkpoint_record, manifest_hash, participant_dir):
    eval_case_id = int(case["eval_case_id"])
    execution_index = next_execution_index(participant_dir, eval_case_id)
    video_path = participant_dir / "videos" / (
        f"case_{eval_case_id:02d}_execution_{execution_index}.mp4"
    )
    spec = case["spec"]
    set_all_seeds(case["runtime_seed"])
    sim.reset_task_state(spec["box_initial_position"])
    if args.save_videos:
        sim.start_video(video_path, fps=args.video_fps)
    policy_call_count = 0
    policy_started = False
    try:
        setup_success, setup_details = sim.scripted_grasp_to_transport_start(spec, save=False)
        setup_end_step = int(sim._sim_step_count)
        if not setup_success:
            raise RuntimeError(f"paired_spec_scripted_setup_failed:{setup_details.get('reason')}")
        start_state = policy_start_state(sim)
        policy.start_episode()
        policy_started = True
        pointcloud_rng = np.random.default_rng(case["point_cloud_seed"])
        observation_horizon = int(policy.policy.global_config.algo.horizon.observation_horizon)
        first_obs = current_obs(sim, 1.0, args.num_points, pointcloud_rng)
        history = deque([first_obs] * observation_horizon, maxlen=observation_horizon)
        trace = [trace_snapshot(sim, 0, 1.0)]
        gripper_state = 1.0
        last_action = None
        success = False
        success_details = None
        termination_reason = "policy_timeout"
        first_policy_call_step = None
        for step in range(args.horizon):
            if first_policy_call_step is None:
                first_policy_call_step = int(sim._sim_step_count)
            action = policy(ob=stacked_obs(history))
            policy_call_count += 1
            try:
                gripper_state, last_action = apply_policy_action(sim, action, args.action_dt)
            except InvalidPolicyAction:
                termination_reason = "nonfinite_or_malformed_policy_action"
                break
            history.append(current_obs(sim, gripper_state, args.num_points, pointcloud_rng))
            trace.append(trace_snapshot(sim, step + 1, gripper_state))
            success, success_details = sim.transport_success()
            if success:
                termination_reason = "success"
                break
        if termination_reason == "policy_timeout" and last_action is not None:
            gripper_state, _ = apply_policy_action(sim, last_action, args.settle_seconds)
            trace.append(trace_snapshot(sim, len(trace), gripper_state))
            success, success_details = sim.transport_success()
            if success:
                termination_reason = "success_after_settle"
        if success_details is None:
            _, success_details = sim.transport_success()
        if termination_reason == "nonfinite_or_malformed_policy_action":
            success = False
            success_details = dict(success_details)
            success_details["success"] = False
            success_details.setdefault("failure_reasons", []).append(
                "nonfinite_or_malformed_policy_action"
            )
        execution_order_valid = bool(
            setup_details["grasped"]
            and setup_details["transport_height_reached"]
            and first_policy_call_step is not None
            and first_policy_call_step >= setup_end_step
        )
        if not execution_order_valid:
            raise RuntimeError("policy_started_before_validated_scripted_setup_boundary")
        return {
            "schema_version": 1,
            "group": GROUP,
            "participant_id": participant,
            "participant_route": "L" if int(participant[1:]) <= 5 else "R",
            "eval_case_id": eval_case_id,
            "valid_scientific_result": True,
            "success": bool(success),
            "termination_reason": termination_reason,
            "policy_started": policy_started,
            "policy_call_count": policy_call_count,
            "policy_steps": policy_call_count,
            "policy_trace_samples": len(trace),
            "execution_index": execution_index,
            "execution_order": [
                "manifest_box_start_reset",
                "scripted_fixed_orientation_approach_grasp_close_lift",
                "validated_grasp_and_transport_height",
                "policy_inference_start",
                "learned_policy_obstacle_avoidance_transport_release",
                "cube_settle_and_frozen_success_test",
            ],
            "execution_order_valid": execution_order_valid,
            "scripted_transport_used": False,
            "policy_inference_start": start_state,
            "setup_details": setup_details,
            "success_details": success_details,
            "target_xy_error": success_details["target_xy_error"],
            "final_cylinder_tilt_degrees": success_details["final_cylinder_tilt_degrees"],
            "maximum_cylinder_tilt_degrees": success_details["maximum_cylinder_tilt_degrees"],
            "box_obstacle_contact_steps": success_details["box_obstacle_contact_steps"],
            "robot_obstacle_contact_steps": success_details["robot_obstacle_contact_steps"],
            "route_behavior": route_behavior(trace),
            "policy_step_trace": trace,
            "paired_spec": case,
            "paired_manifest_sha256": manifest_hash,
            "checkpoint": checkpoint_record["checkpoint"],
            "checkpoint_sha256": checkpoint_record["sha256"],
            "uniform_training_protocol_sha256": checkpoint_record[
                "uniform_training_protocol_sha256"
            ],
            "video_path": str(video_path) if args.save_videos else None,
            "slurm": {
                "job_id": os.environ.get("SLURM_JOB_ID"),
                "array_job_id": os.environ.get("SLURM_ARRAY_JOB_ID"),
                "array_task_id": os.environ.get("SLURM_ARRAY_TASK_ID"),
                "node_list": os.environ.get("SLURM_NODELIST"),
            },
        }
    except Exception as exc:
        record = {
            "schema_version": 1,
            "group": GROUP,
            "participant_id": participant,
            "eval_case_id": eval_case_id,
            "execution_index": execution_index,
            "valid_scientific_result": False,
            "policy_started": policy_started,
            "policy_call_count": policy_call_count,
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
            "paired_manifest_sha256": manifest_hash,
            "paired_spec": case,
            "checkpoint_sha256": checkpoint_record["sha256"],
            "video_path": str(video_path) if args.save_videos else None,
            "classification": "UNREVIEWED_INFRASTRUCTURE_OR_EXECUTION_FAILURE",
            "rerun_authorized": False,
        }
        write_json_exclusive(
            participant_dir
            / "infrastructure_failures"
            / f"case_{eval_case_id:02d}_execution_{execution_index}.json",
            record,
        )
        raise
    finally:
        sim.close_video()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--participant", required=True, choices=PARTICIPANTS)
    parser.add_argument("--checkpoint-manifest", type=Path, required=True)
    parser.add_argument("--spec-manifest", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--horizon", type=int, default=200)
    parser.add_argument("--sample-hz", type=float, default=8.0)
    parser.add_argument("--action-gap", type=int, default=2)
    parser.add_argument("--action-dt", type=float)
    parser.add_argument("--num-points", type=int, default=10000)
    parser.add_argument("--settle-seconds", type=float, default=1.5)
    parser.add_argument("--video-fps", type=int, default=10)
    parser.add_argument("--playback-speed", type=float, default=1000.0)
    parser.add_argument("--save-videos", action="store_true")
    parser.add_argument("--cuda", action="store_true")
    parser.add_argument(
        "--resume-after-reviewed-infrastructure-failure",
        action="store_true",
        help="Preserve completed results and execute only missing cases after external failure review.",
    )
    args = parser.parse_args()
    if args.action_dt is None:
        args.action_dt = float(args.action_gap) / float(args.sample_hz)
    if args.horizon != 200 or args.sample_hz != 8.0 or args.action_gap != 2:
        raise ValueError("Formal rollout protocol is frozen to horizon=200, sample_hz=8, action_gap=2")
    if not math.isclose(args.action_dt, 0.25) or not math.isclose(args.settle_seconds, 1.5):
        raise ValueError("Formal rollout action_dt/settle_seconds must be 0.25/1.5")
    if args.num_points != 10000 or not args.save_videos:
        raise ValueError("Formal rollout requires 10,000 points and saved videos")
    if getattr(task, "RELEASE_Z", None) is None or not np.isclose(task.RELEASE_Z, EXPECTED_RELEASE_Z):
        raise RuntimeError("Shared approved RELEASE_Z=0.08 protocol is not active")

    checkpoint_manifest = load_json(args.checkpoint_manifest)
    spec_manifest = load_json(args.spec_manifest)
    spec_hash = sha256(args.spec_manifest)
    sidecar_path = args.spec_manifest.with_suffix(".sha256.json")
    sidecar = load_json(sidecar_path)
    if sidecar.get("file_sha256") != spec_hash:
        raise ValueError("Paired rollout manifest hash sidecar mismatch")
    canonical = dict(spec_manifest)
    claimed_canonical = canonical.pop("canonical_content_sha256", None)
    if canonical_hash(canonical) != claimed_canonical:
        raise ValueError("Paired rollout manifest canonical content hash mismatch")
    if spec_manifest.get("group") != GROUP or len(spec_manifest.get("eval_cases", [])) != 10:
        raise ValueError("Invalid Target paired rollout manifest")
    if (
        checkpoint_manifest.get("group") != GROUP
        or checkpoint_manifest.get("participant_order") != PARTICIPANTS
        or sha256(args.checkpoint_manifest)
        != spec_manifest.get("checkpoint_gate", {}).get("selected_checkpoints_manifest_sha256")
    ):
        raise ValueError("Checkpoint manifest differs from the one gated before spec freezing")
    frozen_task = spec_manifest.get("frozen_task", {})
    if (
        frozen_task.get("target_xy_tolerance_m") != TARGET_XY_TOLERANCE
        or frozen_task.get("success_criterion") != TARGET_SUCCESS_CRITERION
        or frozen_task.get("success_protocol_scope") != GROUP
        or frozen_task.get("shared_target_xy_tolerance_m_unchanged")
        != task.TARGET_XY_TOLERANCE
        or frozen_task.get("cylinder_upright_tolerance_degrees")
        != task.CYLINDER_UPRIGHT_TOLERANCE_DEGREES
        or frozen_task.get("contacts_are_diagnostic_only") is not True
        or not np.isclose(frozen_task.get("release_ee_z_m", float("nan")), EXPECTED_RELEASE_Z)
    ):
        raise ValueError("Frozen task thresholds differ from the active Target protocol")
    shared_task_record = spec_manifest["software"]
    if sha256(Path(shared_task_record["shared_task_path"])) != shared_task_record["shared_task_sha256"]:
        raise ValueError("Shared task code changed after rollout specs were frozen")
    if sha256(Path(shared_task_record["target_protocol_path"])) != shared_task_record["target_protocol_sha256"]:
        raise ValueError("Target success protocol changed after rollout specs were frozen")
    checkpoint_record = checkpoint_manifest["checkpoints"][args.participant]
    checkpoint = Path(checkpoint_record["checkpoint"])
    if checkpoint_record.get("selected_epoch") != 40 or sha256(checkpoint) != checkpoint_record["sha256"]:
        raise ValueError("Participant checkpoint hash mismatch")

    participant_dir = args.output_root.resolve() / args.participant
    if participant_dir.exists() and not args.resume_after_reviewed_infrastructure_failure:
        raise FileExistsError(f"Refusing to overwrite/re-enter participant rollout root: {participant_dir}")
    participant_dir.mkdir(parents=True, exist_ok=args.resume_after_reviewed_infrastructure_failure)
    summary_path = participant_dir / "summary.json"
    if summary_path.exists():
        raise FileExistsError(f"Participant rollout summary already exists: {summary_path}")

    policy, device = load_policy(checkpoint, args.cuda)
    sim = TargetObstacleTransportSim(gui=False, output_dir=None, sample_hz=args.sample_hz)
    sim.playback_speed = args.playback_speed
    sim.setup()
    results = []
    try:
        for case in spec_manifest["eval_cases"]:
            eval_case_id = int(case["eval_case_id"])
            result_path = participant_dir / "rollouts" / f"rollout_{eval_case_id:02d}.json"
            if result_path.exists():
                if not args.resume_after_reviewed_infrastructure_failure:
                    raise FileExistsError(result_path)
                existing = load_json(result_path)
                if (
                    existing.get("participant_id") != args.participant
                    or existing.get("eval_case_id") != eval_case_id
                    or not existing.get("valid_scientific_result")
                    or existing.get("paired_manifest_sha256") != spec_hash
                    or existing.get("checkpoint_sha256") != checkpoint_record["sha256"]
                ):
                    raise ValueError(f"Existing scientific result is invalid: {result_path}")
                results.append(existing)
                continue
            result = run_case(
                sim,
                policy,
                args.participant,
                case,
                args,
                checkpoint_record,
                spec_hash,
                participant_dir,
            )
            write_json_exclusive(result_path, result)
            results.append(result)
            print(
                f"participant={args.participant} case={eval_case_id} success={result['success']} "
                f"termination={result['termination_reason']} target_error={result['target_xy_error']:.5f} "
                f"tilt={result['final_cylinder_tilt_degrees']:.3f}",
                flush=True,
            )
    finally:
        sim.close_video()
        if sim.client is not None:
            pb.disconnect(sim.client)
    if len(results) != 10 or {row["eval_case_id"] for row in results} != set(range(10)):
        raise RuntimeError("Participant did not produce exactly one valid result per paired spec")
    summary = {
        "schema_version": 1,
        "group": GROUP,
        "participant_id": args.participant,
        "participant_route": "L" if int(args.participant[1:]) <= 5 else "R",
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "device": device,
        "checkpoint": str(checkpoint.resolve()),
        "checkpoint_sha256": checkpoint_record["sha256"],
        "paired_manifest": str(args.spec_manifest.resolve()),
        "paired_manifest_sha256": spec_hash,
        "protocol": {
            "horizon": args.horizon,
            "sample_hz": args.sample_hz,
            "action_gap": args.action_gap,
            "action_dt": args.action_dt,
            "num_points": args.num_points,
            "settle_seconds": args.settle_seconds,
            "policy_boundary": "policy_inference_start after validated common scripted grasp/lift",
            "scripted_transport_used": False,
        },
        "valid_rollout_count": 10,
        "success_count": sum(int(row["success"]) for row in results),
        "edsr": sum(int(row["success"]) for row in results) / 10.0,
        "rollouts": results,
    }
    write_json_exclusive(summary_path, summary)
    print(json.dumps({"participant": args.participant, "success_count": summary["success_count"], "edsr": summary["edsr"]}, indent=2))


if __name__ == "__main__":
    main()
