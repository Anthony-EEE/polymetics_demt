#!/usr/bin/env python3
"""Freeze ten shared, setup-feasible Target rollout specifications.

Candidate replacement is deterministic and policy-blind. The script requires
all ten trained checkpoints to have passed inference smoke, but never loads or
queries a policy while selecting evaluation starts.
"""

import argparse
import hashlib
import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pybullet as pb


GROUP = "simulation_target_group"
EVALUATION_SEED = 20260807
EXPECTED_CASES = 10
EXPECTED_RELEASE_Z = 0.08
EXAMPLES_DIR = Path(__file__).resolve().parents[1]
if str(EXAMPLES_DIR) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_DIR))

import main_obstacle_transport as task  # noqa: E402
from rebuttal_target_pipeline.target_protocol import (  # noqa: E402
    TARGET_SUCCESS_CRITERION,
    TARGET_XY_TOLERANCE,
)
from rollout_contract import stream_seed  # noqa: E402


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(payload):
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def write_json_exclusive(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=2, sort_keys=True)
        stream.write("\n")


def set_all_seeds(seed):
    np.random.seed(seed)
    random.seed(seed)
    try:
        import torch
    except ImportError:
        return
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def frozen_thresholds():
    return {
        "box_start_x_bounds": list(task.BOX_START_X_BOUNDS),
        "box_start_y_bounds": list(task.BOX_START_Y_BOUNDS),
        "box_initial_z": task.BOX_INITIAL_Z,
        "box_initial_quaternion_xyzw": [0.0, 0.0, 0.0, 1.0],
        "obstacle_xy": list(task.OBSTACLE_XY),
        "obstacle_radius": task.OBSTACLE_RADIUS,
        "obstacle_height": task.OBSTACLE_HEIGHT,
        "obstacle_initial_quaternion_xyzw": [0.0, 0.0, 0.0, 1.0],
        "target_xy": list(task.TARGET_XY),
        "target_xy_tolerance_m": TARGET_XY_TOLERANCE,
        "shared_target_xy_tolerance_m_unchanged": task.TARGET_XY_TOLERANCE,
        "cylinder_upright_tolerance_degrees": task.CYLINDER_UPRIGHT_TOLERANCE_DEGREES,
        "transport_start_height_tolerance_m": task.TRANSPORT_START_HEIGHT_TOLERANCE,
        "fixed_gripper_pitch_degrees": task.FIXED_GRIPPER_PITCH_DEGREES,
        "panda_base_position": list(task.PANDA_BASE_POSITION),
        "release_ee_z_m": float(getattr(task, "RELEASE_Z", float("nan"))),
        "success_criterion": TARGET_SUCCESS_CRITERION,
        "success_protocol_scope": GROUP,
        "contacts_are_diagnostic_only": True,
    }


