#!/usr/bin/env python3
"""Validate simulation_control_group raw demonstrations and spatial spread."""

import argparse
import json
import math
import re
from collections import Counter
from pathlib import Path

import numpy as np


GROUP = "simulation_control_group"
PARTICIPANTS = [f"C{index:02d}" for index in range(1, 11)]
ROUTES = {
    participant: ("L" if int(participant[1:]) <= 5 else "R")
    for participant in PARTICIPANTS
}
ROUTE_X_BOUNDS = {"L": (0.10, 0.30), "R": (0.70, 0.90)}
Z_BOUNDS = (0.19, 0.29)
WAYPOINT_Y = 0.25
FRAME_FILES = {
    "point_cloud.ply",
    "arm_joints.txt",
    "hand_joints.txt",
    "ee_pose.txt",
    "time.txt",
    "commanded_speed.txt",
    "commanded_dt.txt",
    "phase.txt",
    "cube_pose.txt",
}


def load_json(path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle, parse_constant=lambda value: (_ for _ in ()).throw(
            ValueError(f"non-standard JSON constant {value} in {path}")
        ))


def require(condition, errors, message):
    if not condition:
        errors.append(message)


def numeric_vector(path, expected_size, errors, allow_nonfinite=False):
    try:
        value = np.atleast_1d(np.loadtxt(str(path), delimiter=",", dtype=float)).reshape(-1)
    except Exception as exc:
        errors.append(f"invalid_numeric:{path}:{type(exc).__name__}:{exc}")
        return None
    if value.size != expected_size:
        errors.append(f"wrong_numeric_size:{path}:expected={expected_size}:actual={value.size}")
    if not allow_nonfinite and not np.all(np.isfinite(value)):
        errors.append(f"nonfinite_numeric:{path}")
    return value


def validate_frame(frame_dir, frame_index, errors):
    actual = {path.name for path in frame_dir.iterdir() if path.is_file()}
    require(actual == FRAME_FILES, errors, f"wrong_frame_files:{frame_dir}:{sorted(actual)}")
    phase_path = frame_dir / "phase.txt"
    phase = phase_path.read_text(encoding="utf-8").strip() if phase_path.is_file() else ""
    require(not phase.startswith("scripted_"), errors, f"scripted_frame:{frame_dir}:{phase}")
    sizes = {
        "arm_joints.txt": 7,
        "hand_joints.txt": 1,
        "ee_pose.txt": 7,
        "time.txt": 1,
        "commanded_speed.txt": 1,
        "commanded_dt.txt": 1,
        "cube_pose.txt": 7,
    }
    values = {
        name: numeric_vector(
            frame_dir / name,
            size,
            errors,
            allow_nonfinite=(
                name == "commanded_speed.txt"
                and phase in {"policy_release", "settle"}
            ),
        )
        for name, size in sizes.items()
        if (frame_dir / name).is_file()
    }
    ply = frame_dir / "point_cloud.ply"
    if ply.is_file():
        with ply.open("rb") as handle:
            require(handle.readline().strip() == b"ply", errors, f"invalid_ply:{ply}")
    if frame_index == 0:
        require(phase == "policy_inference_start", errors, f"wrong_frame0_phase:{frame_dir}:{phase}")
        if values.get("time.txt") is not None:
            require(math.isclose(float(values["time.txt"][0]), 0.0, abs_tol=1e-12), errors, f"wrong_frame0_time:{frame_dir}")
        if values.get("hand_joints.txt") is not None:
            require(math.isclose(float(values["hand_joints.txt"][0]), 1.0, abs_tol=1e-12), errors, f"wrong_frame0_gripper:{frame_dir}")
        if values.get("commanded_speed.txt") is not None:
            require(math.isclose(float(values["commanded_speed.txt"][0]), 0.0, abs_tol=1e-12), errors, f"wrong_frame0_speed:{frame_dir}")


