#!/usr/bin/env python3
import argparse
import json
import math
import os
import random
from collections import deque
from pathlib import Path

import numpy as np
import pybullet as pb

from eval_abla1_trained_policies import (
    RolloutVideoRecorder,
    apply_policy_action,
    current_obs,
    load_policy,
    render_rgb,
    reset_cube,
    set_all_seeds,
    stack_obs_history,
)
from main_orn_mvp import ORN_CONDITIONS, OrientationMvpSim
from rollout_contract import (
    checkpoints_from_manifest,
    condition_rollout_statistics,
    file_sha256,
    load_json,
    paired_discordances,
    stream_seed,
    validate_rollout_files,
    write_json,
)


DEFAULT_MODEL_ROOT = Path("/scratch/prj/eng_demt_robot_learning/trained_models")
DEFAULT_OUTPUT = Path("/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/orn_mvp_full/policy_rollouts_seed628_paired_n50_h200")
DEFAULT_VIDEO_DIR = DEFAULT_OUTPUT / "videos"
CONDITION_ORDER = ("R00", "R15", "R30")


def evaluation_protocol(args):
    return {
        "seed": int(args.seed),
        "num_rollouts": int(args.num_rollouts),
        "horizon": int(args.horizon),
        "sample_hz": float(args.sample_hz),
        "action_gap": int(args.action_gap),
        "action_dt": float(args.action_dt),
        "terminate_on_success": bool(args.terminate_on_success),
        "success_lift_height": float(args.success_lift_height),
        "num_points": int(args.num_points),
        "random_start_bounds": {
            "x": [float(args.random_start_x_min), float(args.random_start_x_max)],
            "y": [0.0, 0.0],
            "z": [float(args.random_start_z_min), float(args.random_start_z_max)],
        },
        "evaluation_distribution": "paired_reachable_random_starts_common_axis_uniform_and_rng",
        "orientation_mapping": "angle_degrees=(2*u-1)*orientation_max_degrees; one orientation for entire trajectory",
        "rng_protocol": "independent spatial/axis/scalar/runtime/point-cloud streams; Python, NumPy, Torch and CUDA reset per rollout",
    }


def latest_checkpoint(model_root, condition, epoch):
    exp_root = Path(model_root) / f"orn_mvp_{condition}_d30_seed1_2gap"
    run_dirs = [p for p in exp_root.iterdir() if p.is_dir()]
    if not run_dirs:
        raise FileNotFoundError(f"No run directories found under {exp_root}")
    run_dir = sorted(run_dirs)[-1]
    ckpt = run_dir / "models" / f"model_epoch_{epoch}.pth"
    if not ckpt.exists():
        candidates = sorted(
            (run_dir / "models").glob("model_epoch_*.pth"),
            key=lambda path: int(path.stem.rsplit("_", 1)[-1]),
        )
        if not candidates:
            raise FileNotFoundError(f"No checkpoints found under {run_dir / 'models'}")
        ckpt = candidates[-1]
    return ckpt


def orientation_from_latents(sim, condition, axis, common_u):
    max_degrees = float(ORN_CONDITIONS[condition])
    default_quat = sim.default_orientation_quat
    axis = np.asarray(axis, dtype=float)
    axis = axis / np.linalg.norm(axis)
    angle_degrees = (2.0 * float(common_u) - 1.0) * max_degrees
    delta_quat = pb.getQuaternionFromAxisAngle(axis.tolist(), math.radians(angle_degrees))
    _, contact_quat = pb.multiplyTransforms(
        [0.0, 0.0, 0.0],
        delta_quat,
        [0.0, 0.0, 0.0],
        default_quat,
    )
    return {
        "orientation_max_degrees": max_degrees,
        "orientation_axis": np.asarray(axis, dtype=float).tolist(),
        "common_u": float(common_u),
        "orientation_angle_degrees": float(angle_degrees),
        "orientation_delta_quat_xyzw": list(delta_quat),
        "contact_quat_xyzw": list(contact_quat),
    }


