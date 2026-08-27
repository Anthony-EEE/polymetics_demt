#!/usr/bin/env python3
"""Validate the frozen simulation_target_group raw collection."""

import argparse
import hashlib
import json
import math
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


EXAMPLES_DIR = Path(__file__).resolve().parents[1]
if str(EXAMPLES_DIR) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_DIR))

from rebuttal_target_pipeline.target_protocol import (  # noqa: E402
    TARGET_SUCCESS_CRITERION,
    TARGET_XY_TOLERANCE,
)
from main_obstacle_transport_target_participants import shared_cube_start  # noqa: E402


GROUP = "simulation_target_group"
SEED = 20260806
PARTICIPANTS = [f"T{index:02d}" for index in range(1, 11)]
EXPECTED_DEMOS = list(range(30))
TARGET_TOLERANCE = TARGET_XY_TOLERANCE
CYLINDER_TILT_TOLERANCE_DEGREES = 10.0
WAYPOINT_TOLERANCE = 0.04
TRANSPORT_HEIGHT_TOLERANCE = 0.015
EXPECTED_RELEASE_Z = 0.08
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


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path, errors, label=None):
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception as exc:
        errors.append(f"invalid_json:{label or path}:{type(exc).__name__}:{exc}")
        return None


def check_equal(errors, condition, message):
    if not condition:
        errors.append(message)


def load_numeric(path, expected_size, errors, require_finite=True):
    try:
        value = np.atleast_1d(np.loadtxt(str(path), delimiter=",", dtype=float)).reshape(-1)
    except Exception as exc:
        errors.append(f"invalid_numeric:{path}:{type(exc).__name__}:{exc}")
        return None
    if value.size != expected_size:
        errors.append(f"wrong_numeric_shape:{path}:expected={expected_size}:actual={value.size}")
    if require_finite and not np.all(np.isfinite(value)):
        errors.append(f"nonfinite_numeric:{path}")
    return value


def ply_vertex_count(path, errors):
    try:
        count = None
        with path.open("rb") as handle:
            first = handle.readline().decode("ascii", errors="strict").strip()
            if first != "ply":
                errors.append(f"invalid_ply_magic:{path}:{first!r}")
                return None
            for _ in range(128):
                line = handle.readline().decode("ascii", errors="strict").strip()
                if line.startswith("element vertex "):
                    count = int(line.split()[-1])
                if line == "end_header":
                    break
            else:
                errors.append(f"missing_ply_end_header:{path}")
                return None
        if count is None or count <= 0:
            errors.append(f"invalid_ply_vertex_count:{path}:{count}")
        return count
    except Exception as exc:
        errors.append(f"invalid_ply:{path}:{type(exc).__name__}:{exc}")
        return None


def frame_index(path):
    match = re.fullmatch(r"frame_(\d+)", path.name)
    return int(match.group(1)) if match else None


def demo_dir_index(path):
    match = re.fullmatch(r"demo_(\d+)", path.name)
    return int(match.group(1)) if match else None


def result_key(result):
    return (
        result.get("participant_id"),
        result.get("demo_index"),
        result.get("attempt_index"),
    )