def validate_result(result, participant_id, demo_index, expected_start, errors):
    route = ROUTES[participant_id]
    prefix = f"{participant_id}:demo={demo_index:02d}"
    require(result.get("group") == GROUP, errors, f"wrong_group:{prefix}:result")
    require(result.get("participant_id") == participant_id, errors, f"wrong_participant:{prefix}")
    require(result.get("condition") == route, errors, f"wrong_route:{prefix}")
    require(result.get("demo_index") == demo_index, errors, f"wrong_demo_index:{prefix}")
    require(result.get("success") is True, errors, f"unsuccessful_demo:{prefix}")

    spec = result.get("spec", {})
    require(spec.get("group") == GROUP, errors, f"wrong_group:{prefix}:spec")
    require(spec.get("participant_waypoint_center") is None, errors, f"control_has_personal_center:{prefix}")
    require(spec.get("box_initial_position") == expected_start, errors, f"wrong_cube_start:{prefix}")
    manipulation = spec.get("control_manipulation", {})
    require(manipulation.get("varied_dimension") == "position", errors, f"wrong_manipulation:{prefix}")
    require(manipulation.get("spatial_consistency_guidance") is False, errors, f"spatial_guidance_enabled:{prefix}")
    sampling = spec.get("waypoint_sampling", {})
    require(sampling.get("sampling") == "independent_uniform_full_route_xz_rectangle", errors, f"wrong_sampling:{prefix}")
    require(sampling.get("across_demo_contraction") is False, errors, f"contraction_enabled:{prefix}")
    require(sampling.get("personal_waypoint_center") is None, errors, f"sampling_has_center:{prefix}")
    require(sampling.get("x_bounds") == list(ROUTE_X_BOUNDS[route]), errors, f"wrong_x_support:{prefix}")
    require(sampling.get("z_bounds") == list(Z_BOUNDS), errors, f"wrong_z_support:{prefix}")
    waypoint = np.asarray(spec.get("middle_waypoint", []), dtype=float)
    if waypoint.shape != (3,) or not np.all(np.isfinite(waypoint)):
        errors.append(f"invalid_waypoint:{prefix}:{waypoint.tolist()}")
    else:
        x_low, x_high = ROUTE_X_BOUNDS[route]
        require(x_low <= waypoint[0] <= x_high, errors, f"waypoint_x_out_of_bounds:{prefix}:{waypoint[0]}")
        require(math.isclose(float(waypoint[1]), WAYPOINT_Y, abs_tol=1e-12), errors, f"wrong_waypoint_y:{prefix}")
        require(Z_BOUNDS[0] <= waypoint[2] <= Z_BOUNDS[1], errors, f"waypoint_z_out_of_bounds:{prefix}:{waypoint[2]}")

    details = result.get("details", {})
    setup = details.get("setup_details", {})
    require(details.get("setup_success") is True, errors, f"setup_failed:{prefix}")
    require(setup.get("grasped") is True, errors, f"grasp_not_verified:{prefix}")
    require(setup.get("transport_height_reached") is True, errors, f"height_not_verified:{prefix}")
    success = details.get("success", {})
    require(success.get("success") is True, errors, f"success_details_false:{prefix}")
    require(not success.get("failure_reasons"), errors, f"success_has_failures:{prefix}")
    thresholds = {
        "target_xy_error": 0.03,
        "final_cylinder_tilt_degrees": 10.0,
        "middle_waypoint_error": 0.04,
    }
    for name, threshold in thresholds.items():
        value = success.get(name)
        require(
            isinstance(value, (int, float)) and math.isfinite(value) and value <= threshold,
            errors,
            f"threshold_failure:{prefix}:{name}={value}:limit={threshold}",
        )
    return waypoint


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--expected-demos", type=int, default=30)
    parser.add_argument("--seed", type=int, default=20260806)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main():
    args = parse_args()
    root = args.root.resolve()
    output = (args.output or root / "validation_report.json").resolve()
    expected_indices = list(range(args.expected_demos))
    errors = []
    manifest = load_json(root / "participant_manifest.json")
    require(manifest.get("group") == GROUP, errors, "wrong_manifest_group")
    require(manifest.get("seed") == args.seed, errors, "wrong_manifest_seed")
    require(manifest.get("num_demos_per_participant") == 30, errors, "wrong_manifest_budget")
    require(list(manifest.get("participants", {})) == PARTICIPANTS, errors, "wrong_participant_order")
    protocol = manifest.get("spatial_protocol", {})
    require(protocol.get("personal_waypoint_centers") is False, errors, "manifest_has_personal_centers")
    require(protocol.get("across_demo_contraction") is False, errors, "manifest_has_contraction")

    actual_dirs = sorted(
        path.name
        for path in root.iterdir()
        if path.is_dir() and re.fullmatch(r"C\d\d", path.name)
    )
    require(actual_dirs == PARTICIPANTS, errors, f"wrong_participant_dirs:{actual_dirs}")
    group_summary_path = root / "summary.json"
    if group_summary_path.is_file():
        group_summary = load_json(group_summary_path)
        require(group_summary.get("group") == GROUP, errors, "wrong_group_summary_group")
        require(group_summary.get("participant_order") == PARTICIPANTS, errors, "wrong_group_summary_order")
        require(group_summary.get("demo_indices") == expected_indices, errors, "wrong_group_summary_demos")

    report = {"group": GROUP, "root": str(root), "participants": {}, "errors": errors}
    accepted_starts_by_demo = {}
    attempt_reasons = Counter()
    for participant_id in PARTICIPANTS:
        participant_dir = root / participant_id
        if not participant_dir.is_dir():
            errors.append(f"missing_participant_dir:{participant_id}")
            report["participants"][participant_id] = {
                "route": ROUTES[participant_id],
                "successful_demos": 0,
                "unique_waypoints": 0,
                "x_span": 0.0,
                "z_span": 0.0,
                "raw_frames": 0,
                "attempt_jsons": 0,
            }
            continue
        summary_path = participant_dir / "summary.json"
        require(summary_path.is_file(), errors, f"missing_participant_summary:{participant_id}")
        summary = load_json(summary_path) if summary_path.is_file() else {}
        require(summary.get("group") == GROUP, errors, f"wrong_summary_group:{participant_id}")
        require(summary.get("participant_id") == participant_id, errors, f"wrong_summary_participant:{participant_id}")
        require(summary.get("requested_demo_indices") == expected_indices, errors, f"wrong_summary_indices:{participant_id}")
        require(summary.get("successful_demos") == args.expected_demos, errors, f"wrong_success_count:{participant_id}")
        waypoints = []
        frame_count = 0
        for demo_index in expected_indices:
            result_path = participant_dir / f"demo_{demo_index:02d}.json"
            require(result_path.is_file(), errors, f"missing_demo_json:{result_path}")
            if not result_path.is_file():
                continue
            result = load_json(result_path)
            expected_start = manifest["shared_cube_starts"][demo_index]["position"]
            waypoint = validate_result(result, participant_id, demo_index, expected_start, errors)
            if waypoint.shape == (3,):
                waypoints.append(waypoint)
            accepted_starts_by_demo.setdefault(demo_index, []).append(result["spec"]["box_initial_position"])
            demo_dir = participant_dir / f"demo_{demo_index}"
            require(demo_dir.is_dir(), errors, f"missing_raw_demo:{demo_dir}")
            if demo_dir.is_dir():
                metadata = load_json(demo_dir / "metadata.json")
                require(metadata.get("group") == GROUP, errors, f"wrong_metadata_group:{participant_id}:{demo_index}")
                require(metadata.get("first_saved_phase") == "policy_inference_start", errors, f"wrong_boundary:{participant_id}:{demo_index}")
                frame_dirs = sorted(
                    (path for path in demo_dir.iterdir() if path.is_dir() and re.fullmatch(r"frame_\d+", path.name)),
                    key=lambda path: int(path.name.split("_")[1]),
                )
                indices = [int(path.name.split("_")[1]) for path in frame_dirs]
                require(indices == list(range(len(frame_dirs))), errors, f"noncontiguous_frames:{demo_dir}")
                require(len(frame_dirs) > 1, errors, f"too_few_frames:{demo_dir}")
                for index, frame_dir in enumerate(frame_dirs):
                    validate_frame(frame_dir, index, errors)
                frame_count += len(frame_dirs)

        attempt_paths = sorted((participant_dir / "attempts").glob("demo_*_attempt_*.json"))
        for path in attempt_paths:
            attempt = load_json(path)
            if not attempt.get("success"):
                details = attempt.get("details", {})
                task_reasons = details.get("success", {}).get("failure_reasons") or []
                if task_reasons:
                    attempt_reasons.update(str(reason) for reason in task_reasons)
                else:
                    reason = (
                        details.get("failure_stage")
                        or details.get("setup_details", {}).get("reason")
                        or "task_failure"
                    )
                    attempt_reasons[str(reason)] += 1
        points = np.asarray(waypoints, dtype=float)
        unique = int(np.unique(np.round(points[:, [0, 2]], 12), axis=0).shape[0]) if len(points) else 0
        x_span = float(np.ptp(points[:, 0])) if len(points) else 0.0
        z_span = float(np.ptp(points[:, 2])) if len(points) else 0.0
        require(unique == args.expected_demos, errors, f"duplicate_waypoints:{participant_id}:unique={unique}")
        if args.expected_demos == 30:
            require(x_span >= 0.14, errors, f"insufficient_x_spread:{participant_id}:{x_span}")
            require(z_span >= 0.07, errors, f"insufficient_z_spread:{participant_id}:{z_span}")
        report["participants"][participant_id] = {
            "route": ROUTES[participant_id],
            "successful_demos": len(waypoints),
            "unique_waypoints": unique,
            "x_span": x_span,
            "z_span": z_span,
            "raw_frames": frame_count,
            "attempt_jsons": len(attempt_paths),
        }

    for demo_index in expected_indices:
        starts = accepted_starts_by_demo.get(demo_index, [])
        require(len(starts) == 10, errors, f"missing_paired_starts:demo={demo_index}:count={len(starts)}")
        if starts:
            require(all(start == starts[0] for start in starts[1:]), errors, f"cross_participant_start_mismatch:demo={demo_index}")
    report["failed_attempt_reasons"] = dict(sorted(attempt_reasons.items()))
    report["error_count"] = len(errors)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    if errors:
        raise SystemExit(f"Control raw validation failed with {len(errors)} errors")


if __name__ == "__main__":
    main()