def create_paired_manifest(args):
    spatial_rng = np.random.default_rng(stream_seed(args.seed, 0, 0x53504154))
    axis_rng = np.random.default_rng(stream_seed(args.seed, 0, 0x41584953))
    scalar_rng = np.random.default_rng(stream_seed(args.seed, 0, 0x5343414C))
    rollouts = []
    sim = OrientationMvpSim(gui=False, output_dir=None, sample_hz=args.sample_hz)
    sim.playback_speed = 1000.0
    sim.setup()
    try:
        source_draw_index = 0
        while len(rollouts) < args.num_rollouts:
            if source_draw_index >= args.num_rollouts * args.random_start_max_attempts:
                raise RuntimeError("Could not generate enough all-condition IK-valid Contact candidates")
            start = np.array(
                [
                    spatial_rng.uniform(args.random_start_x_min, args.random_start_x_max),
                    0.0,
                    spatial_rng.uniform(args.random_start_z_min, args.random_start_z_max),
                ],
                dtype=float,
            )
            axis = axis_rng.normal(size=3)
            norm = float(np.linalg.norm(axis))
            if norm <= 1e-12:
                axis = np.array([0.0, 0.0, 1.0])
            else:
                axis /= norm
            common_u = float(scalar_rng.uniform(0.0, 1.0))
            candidate_index = source_draw_index
            source_draw_index += 1
            condition_orientations = {}
            valid = True
            for condition in CONDITION_ORDER:
                orientation = orientation_from_latents(sim, condition, axis, common_u)
                try:
                    resolved, _, ik_info = sim.sample_reachable_random_start_with_quat(
                        orientation["contact_quat_xyzw"],
                        x_bounds=(start[0], start[0]),
                        z_bounds=(start[2], start[2]),
                        max_attempts=1,
                    )
                except RuntimeError:
                    valid = False
                    break
                if not np.allclose(resolved, start, atol=1e-12):
                    valid = False
                    break
                orientation["manifest_start_ik_validation"] = ik_info
                condition_orientations[condition] = orientation
            if not valid:
                continue
            rollout_index = len(rollouts)
            rollouts.append(
                {
                    "rollout_index": rollout_index,
                    "source_draw_index": candidate_index,
                    "random_start": start.tolist(),
                    "orientation_axis": axis.tolist(),
                    "common_u": common_u,
                    "condition_orientations": condition_orientations,
                    "rng_seed": stream_seed(args.seed, rollout_index, 0x52554E),
                    "point_cloud_rng_seed": stream_seed(args.seed, rollout_index, 0x504344),
                }
            )
    finally:
        sim.close()
    if len({tuple(row["random_start"]) for row in rollouts}) != args.num_rollouts:
        raise RuntimeError("Contact paired manifest contains repeated starts")
    return {
        "schema_version": 2,
        "condition_order": list(CONDITION_ORDER),
        "protocol": evaluation_protocol(args),
        "rollouts": rollouts,
    }


