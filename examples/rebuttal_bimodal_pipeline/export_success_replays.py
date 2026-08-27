#!/usr/bin/env python3
"""Reproduce one successful Bimodal-Target L/R rollout and export joint CSVs.

The formal rollout JSONs contain task-space traces, but not dense arm/gripper
states. This tool deterministically selects one successful realised L route and
one successful realised R route, re-executes the frozen policy/spec/repeat, and
records actual PyBullet joint states in the intervention.csv schema.
"""

from __future__ import annotations

import argparse
import csv
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


REPO = Path(__file__).resolve().parents[2]
EXAMPLES_DIR = REPO / "examples"
ARCAP_ROOT = Path("/users/k23114984/code/arcap_policy/STEP2_train_policy")
for extra in (EXAMPLES_DIR, ARCAP_ROOT):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

import main_obstacle_transport as task  # noqa: E402
from rebuttal_bimodal_pipeline.bimodal_protocol import (  # noqa: E402
    BIMODAL_SUCCESS_CRITERION,
    BIMODAL_XY_TOLERANCE,
    BimodalObstacleTransportSim,
)
from rebuttal_bimodal_pipeline.evaluate_bimodal_policy import (  # noqa: E402
    FROZEN_SPEC_SHA256,
    GROUP,
    PARTICIPANTS,
    TARGET_GROUP,
    apply_policy_action,
    canonical_hash,
    current_obs,
    load_json,
    load_policy,
    policy_sampling_seed,
    route_behavior,
    set_all_seeds,
    sha256,
    stacked_obs,
    trace_snapshot,
)


DEFAULT_SELECTION_SEED = 20260809
CSV_FIELDS = [
    "t",
    "dt",
    "step",
    "state_seq",
    "control_mode",
    "drive_mode",
    "gripper_cmd",
    "gripper_width",
    "q0",
    "q1",
    "q2",
    "q3",
    "q4",
    "q5",
    "q6",
]
ANALYSIS_CSV = (
    REPO
    / "rebuttal_dataset/simulation_bimodal_group/analysis/rollout_results.csv"
)
CHECKPOINT_MANIFEST = (
    REPO
    / "rebuttal_dataset/simulation_bimodal_group/models/selected_checkpoints_manifest.json"
)
SPEC_MANIFEST = (
    REPO
    / "rebuttal_dataset/simulation_target_group/analysis/paired_rollout_specs.json"
)
FORMAL_ROLLOUT_ROOT = (
    REPO / "rebuttal_dataset/simulation_bimodal_group/policy_rollouts"
)
# Optional adapter hook for protocols whose formal evaluator ran all cases in
# one persistent simulator.  The Target-Bimodal exporter leaves this disabled.
PRE_REPRODUCTION_HOOK = None


class ReproductionOutcomeDiverged(RuntimeError):
    """A formal success reran cleanly but did not reproduce success and route."""

    def __init__(self, message, result):
        super().__init__(message)
        self.result = result


