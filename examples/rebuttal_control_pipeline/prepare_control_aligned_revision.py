#!/usr/bin/env python3
"""Freeze the Target-aligned Control configuration without collecting data."""

import argparse
import json
import os
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


EXAMPLES_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = EXAMPLES_DIR.parent
if str(EXAMPLES_DIR) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_DIR))

import main_obstacle_transport as shared_task  # noqa: E402
import main_obstacle_transport_target_participants as target_collector  # noqa: E402
from main_obstacle_transport_control_participants import (  # noqa: E402
    CONTROL_PARTICIPANTS,
    WAYPOINT_ROUTE_X_BOUNDS,
    WAYPOINT_Z_BOUNDS,
    waypoint_spread,
)
from rebuttal_control_pipeline.collect_control_aligned import (  # noqa: E402
    participant_task_spec,
    shared_cube_start,
    write_protocol_preview,
)
from rebuttal_control_pipeline.control_protocol import (  # noqa: E402
    CONTACTS_ARE_DIAGNOSTIC_ONLY,
    CYLINDER_TILT_TOLERANCE_DEGREES,
    EXPECTED_RELEASE_Z,
    FORMAL_SEED,
    GROUP,
    REVISION_ROOT_RELATIVE,
    SUCCESS_CRITERION,
    TARGET_PAIRED_ROLLOUT_MANIFEST_RELATIVE,
    TARGET_PAIRED_ROLLOUT_MANIFEST_SHA256,
    TARGET_XY_TOLERANCE,
    assert_target_aligned_dependencies,
    sha256,
)
from rebuttal_target_pipeline.target_protocol import (  # noqa: E402
    TARGET_SUCCESS_CRITERION,
    TARGET_XY_TOLERANCE as TARGET_IMPLEMENTATION_XY_TOLERANCE,
)


TARGET_FORMAL_ROOT_RELATIVE = Path(
    "rebuttal_dataset/simulation_target_group/full_seed20260806/"
    "protocol_release_z008_target_tol010_start_replenish"
)


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def load_json(path):
    with Path(path).open("r", encoding="utf-8") as stream:
        return json.load(stream)


def verify_target_contract():
    assert_target_aligned_dependencies(check_paired_manifest=True)
    require(
        TARGET_IMPLEMENTATION_XY_TOLERANCE == TARGET_XY_TOLERANCE,
        "Control and Target target-radius constants differ",
    )
    require(
        TARGET_SUCCESS_CRITERION == SUCCESS_CRITERION,
        "Control and Target success-criterion strings differ",
    )

    target_formal_root = REPO_ROOT / TARGET_FORMAL_ROOT_RELATIVE
    target_manifest_path = target_formal_root / "participant_manifest.json"
    paired_path = REPO_ROOT / TARGET_PAIRED_ROLLOUT_MANIFEST_RELATIVE
    target_manifest = load_json(target_manifest_path)
    paired = load_json(paired_path)
    require(target_manifest.get("group") == "simulation_target_group", "Wrong Target manifest group")
    require(target_manifest.get("seed") == FORMAL_SEED, "Wrong Target manifest seed")
    require(len(target_manifest.get("shared_cube_starts", [])) == 30, "Target manifest lacks 30 starts")
    require(paired.get("group") == "simulation_target_group", "Wrong paired manifest group")
    require(len(paired.get("eval_cases", [])) == 10, "Paired manifest lacks ten cases")
    frozen = paired.get("frozen_task", {})
    expected_frozen = {
        "release_ee_z_m": EXPECTED_RELEASE_Z,
        "target_xy_tolerance_m": TARGET_XY_TOLERANCE,
        "cylinder_upright_tolerance_degrees": CYLINDER_TILT_TOLERANCE_DEGREES,
        "contacts_are_diagnostic_only": CONTACTS_ARE_DIAGNOSTIC_ONLY,
        "success_criterion": SUCCESS_CRITERION,
    }
    for key, expected in expected_frozen.items():
        require(frozen.get(key) == expected, f"Paired manifest mismatch for {key}")

    for demo_index in range(30):
        attempt0 = shared_cube_start(FORMAL_SEED, demo_index, 0)
        require(
            attempt0 == target_manifest["shared_cube_starts"][demo_index],
            f"Control attempt-0 start differs from Target manifest at demo {demo_index}",
        )
        for attempt_index in range(30):
            require(
                shared_cube_start(FORMAL_SEED, demo_index, attempt_index)
                == target_collector.shared_cube_start(
                    FORMAL_SEED,
                    demo_index,
                    attempt_index,
                ),
                "Control/Target deterministic start replenishment differs at "
                f"demo={demo_index}, attempt={attempt_index}",
            )
    return target_manifest_path, paired_path


