#!/usr/bin/env python3
"""Validate raw data from the Target-aligned Control protocol revision."""

import argparse
import hashlib
import json
import math
import re
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


EXAMPLES_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = EXAMPLES_DIR.parent
if str(EXAMPLES_DIR) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_DIR))

from main_obstacle_transport_control_participants import (  # noqa: E402
    CONTROL_PARTICIPANTS,
    WAYPOINT_ROUTE_X_BOUNDS,
    WAYPOINT_Z_BOUNDS,
)
from rebuttal_control_pipeline.collect_control_aligned import (  # noqa: E402
    participant_task_spec,
    shared_cube_start,
)
from rebuttal_control_pipeline.control_protocol import (  # noqa: E402
    CONTACTS_ARE_DIAGNOSTIC_ONLY,
    CYLINDER_TILT_TOLERANCE_DEGREES,
    EXPECTED_RELEASE_Z,
    FORMAL_SEED,
    GROUP,
    REVISION_ROOT_RELATIVE,
    SUCCESS_CRITERION,
    TARGET_PAIRED_ROLLOUT_MANIFEST_SHA256,
    TARGET_XY_TOLERANCE,
    assert_target_aligned_dependencies,
)


PARTICIPANTS = list(CONTROL_PARTICIPANTS)
EXPECTED_DEMOS = list(range(30))
WAYPOINT_TOLERANCE = 0.04
TRANSPORT_HEIGHT_TOLERANCE = 0.015
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
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path, errors, label=None):
    try:
        with Path(path).open("r", encoding="utf-8") as stream:
            return json.load(stream)
    except Exception as exc:
        errors.append(f"invalid_json:{label or path}:{type(exc).__name__}:{exc}")
        return None


def check(errors, condition, message):
    if not condition:
        errors.append(message)


def load_numeric(path, expected_size, errors, require_finite=True):
    try:
        value = np.atleast_1d(
            np.loadtxt(str(path), delimiter=",", dtype=float)
        ).reshape(-1)
    except Exception as exc:
        errors.append(f"invalid_numeric:{path}:{type(exc).__name__}:{exc}")
        return None
    if value.size != expected_size:
        errors.append(
            f"wrong_numeric_shape:{path}:expected={expected_size}:actual={value.size}"
        )
    if require_finite and not np.all(np.isfinite(value)):
        errors.append(f"nonfinite_numeric:{path}")
    return value


def validate_frame(frame_dir, expected_index, errors):
    actual = {path.name for path in frame_dir.iterdir() if path.is_file()}
    check(errors, actual == FRAME_FILES, f"wrong_frame_files:{frame_dir}:{sorted(actual)}")
    phase_path = frame_dir / "phase.txt"
    phase = phase_path.read_text(encoding="utf-8").strip() if phase_path.is_file() else None
    if phase is not None and phase.startswith("scripted_"):
        errors.append(f"scripted_frame_in_success_raw:{frame_dir}:{phase}")
    numeric = {}
    for name, size, finite in (
        ("arm_joints.txt", 7, True),
        ("hand_joints.txt", 1, True),
        ("ee_pose.txt", 7, True),
        ("time.txt", 1, True),
        ("commanded_speed.txt", 1, False),
        ("commanded_dt.txt", 1, False),
        ("cube_pose.txt", 7, True),
    ):
        path = frame_dir / name
        if path.is_file():
            numeric[name] = load_numeric(path, size, errors, require_finite=finite)
    ply = frame_dir / "point_cloud.ply"
    if ply.is_file():
        try:
            with ply.open("rb") as stream:
                check(errors, stream.readline().strip() == b"ply", f"invalid_ply:{ply}")
        except Exception as exc:
            errors.append(f"invalid_ply:{ply}:{type(exc).__name__}:{exc}")
    if expected_index == 0:
        check(errors, phase == "policy_inference_start", f"wrong_frame0_phase:{frame_dir}:{phase}")
        for name, expected in (
            ("time.txt", 0.0),
            ("hand_joints.txt", 1.0),
            ("commanded_speed.txt", 0.0),
            ("commanded_dt.txt", 0.0),
        ):
            value = numeric.get(name)
            if value is not None:
                check(
                    errors,
                    math.isclose(float(value[0]), expected, abs_tol=1e-12),
                    f"wrong_frame0_value:{frame_dir}:{name}:{value[0]}",
                )
    return phase, None if numeric.get("time.txt") is None else float(numeric["time.txt"][0])


