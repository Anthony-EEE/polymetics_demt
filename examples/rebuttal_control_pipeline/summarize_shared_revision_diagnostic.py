#!/usr/bin/env python3
"""Validate and summarize non-formal combined shared-revision diagnostics."""

import argparse
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path


GROUP = "simulation_control_group"
ALL_PARTICIPANTS = [f"C{index:02d}" for index in range(1, 11)]
SEED = 20260806
RELEASE_POSE = [0.502, 0.498, 0.04]
RELEASE_XY_OFFSET = [0.002, -0.002]
GRASP_OFFSET = [0.004, -0.008, 0.005]
BOUNDARY_GRASP_OFFSET = [0.004, -0.016, -0.005]
LOW_X_THRESHOLD = 0.23
BOUNDARY_X_THRESHOLD = 0.25
EPSILON = 1e-12


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--participants", nargs="+", default=ALL_PARTICIPANTS)
    parser.add_argument("--demo-indices", nargs="+", type=int, required=True)
    parser.add_argument("--control-manifest", type=Path, required=True)
    parser.add_argument("--target-manifest", type=Path, required=True)
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--wrapper", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def load_json(path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def close(left, right, tolerance=EPSILON):
    if isinstance(left, (list, tuple)) and isinstance(right, (list, tuple)):
        return len(left) == len(right) and all(
            close(a, b, tolerance=tolerance) for a, b in zip(left, right)
        )
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return math.isclose(float(left), float(right), rel_tol=0.0, abs_tol=tolerance)
    return left == right


def norm(values):
    return math.sqrt(sum(float(value) ** 2 for value in values))


def failure_labels(attempt):
    details = attempt.get("details", {})
    reasons = details.get("success", {}).get("failure_reasons") or []
    if reasons:
        return [str(reason) for reason in reasons]
    setup_reason = details.get("setup_details", {}).get("reason")
    if setup_reason:
        return [str(setup_reason)]
    return [str(details.get("failure_stage") or "task_failure")]


