#!/usr/bin/env python3
"""Validate and summarize the complete Control pipeline with Target comparison."""

import argparse
import csv
import hashlib
import io
import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


GROUP = "simulation_control_group"
TARGET_GROUP = "simulation_target_group"
SEED = 20260806
EVALUATION_SEED = 20260807
TARGET_XY_TOLERANCE = 0.10
PAIRED_MANIFEST_SHA256 = (
    "10dbbe16da06b4013899e350fece05687abc8c45471b584ac5a2473a0e486dad"
)
PARTICIPANTS = [f"C{index:02d}" for index in range(1, 11)]
ROUTES = {
    participant: ("L" if int(participant[1:]) <= 5 else "R")
    for participant in PARTICIPANTS
}
OUTPUT_NAMES = [
    "final_results.json",
    "participant_edsr.csv",
    "rollout_results.csv",
    "validation_report.json",
    "experiment_manifest.json",
    "participant_edsr.png",
    "video_index.json",
    "rebuttal_factual_summary.txt",
]


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path):
    with Path(path).open("r", encoding="utf-8") as stream:
        return json.load(stream)


def json_bytes(payload):
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


def write_exclusive(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(payload)


def artifact(path):
    path = Path(path).resolve()
    return {"path": str(path), "sha256": sha256(path), "size_bytes": path.stat().st_size}


def q(value):
    return round(float(value), 6)


def stats(values):
    values = np.asarray(values, dtype=float)
    if values.size < 2 or not np.isfinite(values).all():
        raise ValueError("Participant statistics require at least two finite values")
    return {
        "n_participants": int(values.size),
        "mean": q(np.mean(values)),
        "sample_standard_deviation": q(np.std(values, ddof=1)),
        "ddof": 1,
    }


def csv_bytes(fieldnames, rows):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8")


def failure_labels(row):
    if row["success"]:
        return []
    labels = list(row["success_details"].get("failure_reasons", []))
    termination = row.get("termination_reason")
    if termination in {"policy_timeout", "nonfinite_or_malformed_policy_action"}:
        labels.append(termination)
    if not row.get("policy_started"):
        labels.append("grasp_setup_infrastructure_issue")
    return sorted(set(labels))


def primary_failure(row, labels):
    if not row.get("policy_started"):
        return "grasp_setup_infrastructure_issue"
    for label, primary in (
        ("nonfinite_or_malformed_policy_action", "nonfinite_policy_action"),
        ("cylinder_toppled", "cylinder_topple"),
        ("target_miss", "target_miss"),
        ("policy_timeout", "policy_timeout"),
        ("box_not_settled", "box_not_settled"),
    ):
        if label in labels:
            return primary
    return "other_policy_failure"


def plot_bytes(rows, overall, target_mean):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    buffer = io.BytesIO()
    figure, axis = plt.subplots(figsize=(9.2, 4.8))
    colors = ["#4c78a8" if row["route"] == "L" else "#f58518" for row in rows]
    axis.bar([row["participant_id"] for row in rows], [row["edsr"] for row in rows], color=colors)
    axis.axhline(overall["mean"], color="black", linestyle="--", label=f"Control mean={overall['mean']:.3f}")
    axis.axhline(target_mean, color="#54a24b", linestyle=":", label=f"Target mean={target_mean:.3f}")
    axis.set_ylim(0.0, 1.05)
    axis.set_ylabel("EDSR (successes / 10 paired rollouts)")
    axis.set_xlabel("Control participant-level policy")
    axis.set_title("Control participant-level policy EDSR")
    axis.grid(axis="y", alpha=0.25)
    axis.legend(loc="best")
    figure.tight_layout()
    figure.savefig(buffer, format="png", dpi=180)
    plt.close(figure)
    return buffer.getvalue()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--control-root", type=Path, required=True)
    parser.add_argument("--raw-root", type=Path, required=True)
    parser.add_argument("--helper-root", type=Path, required=True)
    parser.add_argument("--target-root", type=Path, required=True)
    args = parser.parse_args()
    control_root = args.control_root.resolve()
    target_root = args.target_root.resolve()
    raw_root = args.raw_root.resolve()
    analysis_root = control_root / "analysis"
    hdf5_root = control_root / "hdf5"
    models_root = control_root / "models"
    rollout_root = control_root / "policy_rollouts"
    paired_path = target_root / "analysis/paired_rollout_specs.json"
    paired_sidecar_path = target_root / "analysis/paired_rollout_specs.sha256.json"
    output_paths = {name: analysis_root / name for name in OUTPUT_NAMES}
    existing = [str(path) for path in output_paths.values() if path.exists()]
    if existing:
        raise FileExistsError(f"Refusing to overwrite final Control analysis: {existing}")

    required = {
        "raw_configuration": raw_root / "protocol_configuration.json",
        "raw_validation": raw_root / "validation_report.json",
        "hdf5_validation": hdf5_root / "validation_report.json",
        "raw_to_hdf5_manifest": hdf5_root / "raw_to_hdf5_manifest.json",
        "training_manifest": models_root / "training_experiment_manifest.json",
        "model_validation": models_root / "model_validation_report.json",
        "checkpoints": models_root / "selected_checkpoints_manifest.json",
        "paired_rollout_specs": paired_path,
        "paired_rollout_specs_sidecar": paired_sidecar_path,
        "target_hdf5_manifest": target_root / "hdf5/raw_to_hdf5_manifest.json",
        "target_raw_validation": target_root
        / "full_seed20260806/protocol_release_z008_target_tol010_start_replenish/validation_report.json",
        "target_training_manifest": target_root / "models/training_experiment_manifest.json",
        "target_final_results": target_root / "analysis/final_results.json",
        "target_validation": target_root / "analysis/validation_report.json",
    }
    for path in required.values():
        if not path.is_file():
            raise FileNotFoundError(path)
    upstream = {name: artifact(path) for name, path in required.items()}
    raw_configuration = load_json(required["raw_configuration"])
    raw_validation = load_json(required["raw_validation"])
    hdf5_validation = load_json(required["hdf5_validation"])
    hdf5_manifest = load_json(required["raw_to_hdf5_manifest"])
    training = load_json(required["training_manifest"])
    model_validation = load_json(required["model_validation"])
    checkpoints = load_json(required["checkpoints"])
    paired = load_json(paired_path)
    paired_sidecar = load_json(paired_sidecar_path)
    target_hdf5 = load_json(required["target_hdf5_manifest"])
    target_raw_validation = load_json(required["target_raw_validation"])
    target_training = load_json(required["target_training_manifest"])
    target_results = load_json(required["target_final_results"])
    target_validation = load_json(required["target_validation"])
    errors = []

    def check(condition, message):
        if not condition:
            errors.append(message)

    check(raw_configuration.get("group") == GROUP, "wrong_raw_configuration_group")
    alignment = raw_configuration.get("target_alignment", {})
    check(alignment.get("release_ee_z_m") == 0.08, "raw_configuration_release_z_mismatch")
    check(alignment.get("target_xy_tolerance_m") == TARGET_XY_TOLERANCE, "raw_configuration_target_tolerance_mismatch")
    check(alignment.get("cylinder_tilt_tolerance_degrees") == 10.0, "raw_configuration_tilt_mismatch")
    check(alignment.get("contacts_are_diagnostic_only") is True, "raw_configuration_contact_semantics_mismatch")
    check(alignment.get("dual_offset_or_cartesian_diagnostic_revision_applied") is False, "diagnostic_revision_entered_formal_protocol")
    check(raw_validation.get("group") == GROUP and raw_validation.get("passed"), "raw_validation_not_passed")
    check(raw_validation.get("counts", {}).get("participants") == 10, "raw_participant_count_not_10")
    check(raw_validation.get("counts", {}).get("successful_demos") == 300, "raw_demo_count_not_300")
    check(raw_validation.get("counts", {}).get("scripted_frames_in_success_raw") == 0, "raw_contains_scripted_frames")
    for key, expected in {
        "target_xy_error_max_m": TARGET_XY_TOLERANCE,
        "final_cylinder_tilt_max_degrees": 10.0,
        "middle_waypoint_realised_error_max_m": 0.04,
        "transport_height_error_max_m": 0.015,
        "fixed_release_ee_z_m": 0.08,
    }.items():
        check(raw_validation.get("thresholds", {}).get(key) == expected, f"raw_threshold_mismatch:{key}")
        check(target_raw_validation.get("thresholds", {}).get(key) == expected, f"target_raw_threshold_mismatch:{key}")
    check(target_raw_validation.get("passed") is True, "target_raw_validation_not_passed")
    check(hdf5_validation.get("group") == GROUP and hdf5_validation.get("passed"), "hdf5_validation_not_passed")
    check(hdf5_validation.get("counts", {}).get("participant_hdf5") == 10, "hdf5_file_count_not_10")
    check(hdf5_validation.get("counts", {}).get("trajectories") == 300, "hdf5_trajectory_count_not_300")
    check(hdf5_manifest.get("schema") == target_hdf5.get("schema"), "target_control_hdf5_schema_mismatch")
    check(hdf5_manifest.get("split") == target_hdf5.get("split"), "target_control_hdf5_split_mismatch")
    check(training.get("group") == GROUP, "wrong_training_group")
    check(training.get("uniform_training_protocol_sha256") == target_training.get("uniform_training_protocol_sha256"), "target_control_training_protocol_hash_mismatch")
    check(training.get("training_budget") == target_training.get("training_budget"), "target_control_training_budget_mismatch")
    check(training.get("checkpoint_selection_rule") == target_training.get("checkpoint_selection_rule"), "target_control_checkpoint_rule_mismatch")
    check(model_validation.get("group") == GROUP and model_validation.get("passed"), "model_validation_not_passed")
    check(model_validation.get("checkpoint_count") == 10, "checkpoint_count_not_10")
    check(checkpoints.get("group") == GROUP and checkpoints.get("participant_order") == PARTICIPANTS, "checkpoint_manifest_identity_mismatch")
    check(sha256(paired_path) == PAIRED_MANIFEST_SHA256, "paired_manifest_hash_mismatch")
    check(paired_sidecar.get("file_sha256") == PAIRED_MANIFEST_SHA256, "paired_sidecar_hash_mismatch")
    check(paired.get("group") == TARGET_GROUP and paired.get("evaluation_seed") == EVALUATION_SEED, "paired_manifest_identity_mismatch")
    check(paired.get("frozen_task", {}).get("target_xy_tolerance_m") == TARGET_XY_TOLERANCE, "paired_target_tolerance_mismatch")
    check(paired.get("frozen_task", {}).get("contacts_are_diagnostic_only") is True, "paired_contact_semantics_mismatch")
    check(len(paired.get("eval_cases", [])) == 10, "paired_case_count_not_10")
    check(target_validation.get("passed") is True, "target_final_validation_not_passed")
    spec_by_id = {int(row["eval_case_id"]): row for row in paired.get("eval_cases", [])}
    check(set(spec_by_id) == set(range(10)), "paired_case_ids_invalid")

    actual_dirs = sorted(
        path.name
        for path in rollout_root.iterdir()
        if path.is_dir() and path.name.startswith("C")
    ) if rollout_root.is_dir() else []
    check(actual_dirs == PARTICIPANTS, f"rollout_participant_dirs_mismatch:{actual_dirs}")
    all_rows = []
    infrastructure_records = []
    participant_summaries = {}
    for participant in PARTICIPANTS:
        participant_dir = rollout_root / participant
        summary_path = participant_dir / "summary.json"
        if not summary_path.is_file():
            errors.append(f"missing_rollout_summary:{participant}")
            continue
        summary = load_json(summary_path)
        participant_summaries[participant] = summary
        rollout_dir = participant_dir / "rollouts"
        expected_names = {f"rollout_{case_id:02d}.json" for case_id in range(10)}
        actual_names = {path.name for path in rollout_dir.glob("*.json")} if rollout_dir.is_dir() else set()
        check(actual_names == expected_names, f"rollout_json_set_mismatch:{participant}")
        rows = []
        for case_id in range(10):
            path = rollout_dir / f"rollout_{case_id:02d}.json"
            if not path.is_file():
                continue
            row = load_json(path)
            rows.append(row)
            all_rows.append(row)
            prefix = f"{participant}:{case_id}"
            check(row.get("group") == GROUP and row.get("participant_id") == participant, f"rollout_identity:{prefix}")
            check(row.get("eval_case_id") == case_id and row.get("participant_route") == ROUTES[participant], f"rollout_case_route:{prefix}")
            check(row.get("valid_scientific_result") is True and row.get("policy_started") is True, f"invalid_scientific_result:{prefix}")
            check(row.get("execution_order_valid") is True and row.get("scripted_transport_used") is False, f"execution_boundary:{prefix}")
            check(row.get("policy_call_count", 0) > 0, f"no_policy_call:{prefix}")
            check(row.get("paired_manifest_sha256") == PAIRED_MANIFEST_SHA256, f"wrong_paired_hash:{prefix}")
            check(row.get("paired_spec") == spec_by_id.get(case_id), f"wrong_paired_spec:{prefix}")
            checkpoint = checkpoints.get("checkpoints", {}).get(participant, {})
            check(row.get("checkpoint_sha256") == checkpoint.get("sha256"), f"wrong_checkpoint:{prefix}")
            check(row.get("success") == row.get("success_details", {}).get("success"), f"success_mismatch:{prefix}")
            for key in (
                "target_xy_error",
                "final_cylinder_tilt_degrees",
                "maximum_cylinder_tilt_degrees",
                "box_obstacle_contact_steps",
                "robot_obstacle_contact_steps",
            ):
                value = row.get(key)
                check(isinstance(value, (int, float)) and math.isfinite(float(value)), f"nonfinite_metric:{prefix}:{key}")
            if row.get("success"):
                check(row["target_xy_error"] <= TARGET_XY_TOLERANCE, f"success_target_threshold:{prefix}")
                check(row["final_cylinder_tilt_degrees"] <= 10.0, f"success_tilt_threshold:{prefix}")
            video = Path(row.get("video_path", ""))
            check(video.is_file() and video.stat().st_size > 48, f"missing_video:{prefix}:{video}")
        check(summary.get("group") == GROUP and summary.get("participant_id") == participant, f"summary_identity:{participant}")
        check(summary.get("valid_rollout_count") == 10 and summary.get("rollouts") == rows, f"summary_rows:{participant}")
        successes = sum(int(row.get("success", False)) for row in rows)
        check(summary.get("success_count") == successes and summary.get("edsr") == successes / 10.0, f"summary_edsr:{participant}")
        failure_dir = participant_dir / "infrastructure_failures"
        if failure_dir.is_dir():
            infrastructure_records.extend(load_json(path) for path in sorted(failure_dir.glob("*.json")))
    pairs = [(row.get("participant_id"), row.get("eval_case_id")) for row in all_rows]
    check(len(all_rows) == 100 and len(set(pairs)) == 100, f"rollout_pair_count:{len(all_rows)}:{len(set(pairs))}")
    check(not infrastructure_records, f"infrastructure_failure_records_present:{len(infrastructure_records)}")
    if errors:
        raise RuntimeError("Final Control validation failed:\n" + "\n".join(errors))

    participant_rows = []
    for participant in PARTICIPANTS:
        rows = [row for row in all_rows if row["participant_id"] == participant]
        success_count = sum(int(row["success"]) for row in rows)
        participant_rows.append(
            {
                "participant_id": participant,
                "route": ROUTES[participant],
                "success_count": success_count,
                "rollout_count": 10,
                "edsr": q(success_count / 10.0),
            }
        )
    overall = stats([row["edsr"] for row in participant_rows])
    left = stats([row["edsr"] for row in participant_rows if row["route"] == "L"])
    right = stats([row["edsr"] for row in participant_rows if row["route"] == "R"])
    target_stats = target_results["participant_edsr_statistics"]

    primary = Counter()
    multilabel = Counter()
    rollout_csv_rows = []
    video_rows = []
    representative_success = set()
    for row in sorted(all_rows, key=lambda item: (item["participant_id"], item["eval_case_id"])):
        labels = failure_labels(row)
        primary_label = "success" if row["success"] else primary_failure(row, labels)
        if not row["success"]:
            primary[primary_label] += 1
            multilabel.update(labels)
        participant = row["participant_id"]
        representative = (row["success"] and participant not in representative_success) or not row["success"]
        if row["success"]:
            representative_success.add(participant)
        route_behavior = row["route_behavior"]
        rollout_csv_rows.append(
            {
                "participant_id": participant,
                "participant_route": row["participant_route"],
                "eval_case_id": row["eval_case_id"],
                "success": int(row["success"]),
                "termination_reason": row["termination_reason"],
                "primary_failure": primary_label,
                "failure_labels": ";".join(labels),
                "target_xy_error": q(row["target_xy_error"]),
                "final_cylinder_tilt_degrees": q(row["final_cylinder_tilt_degrees"]),
                "maximum_cylinder_tilt_degrees": q(row["maximum_cylinder_tilt_degrees"]),
                "box_obstacle_contact_steps": row["box_obstacle_contact_steps"],
                "robot_obstacle_contact_steps": row["robot_obstacle_contact_steps"],
                "realised_route": route_behavior["realised_route"],
                "minimum_box_cylinder_xy_distance": q(route_behavior["minimum_box_cylinder_xy_distance"]),
                "checkpoint_sha256": row["checkpoint_sha256"],
                "paired_manifest_sha256": row["paired_manifest_sha256"],
                "video_path": row["video_path"],
            }
        )
        video_rows.append(
            {
                "participant_id": participant,
                "eval_case_id": row["eval_case_id"],
                "success": row["success"],
                "primary_failure": primary_label,
                "representative": representative,
                "path": row["video_path"],
                "sha256": sha256(row["video_path"]),
            }
        )

    target_errors = np.asarray([row["target_xy_error"] for row in all_rows])
    tilts = np.asarray([row["final_cylinder_tilt_degrees"] for row in all_rows])
    raw_spread = {
        participant: {
            key: raw_validation["participant_reports"][participant].get(key)
            for key in ("unique_waypoints", "x_span", "z_span")
        }
        for participant in PARTICIPANTS
    }
    diagnostics = {
        "target_xy_error_m": {"mean": q(np.mean(target_errors)), "median": q(np.median(target_errors)), "min": q(np.min(target_errors)), "max": q(np.max(target_errors))},
        "final_cylinder_tilt_degrees": {"mean": q(np.mean(tilts)), "median": q(np.median(tilts)), "min": q(np.min(tilts)), "max": q(np.max(tilts))},
        "contact_steps": {
            "box_obstacle_total": int(sum(row["box_obstacle_contact_steps"] for row in all_rows)),
            "robot_obstacle_total": int(sum(row["robot_obstacle_contact_steps"] for row in all_rows)),
            "contacts_are_diagnostic_only": True,
        },
        "accepted_training_waypoint_spread": raw_spread,
    }
    success_total = sum(int(row["success"]) for row in all_rows)
    comparison = {
        "target_overall": target_stats["overall"],
        "control_overall": overall,
        "control_minus_target_mean": q(overall["mean"] - target_stats["overall"]["mean"]),
        "target_L": target_stats["L"],
        "control_L": left,
        "control_minus_target_L_mean": q(left["mean"] - target_stats["L"]["mean"]),
        "target_R": target_stats["R"],
        "control_R": right,
        "control_minus_target_R_mean": q(right["mean"] - target_stats["R"]["mean"]),
        "same_demo_budget": True,
        "same_hdf5_schema_and_split": True,
        "same_uniform_training_protocol": True,
        "same_checkpoint_selection_rule": True,
        "same_paired_rollout_manifest": True,
        "same_physical_and_success_protocol": True,
        "descriptive_only_no_independence_claim_for_100_rollouts": True,
    }
    final_results = {
        "schema_version": 1,
        "group": GROUP,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "inferential_unit": "participant-level policy",
        "success_protocol": {
            "scope": GROUP,
            "release_ee_z_m": 0.08,
            "target_xy_tolerance_m": TARGET_XY_TOLERANCE,
            "criterion": "target_xy_error<=0.10 and box_settled and cylinder_tilt<=10deg",
            "contacts_are_diagnostic_only": True,
        },
        "participant_results": participant_rows,
        "participant_edsr_statistics": {"overall": overall, "L": left, "R": right},
        "raw_rollout_counts": {"total": 100, "successes": success_total, "failures": 100 - success_total},
        "failure_taxonomy": {"primary_exclusive": dict(sorted(primary.items())), "multi_label": dict(sorted(multilabel.items()))},
        "diagnostics": diagnostics,
        "target_control_comparison": comparison,
    }
    summary_text = (
        f"Control participant-level EDSR (n=10): {overall['mean']:.6f} ± {overall['sample_standard_deviation']:.6f} sample SD (ddof=1).\n"
        f"L (C01–C05): {left['mean']:.6f} ± {left['sample_standard_deviation']:.6f}.\n"
        f"R (C06–C10): {right['mean']:.6f} ± {right['sample_standard_deviation']:.6f}.\n"
        f"Raw paired outcomes: {success_total}/100 successes.\n"
        f"Target overall: {target_stats['overall']['mean']:.6f} ± {target_stats['overall']['sample_standard_deviation']:.6f}; Control−Target mean={comparison['control_minus_target_mean']:.6f}.\n"
        "Both groups use release z=0.08, target radius=0.10 m, tilt<=10 deg, diagnostic-only contacts, the same learner/checkpoint rule, and the exact same paired rollout manifest.\n"
    )

    helper_names = (
        "control_protocol.py",
        "collect_control_aligned.py",
        "validate_control_aligned_raw.py",
        "convert_control_hdf5.py",
        "validate_control_hdf5.py",
        "prepare_control_training.py",
        "train_control_one.py",
        "validate_control_models.py",
        "evaluate_control_policy.py",
        "analyze_control_results.py",
    )
    helpers = {name: artifact(args.helper_root.resolve() / name) for name in helper_names}
    experiment_manifest = {
        "schema_version": 1,
        "group": GROUP,
        "collection_seed": SEED,
        "evaluation_seed": EVALUATION_SEED,
        "participant_order": PARTICIPANTS,
        "routes": ROUTES,
        "success_protocol": final_results["success_protocol"],
        "control_teaching_data_manipulation": "independent full-support L/R waypoint x-z sampling without centre or contraction",
        "paired_rollout_manifest": artifact(paired_path),
        "stage_artifacts": upstream,
        "helpers": helpers,
        "raw_root": str(raw_root),
        "hdf5_root": str(hdf5_root),
        "models_root": str(models_root),
        "policy_rollout_root": str(rollout_root),
        "analysis_root": str(analysis_root),
        "statistics_contract": {"unit": "participant-level policy", "edsr_denominator_per_participant": 10, "sample_standard_deviation_ddof": 1},
        "target_control_comparison_contract": comparison,
    }
    participant_csv = csv_bytes(
        ["participant_id", "route", "success_count", "rollout_count", "edsr"],
        participant_rows,
    )
    rollout_csv = csv_bytes(list(rollout_csv_rows[0]), rollout_csv_rows)
    video_index = {
        "group": GROUP,
        "representative_rule": "first success per participant plus every failed rollout",
        "videos": video_rows,
    }
    planned = {
        "final_results.json": json_bytes(final_results),
        "participant_edsr.csv": participant_csv,
        "rollout_results.csv": rollout_csv,
        "experiment_manifest.json": json_bytes(experiment_manifest),
        "participant_edsr.png": plot_bytes(participant_rows, overall, target_stats["overall"]["mean"]),
        "video_index.json": json_bytes(video_index),
        "rebuttal_factual_summary.txt": summary_text.encode("utf-8"),
    }
    validation_report = {
        "schema_version": 1,
        "group": GROUP,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "passed": True,
        "errors": [],
        "counts": {
            "raw_successful_demos": 300,
            "participant_hdf5": 10,
            "hdf5_trajectories": 300,
            "loadable_inference_smoked_checkpoints": 10,
            "paired_specs": 10,
            "valid_policy_rollouts": 100,
            "unique_participant_eval_case_pairs": 100,
            "participant_edsr_values": 10,
        },
        "cross_checks": {
            "statistics_recomputed_from_ten_saved_edsr": True,
            "sample_standard_deviation_ddof": 1,
            "all_rollouts_reference_exact_target_paired_manifest_hash": True,
            "all_rollouts_reference_correct_control_checkpoint_hash": True,
            "all_rollout_videos_present_nonempty": True,
            "no_scripted_transport_in_policy_rollouts": True,
            "target_control_demo_budget_equal": True,
            "target_control_hdf5_schema_split_equal": True,
            "target_control_training_protocol_equal": True,
            "target_control_checkpoint_rule_equal": True,
            "target_control_physical_success_protocol_equal": True,
        },
        "upstream_artifacts": upstream,
        "planned_output_sha256": {name: hashlib.sha256(payload).hexdigest() for name, payload in planned.items()},
    }
    planned["validation_report.json"] = json_bytes(validation_report)
    for name in OUTPUT_NAMES:
        write_exclusive(output_paths[name], planned[name])
    print(json.dumps(final_results, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