def validate_paired_manifest(args, manifest):
    if manifest.get("condition_order") != list(CONDITION_ORDER):
        raise ValueError("Contact paired manifest condition_order is invalid")
    if manifest.get("protocol") != evaluation_protocol(args):
        raise ValueError("Contact paired manifest protocol does not exactly match evaluation arguments")
    rollouts = manifest.get("rollouts", [])
    if len(rollouts) != args.num_rollouts:
        raise ValueError(f"Contact paired manifest has {len(rollouts)} rollouts, expected {args.num_rollouts}")
    if len({tuple(row.get("random_start", [])) for row in rollouts}) != args.num_rollouts:
        raise ValueError("Contact paired manifest starts are not all distinct")
    for index, spec in enumerate(rollouts):
        if spec.get("rollout_index") != index:
            raise ValueError(f"Contact paired manifest index mismatch at {index}")
        start = spec.get("random_start", [])
        if len(start) != 3 or abs(float(start[1])) > 1e-12:
            raise ValueError(f"Contact paired manifest invalid start at {index}")
        if not (args.random_start_x_min <= start[0] <= args.random_start_x_max and args.random_start_z_min <= start[2] <= args.random_start_z_max):
            raise ValueError(f"Contact paired manifest start out of bounds at {index}")
        axis = np.asarray(spec.get("orientation_axis", []), dtype=float)
        if axis.shape != (3,) or not np.isclose(np.linalg.norm(axis), 1.0, atol=1e-10):
            raise ValueError(f"Contact paired manifest invalid axis at {index}")
        common_u = float(spec.get("common_u", -1.0))
        if not 0.0 <= common_u <= 1.0:
            raise ValueError(f"Contact paired manifest invalid common_u at {index}")
        for condition in CONDITION_ORDER:
            record = spec.get("condition_orientations", {}).get(condition, {})
            expected_angle = (2.0 * common_u - 1.0) * float(ORN_CONDITIONS[condition])
            if not np.isclose(record.get("orientation_angle_degrees"), expected_angle, atol=1e-12):
                raise ValueError(f"Contact paired manifest angle mapping mismatch: rollout {index} {condition}")
            if condition == "R00" and float(record.get("orientation_angle_degrees", math.inf)) != 0.0:
                raise ValueError(f"R00 angle must be exactly zero at rollout {index}")
            if float(record.get("manifest_start_ik_validation", {}).get("realised_error", math.inf)) > 0.025:
                raise ValueError(f"Contact manifest start not IK-valid at rollout {index} {condition}")
        if spec.get("rng_seed") != stream_seed(args.seed, index, 0x52554E):
            raise ValueError(f"Contact runtime RNG seed mismatch at {index}")
        if spec.get("point_cloud_rng_seed") != stream_seed(args.seed, index, 0x504344):
            raise ValueError(f"Contact point-cloud RNG seed mismatch at {index}")
    return rollouts


def run_one_rollout(
    sim,
    policy,
    rollout_index,
    paired_spec,
    condition,
    horizon,
    action_dt,
    success_lift_height,
    random_start_max_attempts,
    num_points,
    terminate_on_success,
    video_recorder=None,
    video_every_n_actions=2,
):
    rollout_seed = int(paired_spec["rng_seed"])
    point_cloud_rng_seed = int(paired_spec["point_cloud_rng_seed"])
    set_all_seeds(rollout_seed)
    reset_cube(sim)
    sim.reset()
    reset_cube(sim)

    orientation = paired_spec["condition_orientations"][condition]
    contact_quat = orientation["contact_quat_xyzw"]
    requested_start = np.asarray(paired_spec["random_start"], dtype=float)
    random_start, random_start_q, random_start_info = sim.sample_reachable_random_start_with_quat(
        contact_quat,
        x_bounds=(requested_start[0], requested_start[0]),
        z_bounds=(requested_start[2], requested_start[2]),
        max_attempts=1,
    )
    sim.reset_to_ee_pose(random_start_q, gripper_width=0.04)

    gripper_state = -1.0
    pcd_rng = np.random.default_rng(point_cloud_rng_seed)
    policy.start_episode()
    obs_horizon = int(policy.policy.global_config.algo.horizon.observation_horizon)
    first_obs = current_obs(sim, gripper_state, num_points=num_points, pcd_rng=pcd_rng)
    obs_history = deque([first_obs] * obs_horizon, maxlen=obs_horizon)

    angle = orientation["orientation_angle_degrees"]
    if video_recorder is not None:
        video_recorder.append(
            render_rgb(sim),
            [
                f"{condition} rollout {rollout_index:02d}",
                f"start angle={angle:.1f} deg",
            ],
        )

    for step in range(int(horizon)):
        obs = stack_obs_history(obs_history)
        action = policy(ob=obs)
        gripper_state = apply_policy_action(sim, action, action_dt=action_dt)
        obs_history.append(current_obs(sim, gripper_state, num_points=num_points, pcd_rng=pcd_rng))
        if video_recorder is not None and step % int(video_every_n_actions) == 0:
            video_recorder.append(
                render_rgb(sim),
                [
                    f"{condition} rollout {rollout_index:02d}",
                    f"step {step + 1:03d} angle={angle:.1f}",
                ],
            )
        if terminate_on_success and sim.cube_pos()[2] >= success_lift_height:
            break

    is_success, details = sim.success(min_cube_z=success_lift_height)
    if video_recorder is not None:
        video_recorder.append(
            render_rgb(sim),
            [
                f"{condition} rollout {rollout_index:02d}",
                f"success={bool(is_success)} z={details['final_cube_z']:.3f}",
            ],
        )
        video_recorder.separator()
    return {
        "condition": condition,
        "rollout_index": rollout_index,
        "paired_spec": paired_spec,
        "rng_seed": rollout_seed,
        "point_cloud_rng_seed": point_cloud_rng_seed,
        "success": bool(is_success),
        "steps": step + 1,
        "time_to_success_s": float((step + 1) * action_dt) if is_success else None,
        "random_start": random_start.tolist(),
        "random_start_info": random_start_info,
        "orientation": orientation,
        "final_cube_z": details["final_cube_z"],
        "success_details": details,
    }