def main():
    args = parse_args()
    participants = list(args.participants)
    demos = list(args.demo_indices)
    if sorted(set(participants)) != sorted(participants) or not set(participants).issubset(ALL_PARTICIPANTS):
        raise ValueError(f"invalid participant list: {participants}")
    if sorted(set(demos)) != sorted(demos) or any(index < 0 or index >= 30 for index in demos):
        raise ValueError(f"invalid demo list: {demos}")

    root = args.root.resolve()
    output = args.output.resolve()
    control_manifest_path = args.control_manifest.resolve()
    target_manifest_path = args.target_manifest.resolve()
    control_manifest = load_json(control_manifest_path)
    target_manifest = load_json(target_manifest_path)
    control_starts = control_manifest.get("shared_cube_starts", [])
    target_starts = target_manifest.get("shared_cube_starts", [])
    errors = []
    if control_starts != target_starts or len(control_starts) != 30:
        errors.append("Control/Target paired cube-start manifest mismatch")

    participant_summaries = {}
    report_hashes = {}
    total_attempts = 0
    total_successes = 0
    labels = Counter()
    labels_by_case = defaultdict(Counter)
    accepted_metrics = {
        "maximum_target_xy_error": 0.0,
        "maximum_middle_waypoint_error": 0.0,
        "maximum_final_cylinder_tilt_degrees": 0.0,
        "maximum_observed_cylinder_tilt_degrees": 0.0,
        "maximum_final_box_linear_speed": 0.0,
        "maximum_final_box_angular_speed": 0.0,
        "maximum_ground_height_error": 0.0,
        "maximum_precise_initial_ik_error": 0.0,
    }

    for participant_id in participants:
        path = root / f"{participant_id}.json"
        if not path.is_file():
            errors.append(f"missing report {path.name}")
            continue
        report_hashes[participant_id] = sha256(path)
        data = load_json(path)
        expected_scalars = {
            "group": GROUP,
            "formal_data": False,
            "diagnostic": "proposed_shared_setup_and_release_revision",
            "shared_change_request": "SCR-001/SCR-C001",
            "seed": SEED,
            "participant_order": [participant_id],
            "demo_indices": demos,
            "release_z": RELEASE_POSE[2],
            "release_xy_offset": RELEASE_XY_OFFSET,
            "precise_initial_ik": True,
            "cartesian_scripted_setup": True,
            "grasp_offset": GRASP_OFFSET,
            "boundary_grasp_offset": BOUNDARY_GRASP_OFFSET,
            "adaptive_low_x_setup": True,
            "low_x_threshold": LOW_X_THRESHOLD,
            "boundary_x_threshold": BOUNDARY_X_THRESHOLD,
            "object_centered_release": False,
            "case_count": len(demos),
        }
        for key, expected in expected_scalars.items():
            if not close(data.get(key), expected):
                errors.append(f"{participant_id}: unexpected {key}: {data.get(key)!r}")

        cases = data.get("cases", [])
        attempts = data.get("attempts", [])
        case_by_demo = {row.get("demo_index"): row for row in cases}
        attempts_by_demo = defaultdict(list)
        for attempt in attempts:
            attempts_by_demo[attempt.get("demo_index")].append(attempt)
        if len(cases) != len(demos) or sorted(case_by_demo) != sorted(demos):
            errors.append(f"{participant_id}: cases differ from requested demo set")

        successes = 0
        failed_demos = []
        participant_labels = Counter()
        for demo_index in demos:
            case = case_by_demo.get(demo_index)
            rows = sorted(
                attempts_by_demo.get(demo_index, []),
                key=lambda row: row.get("attempt_index", -1),
            )
            if case is None:
                continue
            success = bool(case.get("success"))
            successes += int(success)
            if not success:
                failed_demos.append(demo_index)
            if not rows or [row.get("attempt_index") for row in rows] != list(range(len(rows))):
                errors.append(f"{participant_id} demo {demo_index}: non-contiguous attempts")
            if len(rows) > 30:
                errors.append(f"{participant_id} demo {demo_index}: attempt count exceeds 30")
            if success:
                if len([row for row in rows if row.get("success")]) != 1:
                    errors.append(f"{participant_id} demo {demo_index}: accepted-count mismatch")
                if case.get("accepted") != rows[-1] or case.get("accepted_attempt_index") != rows[-1].get("attempt_index"):
                    errors.append(f"{participant_id} demo {demo_index}: terminal accepted attempt mismatch")
            elif len(rows) != 30 or case.get("accepted") is not None:
                errors.append(f"{participant_id} demo {demo_index}: failed case did not exhaust cleanly")

            route = "L" if int(participant_id[1:]) <= 5 else "R"
            x_bounds = [0.1, 0.3] if route == "L" else [0.7, 0.9]
            expected_start = control_starts[demo_index]["position"]
            expected_initial = [expected_start[0], expected_start[1], expected_start[2] + 0.10]
            if expected_start[0] < LOW_X_THRESHOLD:
                expected_active_grasp_offset = GRASP_OFFSET
            elif expected_start[0] < BOUNDARY_X_THRESHOLD:
                expected_active_grasp_offset = BOUNDARY_GRASP_OFFSET
            else:
                expected_active_grasp_offset = [0.0, 0.0, 0.0]
            expected_grasp = [
                expected_start[0] + expected_active_grasp_offset[0],
                expected_start[1] + expected_active_grasp_offset[1],
                0.04 + expected_active_grasp_offset[2],
            ]
            for attempt in rows:
                attempt_index = attempt.get("attempt_index")
                prefix = f"{participant_id} demo {demo_index} attempt {attempt_index}"
                spec = attempt.get("spec", {})
                if attempt.get("group") != GROUP or attempt.get("formal_data") is not False:
                    errors.append(f"{prefix}: group/formal-data marker mismatch")
                if attempt.get("participant_id") != participant_id or spec.get("condition") != route:
                    errors.append(f"{prefix}: participant/route mismatch")
                if spec.get("demo_index") != demo_index or spec.get("attempt_index") != attempt_index:
                    errors.append(f"{prefix}: indices mismatch")
                if not close(spec.get("box_initial_position"), expected_start):
                    errors.append(f"{prefix}: paired cube start mismatch")
                if not close(spec.get("scripted_ee_initial_position"), expected_initial):
                    errors.append(f"{prefix}: exact initial EE target mismatch")
                if not close(spec.get("release_pose"), RELEASE_POSE):
                    errors.append(f"{prefix}: calibrated release pose mismatch")
                waypoint = spec.get("middle_waypoint", [])
                sampling = spec.get("waypoint_sampling", {})
                if (
                    len(waypoint) != 3
                    or not (x_bounds[0] <= waypoint[0] <= x_bounds[1])
                    or not close(waypoint[1], 0.25)
                    or not (0.19 <= waypoint[2] <= 0.29)
                    or sampling.get("sampling") != "independent_uniform_full_route_xz_rectangle"
                    or sampling.get("across_demo_contraction") is not False
                    or sampling.get("position_consistency_guidance") is not False
                ):
                    errors.append(f"{prefix}: independent full-support waypoint mismatch")
                override = spec.get("diagnostic_override", {})
                if (
                    override.get("formal_data") is not False
                    or not close(override.get("release_xy_offset"), RELEASE_XY_OFFSET)
                    or not close(override.get("grasp_offset"), GRASP_OFFSET)
                    or not close(override.get("boundary_grasp_offset"), BOUNDARY_GRASP_OFFSET)
                    or override.get("adaptive_low_x_setup") is not True
                    or not close(override.get("low_x_threshold"), LOW_X_THRESHOLD)
                    or not close(override.get("boundary_x_threshold"), BOUNDARY_X_THRESHOLD)
                    or override.get("precise_initial_ik") is not True
                    or override.get("cartesian_scripted_setup") is not True
                    or override.get("object_centered_release") is not False
                ):
                    errors.append(f"{prefix}: revision marker mismatch")
                details = attempt.get("details", {})
                setup = details.get("setup_details", {})
                if details.get("setup_success"):
                    initial_error = float(setup.get("precise_initial_ik_error", math.inf))
                    accepted_metrics["maximum_precise_initial_ik_error"] = max(
                        accepted_metrics["maximum_precise_initial_ik_error"], initial_error
                    )
                    if expected_start[0] < LOW_X_THRESHOLD:
                        setup_valid = (
                            initial_error <= 0.025 + EPSILON
                            and setup.get("setup_motion") == "cartesian_segments"
                            and setup.get("setup_strategy") == "corrected_low_x"
                            and close(setup.get("low_x_threshold"), LOW_X_THRESHOLD)
                            and close(setup.get("boundary_x_threshold"), BOUNDARY_X_THRESHOLD)
                            and close(setup.get("boundary_grasp_offset"), BOUNDARY_GRASP_OFFSET)
                            and close(setup.get("grasp_offset"), GRASP_OFFSET)
                            and close(setup.get("required_waypoints", {}).get("scripted_ee_initial"), expected_initial)
                            and close(setup.get("required_waypoints", {}).get("grasp"), expected_grasp)
                        )
                    elif expected_start[0] < BOUNDARY_X_THRESHOLD:
                        setup_valid = (
                            initial_error <= 0.025 + EPSILON
                            and setup.get("setup_motion") == "cartesian_segments"
                            and setup.get("setup_strategy") == "corrected_boundary_x"
                            and close(setup.get("low_x_threshold"), LOW_X_THRESHOLD)
                            and close(setup.get("boundary_x_threshold"), BOUNDARY_X_THRESHOLD)
                            and close(setup.get("boundary_grasp_offset"), BOUNDARY_GRASP_OFFSET)
                            and close(setup.get("grasp_offset"), BOUNDARY_GRASP_OFFSET)
                            and close(setup.get("required_waypoints", {}).get("scripted_ee_initial"), expected_initial)
                            and close(setup.get("required_waypoints", {}).get("grasp"), expected_grasp)
                        )
                    else:
                        nominal_grasp = [expected_start[0], expected_start[1], 0.04]
                        setup_valid = (
                            initial_error <= 0.025 + EPSILON
                            and setup.get("setup_motion") == "cartesian_segments"
                            and setup.get("setup_strategy") == "cartesian_nominal_non_low_x"
                            and close(setup.get("low_x_threshold"), LOW_X_THRESHOLD)
                            and close(setup.get("boundary_x_threshold"), BOUNDARY_X_THRESHOLD)
                            and close(setup.get("boundary_grasp_offset"), BOUNDARY_GRASP_OFFSET)
                            and close(setup.get("grasp_offset"), [0.0, 0.0, 0.0])
                            and close(setup.get("required_waypoints", {}).get("scripted_ee_initial"), expected_initial)
                            and close(setup.get("required_waypoints", {}).get("grasp"), nominal_grasp)
                        )
                    if not setup_valid:
                        errors.append(f"{prefix}: adaptive setup evidence mismatch")
                if not attempt.get("success"):
                    attempt_labels = failure_labels(attempt)
                    labels.update(attempt_labels)
                    participant_labels.update(attempt_labels)
                    labels_by_case[(participant_id, demo_index)].update(attempt_labels)

            if success and rows:
                result = rows[-1].get("details", {}).get("success", {})
                target_error = float(result.get("target_xy_error", math.inf))
                waypoint_error = float(result.get("middle_waypoint_error", math.inf))
                final_tilt = float(result.get("final_cylinder_tilt_degrees", math.inf))
                observed_tilt = float(result.get("maximum_cylinder_tilt_degrees", math.inf))
                linear_speed = norm(result.get("final_box_linear_velocity", [math.inf]))
                angular_speed = norm(result.get("final_box_angular_velocity", [math.inf]))
                ground_error = abs(float(result.get("final_box_position", [0, 0, math.inf])[2]) - 0.035)
                if (
                    result.get("success") is not True
                    or result.get("failure_reasons") != []
                    or target_error > 0.03 + EPSILON
                    or result.get("middle_waypoint_reached") is not True
                    or waypoint_error > 0.04 + EPSILON
                    or final_tilt > 10.0 + EPSILON
                    or linear_speed > 0.02 + EPSILON
                    or angular_speed > 0.10 + EPSILON
                    or ground_error > 0.015 + EPSILON
                ):
                    errors.append(f"{participant_id} demo {demo_index}: accepted threshold failure")
                for key, value in (
                    ("maximum_target_xy_error", target_error),
                    ("maximum_middle_waypoint_error", waypoint_error),
                    ("maximum_final_cylinder_tilt_degrees", final_tilt),
                    ("maximum_observed_cylinder_tilt_degrees", observed_tilt),
                    ("maximum_final_box_linear_speed", linear_speed),
                    ("maximum_final_box_angular_speed", angular_speed),
                    ("maximum_ground_height_error", ground_error),
                ):
                    accepted_metrics[key] = max(accepted_metrics[key], value)

        if data.get("successful_cases") != successes:
            errors.append(f"{participant_id}: successful_cases mismatch")
        participant_summaries[participant_id] = {
            "successful_cases": successes,
            "failed_demo_indices": failed_demos,
            "attempts": len(attempts),
            "failure_labels": dict(sorted(participant_labels.items())),
            "report_sha256": report_hashes[participant_id],
        }
        total_attempts += len(attempts)
        total_successes += successes

    zero_byte_files = sorted(
        str(path.relative_to(root))
        for path in root.rglob("*")
        if path.is_file() and path.stat().st_size == 0
    )
    unexpected_payload_files = sorted(
        str(path.relative_to(root))
        for path in root.rglob("*")
        if path.is_file()
        and path.resolve() != output
        and path.suffix.lower() not in {".json", ".out", ".err"}
    )
    if zero_byte_files:
        errors.append("diagnostic root contains zero-byte files")
    if unexpected_payload_files:
        errors.append("diagnostic root contains non-report/log payload files")

    repo_root = Path(__file__).resolve().parents[2]
    sources = {
        "control_manifest": control_manifest_path,
        "target_manifest_read_only": target_manifest_path,
        "shared_task_read_only": repo_root / "examples" / "main_obstacle_transport.py",
        "control_participants": repo_root / "examples" / "main_obstacle_transport_control_participants.py",
        "diagnostic_runner": repo_root / "examples" / "rebuttal_control_pipeline" / "diagnose_shared_revision.py",
        "diagnostic_wrapper": args.wrapper.resolve(),
        "summary_script": Path(__file__).resolve(),
    }
    expected_cases = len(participants) * len(demos)
    summary = {
        "group": GROUP,
        "formal_data": False,
        "diagnostic": "combined_shared_revision_validation",
        "shared_change_request": "SCR-001/SCR-C001",
        "slurm_job_id": str(args.job_id),
        "participant_order": participants,
        "demo_indices": demos,
        "release_pose": RELEASE_POSE,
        "release_xy_offset": RELEASE_XY_OFFSET,
        "grasp_offset": GRASP_OFFSET,
        "boundary_grasp_offset": BOUNDARY_GRASP_OFFSET,
        "adaptive_low_x_setup": True,
        "low_x_threshold": LOW_X_THRESHOLD,
        "boundary_x_threshold": BOUNDARY_X_THRESHOLD,
        "precise_initial_ik": True,
        "cartesian_scripted_setup": True,
        "object_centered_release": False,
        "participants": participant_summaries,
        "totals": {
            "successful_cases": total_successes,
            "failed_cases": expected_cases - total_successes,
            "expected_cases": expected_cases,
            "attempts": total_attempts,
            "candidate_passed": total_successes == expected_cases,
            "formal_data_usable": False,
        },
        "failure_labels": dict(sorted(labels.items())),
        "failure_labels_by_case": {
            f"{participant_id}:{demo_index}": dict(sorted(case_labels.items()))
            for (participant_id, demo_index), case_labels in sorted(labels_by_case.items())
        },
        "accepted_case_metrics": accepted_metrics,
        "paired_cube_starts_match_target": control_starts == target_starts,
        "zero_byte_files": zero_byte_files,
        "unexpected_payload_files": unexpected_payload_files,
        "validation_errors": errors,
        "validation_passed": not errors,
        "report_sha256": report_hashes,
        "source_sha256": {
            name: sha256(path) for name, path in sources.items() if path.is_file()
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(output)
    print(json.dumps({key: summary[key] for key in ("totals", "failure_labels", "accepted_case_metrics", "validation_errors")}, indent=2, sort_keys=True))
    if errors:
        raise SystemExit("combined shared-revision validation failed")


if __name__ == "__main__":
    main()