def validate_frame(frame_dir, expected_index, errors):
    actual_files = {path.name for path in frame_dir.iterdir() if path.is_file()}
    missing = sorted(FRAME_FILES - actual_files)
    extra = sorted(actual_files - FRAME_FILES)
    if missing:
        errors.append(f"missing_frame_files:{frame_dir}:{missing}")
    if extra:
        errors.append(f"unexpected_frame_files:{frame_dir}:{extra}")

    phase_path = frame_dir / "phase.txt"
    phase = phase_path.read_text(encoding="utf-8").strip() if phase_path.is_file() else None
    if phase is not None and phase.startswith("scripted_"):
        errors.append(f"scripted_frame_in_success_raw:{frame_dir}:{phase}")

    numeric = {}
    specs = {
        "arm_joints.txt": (7, True),
        "hand_joints.txt": (1, True),
        "ee_pose.txt": (7, True),
        "time.txt": (1, True),
        # These diagnostics are intentionally NaN when a phase has no single
        # commanded Cartesian speed or interval (for example release/settle).
        # Frame zero is checked separately and must contain exact finite zeros.
        "commanded_speed.txt": (1, False),
        "commanded_dt.txt": (1, False),
        "cube_pose.txt": (7, True),
    }
    for name, (size, require_finite) in specs.items():
        path = frame_dir / name
        if path.is_file():
            numeric[name] = load_numeric(path, size, errors, require_finite=require_finite)
    point_cloud_path = frame_dir / "point_cloud.ply"
    if point_cloud_path.is_file():
        ply_vertex_count(point_cloud_path, errors)

    if expected_index == 0:
        if phase != "policy_inference_start":
            errors.append(f"wrong_frame0_phase:{frame_dir}:{phase}")
        time_value = numeric.get("time.txt")
        hand_value = numeric.get("hand_joints.txt")
        speed_value = numeric.get("commanded_speed.txt")
        dt_value = numeric.get("commanded_dt.txt")
        if time_value is not None and not math.isclose(float(time_value[0]), 0.0, abs_tol=1e-12):
            errors.append(f"wrong_frame0_time:{frame_dir}:{time_value[0]}")
        if hand_value is not None and not math.isclose(float(hand_value[0]), 1.0, abs_tol=1e-12):
            errors.append(f"wrong_frame0_gripper:{frame_dir}:{hand_value[0]}")
        if speed_value is not None and not math.isclose(float(speed_value[0]), 0.0, abs_tol=1e-12):
            errors.append(f"wrong_frame0_commanded_speed:{frame_dir}:{speed_value[0]}")
        if dt_value is not None and not math.isclose(float(dt_value[0]), 0.0, abs_tol=1e-12):
            errors.append(f"wrong_frame0_commanded_dt:{frame_dir}:{dt_value[0]}")
    return phase, None if numeric.get("time.txt") is None else float(numeric["time.txt"][0])


