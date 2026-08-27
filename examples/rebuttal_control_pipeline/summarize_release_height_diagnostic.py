#!/usr/bin/env python3
"""Validate and summarize the non-formal all-starts release-height diagnostic."""

import argparse
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path


GROUP = "simulation_control_group"
PARTICIPANTS = [f"C{index:02d}" for index in range(1, 11)]
DEMOS = list(range(30))
SEED = 20260806
RELEASE_Z = 0.08
MAX_ATTEMPTS = 30
EPSILON = 1e-12


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--control-manifest", type=Path, required=True)
    parser.add_argument("--target-manifest", type=Path, required=True)
    parser.add_argument("--job-id", required=True)
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


def vector_norm(values):
    return math.sqrt(sum(float(value) ** 2 for value in values))


def failure_labels(attempt):
    details = attempt.get("details", {})
    reasons = details.get("success", {}).get("failure_reasons") or []
    if reasons:
        return [str(reason) for reason in reasons]
    setup_reason = details.get("setup_details", {}).get("reason")
    if setup_reason:
        return [str(setup_reason)]
    failure_stage = details.get("failure_stage")
    return [str(failure_stage or "task_failure")]


def main():
    args = parse_args()
    root = args.root.resolve()
    control_manifest_path = args.control_manifest.resolve()
    target_manifest_path = args.target_manifest.resolve()
    output = args.output.resolve()
    control_manifest = load_json(control_manifest_path)
    target_manifest = load_json(target_manifest_path)
    errors = []

    control_starts = control_manifest.get("shared_cube_starts")
    target_starts = target_manifest.get("shared_cube_starts")
    if control_starts != target_starts:
        errors.append("Control and Target shared cube-start manifests differ")
    if not isinstance(control_starts, list) or len(control_starts) != len(DEMOS):
        errors.append("Control manifest does not contain exactly 30 shared cube starts")
        control_starts = [{} for _ in DEMOS]

    overall_labels = Counter()
    labels_by_demo = defaultdict(Counter)
    participants = {}
    failed_case_pairs = []
    total_attempts = 0
    total_successes = 0
    accepted_metrics = {
        "maximum_target_xy_error": 0.0,
        "maximum_middle_waypoint_error": 0.0,
        "maximum_final_cylinder_tilt_degrees": 0.0,
        "maximum_observed_cylinder_tilt_degrees": 0.0,
        "maximum_final_box_linear_speed": 0.0,
        "maximum_final_box_angular_speed": 0.0,
        "maximum_ground_height_error": 0.0,
        "maximum_box_obstacle_contact_steps": 0,
        "maximum_robot_obstacle_contact_steps": 0,
    }
    report_hashes = {}

    for participant_id in PARTICIPANTS:
        path = root / f"{participant_id}.json"
        if not path.is_file():
            errors.append(f"missing diagnostic report: {path.name}")
            continue
        report_hashes[participant_id] = sha256(path)
        data = load_json(path)
        prefix = participant_id
        expected_route = "L" if int(participant_id[1:]) <= 5 else "R"
        expected_x_bounds = [0.1, 0.3] if expected_route == "L" else [0.7, 0.9]

        scalar_expectations = {
            "group": GROUP,
            "formal_data": False,
            "diagnostic": "proposed_shared_release_height",
            "shared_change_request": "SCR-001/SCR-C001",
            "seed": SEED,
            "participant_order": [participant_id],
            "demo_indices": DEMOS,
            "release_z": RELEASE_Z,
            "case_count": len(DEMOS),
        }
        for key, expected in scalar_expectations.items():
            if not close(data.get(key), expected):
                errors.append(f"{prefix}: unexpected {key}: {data.get(key)!r}")

        cases = data.get("cases", [])
        attempts = data.get("attempts", [])
        cases_by_demo = {case.get("demo_index"): case for case in cases}
        attempts_by_demo = defaultdict(list)
        for attempt in attempts:
            attempts_by_demo[attempt.get("demo_index")].append(attempt)
        if len(cases) != len(DEMOS) or sorted(cases_by_demo) != DEMOS:
            errors.append(f"{prefix}: cases are not exactly demo indices 0..29")
        if any(index not in DEMOS for index in attempts_by_demo):
            errors.append(f"{prefix}: attempt contains out-of-range demo index")

        participant_successes = 0
        participant_labels = Counter()
        participant_failed_demos = []
        for demo_index in DEMOS:
            case = cases_by_demo.get(demo_index)
            demo_attempts = sorted(
                attempts_by_demo.get(demo_index, []), key=lambda row: row.get("attempt_index", -1)
            )
            if case is None:
                continue
            success = bool(case.get("success"))
            participant_successes += int(success)
            expected_attempt_indices = list(range(len(demo_attempts)))
            actual_attempt_indices = [row.get("attempt_index") for row in demo_attempts]
            if not demo_attempts or actual_attempt_indices != expected_attempt_indices:
                errors.append(f"{prefix} demo {demo_index}: non-contiguous attempt indices")
            if len(demo_attempts) > MAX_ATTEMPTS:
                errors.append(f"{prefix} demo {demo_index}: more than 30 attempts")
            if success:
                if not demo_attempts[-1].get("success"):
                    errors.append(f"{prefix} demo {demo_index}: successful case lacks terminal success")
                if len([row for row in demo_attempts if row.get("success")]) != 1:
                    errors.append(f"{prefix} demo {demo_index}: expected exactly one accepted attempt")
                accepted_index = case.get("accepted_attempt_index")
                if accepted_index != demo_attempts[-1].get("attempt_index"):
                    errors.append(f"{prefix} demo {demo_index}: accepted attempt index mismatch")
                if case.get("accepted") != demo_attempts[-1]:
                    errors.append(f"{prefix} demo {demo_index}: embedded accepted attempt mismatch")
            else:
                participant_failed_demos.append(demo_index)
                failed_case_pairs.append([participant_id, demo_index])
                if len(demo_attempts) != MAX_ATTEMPTS:
                    errors.append(f"{prefix} demo {demo_index}: failure did not exhaust 30 attempts")
                if any(row.get("success") for row in demo_attempts):
                    errors.append(f"{prefix} demo {demo_index}: failed case contains a success")
                if case.get("accepted") is not None or case.get("accepted_attempt_index") is not None:
                    errors.append(f"{prefix} demo {demo_index}: failed case has an accepted attempt")

            expected_start = control_starts[demo_index].get("position")
            for attempt in demo_attempts:
                attempt_index = attempt.get("attempt_index")
                attempt_prefix = f"{prefix} demo {demo_index} attempt {attempt_index}"
                if attempt.get("group") != GROUP or attempt.get("formal_data") is not False:
                    errors.append(f"{attempt_prefix}: group/formal-data marker mismatch")
                if attempt.get("participant_id") != participant_id:
                    errors.append(f"{attempt_prefix}: participant mismatch")
                spec = attempt.get("spec", {})
                if spec.get("demo_index") != demo_index or spec.get("attempt_index") != attempt_index:
                    errors.append(f"{attempt_prefix}: spec indices mismatch")
                if spec.get("condition") != expected_route:
                    errors.append(f"{attempt_prefix}: route mismatch")
                if not close(spec.get("box_initial_position"), expected_start):
                    errors.append(f"{attempt_prefix}: cube start differs from paired manifest")
                expected_ee = (
                    [expected_start[0], expected_start[1], expected_start[2] + 0.10]
                    if isinstance(expected_start, list) and len(expected_start) == 3
                    else None
                )
                if not close(spec.get("scripted_ee_initial_position"), expected_ee):
                    errors.append(f"{attempt_prefix}: scripted frame-0 EE rule mismatch")
                release_pose = spec.get("release_pose", [])
                if not close(release_pose, [0.5, 0.5, RELEASE_Z]):
                    errors.append(f"{attempt_prefix}: release pose mismatch")
                override = spec.get("diagnostic_override", {})
                if (
                    override.get("formal_data") is not False
                    or override.get("field") != "release_pose_z"
                    or not close(override.get("proposed_shared_value"), RELEASE_Z)
                    or override.get("shared_change_request") != "SCR-001/SCR-C001"
                ):
                    errors.append(f"{attempt_prefix}: diagnostic override marker mismatch")
                sampling = spec.get("waypoint_sampling", {})
                waypoint = spec.get("middle_waypoint", [])
                if (
                    sampling.get("sampling") != "independent_uniform_full_route_xz_rectangle"
                    or sampling.get("across_demo_contraction") is not False
                    or sampling.get("position_consistency_guidance") is not False
                    or not close(sampling.get("x_bounds"), expected_x_bounds)
                    or not close(sampling.get("z_bounds"), [0.19, 0.29])
                    or not close(waypoint[1] if len(waypoint) == 3 else None, 0.25)
                    or not (expected_x_bounds[0] <= waypoint[0] <= expected_x_bounds[1])
                    or not (0.19 <= waypoint[2] <= 0.29)
                ):
                    errors.append(f"{attempt_prefix}: independent full-support waypoint mismatch")

                if not attempt.get("success"):
                    labels = failure_labels(attempt)
                    participant_labels.update(labels)
                    overall_labels.update(labels)
                    labels_by_demo[demo_index].update(labels)

            if success and demo_attempts:
                success_details = demo_attempts[-1].get("details", {}).get("success", {})
                target_error = float(success_details.get("target_xy_error", math.inf))
                waypoint_error = float(success_details.get("middle_waypoint_error", math.inf))
                final_tilt = float(success_details.get("final_cylinder_tilt_degrees", math.inf))
                maximum_tilt = float(success_details.get("maximum_cylinder_tilt_degrees", math.inf))
                linear_speed = vector_norm(success_details.get("final_box_linear_velocity", [math.inf]))
                angular_speed = vector_norm(success_details.get("final_box_angular_velocity", [math.inf]))
                final_position = success_details.get("final_box_position", [0.0, 0.0, math.inf])
                ground_error = abs(float(final_position[2]) - 0.035)
                if (
                    success_details.get("success") is not True
                    or success_details.get("failure_reasons") != []
                    or target_error > 0.03 + EPSILON
                    or success_details.get("middle_waypoint_reached") is not True
                    or waypoint_error > 0.04 + EPSILON
                    or final_tilt > 10.0 + EPSILON
                    or linear_speed > 0.02 + EPSILON
                    or angular_speed > 0.10 + EPSILON
                    or ground_error > 0.015 + EPSILON
                ):
                    errors.append(f"{prefix} demo {demo_index}: accepted threshold check failed")
                accepted_metrics["maximum_target_xy_error"] = max(
                    accepted_metrics["maximum_target_xy_error"], target_error
                )
                accepted_metrics["maximum_middle_waypoint_error"] = max(
                    accepted_metrics["maximum_middle_waypoint_error"], waypoint_error
                )
                accepted_metrics["maximum_final_cylinder_tilt_degrees"] = max(
                    accepted_metrics["maximum_final_cylinder_tilt_degrees"], final_tilt
                )
                accepted_metrics["maximum_observed_cylinder_tilt_degrees"] = max(
                    accepted_metrics["maximum_observed_cylinder_tilt_degrees"], maximum_tilt
                )
                accepted_metrics["maximum_final_box_linear_speed"] = max(
                    accepted_metrics["maximum_final_box_linear_speed"], linear_speed
                )
                accepted_metrics["maximum_final_box_angular_speed"] = max(
                    accepted_metrics["maximum_final_box_angular_speed"], angular_speed
                )
                accepted_metrics["maximum_ground_height_error"] = max(
                    accepted_metrics["maximum_ground_height_error"], ground_error
                )
                for key in ("maximum_box_obstacle_contact_steps", "maximum_robot_obstacle_contact_steps"):
                    source_key = key.removeprefix("maximum_")
                    accepted_metrics[key] = max(
                        accepted_metrics[key], int(success_details.get(source_key, 0))
                    )

        if data.get("successful_cases") != participant_successes:
            errors.append(f"{prefix}: successful_cases disagrees with cases")
        total_attempts += len(attempts)
        total_successes += participant_successes
        participants[participant_id] = {
            "attempts": len(attempts),
            "successful_cases": participant_successes,
            "failed_cases": len(participant_failed_demos),
            "failed_demo_indices": participant_failed_demos,
            "failure_labels": dict(sorted(participant_labels.items())),
            "report_sha256": report_hashes[participant_id],
        }

    unexpected_payload_files = sorted(
        str(path.relative_to(root))
        for path in root.rglob("*")
        if path.is_file()
        and path.resolve() != output
        and path.suffix.lower() not in {".json", ".out", ".err"}
    )
    if unexpected_payload_files:
        errors.append("diagnostic root contains non-report/log payload files")

    failed_demo_sets = {
        participant_id: row["failed_demo_indices"] for participant_id, row in participants.items()
    }
    common_failed_demo_indices = (
        sorted(set.intersection(*(set(values) for values in failed_demo_sets.values())))
        if len(failed_demo_sets) == len(PARTICIPANTS)
        else []
    )
    proposed_fix_passed = total_successes == 300
    repo_root = Path(__file__).resolve().parents[2]
    source_paths = {
        "control_manifest": control_manifest_path,
        "target_manifest_read_only": target_manifest_path,
        "shared_task_read_only": repo_root / "examples" / "main_obstacle_transport.py",
        "control_participants": repo_root / "examples" / "main_obstacle_transport_control_participants.py",
        "diagnostic_runner": repo_root / "examples" / "rebuttal_control_pipeline" / "diagnose_release_height.py",
        "diagnostic_wrapper": repo_root / "examples" / "rebuttal_control_pipeline" / "diagnose_release_height_array.sbatch",
        "summary_script": Path(__file__).resolve(),
    }
    summary = {
        "group": GROUP,
        "formal_data": False,
        "diagnostic": "proposed_shared_release_height_all_participants_all_starts",
        "shared_change_request": "SCR-001/SCR-C001",
        "slurm_array_job_id": str(args.job_id),
        "seed": SEED,
        "release_z": RELEASE_Z,
        "participants": participants,
        "totals": {
            "successful_cases": total_successes,
            "failed_cases": 300 - total_successes,
            "expected_cases": 300,
            "attempts": total_attempts,
            "proposed_fix_passed": proposed_fix_passed,
            "formal_data_usable": False,
        },
        "common_failed_demo_indices": common_failed_demo_indices,
        "failed_case_pairs": failed_case_pairs,
        "failure_labels": dict(sorted(overall_labels.items())),
        "failure_labels_by_demo": {
            str(index): dict(sorted(labels.items())) for index, labels in sorted(labels_by_demo.items())
        },
        "accepted_case_metrics": accepted_metrics,
        "paired_cube_starts_match_target": control_starts == target_starts,
        "unexpected_payload_files": unexpected_payload_files,
        "validation_errors": errors,
        "validation_passed": not errors,
        "report_sha256": report_hashes,
        "source_sha256": {
            name: sha256(path) for name, path in source_paths.items() if path.is_file()
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(output)
    print(json.dumps({key: summary[key] for key in ("totals", "common_failed_demo_indices", "failure_labels", "validation_errors")}, indent=2, sort_keys=True))
    if errors:
        raise SystemExit("release-height diagnostic summary validation failed")


if __name__ == "__main__":
    main()