def verify_control_manipulation():
    spreads = {}
    for participant_id, participant in CONTROL_PARTICIPANTS.items():
        specs = [
            participant_task_spec(participant_id, demo_index, 0, FORMAL_SEED)
            for demo_index in range(30)
        ]
        points = np.asarray([spec["middle_waypoint"] for spec in specs], dtype=float)
        spread = waypoint_spread(points)
        spreads[participant_id] = spread
        x_low, x_high = WAYPOINT_ROUTE_X_BOUNDS[participant["route"]]
        require(np.all(points[:, 0] >= x_low), f"{participant_id} waypoint below x support")
        require(np.all(points[:, 0] <= x_high), f"{participant_id} waypoint above x support")
        require(np.all(points[:, 2] >= WAYPOINT_Z_BOUNDS[0]), f"{participant_id} waypoint below z support")
        require(np.all(points[:, 2] <= WAYPOINT_Z_BOUNDS[1]), f"{participant_id} waypoint above z support")
        require(spread["unique_count"] == 30, f"{participant_id} lacks 30 unique waypoints")
        require(spread["x_span"] >= 0.14, f"{participant_id} x spread too narrow")
        require(spread["z_span"] >= 0.07, f"{participant_id} z spread too narrow")
        for spec in specs:
            box = spec["box_initial_position"]
            require(
                spec["scripted_ee_initial_position"]
                == [box[0], box[1], box[2] + 0.10],
                f"{participant_id} initial EE rule changed",
            )
            require(spec["release_pose"] == [0.5, 0.5, 0.08], "Release pose mismatch")
            require(spec["participant_waypoint_center"] is None, "Control acquired a centre")
            require(
                spec["waypoint_sampling"]["across_demo_contraction"] is False,
                "Control acquired across-demo contraction",
            )
    return spreads


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=REPO_ROOT / REVISION_ROOT_RELATIVE,
    )
    args = parser.parse_args()
    revision_root = args.root.resolve()
    expected_root = (REPO_ROOT / REVISION_ROOT_RELATIVE).resolve()
    if revision_root != expected_root:
        raise ValueError(f"Frozen revision root must be {expected_root}")
    if revision_root.exists():
        raise FileExistsError(
            f"Refusing to overwrite/re-enter immutable revision root: {revision_root}"
        )

    target_manifest_path, paired_path = verify_target_contract()
    spreads = verify_control_manipulation()
    source_paths = {
        "historical_control_collector": EXAMPLES_DIR
        / "main_obstacle_transport_control_participants.py",
        "aligned_control_collector": Path(__file__).resolve().parent
        / "collect_control_aligned.py",
        "control_protocol": Path(__file__).resolve().parent / "control_protocol.py",
        "control_preflight": Path(__file__).resolve().parent
        / "preflight_control_aligned_candidates.py",
        "control_raw_validator": Path(__file__).resolve().parent
        / "validate_control_aligned_raw.py",
        "control_array_wrapper": Path(__file__).resolve().parent
        / "collect_control_aligned_array.sbatch",
        "shared_task": EXAMPLES_DIR / "main_obstacle_transport.py",
        "target_collector": EXAMPLES_DIR
        / "main_obstacle_transport_target_participants.py",
        "target_protocol": EXAMPLES_DIR / "rebuttal_target_pipeline/target_protocol.py",
        "target_raw_validator": EXAMPLES_DIR
        / "rebuttal_target_pipeline/validate_raw_collection.py",
        "target_participant_manifest": target_manifest_path,
        "target_paired_rollout_manifest": paired_path,
    }
    missing = [str(path) for path in source_paths.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Missing frozen source/config dependencies: {missing}")

    revision_root.parent.mkdir(parents=True, exist_ok=True)
    temporary_root = Path(
        tempfile.mkdtemp(
            prefix=f".{revision_root.name}.preparing.",
            dir=revision_root.parent,
        )
    )
    try:
        preview = write_protocol_preview(temporary_root, FORMAL_SEED)
        target_manifest = load_json(target_manifest_path)
        require(
            preview["shared_cube_starts"] == target_manifest["shared_cube_starts"],
            "Prepared attempt-0 cube starts differ from Target",
        )
        (temporary_root / "logs").mkdir()
        configuration = {
            "schema_version": 1,
            "status": "CONFIGURATION_PREPARED_AWAITING_EXPLICIT_START",
            "prepared_at_utc": datetime.now(timezone.utc).isoformat(),
            "group": GROUP,
            "seed": FORMAL_SEED,
            "revision_name": revision_root.name,
            "revision_root": str(revision_root),
            "collection_started": False,
            "collection_start_gate": "wait for explicit user instruction: 开始收集数据",
            "historical_failed_data_policy": {
                "preserve_without_overwrite": True,
                "historical_root": str(
                    (REPO_ROOT / "rebuttal_dataset/simulation_control_group/full_seed20260806").resolve()
                ),
                "historical_array_job_id": "36353493",
                "held_tasks_are_not_released_by_preparation": True,
            },
            "target_alignment": {
                "release_ee_z_m": EXPECTED_RELEASE_Z,
                "target_xy_tolerance_m": TARGET_XY_TOLERANCE,
                "cylinder_tilt_tolerance_degrees": CYLINDER_TILT_TOLERANCE_DEGREES,
                "contacts_are_diagnostic_only": CONTACTS_ARE_DIAGNOSTIC_ONLY,
                "success_criterion": SUCCESS_CRITERION,
                "broad_cube_start_bounds": {
                    "x": list(shared_task.BOX_START_X_BOUNDS),
                    "y": list(shared_task.BOX_START_Y_BOUNDS),
                    "z": shared_task.BOX_INITIAL_Z,
                },
                "deterministic_start_replenishment": (
                    "Target-identical attempt-seeded 30-point Latin-hypercube x "
                    "plus uniform y; same (demo,attempt) candidate across participants"
                ),
                "initial_ee_rule": "[box_x, box_y, box_z + 0.10]",
                "scripted_setup": "grasp/lift must validate before policy frame saving",
                "first_saved_phase": "policy_inference_start",
                "scripted_setup_saved": False,
                "dual_offset_or_cartesian_diagnostic_revision_applied": False,
            },
            "control_teaching_data_manipulation": {
                "sampling": "independent_uniform_full_route_xz_rectangle",
                "route_x_bounds": WAYPOINT_ROUTE_X_BOUNDS,
                "waypoint_y": 0.25,
                "waypoint_z_bounds": list(WAYPOINT_Z_BOUNDS),
                "personal_waypoint_centers": False,
                "across_demo_contraction": False,
                "attempt0_spread": spreads,
            },
            "paired_rollout_contract": {
                "manifest": str(paired_path.resolve()),
                "file_sha256": TARGET_PAIRED_ROLLOUT_MANIFEST_SHA256,
                "reuse_without_regeneration": True,
                "eval_case_count": 10,
            },
            "software_and_dependency_hashes": {
                name: {"path": str(path.resolve()), "sha256": sha256(path)}
                for name, path in source_paths.items()
            },
        }
        with (temporary_root / "protocol_configuration.json").open(
            "x", encoding="utf-8"
        ) as stream:
            json.dump(configuration, stream, indent=2, sort_keys=True)
            stream.write("\n")
        os.replace(temporary_root, revision_root)
    except Exception:
        if temporary_root.exists():
            shutil.rmtree(temporary_root)
        raise
    print(
        json.dumps(
            {
                "status": "CONFIGURATION_PREPARED_AWAITING_EXPLICIT_START",
                "root": str(revision_root),
                "paired_manifest_sha256": TARGET_PAIRED_ROLLOUT_MANIFEST_SHA256,
                "collection_started": False,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