def evaluate_condition(args, condition, ckpt, paired_rollouts, paired_manifest_sha256):
    policy, device = load_policy(ckpt, cuda=args.cuda)
    print(f"[{condition}] checkpoint={ckpt}")
    print(f"[{condition}] device={device}")

    set_all_seeds(args.seed)

    sim = OrientationMvpSim(gui=args.gui, output_dir=None, sample_hz=args.sample_hz)
    sim.playback_speed = args.playback_speed
    sim.video_width = int(args.video_width)
    sim.video_height = int(args.video_height)
    sim.setup()

    results = []
    video_recorder = None
    video_path = args.video_dir / f"orn_mvp_{condition}_seed{args.seed}_n{args.num_rollouts}.mp4"
    if args.save_videos:
        video_recorder = RolloutVideoRecorder(video_path, fps=args.video_fps)
        print(f"[{condition}] writing video={video_path}")
    try:
        for i in range(args.num_rollouts):
            result = run_one_rollout(
                sim=sim,
                policy=policy,
                rollout_index=i,
                paired_spec=paired_rollouts[i],
                condition=condition,
                horizon=args.horizon,
                action_dt=args.action_dt,
                success_lift_height=args.success_lift_height,
                random_start_max_attempts=args.random_start_max_attempts,
                num_points=args.num_points,
                terminate_on_success=args.terminate_on_success,
                video_recorder=video_recorder,
                video_every_n_actions=args.video_every_n_actions,
            )
            results.append(result)
            write_json(args.output_dir / "rollouts" / condition / f"rollout_{i:03d}.json", result)
            print(
                f"[{condition}] rollout {i:02d}: success={result['success']} "
                f"final_cube_z={result['final_cube_z']:.4f} "
                f"steps={result['steps']} "
                f"angle={result['orientation']['orientation_angle_degrees']:.2f} "
                f"random_start={np.round(result['random_start'], 4).tolist()}",
                flush=True,
            )
    finally:
        if video_recorder is not None:
            video_recorder.close()
        if sim.client is not None:
            pb.disconnect(sim.client)

    success_count = sum(int(r["success"]) for r in results)
    return {
        "condition": condition,
        "checkpoint": str(ckpt),
        "checkpoint_sha256": file_sha256(ckpt),
        "device": device,
        "num_rollouts": len(results),
        "success_count": success_count,
        "success_rate": success_count / max(1, len(results)),
        "condition_config": {"orientation_max_degrees": ORN_CONDITIONS[condition]},
        "protocol": evaluation_protocol(args),
        "checkpoint_manifest": str(args.checkpoint_manifest),
        "paired_manifest": str(args.paired_manifest),
        "paired_manifest_sha256": paired_manifest_sha256,
        "execution": {
            "slurm_job_id": os.environ.get("SLURM_JOB_ID"),
            "slurm_array_job_id": os.environ.get("SLURM_ARRAY_JOB_ID"),
            "slurm_array_task_id": os.environ.get("SLURM_ARRAY_TASK_ID"),
            "slurm_node_list": os.environ.get("SLURM_NODELIST"),
        },
        "evaluation_distribution": "paired_reachable_random_starts_common_axis_uniform_and_rng",
        "video_path": str(video_path) if args.save_videos else None,
        "rollouts": results,
    }