def successful_lr_rows(path: Path = ANALYSIS_CSV):
    with Path(path).open("r", encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    selected = {
        route: [
            row
            for row in rows
            if row["success"] == "1" and row["realised_route"] == route
        ]
        for route in ("L", "R")
    }
    if not selected["L"] or not selected["R"]:
        raise RuntimeError("Formal analysis does not contain successful L and R rollouts")
    return selected


def select_successes(successes, seed):
    """Select in stable L-then-R order with one reproducible RNG stream."""

    rng = random.Random(int(seed))
    return {route: dict(rng.choice(successes[route])) for route in ("L", "R")}


def ordered_success_candidates(successes, seed):
    """Put the original random choices first, then deterministically shuffle fallbacks."""

    rng = random.Random(int(seed))
    first = {route: rng.choice(successes[route]) for route in ("L", "R")}
    orders = {}
    for route in ("L", "R"):
        remaining = [row for row in successes[route] if row is not first[route]]
        rng.shuffle(remaining)
        orders[route] = [dict(first[route])] + [dict(row) for row in remaining]
    return orders


def formal_result_path(row):
    return FORMAL_ROLLOUT_ROOT / row["participant_id"] / "rollouts" / (
        f"rollout_case_{int(row['eval_case_id']):02d}_repeat_"
        f"{int(row['repeat_index'])}.json"
    )


def validate_selected_formal_result(route, row, checkpoint_record, spec_hash):
    path = formal_result_path(row)
    result = load_json(path)
    expected_seed = policy_sampling_seed(
        row["participant_id"], int(row["eval_case_id"]), int(row["repeat_index"])
    )
    checks = {
        "group": result.get("group") == GROUP,
        "participant": result.get("participant_id") == row["participant_id"],
        "case": result.get("eval_case_id") == int(row["eval_case_id"]),
        "repeat": result.get("repeat_index") == int(row["repeat_index"]),
        "sampling_seed": result.get("policy_sampling_seed") == expected_seed,
        "valid": result.get("valid_scientific_result") is True,
        "success": result.get("success") is True,
        "route": result.get("route_behavior", {}).get("realised_route") == route,
        "spec_hash": result.get("paired_manifest_sha256") == spec_hash,
        "checkpoint_hash": result.get("checkpoint_sha256")
        == checkpoint_record["sha256"],
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError(f"Selected formal result failed checks {failed}: {path}")
    return path, result


class JointTrajectoryRecordingSim(BimodalObstacleTransportSim):
    """Bimodal simulator that samples actual joints at a fixed simulation rate."""

    def __init__(self, *args, record_hz=30.0, **kwargs):
        self.record_hz = float(record_hz)
        self._record_stride = None
        self._recording_armed = False
        self._recording = False
        self._record_start_sim_step = None
        self._next_record_offset = None
        self._last_recorded_sim_step = None
        self._commanded_gripper_state = -1.0
        self.joint_rows = []
        super().__init__(*args, **kwargs)
        stride = float(self.control_hz) / self.record_hz
        if not math.isclose(stride, round(stride), rel_tol=0.0, abs_tol=1e-12):
            raise ValueError(
                f"record_hz={self.record_hz} must divide control_hz={self.control_hz}"
            )
        self._record_stride = int(round(stride))

    def _apply_gripper(self, width, force=60, max_vel=0.08):
        finger_width = float(np.clip(width, 0.0, 0.04))
        # Evaluator convention: -1=open (0.04 m per finger), +1=closed.
        self._commanded_gripper_state = float(
            np.clip(1.0 - finger_width / 0.02, -1.0, 1.0)
        )
        return super()._apply_gripper(finger_width, force=force, max_vel=max_vel)

    def arm_recording_at_scripted_initial_pose(self):
        if self._recording or self._recording_armed:
            raise RuntimeError("Joint recording has already been armed")
        self._recording_armed = True

    def reset_to_ee_pose(self, q, gripper_width=0.04):
        super().reset_to_ee_pose(q, gripper_width=gripper_width)
        if self._recording_armed:
            self._recording_armed = False
            self._recording = True
            self._record_start_sim_step = int(self._sim_step_count)
            self._next_record_offset = self._record_stride
            self._capture_joint_row()

    def _step_simulation(self, sleep_dt):
        super()._step_simulation(sleep_dt)
        if not self._recording:
            return
        offset = int(self._sim_step_count) - int(self._record_start_sim_step)
        if offset >= self._next_record_offset:
            self._capture_joint_row()
            self._next_record_offset += self._record_stride

    def _capture_joint_row(self):
        sim_step = int(self._sim_step_count)
        if self._last_recorded_sim_step == sim_step:
            return
        elapsed = (
            sim_step - int(self._record_start_sim_step)
        ) / float(self.control_hz)
        previous_t = float(self.joint_rows[-1]["t"]) if self.joint_rows else elapsed
        arm_q = [
            float(pb.getJointState(self.panda, joint)[0])
            for joint in self.arm_joint_indices
        ]
        gripper_width = sum(
            float(pb.getJointState(self.panda, joint)[0])
            for joint in (self.left_finger_joint, self.right_finger_joint)
        )
        sequence = len(self.joint_rows)
        row = {
            "t": float(elapsed),
            "dt": 0.0 if sequence == 0 else float(elapsed - previous_t),
            "step": sequence,
            "state_seq": sequence,
            "control_mode": "takeover",
            "drive_mode": "cartesian_freedrive",
            "gripper_cmd": float(self._commanded_gripper_state),
            "gripper_width": float(gripper_width),
        }
        row.update({f"q{index}": value for index, value in enumerate(arm_q)})
        self.joint_rows.append(row)
        self._last_recorded_sim_step = sim_step

    def finish_recording(self):
        if not self._recording:
            raise RuntimeError("Joint recording never reached the scripted initial pose")
        self._capture_joint_row()
        self._recording = False
        return list(self.joint_rows)


def validate_manifests():
    checkpoint_manifest = load_json(CHECKPOINT_MANIFEST)
    spec_manifest = load_json(SPEC_MANIFEST)
    spec_hash = sha256(SPEC_MANIFEST)
    sidecar = load_json(SPEC_MANIFEST.with_suffix(".sha256.json"))
    canonical = dict(spec_manifest)
    claimed_canonical = canonical.pop("canonical_content_sha256", None)
    if spec_hash != FROZEN_SPEC_SHA256:
        raise ValueError("Frozen Target paired rollout manifest file hash changed")
    if sidecar.get("file_sha256") != spec_hash:
        raise ValueError("Frozen Target paired rollout sidecar hash mismatch")
    if canonical_hash(canonical) != claimed_canonical:
        raise ValueError("Frozen Target paired rollout canonical hash mismatch")
    if spec_manifest.get("group") != TARGET_GROUP:
        raise ValueError("Unexpected paired rollout group")
    if len(spec_manifest.get("eval_cases", [])) != 10:
        raise ValueError("Expected ten frozen evaluation cases")
    if checkpoint_manifest.get("group") != GROUP:
        raise ValueError("Unexpected checkpoint group")
    if checkpoint_manifest.get("participant_order") != PARTICIPANTS:
        raise ValueError("Unexpected Bimodal checkpoint participant order")
    frozen_task = spec_manifest.get("frozen_task", {})
    if (
        frozen_task.get("target_xy_tolerance_m") != BIMODAL_XY_TOLERANCE
        or frozen_task.get("success_criterion") != BIMODAL_SUCCESS_CRITERION
    ):
        raise ValueError("Frozen success protocol differs from replay protocol")
    return checkpoint_manifest, spec_manifest, spec_hash


def write_csv(path, rows, fieldnames=CSV_FIELDS):
    path = Path(path)
    if path.exists() or path.is_symlink():
        raise FileExistsError(f"Refusing to overwrite CSV: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
        stream.flush()
        os.fsync(stream.fileno())


def write_json(path, payload):
    path = Path(path)
    if path.exists() or path.is_symlink():
        raise FileExistsError(f"Refusing to overwrite JSON: {path}")
    with path.open("x", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def inventory_rows(successes):
    rows = []
    for route in ("L", "R"):
        for row in successes[route]:
            rows.append(
                {
                    "realised_route": route,
                    "participant_id": row["participant_id"],
                    "eval_case_id": int(row["eval_case_id"]),
                    "repeat_index": int(row["repeat_index"]),
                    "policy_sampling_seed": int(row["policy_sampling_seed"]),
                    "termination_reason": row["termination_reason"],
                    "target_xy_error": float(row["target_xy_error"]),
                    "video_path": row["video_path"],
                    "formal_result_path": str(formal_result_path(row).resolve()),
                }
            )
    return rows


def reproduce_one(
    route,
    selected_row,
    checkpoint_manifest,
    spec_manifest,
    spec_hash,
    case_dir,
    args,
):
    participant = selected_row["participant_id"]
    eval_case_id = int(selected_row["eval_case_id"])
    repeat_index = int(selected_row["repeat_index"])
    checkpoint_record = checkpoint_manifest["checkpoints"][participant]
    checkpoint = Path(checkpoint_record["checkpoint"])
    if checkpoint_record.get("selected_epoch") != 40:
        raise ValueError(f"{participant} checkpoint is not epoch 40")
    if sha256(checkpoint) != checkpoint_record["sha256"]:
        raise ValueError(f"{participant} checkpoint hash mismatch")
    original_path, original = validate_selected_formal_result(
        route, selected_row, checkpoint_record, spec_hash
    )
    case = next(
        row
        for row in spec_manifest["eval_cases"]
        if int(row["eval_case_id"]) == eval_case_id
    )
    if case != original["paired_spec"]:
        raise ValueError(f"Embedded paired spec differs for {original_path}")

    policy, device = load_policy(checkpoint, args.cuda)
    sim = JointTrajectoryRecordingSim(
        gui=False, output_dir=None, sample_hz=args.sample_hz, record_hz=args.record_hz
    )
    sim.playback_speed = args.playback_speed
    sim.setup()
    if PRE_REPRODUCTION_HOOK is not None:
        PRE_REPRODUCTION_HOOK(
            policy=policy,
            sim=sim,
            participant=participant,
            selected_eval_case_id=eval_case_id,
            selected_repeat_index=repeat_index,
            checkpoint_record=checkpoint_record,
            spec_manifest=spec_manifest,
            spec_hash=spec_hash,
            args=args,
            case_dir=case_dir,
        )
    video_path = case_dir / "reproduction.mp4"
    trace = []
    success = False
    success_details = None
    termination_reason = "policy_timeout"
    policy_call_count = 0
    policy_start_row = None
    try:
        set_all_seeds(case["runtime_seed"])
        sim.reset_task_state(case["spec"]["box_initial_position"])
        if args.save_videos:
            sim.start_video(video_path, fps=args.video_fps)
        sim.arm_recording_at_scripted_initial_pose()
        setup_success, setup_details = sim.scripted_grasp_to_transport_start(
            case["spec"], save=False
        )
        if not setup_success:
            raise RuntimeError(
                f"paired_spec_scripted_setup_failed:{setup_details.get('reason')}"
            )
        policy_start_row = len(sim.joint_rows) - 1
        set_all_seeds(policy_sampling_seed(participant, eval_case_id, repeat_index))
        policy.start_episode()
        pointcloud_rng = np.random.default_rng(case["point_cloud_seed"])
        observation_horizon = int(
            policy.policy.global_config.algo.horizon.observation_horizon
        )
        first_obs = current_obs(sim, 1.0, args.num_points, pointcloud_rng)
        history = deque(
            [first_obs] * observation_horizon, maxlen=observation_horizon
        )
        gripper_state = 1.0
        trace = [trace_snapshot(sim, 0, gripper_state)]
        last_action = None
        for step in range(args.horizon):
            action = policy(ob=stacked_obs(history))
            policy_call_count += 1
            gripper_state, last_action = apply_policy_action(
                sim, action, args.action_dt
            )
            history.append(
                current_obs(sim, gripper_state, args.num_points, pointcloud_rng)
            )
            trace.append(trace_snapshot(sim, step + 1, gripper_state))
            success, success_details = sim.transport_success()
            if success:
                termination_reason = "success"
                break
        if termination_reason == "policy_timeout" and last_action is not None:
            gripper_state, _ = apply_policy_action(
                sim, last_action, args.settle_seconds
            )
            trace.append(trace_snapshot(sim, len(trace), gripper_state))
            success, success_details = sim.transport_success()
            if success:
                termination_reason = "success_after_settle"
        if success_details is None:
            _, success_details = sim.transport_success()
        joint_rows = sim.finish_recording()
    finally:
        sim.close_video()
        if sim.client is not None:
            pb.disconnect(sim.client)

    reproduced_route = route_behavior(trace)["realised_route"]
    intervention_path = case_dir / "intervention.csv"
    write_csv(intervention_path, joint_rows)
    result = {
        "participant_id": participant,
        "eval_case_id": eval_case_id,
        "repeat_index": repeat_index,
        "policy_sampling_seed": policy_sampling_seed(
            participant, eval_case_id, repeat_index
        ),
        "expected_route": route,
        "reproduced_route": reproduced_route,
        "original_success": True,
        "reproduced_success": bool(success),
        "original_termination_reason": original["termination_reason"],
        "reproduced_termination_reason": termination_reason,
        "original_policy_steps": int(original["policy_steps"]),
        "reproduced_policy_steps": int(policy_call_count),
        "original_target_xy_error": float(original["target_xy_error"]),
        "reproduced_target_xy_error": float(success_details["target_xy_error"]),
        "outcome_reproduced": bool(success and reproduced_route == route),
        "joint_record_hz": float(args.record_hz),
        "joint_row_count": len(joint_rows),
        "duration_seconds": float(joint_rows[-1]["t"]),
        "policy_start_row": int(policy_start_row),
        "intervention_csv_relative_to_export_root": f"{route}/intervention.csv",
        "intervention_csv_sha256": sha256(intervention_path),
        "reproduction_video_relative_to_export_root": (
            f"{route}/reproduction.mp4" if args.save_videos else None
        ),
        "original_result": str(original_path.resolve()),
        "original_result_sha256": sha256(original_path),
        "original_video": original["video_path"],
        "checkpoint": str(checkpoint.resolve()),
        "checkpoint_sha256": checkpoint_record["sha256"],
        "paired_manifest_sha256": spec_hash,
        "device": device,
        "box_initial_position": case["spec"]["box_initial_position"],
        "csv_schema": CSV_FIELDS,
        "gripper_width_semantics": (
            "measured sum of the two PyBullet finger-joint positions; "
            "approximately 0.08 m open and 0.0 m closed"
        ),
        "gripper_cmd_semantics": "evaluator convention: -1=open, +1=closed",
        "trajectory_scope": (
            "scripted initial EE pose through grasp/lift and learned policy "
            "transport/release until the frozen success test passes"
        ),
    }
    write_json(case_dir / "reproduction.json", result)
    if not success or reproduced_route != route:
        raise ReproductionOutcomeDiverged(
            f"Reproduction diverged for {participant}/case{eval_case_id}/repeat{repeat_index}: "
            f"expected successful {route}, got success={success}, route={reproduced_route}",
            result,
        )
    return result


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection-seed", type=int, default=DEFAULT_SELECTION_SEED)
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--record-hz", type=float, default=30.0)
    parser.add_argument("--sample-hz", type=float, default=8.0)
    parser.add_argument("--horizon", type=int, default=200)
    parser.add_argument("--action-gap", type=int, default=2)
    parser.add_argument("--action-dt", type=float, default=0.25)
    parser.add_argument("--num-points", type=int, default=10000)
    parser.add_argument("--settle-seconds", type=float, default=1.5)
    parser.add_argument("--playback-speed", type=float, default=1000.0)
    parser.add_argument("--video-fps", type=int, default=10)
    parser.add_argument("--save-videos", action="store_true")
    parser.add_argument("--cuda", action="store_true")
    parser.add_argument(
        "--selection-only",
        action="store_true",
        help="Write the inventory/selection manifest without loading policies.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    if args.horizon != 200 or args.sample_hz != 8.0 or args.action_gap != 2:
        raise ValueError("Frozen rollout requires horizon=200, sample_hz=8, action_gap=2")
    if not math.isclose(args.action_dt, 0.25) or not math.isclose(
        args.settle_seconds, 1.5
    ):
        raise ValueError("Frozen rollout requires action_dt=0.25, settle_seconds=1.5")
    if args.num_points != 10000:
        raise ValueError("Frozen rollout requires 10,000 point-cloud points")
    if args.output_root is None:
        args.output_root = (
            REPO / "bimodal_target_replays" / f"seed_{args.selection_seed}"
        )
    output_root = args.output_root.resolve()
    if output_root.exists() or output_root.is_symlink():
        raise FileExistsError(f"Refusing to overwrite replay export: {output_root}")
    output_root.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_root.with_name(f".{output_root.name}.inprogress.{os.getpid()}")
    if temporary.exists() or temporary.is_symlink():
        raise FileExistsError(f"Stale replay export temporary exists: {temporary}")
    temporary.mkdir()

    try:
        successes = successful_lr_rows()
        candidate_orders = ordered_success_candidates(successes, args.selection_seed)
        selected = {route: candidate_orders[route][0] for route in ("L", "R")}
        inventory = inventory_rows(successes)
        inventory_fields = list(inventory[0])
        write_csv(temporary / "successful_lr_cases.csv", inventory, inventory_fields)
        selection = {
            "selection_seed": args.selection_seed,
            "selection_algorithm": (
                "random.Random(seed), one choice from formal successful rows in "
                "stable analysis CSV order for L then R"
            ),
            "fallback_algorithm": (
                "if a clean rerun does not reproduce both success and route, try "
                "the remaining formal successes in a deterministic shuffled order"
            ),
            "successful_counts": {
                route: len(successes[route]) for route in ("L", "R")
            },
            "selected": {
                route: {
                    key: selected[route][key]
                    for key in (
                        "participant_id",
                        "eval_case_id",
                        "repeat_index",
                        "policy_sampling_seed",
                        "realised_route",
                        "target_xy_error",
                        "video_path",
                    )
                }
                for route in ("L", "R")
            },
        }
        write_json(temporary / "selection.json", selection)
        if args.selection_only:
            os.replace(temporary, output_root)
            print(json.dumps(selection, indent=2, sort_keys=True))
            return

        checkpoint_manifest, spec_manifest, spec_hash = validate_manifests()
        reproductions = {}
        divergences = {"L": [], "R": []}
        for route in ("L", "R"):
            for attempt_index, candidate in enumerate(candidate_orders[route]):
                case_dir = temporary / route
                case_dir.mkdir()
                try:
                    reproductions[route] = reproduce_one(
                        route,
                        candidate,
                        checkpoint_manifest,
                        spec_manifest,
                        spec_hash,
                        case_dir,
                        args,
                    )
                    break
                except ReproductionOutcomeDiverged as exc:
                    failed_dir = (
                        temporary
                        / "diverged_reproductions"
                        / route
                        / f"attempt_{attempt_index:02d}_{candidate['participant_id']}_"
                        f"case_{int(candidate['eval_case_id']):02d}_repeat_"
                        f"{int(candidate['repeat_index'])}"
                    )
                    failed_dir.parent.mkdir(parents=True, exist_ok=True)
                    os.replace(case_dir, failed_dir)
                    divergence = dict(exc.result)
                    divergence["diagnostic_directory_relative_to_export_root"] = str(
                        failed_dir.relative_to(temporary)
                    )
                    divergences[route].append(divergence)
                    print(str(exc), flush=True)
            else:
                raise RuntimeError(f"No formal successful {route} case reproduced")
            print(
                f"route={route} participant={reproductions[route]['participant_id']} "
                f"case={reproductions[route]['eval_case_id']} "
                f"repeat={reproductions[route]['repeat_index']} "
                f"rows={reproductions[route]['joint_row_count']} "
                f"duration={reproductions[route]['duration_seconds']:.3f}s",
                flush=True,
            )
        manifest = {
            "schema_version": 1,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "group": GROUP,
            "purpose": "joint-and-gripper replay export from successful Bimodal-Target rollouts",
            "selection": selection,
            "reproductions": reproductions,
            "diverged_reproductions_before_success": divergences,
            "root_intervention_csv_preserved": str((REPO / "intervention.csv").resolve()),
            "usage": (
                "Use L/intervention.csv or R/intervention.csv as ./intervention.csv "
                "for one replay at a time."
            ),
        }
        write_json(temporary / "manifest.json", manifest)
        os.replace(temporary, output_root)
        print(json.dumps(manifest, indent=2, sort_keys=True))
    except Exception:
        print(f"Replay export failed; partial diagnostics retained at {temporary}", file=sys.stderr)
        raise


if __name__ == "__main__":
    main()