def candidate_spec(eval_seed, candidate_index):
    candidate_seed = stream_seed(eval_seed, candidate_index, 0x53504543)
    rng = np.random.default_rng(candidate_seed)
    # Route is a sampling placeholder only. No route waypoint or scripted
    # transport is used by learned-policy rollout; setup uses only box start
    # and sampled transport height.
    spec = task.sample_task_spec(rng, "L", candidate_index)
    spec.update(
        {
            "group": GROUP,
            "candidate_index": candidate_index,
            "candidate_seed": candidate_seed,
            "route_waypoint_used_during_rollout": False,
            "scripted_transport_used_during_rollout": False,
            "box_initial_quaternion_xyzw": [0.0, 0.0, 0.0, 1.0],
        }
    )
    return spec


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=EVALUATION_SEED)
    parser.add_argument("--max-candidates", type=int, default=1000)
    parser.add_argument("--sample-hz", type=float, default=8.0)
    parser.add_argument("--playback-speed", type=float, default=1000.0)
    args = parser.parse_args()
    if args.seed != EVALUATION_SEED:
        raise ValueError(f"Evaluation seed is frozen to {EVALUATION_SEED}")
    if args.output.exists() or args.output.with_suffix(".sha256.json").exists():
        raise FileExistsError("Refusing to overwrite a frozen rollout manifest or hash sidecar")
    release_z = getattr(task, "RELEASE_Z", None)
    if release_z is None or not np.isclose(float(release_z), EXPECTED_RELEASE_Z):
        raise RuntimeError(
            "Shared release-height protocol is not the approved RELEASE_Z=0.08 revision; "
            "SCR-001 must be approved and applied before freezing evaluation specs"
        )
    model_validation_path = args.models_root.resolve() / "model_validation_report.json"
    checkpoint_manifest_path = args.models_root.resolve() / "selected_checkpoints_manifest.json"
    for required in (model_validation_path, checkpoint_manifest_path):
        if not required.is_file():
            raise FileNotFoundError(required)
    model_validation = json.loads(model_validation_path.read_text(encoding="utf-8"))
    checkpoints = json.loads(checkpoint_manifest_path.read_text(encoding="utf-8"))
    if not model_validation.get("passed") or model_validation.get("checkpoint_count") != 10:
        raise ValueError("Ten checkpoints have not passed load/inference smoke")
    if checkpoints.get("participant_order") != [f"T{i:02d}" for i in range(1, 11)]:
        raise ValueError("Checkpoint manifest participant order is invalid")

    accepted = []
    rejected = []
    candidate_index = 0
    sim = task.ObstacleTransportSim(gui=False, output_dir=None, sample_hz=args.sample_hz)
    sim.playback_speed = args.playback_speed
    sim.setup()
    try:
        while len(accepted) < EXPECTED_CASES and candidate_index < args.max_candidates:
            spec = candidate_spec(args.seed, candidate_index)
            set_all_seeds(spec["candidate_seed"])
            sim.reset_task_state(spec["box_initial_position"])
            setup_success, setup_details = sim.scripted_grasp_to_transport_start(spec, save=False)
            record = {
                "candidate_index": candidate_index,
                "candidate_seed": spec["candidate_seed"],
                "spec": spec,
                "setup_preflight": {
                    "success": bool(setup_success),
                    "details": setup_details,
                },
            }
            if setup_success:
                eval_case_id = len(accepted)
                record.update(
                    {
                        "eval_case_id": eval_case_id,
                        "evaluation_seed": args.seed,
                        "runtime_seed": stream_seed(args.seed, eval_case_id, 0x52554E),
                        "point_cloud_seed": stream_seed(args.seed, eval_case_id, 0x504344),
                    }
                )
                accepted.append(record)
            else:
                rejected.append(record)
            candidate_index += 1
    finally:
        if sim.client is not None:
            pb.disconnect(sim.client)
    if len(accepted) != EXPECTED_CASES:
        raise RuntimeError(
            f"Only found {len(accepted)}/{EXPECTED_CASES} setup-feasible starts after "
            f"{candidate_index} deterministic candidates"
        )
    positions = [tuple(row["spec"]["box_initial_position"]) for row in accepted]
    if len(set(positions)) != EXPECTED_CASES:
        raise RuntimeError("Accepted rollout specs do not have ten distinct cube positions")
    for row in accepted:
        box = row["spec"]["box_initial_position"]
        initial_ee = row["spec"]["scripted_ee_initial_position"]
        expected = [box[0], box[1], box[2] + 0.10]
        if not np.array_equal(np.asarray(initial_ee), np.asarray(expected)):
            raise RuntimeError("Scripted EE initial pose violates the exact x/y-aligned +0.10 rule")
        if not np.isclose(row["spec"]["release_pose"][2], EXPECTED_RELEASE_Z):
            raise RuntimeError("Sampled spec does not use the approved fixed release height")

    shared_task_path = Path(task.__file__).resolve()
    manifest = {
        "schema_version": 1,
        "group": GROUP,
        "status": "FROZEN_BEFORE_FORMAL_POLICY_ROLLOUT",
        "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
        "evaluation_seed": args.seed,
        "eval_case_count": EXPECTED_CASES,
        "candidate_generation": {
            "candidate_seed_rule": "SeedSequence([evaluation_seed, candidate_index, 0x53504543])",
            "deterministic_replenishment_rule": (
                "scan candidate_index from zero; accept iff common scripted grasp/lift preflight passes; "
                "continue until ten distinct accepted cube starts"
            ),
            "policy_blind": True,
            "candidate_count_examined": candidate_index,
            "rejected_candidate_count": len(rejected),
        },
        "rng_streams": {
            "runtime_seed_rule": "SeedSequence([evaluation_seed, eval_case_id, 0x52554E])",
            "point_cloud_seed_rule": "SeedSequence([evaluation_seed, eval_case_id, 0x504344])",
        },
        "simulator_execution": {
            "sample_hz": float(args.sample_hz),
            "playback_speed": float(args.playback_speed),
            "gui": False,
            "renderer": "PyBullet TinyRenderer through frozen shared task implementation",
            "all_stochastic_streams_are_explicit_per_case": True,
        },
        "frozen_task": frozen_thresholds(),
        "eval_cases": accepted,
        "rejected_candidates": rejected,
        "paired_contract": {
            "same_ten_specs_for_every_target_policy": True,
            "same_start_geometry_can_be_reused_by_control": True,
            "target_success_threshold_is_target_only": True,
            "control_protocol_was_not_modified": True,
            "policy_inference_boundary": "after validated scripted fixed-orientation grasp and lift",
            "policy_responsibility": "obstacle avoidance, transport, release",
        },
        "checkpoint_gate": {
            "model_validation_report": str(model_validation_path),
            "model_validation_report_sha256": sha256(model_validation_path),
            "selected_checkpoints_manifest": str(checkpoint_manifest_path),
            "selected_checkpoints_manifest_sha256": sha256(checkpoint_manifest_path),
        },
        "software": {
            "shared_task_path": str(shared_task_path),
            "shared_task_sha256": sha256(shared_task_path),
            "generator_path": str(Path(__file__).resolve()),
            "generator_sha256": sha256(Path(__file__).resolve()),
            "target_protocol_path": str(Path(__file__).resolve().parent / "target_protocol.py"),
            "target_protocol_sha256": sha256(Path(__file__).resolve().parent / "target_protocol.py"),
        },
    }
    manifest["canonical_content_sha256"] = canonical_hash(manifest)
    write_json_exclusive(args.output, manifest)
    sidecar = {
        "group": GROUP,
        "manifest": str(args.output.resolve()),
        "file_sha256": sha256(args.output),
        "canonical_content_sha256": manifest["canonical_content_sha256"],
    }
    write_json_exclusive(args.output.with_suffix(".sha256.json"), sidecar)
    print(json.dumps({"manifest": str(args.output), "sha256": sidecar["file_sha256"], "accepted": 10, "rejected": len(rejected)}, indent=2))


if __name__ == "__main__":
    main()