def merge_condition_summaries(args, checkpoint_manifest, paired_manifest, paired_manifest_sha256):
    if tuple(args.conditions) != CONDITION_ORDER:
        raise ValueError(f"Contact merge requires exact condition order {CONDITION_ORDER}")
    summaries = []
    realised_starts = None
    paired_specs = None
    for condition in CONDITION_ORDER:
        path = args.output_dir / f"orn_mvp_{condition}_seed{args.seed}_n{args.num_rollouts}.json"
        if not path.is_file():
            raise FileNotFoundError(f"Missing Contact condition summary: {path}")
        summary = load_json(path)
        if summary.get("condition") != condition:
            raise ValueError(f"{path} has wrong condition")
        if summary.get("protocol") != paired_manifest["protocol"]:
            raise ValueError(f"{condition} protocol differs from paired manifest")
        if summary.get("paired_manifest_sha256") != paired_manifest_sha256:
            raise ValueError(f"{condition} paired manifest hash mismatch")
        expected_checkpoint = checkpoint_manifest["checkpoints"][condition]
        if summary.get("checkpoint") != expected_checkpoint["path"] or summary.get("checkpoint_sha256") != expected_checkpoint["sha256"]:
            raise ValueError(f"{condition} checkpoint path/hash mismatch")
        rows = summary.get("rollouts", [])
        if len(rows) != args.num_rollouts:
            raise ValueError(f"{condition} has {len(rows)} rollouts, expected {args.num_rollouts}")
        validate_rollout_files(args.output_dir, condition, args.num_rollouts, rows)
        specs = [row.get("paired_spec") for row in rows]
        starts = [row.get("random_start") for row in rows]
        if specs != paired_manifest["rollouts"]:
            raise ValueError(f"{condition} paired specs differ from manifest")
        if paired_specs is None:
            paired_specs = specs
            realised_starts = starts
        elif specs != paired_specs or starts != realised_starts:
            raise ValueError(f"{condition} paired specs/realised starts differ across conditions")
        for row in rows:
            details = row.get("success_details", {})
            if details.get("criterion") != "final_cube_z >= min_cube_z" or float(details.get("min_cube_z", -1)) != args.success_lift_height:
                raise ValueError(f"{condition} has inconsistent success rule")
        summaries.append(summary)
    summary_by_condition = {summary["condition"]: summary for summary in summaries}
    aggregate = {
        **paired_manifest["protocol"],
        "condition_order": list(CONDITION_ORDER),
        "checkpoint_manifest": str(args.checkpoint_manifest),
        "checkpoint_manifest_sha256": file_sha256(args.checkpoint_manifest),
        "paired_manifest": str(args.paired_manifest),
        "paired_manifest_sha256": paired_manifest_sha256,
        "condition_statistics": {
            condition: condition_rollout_statistics(summary_by_condition[condition])
            for condition in CONDITION_ORDER
        },
        "paired_success_discordances": paired_discordances(CONDITION_ORDER, summary_by_condition),
        "summaries": [summary_by_condition[condition] for condition in CONDITION_ORDER],
    }
    aggregate_path = args.output_dir / f"summary_seed{args.seed}_n{args.num_rollouts}.json"
    write_json(aggregate_path, aggregate)
    print(f"Wrote strict Contact aggregate {aggregate_path}")
    return aggregate_path