def validate_attempt_spec(result, participant_id, demo_index, attempt_index, errors):
    prefix = f"{participant_id}:demo={demo_index}:attempt={attempt_index}"
    expected = participant_task_spec(
        participant_id,
        demo_index,
        attempt_index,
        FORMAL_SEED,
    )
    check(errors, result.get("group") == GROUP, f"wrong_group:{prefix}")
    check(errors, result.get("participant_id") == participant_id, f"wrong_participant:{prefix}")
    check(errors, result.get("condition") == CONTROL_PARTICIPANTS[participant_id]["route"], f"wrong_route:{prefix}")
    check(errors, result.get("demo_index") == demo_index, f"wrong_demo_index:{prefix}")
    check(errors, result.get("attempt_index") == attempt_index, f"wrong_attempt_index:{prefix}")
    spec = result.get("spec", {})
    check(errors, spec == expected, f"deterministic_spec_mismatch:{prefix}")
    if not isinstance(spec, dict):
        return
    box = spec.get("box_initial_position", [])
    expected_ee = [box[0], box[1], box[2] + 0.10] if len(box) == 3 else None
    check(errors, spec.get("scripted_ee_initial_position") == expected_ee, f"wrong_initial_ee:{prefix}")
    check(errors, spec.get("release_pose") == [0.5, 0.5, EXPECTED_RELEASE_Z], f"wrong_release_pose:{prefix}")
    check(errors, spec.get("target_xy_tolerance_m") == TARGET_XY_TOLERANCE, f"wrong_target_tolerance:{prefix}")
    check(errors, spec.get("success_criterion") == SUCCESS_CRITERION, f"wrong_success_criterion:{prefix}")
    check(errors, spec.get("success_protocol_scope") == GROUP, f"wrong_success_scope:{prefix}")
    check(errors, spec.get("contacts_are_diagnostic_only") is True, f"contacts_not_diagnostic:{prefix}")
    if attempt_index == 0:
        check(
            errors,
            "deterministic_replenishment" not in spec.get("box_start_sampling", {}),
            f"attempt0_marked_replenishment:{prefix}",
        )
    else:
        replenishment = spec.get("box_start_sampling", {}).get(
            "deterministic_replenishment", {}
        )
        check(errors, replenishment.get("attempt_index") == attempt_index, f"wrong_replenishment_index:{prefix}")
        check(errors, replenishment.get("shared_across_participants") is True, f"replenishment_not_shared:{prefix}")