def validate_success_result(result, participant_id, demo_index, participant, manifest, errors):
    route = participant["route"]
    center = np.asarray(participant["center"], dtype=float)
    prefix = f"{participant_id}:demo={demo_index}"
    check_equal(errors, result.get("group") == GROUP, f"wrong_group:{prefix}:result")
    check_equal(errors, result.get("participant_id") == participant_id, f"wrong_participant:{prefix}:result")
    check_equal(errors, result.get("condition") == route, f"wrong_route:{prefix}:result")
    check_equal(errors, result.get("demo_index") == demo_index, f"wrong_demo_index:{prefix}:result")
    check_equal(errors, result.get("success") is True, f"unsuccessful_formal_demo:{prefix}")

    spec = result.get("spec", {})
    check_equal(errors, spec.get("group") == GROUP, f"wrong_group:{prefix}:spec")
    check_equal(errors, spec.get("participant_id") == participant_id, f"wrong_participant:{prefix}:spec")
    check_equal(errors, spec.get("condition") == route, f"wrong_route:{prefix}:spec")
    check_equal(errors, spec.get("demo_index") == demo_index, f"wrong_demo_index:{prefix}:spec")
    check_equal(
        errors,
        spec.get("target_xy_tolerance_m") == TARGET_TOLERANCE,
        f"wrong_target_tolerance:{prefix}:spec",
    )
    check_equal(
        errors,
        spec.get("success_criterion") == TARGET_SUCCESS_CRITERION,
        f"wrong_success_criterion:{prefix}:spec",
    )
    check_equal(
        errors,
        spec.get("success_protocol_scope") == GROUP,
        f"wrong_success_protocol_scope:{prefix}:spec",
    )
    check_equal(
        errors,
        spec.get("shared_cube_start_manifest") == f"seed_{SEED}_vertical_start_lhs30",
        f"wrong_shared_start_manifest:{prefix}",
    )
    attempt_index = int(result.get("attempt_index", -1))
    expected_sampling = shared_cube_start(SEED, demo_index, attempt_index)
    expected_start = np.asarray(expected_sampling["position"], dtype=float)
    actual_start = np.asarray(spec.get("box_initial_position", []), dtype=float)
    if actual_start.shape != (3,) or not np.allclose(actual_start, expected_start, atol=1e-12, rtol=0.0):
        errors.append(f"wrong_cube_start:{prefix}:expected={expected_start.tolist()}:actual={actual_start.tolist()}")
    check_equal(
        errors,
        spec.get("box_start_sampling") == expected_sampling,
        f"wrong_box_start_sampling:{prefix}:attempt={attempt_index}",
    )
    if attempt_index == 0:
        check_equal(
            errors,
            expected_sampling == manifest["shared_cube_starts"][demo_index],
            f"attempt0_start_differs_from_authoritative_manifest:{prefix}",
        )
    else:
        check_equal(
            errors,
            expected_sampling.get("deterministic_replenishment", {}).get(
                "shared_across_participants"
            )
            is True,
            f"missing_start_replenishment_provenance:{prefix}",
        )
    expected_ee_start = expected_start + np.asarray([0.0, 0.0, 0.10])
    actual_ee_start = np.asarray(spec.get("scripted_ee_initial_position", []), dtype=float)
    if actual_ee_start.shape != (3,) or not np.allclose(actual_ee_start, expected_ee_start, atol=1e-12, rtol=0.0):
        errors.append(f"wrong_scripted_ee_initial:{prefix}")
    actual_center = np.asarray(spec.get("participant_waypoint_center", []), dtype=float)
    if actual_center.shape != (3,) or not np.allclose(actual_center, center, atol=1e-12, rtol=0.0):
        errors.append(f"wrong_participant_center:{prefix}")
    release_pose = np.asarray(spec.get("release_pose", []), dtype=float)
    expected_release = np.asarray([0.50, 0.50, EXPECTED_RELEASE_Z], dtype=float)
    if release_pose.shape != (3,) or not np.allclose(
        release_pose, expected_release, atol=1e-12, rtol=0.0
    ):
        errors.append(
            f"wrong_approved_release_pose:{prefix}:expected={expected_release.tolist()}:"
            f"actual={release_pose.tolist()}"
        )

    details = result.get("details", {})
    setup = details.get("setup_details", {})
    check_equal(errors, details.get("setup_success") is True, f"setup_not_successful:{prefix}")
    check_equal(errors, setup.get("grasped") is True, f"grasp_not_verified:{prefix}")
    check_equal(errors, setup.get("transport_height_reached") is True, f"height_not_verified:{prefix}")
    height_error = setup.get("transport_height_error")
    if not isinstance(height_error, (int, float)) or not math.isfinite(height_error) or height_error > TRANSPORT_HEIGHT_TOLERANCE:
        errors.append(f"transport_height_error_out_of_bounds:{prefix}:{height_error}")
    policy_start = details.get("policy_inference_start", {})
    check_equal(errors, policy_start.get("gripper_state") == 1.0, f"policy_start_gripper_not_closed:{prefix}")

    success = details.get("success", {})
    check_equal(errors, success.get("success") is True, f"success_details_false:{prefix}")
    check_equal(errors, not success.get("failure_reasons"), f"success_has_failure_reasons:{prefix}")
    check_equal(
        errors,
        success.get("target_xy_tolerance") == TARGET_TOLERANCE,
        f"wrong_success_target_tolerance:{prefix}",
    )
    check_equal(
        errors,
        success.get("criterion") == TARGET_SUCCESS_CRITERION,
        f"wrong_success_details_criterion:{prefix}",
    )
    target_error = success.get("target_xy_error")
    cylinder_tilt = success.get("final_cylinder_tilt_degrees")
    waypoint_error = success.get("middle_waypoint_error")
    for name, value, threshold in (
        ("target_xy_error", target_error, TARGET_TOLERANCE),
        ("final_cylinder_tilt_degrees", cylinder_tilt, CYLINDER_TILT_TOLERANCE_DEGREES),
        ("middle_waypoint_error", waypoint_error, WAYPOINT_TOLERANCE),
    ):
        if not isinstance(value, (int, float)) or not math.isfinite(value) or value > threshold:
            errors.append(f"threshold_failure:{prefix}:{name}={value}:threshold={threshold}")
    return {
        "target_xy_error": target_error,
        "final_cylinder_tilt_degrees": cylinder_tilt,
        "maximum_cylinder_tilt_degrees": success.get("maximum_cylinder_tilt_degrees"),
        "middle_waypoint_error": waypoint_error,
        "box_obstacle_contact_steps": success.get("box_obstacle_contact_steps"),
        "robot_obstacle_contact_steps": success.get("robot_obstacle_contact_steps"),
    }


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--authoritative-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main():
    args = parse_args()
    root = args.root.resolve()
    output = (args.output or root / "validation_report.json").resolve()
    errors = []
    warnings = []
    manifest_path = root / "participant_manifest.json"
    manifest = load_json(manifest_path, errors, "formal_participant_manifest")
    authoritative = load_json(args.authoritative_manifest.resolve(), errors, "authoritative_participant_manifest")
    if manifest is None or authoritative is None:
        raise SystemExit("Cannot validate without both participant manifests")
    check_equal(errors, manifest == authoritative, "formal_manifest_differs_from_authoritative_smoke")
    check_equal(errors, manifest.get("group") == GROUP, "wrong_manifest_group")
    check_equal(errors, manifest.get("seed") == SEED, "wrong_manifest_seed")
    check_equal(errors, manifest.get("num_demos_per_participant") == 30, "wrong_manifest_demo_count")
    check_equal(errors, list(manifest.get("participants", {})) == PARTICIPANTS, "wrong_manifest_participant_order")

    for path in sorted(root.rglob("*.json")):
        if path.resolve() != output:
            load_json(path, errors)

    partial_files = [
        str(path.relative_to(root))
        for path in root.rglob("*")
        if path.is_file() and (
            path.suffix.lower() in {".tmp", ".part", ".partial"}
            or path.name.endswith("~")
        )
    ]
    if partial_files:
        errors.append(f"partial_artifacts:{partial_files}")

    actual_participant_dirs = sorted(
        path.name for path in root.iterdir() if path.is_dir() and re.fullmatch(r"T\d\d", path.name)
    )
    check_equal(errors, actual_participant_dirs == PARTICIPANTS, f"wrong_participant_dirs:{actual_participant_dirs}")

    group_summary = load_json(root / "summary.json", errors, "group_summary")
    if group_summary is not None:
        check_equal(errors, group_summary.get("group") == GROUP, "wrong_group_summary_group")
        check_equal(errors, group_summary.get("seed") == SEED, "wrong_group_summary_seed")
        check_equal(errors, group_summary.get("participant_order") == PARTICIPANTS, "wrong_group_summary_participants")
        check_equal(errors, group_summary.get("demo_indices") == EXPECTED_DEMOS, "wrong_group_summary_demo_indices")
        check_equal(errors, group_summary.get("successful_participants") == 10, "wrong_group_summary_success_count")

    all_demo_keys = []
    all_attempt_keys = []
    success_attempt_keys = set()
    all_metrics = []
    frame_total = 0
    phase_counts = {}
    participant_reports = {}
    frame_executor = ThreadPoolExecutor(max_workers=24)

    for participant_id in PARTICIPANTS:
        participant_dir = root / participant_id
        participant = manifest["participants"][participant_id]
        route = participant["route"]
        summary = load_json(participant_dir / "summary.json", errors, f"{participant_id}_summary")
        if summary is not None:
            check_equal(errors, summary.get("group") == GROUP, f"wrong_group:{participant_id}:summary")
            check_equal(errors, summary.get("participant_id") == participant_id, f"wrong_participant:{participant_id}:summary")
            check_equal(errors, summary.get("participant") == participant, f"wrong_participant_record:{participant_id}:summary")
            check_equal(errors, summary.get("seed") == SEED, f"wrong_seed:{participant_id}:summary")
            check_equal(errors, summary.get("requested_demo_indices") == EXPECTED_DEMOS, f"wrong_requested_indices:{participant_id}")
            check_equal(errors, summary.get("successful_demos") == 30, f"wrong_success_count:{participant_id}")
            check_equal(
                errors,
                summary.get("target_xy_tolerance_m") == TARGET_TOLERANCE,
                f"wrong_target_tolerance:{participant_id}:summary",
            )
            check_equal(
                errors,
                summary.get("success_criterion") == TARGET_SUCCESS_CRITERION,
                f"wrong_success_criterion:{participant_id}:summary",
            )
            check_equal(
                errors,
                summary.get("success_protocol_scope") == GROUP,
                f"wrong_success_protocol_scope:{participant_id}:summary",
            )

        summary_successes = summary.get("successes", []) if summary is not None else []
        if summary is not None:
            check_equal(errors, len(summary_successes) == 30, f"wrong_summary_success_rows:{participant_id}")
        success_by_demo = {row.get("demo_index"): row for row in summary_successes}
        if summary is not None:
            check_equal(errors, sorted(success_by_demo) == EXPECTED_DEMOS, f"wrong_success_demo_indices:{participant_id}")

        demo_json_paths = sorted(participant_dir.glob("demo_[0-9][0-9].json")) if participant_dir.is_dir() else []
        demo_json_indices = sorted(int(path.stem.split("_")[1]) for path in demo_json_paths)
        check_equal(errors, demo_json_indices == EXPECTED_DEMOS, f"wrong_demo_json_indices:{participant_id}:{demo_json_indices}")
        raw_dirs = sorted(
            (
                path
                for path in participant_dir.iterdir()
                if path.is_dir() and demo_dir_index(path) is not None
            ) if participant_dir.is_dir() else (),
            key=demo_dir_index,
        )
        raw_indices = [demo_dir_index(path) for path in raw_dirs]
        check_equal(errors, raw_indices == EXPECTED_DEMOS, f"wrong_raw_demo_indices:{participant_id}:{raw_indices}")

        attempt_paths = sorted((participant_dir / "attempts").glob("demo_*_attempt_*.json"))
        attempts_by_demo = {demo_index: [] for demo_index in EXPECTED_DEMOS}
        for path in attempt_paths:
            attempt = load_json(path, errors)
            if attempt is None:
                continue
            key = result_key(attempt)
            all_attempt_keys.append(key)
            check_equal(errors, attempt.get("group") == GROUP, f"wrong_group:{path}:attempt")
            check_equal(errors, attempt.get("participant_id") == participant_id, f"wrong_participant:{path}:attempt")
            check_equal(errors, attempt.get("condition") == route, f"wrong_route:{path}:attempt")
            demo_index = attempt.get("demo_index")
            if demo_index in attempts_by_demo:
                attempts_by_demo[demo_index].append(attempt)
            else:
                errors.append(f"attempt_demo_out_of_range:{path}:{demo_index}")
        check_equal(errors, len(all_attempt_keys) == len(set(all_attempt_keys)), "duplicate_attempt_keys")

        participant_metrics = []
        participant_frames = 0
        participant_failures = sum(
            row.get("success") is not True
            for attempts in attempts_by_demo.values()
            for row in attempts
        )
        for demo_index in EXPECTED_DEMOS:
            prefix = f"{participant_id}:demo={demo_index}"
            result = load_json(participant_dir / f"demo_{demo_index:02d}.json", errors, prefix)
            if result is None:
                continue
            all_demo_keys.append((participant_id, demo_index))
            metrics = validate_success_result(result, participant_id, demo_index, participant, manifest, errors)
            participant_metrics.append(metrics)
            all_metrics.append(metrics)
            summary_result = success_by_demo.get(demo_index)
            if summary is not None:
                check_equal(errors, summary_result == result, f"summary_demo_result_mismatch:{prefix}")

            attempts = sorted(attempts_by_demo[demo_index], key=lambda row: row.get("attempt_index", -1))
            success_attempts = [row for row in attempts if row.get("success") is True]
            check_equal(errors, len(success_attempts) == 1, f"wrong_success_attempt_count:{prefix}:{len(success_attempts)}")
            if success_attempts:
                success_attempt = success_attempts[0]
                success_attempt_keys.add(result_key(success_attempt))
                check_equal(errors, success_attempt == result, f"success_attempt_demo_mismatch:{prefix}")
                expected_attempt_indices = list(range(int(success_attempt["attempt_index"]) + 1))
                actual_attempt_indices = [row.get("attempt_index") for row in attempts]
                check_equal(errors, actual_attempt_indices == expected_attempt_indices, f"attempt_gap_or_extra:{prefix}:{actual_attempt_indices}")

            raw_dir = participant_dir / f"demo_{demo_index}"
            metadata = load_json(raw_dir / "metadata.json", errors, f"{prefix}:metadata")
            if metadata is None:
                continue
            check_equal(errors, metadata.get("group") == GROUP, f"wrong_group:{prefix}:metadata")
            check_equal(errors, metadata.get("participant_id") == participant_id, f"wrong_participant:{prefix}:metadata")
            check_equal(errors, metadata.get("condition") == route, f"wrong_route:{prefix}:metadata")
            check_equal(errors, metadata.get("demo_index") == demo_index, f"wrong_demo_index:{prefix}:metadata")
            check_equal(errors, metadata.get("attempt_index") == result.get("attempt_index"), f"wrong_attempt_index:{prefix}:metadata")
            check_equal(errors, metadata.get("first_saved_phase") == "policy_inference_start", f"wrong_boundary:{prefix}:metadata")
            check_equal(errors, metadata.get("scripted_setup_saved") is False, f"scripted_setup_flag:{prefix}:metadata")
            check_equal(errors, metadata.get("spec") == result.get("spec"), f"metadata_spec_mismatch:{prefix}")

            frame_dirs = sorted(
                (path for path in raw_dir.iterdir() if path.is_dir() and frame_index(path) is not None),
                key=frame_index,
            )
            indices = [frame_index(path) for path in frame_dirs]
            check_equal(errors, indices == list(range(len(frame_dirs))), f"noncontiguous_frames:{prefix}:{indices[:5]}...{indices[-5:] if indices else []}")
            check_equal(errors, metadata.get("frame_count") == len(frame_dirs), f"metadata_frame_count_mismatch:{prefix}:metadata={metadata.get('frame_count')}:actual={len(frame_dirs)}")
            if not frame_dirs:
                errors.append(f"empty_success_raw_demo:{prefix}")
            times = []
            frame_results = frame_executor.map(
                lambda indexed: validate_frame(indexed[1], indexed[0], errors),
                enumerate(frame_dirs),
            )
            for phase, time_value in frame_results:
                if phase is not None:
                    phase_counts[phase] = phase_counts.get(phase, 0) + 1
                if time_value is not None:
                    times.append(time_value)
            if times and any(later + 1e-12 < earlier for earlier, later in zip(times, times[1:])):
                errors.append(f"nonmonotonic_frame_times:{prefix}")
            frame_total += len(frame_dirs)
            participant_frames += len(frame_dirs)

            video_path = Path(result.get("video_path", ""))
            if not video_path.is_file() or video_path.stat().st_size <= 48:
                errors.append(f"missing_or_partial_success_video:{prefix}:{video_path}")
            plot_path = participant_dir / "plots" / f"demo_{demo_index:02d}_attempt_{int(result.get('attempt_index', -1)):02d}.png"
            if not plot_path.is_file() or plot_path.stat().st_size == 0:
                errors.append(f"missing_success_plot:{prefix}:{plot_path}")

        participant_reports[participant_id] = {
            "route": route,
            "successful_demos": len(participant_metrics),
            "failed_attempts": participant_failures,
            "raw_frames": participant_frames,
            "target_xy_error_max": max((row["target_xy_error"] for row in participant_metrics), default=None),
            "final_cylinder_tilt_degrees_max": max((row["final_cylinder_tilt_degrees"] for row in participant_metrics), default=None),
            "middle_waypoint_error_max": max((row["middle_waypoint_error"] for row in participant_metrics), default=None),
        }

    frame_executor.shutdown(wait=True)

    check_equal(errors, len(all_demo_keys) == 300, f"wrong_total_demo_count:{len(all_demo_keys)}")
    check_equal(errors, len(set(all_demo_keys)) == 300, f"duplicate_demo_keys:{len(all_demo_keys) - len(set(all_demo_keys))}")
    check_equal(errors, len(success_attempt_keys) == 300, f"wrong_unique_success_attempt_count:{len(success_attempt_keys)}")

    empty_dirs = []
    for path in root.rglob("*"):
        if path.is_dir():
            try:
                next(path.iterdir())
            except StopIteration:
                empty_dirs.append(str(path.relative_to(root)))
    if empty_dirs:
        errors.append(f"empty_directories:{empty_dirs}")

    zero_size_formal_files = [
        str(path.relative_to(root))
        for path in root.rglob("*")
        if path.is_file()
        and path.resolve() != output
        and path.suffix.lower() in {".json", ".mp4", ".png", ".ply", ".txt"}
        and path.stat().st_size == 0
    ]
    if zero_size_formal_files:
        errors.append(f"zero_size_formal_files:{zero_size_formal_files}")

    report = {
        "group": GROUP,
        "seed": SEED,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "root": str(root),
        "passed": not errors,
        "errors": errors,
        "warnings": warnings,
        "thresholds": {
            "target_xy_error_max_m": TARGET_TOLERANCE,
            "final_cylinder_tilt_max_degrees": CYLINDER_TILT_TOLERANCE_DEGREES,
            "middle_waypoint_realised_error_max_m": WAYPOINT_TOLERANCE,
            "transport_height_error_max_m": TRANSPORT_HEIGHT_TOLERANCE,
            "fixed_release_ee_z_m": EXPECTED_RELEASE_Z,
        },
        "counts": {
            "participants": len(actual_participant_dirs),
            "successful_demos": len(all_demo_keys),
            "unique_successful_demos": len(set(all_demo_keys)),
            "attempt_records": len(all_attempt_keys),
            "successful_attempt_records": len(success_attempt_keys),
            "failed_attempt_records": len(all_attempt_keys) - len(success_attempt_keys),
            "raw_frames": frame_total,
            "scripted_frames_in_success_raw": sum(
                count for phase, count in phase_counts.items() if phase.startswith("scripted_")
            ),
            "empty_directories": len(empty_dirs),
            "partial_artifacts": len(partial_files),
            "zero_size_formal_files": len(zero_size_formal_files),
        },
        "phase_counts": dict(sorted(phase_counts.items())),
        "participant_reports": participant_reports,
        "metric_extrema": {
            "target_xy_error_max": max((row["target_xy_error"] for row in all_metrics), default=None),
            "final_cylinder_tilt_degrees_max": max((row["final_cylinder_tilt_degrees"] for row in all_metrics), default=None),
            "maximum_cylinder_tilt_degrees_max": max((row["maximum_cylinder_tilt_degrees"] for row in all_metrics), default=None),
            "middle_waypoint_error_max": max((row["middle_waypoint_error"] for row in all_metrics), default=None),
        },
        "hashes": {
            "formal_participant_manifest_sha256": sha256(manifest_path),
            "authoritative_participant_manifest_sha256": sha256(args.authoritative_manifest.resolve()),
        },
        "software": {
            name: {"path": str(path.resolve()), "sha256": sha256(path.resolve())}
            for name, path in {
                "target_collector": Path(__file__).resolve().parents[1]
                / "main_obstacle_transport_target_participants.py",
                "shared_task": Path(__file__).resolve().parents[1] / "main_obstacle_transport.py",
                "raw_validator": Path(__file__).resolve(),
                "target_success_protocol": Path(__file__).resolve().parent
                / "target_protocol.py",
            }.items()
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