def parse_args():
    parser = argparse.ArgumentParser(
        description="Evaluate orientation-MVP trained diffusion policies in the PyBullet cube lift task."
    )
    parser.add_argument("--model-root", type=Path, default=DEFAULT_MODEL_ROOT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--conditions", nargs="+", default=["R00", "R15", "R30"], choices=sorted(ORN_CONDITIONS))
    parser.add_argument("--epoch", type=int, default=40)
    parser.add_argument("--checkpoint-manifest", type=Path, default=None)
    parser.add_argument("--paired-manifest", type=Path, default=None)
    parser.add_argument("--write-paired-manifest", type=Path, default=None)
    parser.add_argument("--generate-paired-manifest-only", action="store_true")
    parser.add_argument("--skip-aggregate", action="store_true")
    parser.add_argument("--merge-only", action="store_true")
    parser.add_argument("--seed", type=int, default=628)
    parser.add_argument("--num-rollouts", type=int, default=50)
    parser.add_argument("--horizon", type=int, default=200)
    parser.add_argument("--sample-hz", type=float, default=8.0)
    parser.add_argument("--action-gap", type=int, default=2)
    parser.add_argument("--action-dt", type=float, default=None)
    parser.add_argument("--num-points", type=int, default=10000)
    parser.add_argument("--success-lift-height", type=float, default=0.20)
    parser.add_argument("--random-start-x-min", type=float, default=0.20)
    parser.add_argument("--random-start-x-max", type=float, default=0.60)
    parser.add_argument("--random-start-z-min", type=float, default=0.20)
    parser.add_argument("--random-start-z-max", type=float, default=0.60)
    parser.add_argument("--random-start-max-attempts", type=int, default=200)
    parser.add_argument("--playback-speed", type=float, default=100.0)
    parser.add_argument("--cuda", action="store_true", help="Use CUDA if available.")
    parser.add_argument("--gui", action="store_true")
    parser.add_argument("--terminate-on-success", action="store_true")
    parser.add_argument("--save-videos", action="store_true")
    parser.add_argument("--video-dir", type=Path, default=DEFAULT_VIDEO_DIR)
    parser.add_argument("--video-fps", type=int, default=20)
    parser.add_argument("--video-every-n-actions", type=int, default=2)
    parser.add_argument("--video-width", type=int, default=320)
    parser.add_argument("--video-height", type=int, default=320)
    return parser.parse_args()


def main():
    args = parse_args()
    if args.action_dt is None:
        args.action_dt = float(args.action_gap) / float(args.sample_hz)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    if args.save_videos:
        args.video_dir.mkdir(parents=True, exist_ok=True)

    if args.write_paired_manifest is not None:
        write_json(args.write_paired_manifest, create_paired_manifest(args))
        print(f"Wrote paired Contact manifest {args.write_paired_manifest}")
        if args.generate_paired_manifest_only:
            return
    if args.checkpoint_manifest is None or args.paired_manifest is None:
        raise ValueError("--checkpoint-manifest and --paired-manifest are required")
    checkpoint_manifest, checkpoint_paths = checkpoints_from_manifest(
        args.checkpoint_manifest, CONDITION_ORDER, args.conditions
    )
    paired_manifest = load_json(args.paired_manifest)
    paired_rollouts = validate_paired_manifest(args, paired_manifest)
    paired_manifest_sha256 = file_sha256(args.paired_manifest)
    if args.merge_only:
        merge_condition_summaries(args, checkpoint_manifest, paired_manifest, paired_manifest_sha256)
        return

    summaries = []
    for condition in args.conditions:
        ckpt = checkpoint_paths[condition]
        summary = evaluate_condition(args, condition, ckpt, paired_rollouts, paired_manifest_sha256)
        summaries.append(summary)
        out_path = args.output_dir / f"orn_mvp_{condition}_seed{args.seed}_n{args.num_rollouts}.json"
        write_json(out_path, summary)

    if not args.skip_aggregate:
        if tuple(args.conditions) != CONDITION_ORDER:
            raise ValueError("Contact aggregate requires all conditions; use --skip-aggregate for array tasks")
        aggregate_path = merge_condition_summaries(args, checkpoint_manifest, paired_manifest, paired_manifest_sha256)

    print("\nSuccess rates")
    for s in summaries:
        print(f"{s['condition']}: {s['success_count']}/{s['num_rollouts']} = {s['success_rate']:.3f}")
    if not args.skip_aggregate:
        print(f"\nWrote {aggregate_path}")


if __name__ == "__main__":
    main()