def validate_success(result, participant_id, demo_index, errors):
    attempt_index = int(result.get("attempt_index", -1))
    prefix = f"{participant_id}:demo={demo_index}:attempt={attempt_index}"
    check(errors, result.get("success") is True, f"unsuccessful_formal_demo:{prefix}")
    details = result.get("details", {})
    setup = details.get("setup_details", {})
    check(errors, details.get("setup_success") is True, f"setup_not_successful:{prefix}")
    check(errors, setup.get("grasped") is True, f"grasp_not_verified:{prefix}")
    check(errors, setup.get("transport_height_reached") is True, f"height_not_verified:{prefix}")
    height_error = setup.get("transport_height_error")
    check(
        errors,
        isinstance(height_error, (int, float))
        and math.isfinite(height_error)
        and height_error <= TRANSPORT_HEIGHT_TOLERANCE,
        f"transport_height_error:{prefix}:{height_error}",
    )
    check(
        errors,
        details.get("policy_inference_start", {}).get("gripper_state") == 1.0,
        f"policy_start_gripper_not_closed:{prefix}",
    )
    success = details.get("success", {})
    check(errors, success.get("success") is True, f"success_details_false:{prefix}")
    check(errors, not success.get("failure_reasons"), f"success_has_failures:{prefix}")
    check(errors, success.get("criterion") == SUCCESS_CRITERION, f"wrong_details_criterion:{prefix}")
    check(errors, success.get("target_xy_tolerance") == TARGET_XY_TOLERANCE, f"wrong_details_tolerance:{prefix}")
    check(errors, success.get("contacts_are_diagnostic_only") is True, f"wrong_contact_semantics:{prefix}")
    metrics = {
        "target_xy_error": (success.get("target_xy_error"), TARGET_XY_TOLERANCE),
        "final_cylinder_tilt_degrees": (
            success.get("final_cylinder_tilt_degrees"),
            CYLINDER_TILT_TOLERANCE_DEGREES,
        ),
        "middle_waypoint_error": (
            success.get("middle_waypoint_error"),
            WAYPOINT_TOLERANCE,
        ),
    }
    for name, (value, threshold) in metrics.items():
        check(
            errors,
            isinstance(value, (int, float))
            and math.isfinite(value)
            and value <= threshold,
            f"threshold_failure:{prefix}:{name}={value}:limit={threshold}",
        )
    for name in ("box_obstacle_contact_steps", "robot_obstacle_contact_steps"):
        value = success.get(name)
        check(
            errors,
            isinstance(value, int) and value >= 0,
            f"invalid_diagnostic_contact_count:{prefix}:{name}={value}",
        )
    return success


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    assert_target_aligned_dependencies(check_paired_manifest=True)
    root = args.root.resolve()
    expected_root = (REPO_ROOT / REVISION_ROOT_RELATIVE).resolve()
    if root != expected_root:
        raise ValueError(f"Validator is frozen to {expected_root}")
    output = (args.output or root / "validation_report.json").resolve()
    errors = []
    warnings = []

    configuration = load_json(root / "protocol_configuration.json", errors, "configuration")
    manifest = load_json(root / "participant_manifest.json", errors, "participant_manifest")
    if configuration is None or manifest is None:
        raise SystemExit("Cannot validate without frozen configuration and manifest")
    check(errors, configuration.get("group") == GROUP, "wrong_configuration_group")
    check(errors, configuration.get("seed") == FORMAL_SEED, "wrong_configuration_seed")
    paired = configuration.get("paired_rollout_contract", {})
    check(errors, paired.get("file_sha256") == TARGET_PAIRED_ROLLOUT_MANIFEST_SHA256, "wrong_paired_manifest_hash")
    check(errors, paired.get("reuse_without_regeneration") is True, "paired_manifest_not_reused")
    check(errors, manifest.get("group") == GROUP, "wrong_manifest_group")
    check(errors, manifest.get("seed") == FORMAL_SEED, "wrong_manifest_seed")
    check(errors, list(manifest.get("participants", {})) == PARTICIPANTS, "wrong_participant_order")
    check(errors, manifest.get("num_demos_per_participant") == 30, "wrong_manifest_demo_count")
    protocol = manifest.get("physical_success_protocol", {})
    check(errors, protocol.get("release_ee_z_m") == EXPECTED_RELEASE_Z, "wrong_manifest_release_z")
    check(errors, protocol.get("target_xy_tolerance_m") == TARGET_XY_TOLERANCE, "wrong_manifest_target_tolerance")
    check(errors, protocol.get("contacts_are_diagnostic_only") is True, "wrong_manifest_contact_semantics")
    for demo_index in EXPECTED_DEMOS:
        check(
            errors,
            manifest.get("shared_cube_starts", [None] * 30)[demo_index]
            == shared_cube_start(FORMAL_SEED, demo_index, 0),
            f"wrong_attempt0_manifest_start:demo={demo_index}",
        )

    partial_files = [
        str(path.relative_to(root))
        for path in root.rglob("*")
        if path.is_file()
        and (
            path.suffix.lower() in {".tmp", ".part", ".partial"}
            or path.name.endswith("~")
        )
    ]
    if partial_files:
        errors.append(f"partial_artifacts:{partial_files}")
    actual_dirs = sorted(
        path.name
        for path in root.iterdir()
        if path.is_dir() and re.fullmatch(r"C\d\d", path.name)
    )
    check(errors, actual_dirs == PARTICIPANTS, f"wrong_participant_dirs:{actual_dirs}")

    group_summary = load_json(root / "summary.json", errors, "group_summary")
    if group_summary is not None:
        check(errors, group_summary.get("group") == GROUP, "wrong_group_summary_group")
        check(errors, group_summary.get("seed") == FORMAL_SEED, "wrong_group_summary_seed")
        check(errors, group_summary.get("participant_order") == PARTICIPANTS, "wrong_group_summary_participants")
        check(errors, group_summary.get("demo_indices") == EXPECTED_DEMOS, "wrong_group_summary_demos")
        check(errors, group_summary.get("successful_participants") == 10, "wrong_group_summary_count")

    all_demo_keys = []
    all_attempt_keys = []
    metrics = []
    frame_total = 0
    phase_counts = Counter()
    failure_reasons = Counter()
    participant_reports = {}
    frame_executor = ThreadPoolExecutor(max_workers=24)
    for participant_id in PARTICIPANTS:
        participant_dir = root / participant_id
        summary = load_json(participant_dir / "summary.json", errors, f"{participant_id}_summary")
        if summary is None:
            participant_reports[participant_id] = {"successful_demos": 0}
            continue
        check(errors, summary.get("successful_demos") == 30, f"wrong_success_count:{participant_id}")
        check(errors, summary.get("target_xy_tolerance_m") == TARGET_XY_TOLERANCE, f"wrong_summary_tolerance:{participant_id}")
        check(errors, summary.get("success_criterion") == SUCCESS_CRITERION, f"wrong_summary_criterion:{participant_id}")
        check(errors, summary.get("contacts_are_diagnostic_only") is True, f"wrong_summary_contacts:{participant_id}")
        summary_successes = summary.get("successes", [])
        success_by_demo = {row.get("demo_index"): row for row in summary_successes}
        check(errors, sorted(success_by_demo) == EXPECTED_DEMOS, f"wrong_summary_demo_indices:{participant_id}")

        attempts_by_demo = {demo_index: [] for demo_index in EXPECTED_DEMOS}
        attempt0_waypoints = []
        attempt_paths = sorted((participant_dir / "attempts").glob("demo_*_attempt_*.json"))
        for path in attempt_paths:
            attempt = load_json(path, errors)
            if attempt is None:
                continue
            demo_index = attempt.get("demo_index")
            attempt_index = attempt.get("attempt_index")
            key = (participant_id, demo_index, attempt_index)
            all_attempt_keys.append(key)
            if demo_index not in attempts_by_demo or not isinstance(attempt_index, int):
                errors.append(f"invalid_attempt_key:{path}:{key}")
                continue
            expected_name = f"demo_{demo_index:02d}_attempt_{attempt_index:02d}.json"
            check(errors, path.name == expected_name, f"wrong_attempt_filename:{path}")
            validate_attempt_spec(attempt, participant_id, demo_index, attempt_index, errors)
            attempts_by_demo[demo_index].append(attempt)
            if attempt_index == 0:
                try:
                    attempt0_waypoint = np.asarray(
                        attempt["spec"]["middle_waypoint"], dtype=float
                    )
                except (KeyError, TypeError, ValueError):
                    attempt0_waypoint = np.asarray([], dtype=float)
                if attempt0_waypoint.shape == (3,) and np.all(
                    np.isfinite(attempt0_waypoint)
                ):
                    attempt0_waypoints.append(attempt0_waypoint)
                else:
                    errors.append(
                        f"invalid_attempt0_waypoint:{participant_id}:demo={demo_index}"
                    )
            if attempt.get("success") is not True:
                labels = attempt.get("details", {}).get("success", {}).get("failure_reasons") or []
                if labels:
                    failure_reasons.update(str(label) for label in labels)
                else:
                    failure_reasons[
                        str(
                            attempt.get("details", {}).get("failure_stage")
                            or attempt.get("details", {}).get("setup_details", {}).get("reason")
                            or "task_failure"
                        )
                    ] += 1

        waypoints = []
        participant_frames = 0
        participant_metrics = []
        for demo_index in EXPECTED_DEMOS:
            prefix = f"{participant_id}:demo={demo_index}"
            result = load_json(participant_dir / f"demo_{demo_index:02d}.json", errors, prefix)
            if result is None:
                continue
            all_demo_keys.append((participant_id, demo_index))
            validate_attempt_spec(
                result,
                participant_id,
                demo_index,
                int(result.get("attempt_index", -1)),
                errors,
            )
            success_details = validate_success(result, participant_id, demo_index, errors)
            metrics.append(success_details)
            participant_metrics.append(success_details)
            check(errors, success_by_demo.get(demo_index) == result, f"summary_result_mismatch:{prefix}")
            attempts = sorted(attempts_by_demo[demo_index], key=lambda row: row.get("attempt_index", -1))
            accepted_index = int(result.get("attempt_index", -1))
            check(
                errors,
                [row.get("attempt_index") for row in attempts]
                == list(range(accepted_index + 1)),
                f"attempt_gap_or_extra:{prefix}",
            )
            check(errors, attempts and attempts[-1] == result, f"terminal_attempt_mismatch:{prefix}")
            check(errors, sum(row.get("success") is True for row in attempts) == 1, f"wrong_success_attempt_count:{prefix}")
            waypoints.append(result["spec"]["middle_waypoint"])

            raw_dir = participant_dir / f"demo_{demo_index}"
            metadata = load_json(raw_dir / "metadata.json", errors, f"{prefix}:metadata")
            if metadata is None:
                continue
            check(errors, metadata.get("group") == GROUP, f"wrong_metadata_group:{prefix}")
            check(errors, metadata.get("attempt_index") == accepted_index, f"wrong_metadata_attempt:{prefix}")
            check(errors, metadata.get("first_saved_phase") == "policy_inference_start", f"wrong_boundary:{prefix}")
            check(errors, metadata.get("scripted_setup_saved") is False, f"scripted_setup_saved:{prefix}")
            check(errors, metadata.get("spec") == result.get("spec"), f"metadata_spec_mismatch:{prefix}")
            frame_dirs = sorted(
                (path for path in raw_dir.iterdir() if path.is_dir() and re.fullmatch(r"frame_\d+", path.name)),
                key=lambda path: int(path.name.split("_")[1]),
            ) if raw_dir.is_dir() else []
            indices = [int(path.name.split("_")[1]) for path in frame_dirs]
            check(errors, indices == list(range(len(frame_dirs))), f"noncontiguous_frames:{prefix}")
            check(errors, len(frame_dirs) > 1, f"empty_or_short_raw:{prefix}")
            check(errors, metadata.get("frame_count") == len(frame_dirs), f"frame_count_mismatch:{prefix}")
            times = []
            for phase, time_value in frame_executor.map(
                lambda item: validate_frame(item[1], item[0], errors),
                enumerate(frame_dirs),
            ):
                if phase is not None:
                    phase_counts[phase] += 1
                if time_value is not None:
                    times.append(time_value)
            if any(later + 1e-12 < earlier for earlier, later in zip(times, times[1:])):
                errors.append(f"nonmonotonic_times:{prefix}")
            frame_total += len(frame_dirs)
            participant_frames += len(frame_dirs)
            video = Path(result.get("video_path", ""))
            check(errors, video.is_file() and video.stat().st_size > 48, f"missing_success_video:{prefix}:{video}")
            plot = participant_dir / "plots" / f"demo_{demo_index:02d}_attempt_{accepted_index:02d}.png"
            check(errors, plot.is_file() and plot.stat().st_size > 0, f"missing_success_plot:{prefix}:{plot}")

        points = np.asarray(waypoints, dtype=float)
        unique = int(np.unique(np.round(points[:, [0, 2]], 12), axis=0).shape[0]) if len(points) else 0
        x_span = float(np.ptp(points[:, 0])) if len(points) else 0.0
        z_span = float(np.ptp(points[:, 2])) if len(points) else 0.0
        attempt0_points = np.asarray(attempt0_waypoints, dtype=float)
        attempt0_unique = (
            int(
                np.unique(
                    np.round(attempt0_points[:, [0, 2]], 12), axis=0
                ).shape[0]
            )
            if len(attempt0_points)
            else 0
        )
        attempt0_x_span = (
            float(np.ptp(attempt0_points[:, 0])) if len(attempt0_points) else 0.0
        )
        attempt0_z_span = (
            float(np.ptp(attempt0_points[:, 2])) if len(attempt0_points) else 0.0
        )
        check(errors, unique == 30, f"duplicate_waypoints:{participant_id}:{unique}")
        check(
            errors,
            len(attempt0_points) == 30 and attempt0_unique == 30,
            f"invalid_attempt0_waypoint_set:{participant_id}:"
            f"count={len(attempt0_points)}:unique={attempt0_unique}",
        )
        check(
            errors,
            attempt0_x_span >= 0.14,
            f"insufficient_attempt0_x_spread:{participant_id}:{attempt0_x_span}",
        )
        check(
            errors,
            attempt0_z_span >= 0.07,
            f"insufficient_attempt0_z_spread:{participant_id}:{attempt0_z_span}",
        )
        participant_reports[participant_id] = {
            "route": CONTROL_PARTICIPANTS[participant_id]["route"],
            "successful_demos": len(waypoints),
            "attempt_records": len(attempt_paths),
            "failed_attempts": len(attempt_paths) - len(waypoints),
            "unique_waypoints": unique,
            "x_span": x_span,
            "z_span": z_span,
            "accepted_waypoint_spread_is_diagnostic": True,
            "attempt0_unique_waypoints": attempt0_unique,
            "attempt0_x_span": attempt0_x_span,
            "attempt0_z_span": attempt0_z_span,
            "waypoint_spread_gate_basis": "frozen_attempt0_candidates",
            "raw_frames": participant_frames,
            "target_xy_error_max": max((row.get("target_xy_error") for row in participant_metrics), default=None),
        }
    frame_executor.shutdown(wait=True)

    check(errors, len(all_demo_keys) == 300, f"wrong_total_demo_count:{len(all_demo_keys)}")
    check(errors, len(set(all_demo_keys)) == 300, "duplicate_demo_keys")
    check(errors, len(all_attempt_keys) == len(set(all_attempt_keys)), "duplicate_attempt_keys")
    empty_dirs = []
    for path in root.rglob("*"):
        if path.is_dir():
            try:
                next(path.iterdir())
            except StopIteration:
                empty_dirs.append(str(path.relative_to(root)))
    if empty_dirs:
        errors.append(f"empty_directories:{empty_dirs}")
    zero_files = [
        str(path.relative_to(root))
        for path in root.rglob("*")
        if path.is_file()
        and path.resolve() != output
        and path.suffix.lower() in {".json", ".mp4", ".png", ".ply", ".txt"}
        and path.stat().st_size == 0
    ]
    if zero_files:
        errors.append(f"zero_size_formal_files:{zero_files}")

    report = {
        "schema_version": 1,
        "group": GROUP,
        "seed": FORMAL_SEED,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "root": str(root),
        "passed": not errors,
        "errors": errors,
        "warnings": warnings,
        "thresholds": {
            "target_xy_error_max_m": TARGET_XY_TOLERANCE,
            "final_cylinder_tilt_max_degrees": CYLINDER_TILT_TOLERANCE_DEGREES,
            "middle_waypoint_realised_error_max_m": WAYPOINT_TOLERANCE,
            "transport_height_error_max_m": TRANSPORT_HEIGHT_TOLERANCE,
            "fixed_release_ee_z_m": EXPECTED_RELEASE_Z,
            "contacts_are_diagnostic_only": CONTACTS_ARE_DIAGNOSTIC_ONLY,
            "attempt0_waypoint_x_span_min_m": 0.14,
            "attempt0_waypoint_z_span_min_m": 0.07,
        },
        "counts": {
            "participants": len(actual_dirs),
            "successful_demos": len(all_demo_keys),
            "attempt_records": len(all_attempt_keys),
            "failed_attempt_records": len(all_attempt_keys) - len(all_demo_keys),
            "raw_frames": frame_total,
            "scripted_frames_in_success_raw": sum(
                count for phase, count in phase_counts.items() if phase.startswith("scripted_")
            ),
            "empty_directories": len(empty_dirs),
            "partial_artifacts": len(partial_files),
            "zero_size_formal_files": len(zero_files),
        },
        "phase_counts": dict(sorted(phase_counts.items())),
        "failure_reasons": dict(sorted(failure_reasons.items())),
        "participant_reports": participant_reports,
        "metric_extrema": {
            key: max((row.get(key) for row in metrics), default=None)
            for key in (
                "target_xy_error",
                "final_cylinder_tilt_degrees",
                "maximum_cylinder_tilt_degrees",
                "middle_waypoint_error",
                "box_obstacle_contact_steps",
                "robot_obstacle_contact_steps",
            )
        },
        "hashes": {
            "participant_manifest_sha256": sha256(root / "participant_manifest.json"),
            "protocol_configuration_sha256": sha256(root / "protocol_configuration.json"),
            "paired_rollout_manifest_sha256": TARGET_PAIRED_ROLLOUT_MANIFEST_SHA256,
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
