#!/usr/bin/env python3
"""Validate 200 Control-Bimodal rollouts and create route-choice/success statistics."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

EXAMPLES_ROOT = Path(__file__).resolve().parents[1]
if str(EXAMPLES_ROOT) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_ROOT))

from rebuttal_control_bimodal_pipeline.common import (  # noqa: E402
    BIMODAL_GROUP,
    EXPECTED_NORMALIZED_TRAINING_PROTOCOL_SHA256,
    MATCHED_BIMODAL_PARTICIPANTS,
    verify_frozen_inputs,
)


GROUP = "simulation_control_bimodal_group"
TARGET_GROUP = "simulation_target_group"
PARTICIPANTS = [f"CB{index:02d}" for index in range(1, 11)]
TARGET_SPEC_SHA256 = "10dbbe16da06b4013899e350fece05687abc8c45471b584ac5a2473a0e486dad"
TARGET_XY_TOLERANCE = 0.10
# Preserve both the originally frozen gate and the user-authorized engineering
# interpretation.  The latter was explicitly approved after rollout, so the
# generated artifacts must disclose that it is a post-rollout amendment rather
# than silently rewriting the preregistered contract.
ORIGINAL_REPEAT_TRANSLATION_TOLERANCE_METRES = 1e-5
ORIGINAL_REPEAT_ORIENTATION_TOLERANCE_DEGREES = 0.01
REPEAT_TRANSLATION_TOLERANCE_METRES = 2e-3
REPEAT_ORIENTATION_TOLERANCE_DEGREES = 3.0
REPEAT_PROTOCOL_AMENDMENT = {
    "status": "post_rollout_user_authorized_protocol_amendment",
    "authorized_local_date": "2026-08-08",
    "rationale": (
        "Millimetre-scale contact-pose variation is expected in real rollouts and "
        "does not invalidate otherwise matched scripted setup commands."
    ),
    "original_translation_tolerance_metres": ORIGINAL_REPEAT_TRANSLATION_TOLERANCE_METRES,
    "original_orientation_tolerance_degrees": ORIGINAL_REPEAT_ORIENTATION_TOLERANCE_DEGREES,
    "amended_translation_tolerance_metres": REPEAT_TRANSLATION_TOLERANCE_METRES,
    "amended_orientation_tolerance_degrees": REPEAT_ORIENTATION_TOLERANCE_DEGREES,
    "thresholds_amended_after_rollout": True,
    "original_gate_result_retained": True,
    "rollouts_rerun_or_replaced": False,
}
OUTPUT_NAMES = [
    "final_results.json",
    "participant_success_rates.csv",
    "route_choice_summary.csv",
    "rollout_results.csv",
    "validation_report.json",
    "experiment_manifest.json",
    "route_success_summary.png",
    "video_index.json",
    "factual_summary.txt",
    "bimodal_comparison.json",
    "bimodal_comparison.csv",
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
        stream.flush()
        os.fsync(stream.fileno())


def q(value):
    return round(float(value), 6)


def rate(numerator, denominator):
    return None if denominator == 0 else q(numerator / denominator)


def statistics(values):
    values = np.asarray(values, dtype=float)
    if values.size != 10:
        raise ValueError("Participant-level statistics require exactly ten policies")
    return {
        "n_participant_policies": 10,
        "mean": q(np.mean(values)),
        "sample_standard_deviation": q(np.std(values, ddof=1)),
        "ddof": 1,
    }


def csv_payload(fieldnames, rows):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8")


def finite_tree(value):
    if isinstance(value, dict):
        return all(finite_tree(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return all(finite_tree(item) for item in value)
    if isinstance(value, float):
        return math.isfinite(value)
    return True


def vector_distance(left, right, expected_size):
    """Return Euclidean distance, or infinity for malformed/nonfinite vectors."""
    try:
        left = np.asarray(left, dtype=float)
        right = np.asarray(right, dtype=float)
    except (TypeError, ValueError):
        return float("inf")
    if left.shape != (expected_size,) or right.shape != (expected_size,):
        return float("inf")
    if not np.all(np.isfinite(left)) or not np.all(np.isfinite(right)):
        return float("inf")
    return float(np.linalg.norm(left - right))


def quaternion_distance_degrees(left, right):
    """Return the sign-invariant shortest angular distance between quaternions."""
    try:
        left = np.asarray(left, dtype=float)
        right = np.asarray(right, dtype=float)
    except (TypeError, ValueError):
        return float("inf")
    if left.shape != (4,) or right.shape != (4,):
        return float("inf")
    left_norm = float(np.linalg.norm(left))
    right_norm = float(np.linalg.norm(right))
    if (
        not np.all(np.isfinite(left))
        or not np.all(np.isfinite(right))
        or left_norm <= 0.0
        or right_norm <= 0.0
    ):
        return float("inf")
    cosine = float(np.clip(abs(np.dot(left, right)) / (left_norm * right_norm), -1.0, 1.0))
    return float(math.degrees(2.0 * math.acos(cosine)))


def repeat_threshold_exceedances(distances, translation_tolerance, orientation_tolerance):
    """Return every repeat metric outside the supplied engineering envelope."""
    exceeded = {}
    for key, value in distances.items():
        tolerance = (
            orientation_tolerance
            if key.endswith("orientation_delta_degrees")
            else translation_tolerance
        )
        if not math.isfinite(value) or value > tolerance:
            exceeded[key] = value
    return exceeded


def policy_sampling_seed(participant, case_id, repeat_index):
    return 20260807 + int(participant[2:]) * 10000 + int(case_id) * 10 + int(repeat_index)


def recompute_route(trace, task):
    points = np.asarray([row["box_position"] for row in trace], dtype=float)
    if len(points) == 0:
        return {"realised_route": "indeterminate", "reason": "empty_policy_trace"}
    obstacle_xy = np.asarray(task.OBSTACLE_XY, dtype=float)
    half_width = float(task.OBSTACLE_RADIUS + task.BOX_HALF_EXTENT)
    in_band = np.abs(points[:, 1] - obstacle_xy[1]) <= half_width
    closest = int(np.argmin(np.abs(points[:, 1] - obstacle_xy[1])))
    x_reference = (
        float(np.median(points[in_band, 0])) if np.any(in_band) else float(points[closest, 0])
    )
    reached = bool(np.any(in_band))
    return {
        "realised_route": ("L" if x_reference < obstacle_xy[0] else "R") if reached else "indeterminate",
        "crossed_obstacle_y_band": reached,
        "obstacle_y_band_half_width": half_width,
        "box_x_reference": x_reference,
        "box_x_at_closest_obstacle_y": float(points[closest, 0]),
        "box_y_at_closest_obstacle_y": float(points[closest, 1]),
        "minimum_box_cylinder_xy_distance": float(
            np.min(np.linalg.norm(points[:, :2] - obstacle_xy, axis=1))
        ),
    }


def recompute_success(row, task):
    """Recompute the complete frozen success predicate from final physical state."""
    details = row["success_details"]
    box_position = np.asarray(details["final_box_position"], dtype=float)
    linear_velocity = np.asarray(details["final_box_linear_velocity"], dtype=float)
    angular_velocity = np.asarray(details["final_box_angular_velocity"], dtype=float)
    cylinder_quaternion = details["final_cylinder_quaternion_xyzw"]
    target_error = float(
        np.linalg.norm(box_position[:2] - np.asarray(task.TARGET_XY, dtype=float))
    )
    cylinder_tilt = float(task.quaternion_upright_error_degrees(cylinder_quaternion))
    target_reached = target_error <= TARGET_XY_TOLERANCE
    box_settled = bool(
        np.linalg.norm(linear_velocity) <= 0.02
        and np.linalg.norm(angular_velocity) <= 0.10
        and abs(float(box_position[2]) - float(task.BOX_HALF_EXTENT)) <= 0.015
    )
    cylinder_upright = cylinder_tilt <= float(task.CYLINDER_UPRIGHT_TOLERANCE_DEGREES)
    failure_reasons = []
    if not target_reached:
        failure_reasons.append("target_miss")
    if not box_settled:
        failure_reasons.append("box_not_settled")
    if not cylinder_upright:
        failure_reasons.append("cylinder_toppled")
    success = bool(target_reached and box_settled and cylinder_upright)
    if row.get("termination_reason") == "nonfinite_or_malformed_policy_action":
        success = False
        failure_reasons.append("nonfinite_or_malformed_policy_action")
    return {
        "success": success,
        "failure_reasons": failure_reasons,
        "target_xy_error": target_error,
        "final_cylinder_tilt_degrees": cylinder_tilt,
    }


def failure_labels(row):
    if row["success"]:
        return []
    labels = list(row["success_details"].get("failure_reasons", []))
    termination = row.get("termination_reason")
    if termination == "policy_timeout" and termination not in labels:
        labels.append(termination)
    if termination == "nonfinite_or_malformed_policy_action" and termination not in labels:
        labels.append(termination)
    return sorted(set(labels))


def primary_failure(row, labels):
    if "nonfinite_or_malformed_policy_action" in labels:
        return "nonfinite_policy_action"
    if "cylinder_toppled" in labels:
        return "cylinder_topple"
    if "target_miss" in labels:
        return "target_miss"
    if row.get("termination_reason") == "policy_timeout":
        return "policy_timeout"
    if "box_not_settled" in labels:
        return "box_not_settled"
    return "other_policy_failure"


def artifact(path):
    path = Path(path).resolve()
    return {"path": str(path), "sha256": sha256(path), "size_bytes": path.stat().st_size}


def plot_bytes(participant_rows, pooled, comparison_rows):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    buffer = io.BytesIO()
    figure, axes = plt.subplots(1, 3, figsize=(17.0, 4.8))
    names = [row["participant_id"] for row in participant_rows]
    left = np.asarray([row["n_L"] for row in participant_rows])
    right = np.asarray([row["n_R"] for row in participant_rows])
    indeterminate = np.asarray([row["n_indeterminate"] for row in participant_rows])
    axes[0].bar(names, left, label="L", color="#4c78a8")
    axes[0].bar(names, right, bottom=left, label="R", color="#f58518")
    axes[0].bar(names, indeterminate, bottom=left + right, label="indeterminate", color="#bab0ac")
    axes[0].axhline(10, color="black", linestyle="--", linewidth=1.0)
    axes[0].set_ylabel("Route choices / 20")
    axes[0].set_title("Realised route choices")
    axes[0].legend()
    axes[1].bar(
        names,
        [row["overall_success_rate"] for row in participant_rows],
        color="#54a24b",
    )
    axes[1].axhline(
        pooled["overall_success_rate"],
        color="black",
        linestyle="--",
        linewidth=1.0,
        label=f"pooled={pooled['overall_success_rate']:.3f}",
    )
    axes[1].set_ylim(0, 1.05)
    axes[1].set_ylabel("Successes / 20")
    axes[1].set_title("Per-policy overall success")
    axes[1].legend()
    x = np.arange(len(names))
    width = 0.38
    axes[2].bar(
        x - width / 2,
        [row["bimodal_overall_success_rate"] for row in comparison_rows],
        width,
        label="Bxx (Target-derived)",
        color="#9c755f",
    )
    axes[2].bar(
        x + width / 2,
        [row["control_bimodal_overall_success_rate"] for row in comparison_rows],
        width,
        label="CBxx (Control-derived)",
        color="#54a24b",
    )
    axes[2].axhline(0, color="black", linewidth=0.8)
    axes[2].set_xticks(x, names)
    axes[2].set_ylim(0, 1.05)
    axes[2].set_ylabel("Successes / 20")
    axes[2].set_title("Index-matched CBxx versus Bxx")
    axes[2].legend(fontsize=8)
    for axis in axes:
        axis.tick_params(axis="x", rotation=45)
        axis.grid(axis="y", alpha=0.25)
    figure.tight_layout()
    figure.savefig(buffer, format="png", dpi=180)
    plt.close(figure)
    return buffer.getvalue()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--control_bimodal-root", type=Path, required=True)
    parser.add_argument("--target-spec", type=Path, required=True)
    parser.add_argument("--bimodal-root", type=Path, required=True)
    parser.add_argument("--helper-root", type=Path, required=True)
    args = parser.parse_args()
    root = args.control_bimodal_root.resolve()
    bimodal_root = args.bimodal_root.resolve()
    frozen_inputs = verify_frozen_inputs()
    analysis_root = root / "analysis"
    temporary_analysis_root = analysis_root.with_name(
        f"{analysis_root.name}.inprogress.{os.getpid()}"
    )
    if analysis_root.exists() or analysis_root.is_symlink():
        raise FileExistsError(f"Refusing to overwrite final analysis root: {analysis_root}")
    if temporary_analysis_root.exists() or temporary_analysis_root.is_symlink():
        raise FileExistsError(f"Stale final-analysis temporary root: {temporary_analysis_root}")
    hdf5_root = root / "hdf5"
    models_root = root / "models"
    rollout_root = root / "policy_rollouts"
    output_paths = {name: temporary_analysis_root / name for name in OUTPUT_NAMES}
    examples = args.helper_root.resolve().parent
    if str(examples) not in sys.path:
        sys.path.insert(0, str(examples))
    import main_obstacle_transport as task

    required = {
        "pairing_manifest": root / "pairing_manifest.json",
        "mixed_validation": root / "mixed_raw_validation_report.json",
        "hdf5_validation": hdf5_root / "validation_report.json",
        "hdf5_build_manifest": hdf5_root / "build_manifest.json",
        "training_manifest": models_root / "training_experiment_manifest.json",
        "model_validation": models_root / "model_validation_report.json",
        "selected_checkpoints": models_root / "selected_checkpoints_manifest.json",
        "target_paired_specs": args.target_spec.resolve(),
        "bimodal_final_results": bimodal_root / "analysis/final_results.json",
        "bimodal_final_validation": bimodal_root / "analysis/validation_report.json",
        "bimodal_rollout_results_csv": bimodal_root / "analysis/rollout_results.csv",
    }
    for path in required.values():
        if not path.is_file():
            raise FileNotFoundError(path)
    artifacts = {name: artifact(path) for name, path in required.items()}
    pairing = load_json(required["pairing_manifest"])
    mixed_validation = load_json(required["mixed_validation"])
    hdf5_validation = load_json(required["hdf5_validation"])
    training_manifest = load_json(required["training_manifest"])
    model_validation = load_json(required["model_validation"])
    checkpoints = load_json(required["selected_checkpoints"])
    specs = load_json(required["target_paired_specs"])
    bimodal_results = load_json(required["bimodal_final_results"])
    bimodal_validation = load_json(required["bimodal_final_validation"])
    errors = []
    if pairing.get("group") != GROUP or pairing.get("participant_order") != PARTICIPANTS:
        errors.append("invalid_pairing_manifest")
    if not mixed_validation.get("passed") or mixed_validation.get("counts", {}).get("trajectory_memberships") != 600:
        errors.append("mixed_validation_not_passed_600")
    if (
        not hdf5_validation.get("passed")
        or hdf5_validation.get("counts", {}).get("participant_hdf5") != 10
        or hdf5_validation.get("counts", {}).get("trajectory_memberships") != 600
        or hdf5_validation.get("counts", {}).get("loader_smokes") != 20
    ):
        errors.append("hdf5_validation_not_passed_10x60_and_20_loaders")
    if training_manifest.get("group") != GROUP or training_manifest.get("participant_order") != PARTICIPANTS:
        errors.append("invalid_training_manifest")
    if (
        not training_manifest.get("bimodal_matched_scientific_protocol", {}).get("matched")
        or training_manifest.get("uniform_training_protocol_sha256")
        != EXPECTED_NORMALIZED_TRAINING_PROTOCOL_SHA256
    ):
        errors.append("training_protocol_not_exact_bimodal_match")
    if not model_validation.get("passed") or model_validation.get("checkpoint_count") != 10:
        errors.append("model_validation_not_passed_10")
    if checkpoints.get("group") != GROUP or checkpoints.get("participant_order") != PARTICIPANTS:
        errors.append("invalid_checkpoint_manifest")
    if sha256(required["target_paired_specs"]) != TARGET_SPEC_SHA256:
        errors.append("target_spec_file_hash_changed")
    if specs.get("group") != TARGET_GROUP or len(specs.get("eval_cases", [])) != 10:
        errors.append("invalid_target_specs")
    if (
        bimodal_results.get("group") != BIMODAL_GROUP
        or len(bimodal_results.get("participant_results", [])) != 10
        or bimodal_validation.get("group") != BIMODAL_GROUP
        or bimodal_validation.get("passed") is not True
    ):
        errors.append("invalid_frozen_bimodal_final_results_or_validation")
    expected_bimodal_rollout_csv_hash = bimodal_validation.get(
        "planned_output_sha256", {}
    ).get("rollout_results.csv")
    if (
        not expected_bimodal_rollout_csv_hash
        or sha256(required["bimodal_rollout_results_csv"])
        != expected_bimodal_rollout_csv_hash
    ):
        errors.append("frozen_bimodal_rollout_csv_hash_mismatch")
    spec_by_id = {int(row["eval_case_id"]): row for row in specs.get("eval_cases", [])}
    if set(spec_by_id) != set(range(10)):
        errors.append("target_spec_ids_not_0_through_9")

    participant_dirs = (
        sorted(path.name for path in rollout_root.iterdir() if path.is_dir() and path.name.startswith("CB"))
        if rollout_root.is_dir()
        else []
    )
    if participant_dirs != PARTICIPANTS:
        errors.append(f"rollout_participant_dirs_mismatch:{participant_dirs}")
    all_rows = []
    summaries = {}
    infrastructure_history = []
    repeat_equivalence = {
        "paired_repeat_count": 0,
        "acceptance_basis": REPEAT_PROTOCOL_AMENDMENT,
        "translation_tolerance_metres": REPEAT_TRANSLATION_TOLERANCE_METRES,
        "orientation_tolerance_degrees": REPEAT_ORIENTATION_TOLERANCE_DEGREES,
        "original_translation_tolerance_metres": ORIGINAL_REPEAT_TRANSLATION_TOLERANCE_METRES,
        "original_orientation_tolerance_degrees": ORIGINAL_REPEAT_ORIENTATION_TOLERANCE_DEGREES,
        "original_gate_violations": [],
        "amended_gate_violations": [],
        "maximum_setup_box_position_delta_metres": 0.0,
        "maximum_setup_ee_position_delta_metres": 0.0,
        "maximum_setup_transport_height_error_delta_metres": 0.0,
        "maximum_policy_start_box_position_delta_metres": 0.0,
        "maximum_policy_start_box_orientation_delta_degrees": 0.0,
        "maximum_policy_start_ee_position_delta_metres": 0.0,
        "maximum_policy_start_ee_orientation_delta_degrees": 0.0,
    }
    for participant in PARTICIPANTS:
        participant_dir = rollout_root / participant
        summary_path = participant_dir / "summary.json"
        if not summary_path.is_file():
            errors.append(f"missing_summary:{participant}")
            continue
        summary = load_json(summary_path)
        summaries[participant] = summary
        expected_names = {
            f"rollout_case_{case:02d}_repeat_{repeat}.json"
            for case in range(10)
            for repeat in (0, 1)
        }
        rollout_dir = participant_dir / "rollouts"
        actual_names = {path.name for path in rollout_dir.glob("*.json")} if rollout_dir.is_dir() else set()
        if actual_names != expected_names:
            errors.append(f"rollout_json_set_mismatch:{participant}")
        rows = []
        for case in range(10):
            for repeat in (0, 1):
                path = rollout_dir / f"rollout_case_{case:02d}_repeat_{repeat}.json"
                if not path.is_file():
                    continue
                row = load_json(path)
                rows.append(row)
                all_rows.append(row)
                prefix = f"{participant}:{case}:{repeat}"
                if (
                    row.get("group") != GROUP
                    or row.get("participant_id") != participant
                    or row.get("eval_case_id") != case
                    or row.get("repeat_index") != repeat
                ):
                    errors.append(f"identity_mismatch:{prefix}")
                if row.get("policy_sampling_seed") != policy_sampling_seed(participant, case, repeat):
                    errors.append(f"policy_sampling_seed_mismatch:{prefix}")
                if not row.get("valid_scientific_result") or not row.get("policy_started"):
                    errors.append(f"invalid_scientific_result:{prefix}")
                if not row.get("execution_order_valid") or row.get("scripted_transport_used"):
                    errors.append(f"execution_boundary_violation:{prefix}")
                if row.get("policy_call_count", 0) <= 0:
                    errors.append(f"no_policy_calls:{prefix}")
                if row.get("paired_manifest_sha256") != TARGET_SPEC_SHA256 or row.get("paired_spec") != spec_by_id.get(case):
                    errors.append(f"paired_spec_mismatch:{prefix}")
                checkpoint = checkpoints.get("checkpoints", {}).get(participant, {})
                if row.get("checkpoint_sha256") != checkpoint.get("sha256"):
                    errors.append(f"checkpoint_mismatch:{prefix}")
                config_record = training_manifest.get("configs", {}).get(participant, {})
                config_path = Path(config_record.get("path", ""))
                if (
                    row.get("config_sha256") != checkpoint.get("config_sha256")
                    or row.get("config_sha256") != config_record.get("sha256")
                    or not config_path.is_file()
                    or sha256(config_path) != config_record.get("sha256")
                ):
                    errors.append(f"config_hash_mismatch:{prefix}")
                if row.get("uniform_training_protocol_sha256") != checkpoint.get(
                    "uniform_training_protocol_sha256"
                ):
                    errors.append(f"training_protocol_hash_mismatch:{prefix}")
                recomputed_success = recompute_success(row, task)
                if (
                    row.get("success") != row.get("success_details", {}).get("success")
                    or row.get("success") != recomputed_success["success"]
                    or row.get("success_details", {}).get("failure_reasons")
                    != recomputed_success["failure_reasons"]
                    or not math.isclose(
                        row.get("target_xy_error", float("nan")),
                        recomputed_success["target_xy_error"],
                        rel_tol=0.0,
                        abs_tol=1e-12,
                    )
                    or not math.isclose(
                        row.get("final_cylinder_tilt_degrees", float("nan")),
                        recomputed_success["final_cylinder_tilt_degrees"],
                        rel_tol=0.0,
                        abs_tol=1e-12,
                    )
                ):
                    errors.append(f"success_detail_mismatch:{prefix}")
                if row.get("success_details", {}).get("success_protocol_scope") != GROUP:
                    errors.append(f"wrong_success_protocol_scope:{prefix}")
                if row.get("success_details", {}).get("criterion") != "target_xy_error<=0.10 and box_settled and cylinder_tilt<=10deg":
                    errors.append(f"wrong_success_criterion:{prefix}")
                if row.get("success") and (
                    row.get("target_xy_error", float("inf")) > TARGET_XY_TOLERANCE
                    or row.get("final_cylinder_tilt_degrees", float("inf")) > 10.0
                ):
                    errors.append(f"successful_result_violates_threshold:{prefix}")
                recomputed = recompute_route(row.get("policy_step_trace", []), task)
                recorded = row.get("route_behavior", {})
                for key in (
                    "realised_route",
                    "crossed_obstacle_y_band",
                    "obstacle_y_band_half_width",
                    "box_x_reference",
                    "box_x_at_closest_obstacle_y",
                    "box_y_at_closest_obstacle_y",
                    "minimum_box_cylinder_xy_distance",
                ):
                    if recomputed.get(key) != recorded.get(key):
                        errors.append(f"route_recomputation_mismatch:{prefix}:{key}")
                if not finite_tree(row):
                    errors.append(f"nonfinite_rollout_json:{prefix}")
                video_path = Path(row.get("video_path", ""))
                if not video_path.is_file() or video_path.stat().st_size <= 48:
                    errors.append(f"missing_or_partial_video:{prefix}:{video_path}")
        expected_summary_routes = {
            route: sum(row.get("route_behavior", {}).get("realised_route") == route for row in rows)
            for route in ("L", "R", "indeterminate")
        }
        successes = sum(int(row.get("success", False)) for row in rows)
        rows_by_key = {
            (row.get("eval_case_id"), row.get("repeat_index")): row for row in rows
        }
        for case in range(10):
            left = rows_by_key.get((case, 0))
            right = rows_by_key.get((case, 1))
            if left is None or right is None:
                continue
            repeat_equivalence["paired_repeat_count"] += 1
            left_setup = left.get("setup_details", {})
            right_setup = right.get("setup_details", {})
            left_start = left.get("policy_inference_start", {})
            right_start = right.get("policy_inference_start", {})
            setup_exact_keys = (
                "stage",
                "reason",
                "grasped",
                "transport_height_reached",
                "transport_height_tolerance",
                "required_waypoints",
                "transport_start",
            )
            start_exact_keys = ("phase", "time", "gripper_state", "gripper_closed")
            if (
                not isinstance(left_setup, dict)
                or not isinstance(right_setup, dict)
                or set(left_setup) != set(right_setup)
                or any(left_setup.get(key) != right_setup.get(key) for key in setup_exact_keys)
            ):
                errors.append(f"repeat_scripted_setup_contract_mismatch:{participant}:{case}")
            # sim_step is a simulator-wide diagnostic counter that
            # intentionally accumulates across cases; it is not physical state.
            if (
                not isinstance(left_start, dict)
                or not isinstance(right_start, dict)
                or set(left_start) - {"sim_step"} != set(right_start) - {"sim_step"}
                or any(left_start.get(key) != right_start.get(key) for key in start_exact_keys)
            ):
                errors.append(f"repeat_policy_start_contract_mismatch:{participant}:{case}")

            distances = {
                "maximum_setup_box_position_delta_metres": vector_distance(
                    left_setup.get("box_position_after_lift"),
                    right_setup.get("box_position_after_lift"),
                    3,
                ),
                "maximum_setup_ee_position_delta_metres": vector_distance(
                    left_setup.get("ee_position_after_lift"),
                    right_setup.get("ee_position_after_lift"),
                    3,
                ),
                "maximum_policy_start_box_position_delta_metres": vector_distance(
                    left_start.get("box_position"), right_start.get("box_position"), 3
                ),
                "maximum_policy_start_box_orientation_delta_degrees": quaternion_distance_degrees(
                    left_start.get("box_quaternion_xyzw"),
                    right_start.get("box_quaternion_xyzw"),
                ),
                "maximum_policy_start_ee_position_delta_metres": vector_distance(
                    left_start.get("ee_position"), right_start.get("ee_position"), 3
                ),
                "maximum_policy_start_ee_orientation_delta_degrees": quaternion_distance_degrees(
                    left_start.get("ee_quaternion_xyzw"),
                    right_start.get("ee_quaternion_xyzw"),
                ),
            }
            try:
                distances["maximum_setup_transport_height_error_delta_metres"] = abs(
                    float(left_setup["transport_height_error"])
                    - float(right_setup["transport_height_error"])
                )
            except (KeyError, TypeError, ValueError):
                distances["maximum_setup_transport_height_error_delta_metres"] = float("inf")
            for key, value in distances.items():
                repeat_equivalence[key] = max(repeat_equivalence[key], value)
            original_exceeded = repeat_threshold_exceedances(
                distances,
                ORIGINAL_REPEAT_TRANSLATION_TOLERANCE_METRES,
                ORIGINAL_REPEAT_ORIENTATION_TOLERANCE_DEGREES,
            )
            amended_exceeded = repeat_threshold_exceedances(
                distances,
                REPEAT_TRANSLATION_TOLERANCE_METRES,
                REPEAT_ORIENTATION_TOLERANCE_DEGREES,
            )
            if original_exceeded:
                repeat_equivalence["original_gate_violations"].append(
                    {
                        "participant_id": participant,
                        "eval_case_id": case,
                        "exceeded_metrics": original_exceeded,
                    }
                )
            if amended_exceeded:
                repeat_equivalence["amended_gate_violations"].append(
                    {
                        "participant_id": participant,
                        "eval_case_id": case,
                        "exceeded_metrics": amended_exceeded,
                    }
                )
                for key, value in amended_exceeded.items():
                    errors.append(
                        f"repeat_physical_equivalence_exceeded:{participant}:{case}:{key}:{value}"
                    )
        if (
            summary.get("group") != GROUP
            or summary.get("participant_id") != participant
            or summary.get("valid_rollout_count") != 20
            or summary.get("rollouts") != rows
            or summary.get("success_count") != successes
            or summary.get("overall_success_rate") != successes / 20.0
            or summary.get("route_counts") != expected_summary_routes
        ):
            errors.append(f"summary_mismatch:{participant}")
        failure_dir = participant_dir / "infrastructure_failures"
        if failure_dir.is_dir():
            for path in sorted(failure_dir.glob("*.json")):
                record = load_json(path)
                infrastructure_history.append(record)
                if record.get("classification") == "UNREVIEWED_INFRASTRUCTURE_OR_EXECUTION_FAILURE":
                    errors.append(f"unreviewed_infrastructure_failure:{path}")

    repeat_equivalence["original_gate_passed"] = not repeat_equivalence[
        "original_gate_violations"
    ]
    repeat_equivalence["amended_gate_passed"] = not repeat_equivalence[
        "amended_gate_violations"
    ]
    repeat_equivalence["original_gate_violating_pair_count"] = len(
        repeat_equivalence["original_gate_violations"]
    )
    repeat_equivalence["amended_gate_violating_pair_count"] = len(
        repeat_equivalence["amended_gate_violations"]
    )

    keys = [(row.get("participant_id"), row.get("eval_case_id"), row.get("repeat_index")) for row in all_rows]
    seeds = [row.get("policy_sampling_seed") for row in all_rows]
    videos = [row.get("video_path") for row in all_rows]
    if len(all_rows) != 200 or len(set(keys)) != 200:
        errors.append(f"rollout_key_count_or_uniqueness:{len(all_rows)}:{len(set(keys))}")
    if len(set(seeds)) != 200:
        errors.append(f"policy_sampling_seeds_not_unique:{len(set(seeds))}")
    if len(set(videos)) != 200:
        errors.append(f"video_paths_not_unique:{len(set(videos))}")
    video_hash_by_path = {
        path: sha256(path)
        for path in videos
        if Path(path).is_file() and Path(path).stat().st_size > 48
    }
    if len(video_hash_by_path) != 200 or len(set(video_hash_by_path.values())) != 200:
        errors.append(
            f"video_hash_count_or_uniqueness:{len(video_hash_by_path)}:"
            f"{len(set(video_hash_by_path.values()))}"
        )
    if not infrastructure_history and any(row.get("execution_index") != 0 for row in all_rows):
        errors.append("nonzero_execution_index_without_preserved_infrastructure_history")
    if errors:
        raise RuntimeError("Final Control-Bimodal validation failed:\n" + "\n".join(errors))

    participant_rows = []
    for participant in PARTICIPANTS:
        rows = [row for row in all_rows if row["participant_id"] == participant]
        route_counts = Counter(row["route_behavior"]["realised_route"] for row in rows)
        success_by_route = Counter(
            row["route_behavior"]["realised_route"] for row in rows if row["success"]
        )
        total_success = sum(int(row["success"]) for row in rows)
        n_left = route_counts["L"]
        n_right = route_counts["R"]
        n_indeterminate = route_counts["indeterminate"]
        participant_rows.append(
            {
                "participant_id": participant,
                "n_L": n_left,
                "n_R": n_right,
                "n_indeterminate": n_indeterminate,
                "p_L_all_20": q(n_left / 20.0),
                "p_R_all_20": q(n_right / 20.0),
                "p_indeterminate_all_20": q(n_indeterminate / 20.0),
                "success_L": success_by_route["L"],
                "success_R": success_by_route["R"],
                "success_indeterminate": success_by_route["indeterminate"],
                "success_rate_L": rate(success_by_route["L"], n_left),
                "success_rate_R": rate(success_by_route["R"], n_right),
                "success_rate_indeterminate": rate(success_by_route["indeterminate"], n_indeterminate),
                "success_total": total_success,
                "overall_success_rate": q(total_success / 20.0),
                "p_L_minus_0p5": q(n_left / 20.0 - 0.5),
                "absolute_L_deviation_from_0p5": q(abs(n_left / 20.0 - 0.5)),
                "observed_complete_mode_collapse": bool(n_left == 20 or n_right == 20),
            }
        )

    pooled_routes = Counter(row["route_behavior"]["realised_route"] for row in all_rows)
    pooled_success_routes = Counter(
        row["route_behavior"]["realised_route"] for row in all_rows if row["success"]
    )
    total_success = sum(int(row["success"]) for row in all_rows)
    pooled = {
        "n_L": pooled_routes["L"],
        "n_R": pooled_routes["R"],
        "n_indeterminate": pooled_routes["indeterminate"],
        "p_L_all_200": q(pooled_routes["L"] / 200.0),
        "p_R_all_200": q(pooled_routes["R"] / 200.0),
        "p_indeterminate_all_200": q(pooled_routes["indeterminate"] / 200.0),
        "success_L": pooled_success_routes["L"],
        "success_R": pooled_success_routes["R"],
        "success_indeterminate": pooled_success_routes["indeterminate"],
        "success_rate_L": rate(pooled_success_routes["L"], pooled_routes["L"]),
        "success_rate_R": rate(pooled_success_routes["R"], pooled_routes["R"]),
        "success_rate_indeterminate": rate(
            pooled_success_routes["indeterminate"], pooled_routes["indeterminate"]
        ),
        "success_total": total_success,
        "overall_success_rate": q(total_success / 200.0),
        "p_L_minus_0p5": q(pooled_routes["L"] / 200.0 - 0.5),
    }
    participant_statistics = statistics(
        [row["overall_success_rate"] for row in participant_rows]
    )
    primary_taxonomy = Counter()
    multilabel_taxonomy = Counter()
    rollout_csv_rows = []
    video_rows = []
    for row in sorted(all_rows, key=lambda item: (item["participant_id"], item["eval_case_id"], item["repeat_index"])):
        labels = failure_labels(row)
        primary = "success" if row["success"] else primary_failure(row, labels)
        if not row["success"]:
            primary_taxonomy[primary] += 1
            multilabel_taxonomy.update(labels)
        route = row["route_behavior"]["realised_route"]
        rollout_csv_rows.append(
            {
                "participant_id": row["participant_id"],
                "eval_case_id": row["eval_case_id"],
                "repeat_index": row["repeat_index"],
                "policy_sampling_seed": row["policy_sampling_seed"],
                "realised_route": route,
                "success": int(row["success"]),
                "success_within_route": int(row["success"]),
                "termination_reason": row["termination_reason"],
                "primary_failure": primary,
                "failure_labels": ";".join(labels),
                "target_xy_error": q(row["target_xy_error"]),
                "final_cylinder_tilt_degrees": q(row["final_cylinder_tilt_degrees"]),
                "minimum_box_cylinder_xy_distance": q(
                    row["route_behavior"]["minimum_box_cylinder_xy_distance"]
                ),
                "checkpoint_sha256": row["checkpoint_sha256"],
                "config_sha256": row["config_sha256"],
                "paired_manifest_sha256": row["paired_manifest_sha256"],
                "video_path": row["video_path"],
            }
        )
        video_rows.append(
            {
                "participant_id": row["participant_id"],
                "eval_case_id": row["eval_case_id"],
                "repeat_index": row["repeat_index"],
                "realised_route": route,
                "success": row["success"],
                "path": row["video_path"],
                "sha256": video_hash_by_path[row["video_path"]],
            }
        )

    with required["bimodal_rollout_results_csv"].open(
        "r", encoding="utf-8", newline=""
    ) as stream:
        bimodal_rollout_rows = list(csv.DictReader(stream))
    if len(bimodal_rollout_rows) != 200:
        errors.append(f"frozen_bimodal_rollout_csv_row_count:{len(bimodal_rollout_rows)}")
    bimodal_participant_rows = {
        row["participant_id"]: row for row in bimodal_results["participant_results"]
    }
    bimodal_rollout_by_key = {
        (
            row["participant_id"],
            int(row["eval_case_id"]),
            int(row["repeat_index"]),
        ): row
        for row in bimodal_rollout_rows
    }
    comparison_rows = []
    comparison_csv_rows = []
    matched_key_summary = Counter()
    for control_id, bimodal_id, control_row in zip(
        PARTICIPANTS, MATCHED_BIMODAL_PARTICIPANTS, participant_rows
    ):
        bimodal_row = bimodal_participant_rows.get(bimodal_id)
        if bimodal_row is None:
            errors.append(f"missing_matched_bimodal_participant:{bimodal_id}")
            continue
        control_policy_rollouts = [
            row for row in rollout_csv_rows if row["participant_id"] == control_id
        ]
        bimodal_policy_rollouts = [
            row for row in bimodal_rollout_rows if row["participant_id"] == bimodal_id
        ]
        if len(control_policy_rollouts) != 20 or len(bimodal_policy_rollouts) != 20:
            errors.append(f"matched_policy_rollout_count:{control_id}:{bimodal_id}")
        control_failures = Counter(
            row["primary_failure"]
            for row in control_policy_rollouts
            if row["primary_failure"] != "success"
        )
        bimodal_failures = Counter(
            row["primary_failure"]
            for row in bimodal_policy_rollouts
            if row["primary_failure"] != "success"
        )
        failure_categories = sorted(set(control_failures) | set(bimodal_failures))
        failure_differences = {
            category: int(control_failures[category] - bimodal_failures[category])
            for category in failure_categories
        }
        for case in range(10):
            for repeat in (0, 1):
                control_rollout = next(
                    (
                        row
                        for row in control_policy_rollouts
                        if int(row["eval_case_id"]) == case
                        and int(row["repeat_index"]) == repeat
                    ),
                    None,
                )
                bimodal_rollout = bimodal_rollout_by_key.get((bimodal_id, case, repeat))
                if control_rollout is None or bimodal_rollout is None:
                    errors.append(f"missing_matched_rollout_key:{control_id}:{case}:{repeat}")
                    continue
                matched_key_summary["matched_keys"] += 1
                if int(control_rollout["policy_sampling_seed"]) == int(
                    bimodal_rollout["policy_sampling_seed"]
                ):
                    matched_key_summary["common_policy_sampling_seed"] += 1
                else:
                    errors.append(f"matched_seed_mismatch:{control_id}:{case}:{repeat}")
                if control_rollout["realised_route"] == bimodal_rollout["realised_route"]:
                    matched_key_summary["same_realised_route"] += 1
                if int(control_rollout["success"]) == int(bimodal_rollout["success"]):
                    matched_key_summary["same_success_outcome"] += 1
        comparison = {
            "control_bimodal_participant": control_id,
            "bimodal_participant": bimodal_id,
            "p_L_all_20_difference": q(
                control_row["p_L_all_20"] - bimodal_row["p_L_all_20"]
            ),
            "p_R_all_20_difference": q(
                control_row["p_R_all_20"] - bimodal_row["p_R_all_20"]
            ),
            "p_indeterminate_all_20_difference": q(
                control_row["p_indeterminate_all_20"]
                - bimodal_row["p_indeterminate_all_20"]
            ),
            "success_rate_L_difference": (
                None
                if control_row["success_rate_L"] is None
                or bimodal_row["success_rate_L"] is None
                else q(control_row["success_rate_L"] - bimodal_row["success_rate_L"])
            ),
            "success_rate_R_difference": (
                None
                if control_row["success_rate_R"] is None
                or bimodal_row["success_rate_R"] is None
                else q(control_row["success_rate_R"] - bimodal_row["success_rate_R"])
            ),
            "control_bimodal_overall_success_rate": control_row["overall_success_rate"],
            "bimodal_overall_success_rate": bimodal_row["overall_success_rate"],
            "overall_success_rate_difference": q(
                control_row["overall_success_rate"] - bimodal_row["overall_success_rate"]
            ),
            "control_bimodal_primary_failures": dict(sorted(control_failures.items())),
            "bimodal_primary_failures": dict(sorted(bimodal_failures.items())),
            "primary_failure_count_differences": failure_differences,
        }
        comparison_rows.append(comparison)
        comparison_csv_rows.append(
            {
                **{
                    key: value
                    for key, value in comparison.items()
                    if not isinstance(value, dict)
                },
                "control_bimodal_primary_failures_json": json.dumps(
                    comparison["control_bimodal_primary_failures"], sort_keys=True
                ),
                "bimodal_primary_failures_json": json.dumps(
                    comparison["bimodal_primary_failures"], sort_keys=True
                ),
                "primary_failure_count_differences_json": json.dumps(
                    failure_differences, sort_keys=True
                ),
            }
        )
    if errors:
        raise RuntimeError("Matched Bimodal comparison validation failed:\n" + "\n".join(errors))
    matched_overall_statistics = statistics(
        [row["overall_success_rate_difference"] for row in comparison_rows]
    )
    bimodal_pooled = bimodal_results["pooled_200_rollouts"]
    pooled_comparison = {
        "p_L_all_200_difference": q(pooled["p_L_all_200"] - bimodal_pooled["p_L_all_200"]),
        "p_R_all_200_difference": q(pooled["p_R_all_200"] - bimodal_pooled["p_R_all_200"]),
        "p_indeterminate_all_200_difference": q(
            pooled["p_indeterminate_all_200"] - bimodal_pooled["p_indeterminate_all_200"]
        ),
        "overall_success_rate_difference": q(
            pooled["overall_success_rate"] - bimodal_pooled["overall_success_rate"]
        ),
    }
    bimodal_primary_taxonomy = Counter(
        row["primary_failure"]
        for row in bimodal_rollout_rows
        if row["primary_failure"] != "success"
    )
    pooled_failure_categories = sorted(set(primary_taxonomy) | set(bimodal_primary_taxonomy))
    pooled_comparison["primary_failure_count_differences"] = {
        category: int(primary_taxonomy[category] - bimodal_primary_taxonomy[category])
        for category in pooled_failure_categories
    }
    bimodal_comparison = {
        "schema_version": 1,
        "comparison": "CBxx minus Bxx",
        "validation_basis": {
            "repeat_protocol_amendment": REPEAT_PROTOCOL_AMENDMENT,
            "repeat_equivalence": repeat_equivalence,
        },
        "participant_policy_is_inferential_unit": True,
        "matched_policy_rows": comparison_rows,
        "matched_overall_success_rate_difference_statistics": matched_overall_statistics,
        "pooled_200_rollout_descriptive_differences": pooled_comparison,
        "matched_rollout_key_description": {
            **dict(matched_key_summary),
            "matched_rollouts_are_not_200_independent_participant_observations": True,
        },
    }

    final_results = {
        "schema_version": 1,
        "group": GROUP,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "inferential_unit": "Control-Bimodal participant-level policy",
        "validation_basis": {
            "repeat_protocol_amendment": REPEAT_PROTOCOL_AMENDMENT,
            "repeat_equivalence": repeat_equivalence,
        },
        "participant_results": participant_rows,
        "pooled_200_rollouts": pooled,
        "participant_overall_success_statistics": participant_statistics,
        "failure_taxonomy": {
            "primary_exclusive": dict(sorted(primary_taxonomy.items())),
            "multi_label": dict(sorted(multilabel_taxonomy.items())),
            "reviewed_or_unreviewed_rollout_infrastructure_records": len(infrastructure_history),
        },
        "data_reuse_limitation": {
            "control_bimodal_trajectory_memberships": 600,
            "underlying_unique_control_trajectories": 300,
            "source_reuse_is_unequal_due_to_frozen_random_pairing": True,
            "memberships_are_not_600_independent_demonstrations": True,
        },
        "matched_bimodal_comparison_summary": {
            "matched_overall_success_rate_difference_statistics": matched_overall_statistics,
            "pooled_200_rollout_descriptive_differences": pooled_comparison,
        },
        "route_contract": {
            "selection_denominator_includes_all_rollouts": True,
            "indeterminate_outcomes_are_never_discarded": True,
            "conditional_zero_denominator_is_null": True,
            "forced_route_balance": False,
        },
    }
    summary_lines = [
        "Control-Bimodal route and success summary",
        *(
            f"{row['participant_id']}: L={row['n_L']}, R={row['n_R']}, "
            f"indeterminate={row['n_indeterminate']}, success_L={row['success_rate_L']}, "
            f"success_R={row['success_rate_R']}, overall={row['overall_success_rate']}"
            for row in participant_rows
        ),
        f"Pooled: {json.dumps(pooled, sort_keys=True)}",
        (
            "Participant-policy overall success mean ± sample SD: "
            f"{participant_statistics['mean']} ± "
            f"{participant_statistics['sample_standard_deviation']} (ddof=1)"
        ),
        (
            "Matched CBxx-Bxx overall-success difference mean ± sample SD: "
            f"{matched_overall_statistics['mean']} ± "
            f"{matched_overall_statistics['sample_standard_deviation']} (ddof=1)"
        ),
        "The 600 memberships reuse 300 underlying Control trajectories with unequal multiplicity.",
        "The 200 matched rollout keys are descriptive common-random-number pairs, not 200 independent participant observations.",
        (
            "Repeat gate: the original 10 micrometre / 0.01 degree gate failed "
            "for 2 of 100 pairs; a user-authorized post-rollout 2 mm / 3 degree "
            "engineering envelope passed all 100 pairs. No rollout was rerun or replaced."
        ),
    ]
    helper_records = {
        path.name: artifact(path)
        for path in sorted(args.helper_root.resolve().glob("*"))
        if path.is_file()
    }
    training_slurm = {
        participant: load_json(
            model_validation["participants"][participant]["selected_training_status"]
        ).get("slurm")
        for participant in PARTICIPANTS
    }
    rollout_array_job_ids = sorted(
        {
            row.get("slurm", {}).get("array_job_id")
            for row in all_rows
            if row.get("slurm", {}).get("array_job_id")
        }
    )
    experiment_manifest = {
        "schema_version": 1,
        "group": GROUP,
        "participant_order": PARTICIPANTS,
        "pairings": pairing["pairs"],
        "design": pairing["design"],
        "target_paired_rollout_specs": artifacts["target_paired_specs"],
        "repeats_per_policy_case": 2,
        "total_rollouts": 200,
        "success_criterion": "target_xy_error<=0.10 and box_settled and cylinder_tilt<=10deg",
        "checkpoint_selection": checkpoints["selection_rule"],
        "training_budget": training_manifest["training_budget"],
        "uniform_training_protocol_sha256": training_manifest["uniform_training_protocol_sha256"],
        "stage_artifacts": artifacts,
        "frozen_inputs": frozen_inputs,
        "helpers": helper_records,
        "hdf5_build_attempts": 1,
        "hdf5_infrastructure_recovery": None,
        "rollout_infrastructure_history": infrastructure_history,
        "matched_bimodal_comparison": {
            "comparison": "CBxx minus Bxx",
            "existing_bimodal_group": BIMODAL_GROUP,
            "matched_participant_mapping": dict(
                zip(PARTICIPANTS, MATCHED_BIMODAL_PARTICIPANTS)
            ),
            "existing_bimodal_results": artifacts["bimodal_final_results"],
            "existing_bimodal_validation": artifacts["bimodal_final_validation"],
        },
        "slurm": {
            "training_by_participant": training_slurm,
            "training_array_job_ids": sorted(
                {row.get("array_job_id") for row in training_slurm.values() if row}
            ),
            "rollout_array_job_ids": rollout_array_job_ids,
        },
        "isolation_audit": {
            "control_bimodal_owned_roots_only": True,
            "all_frozen_inputs_reverified_by_hash_at_each_gate": True,
            "target_control_and_existing_bimodal_remained_read_only": True,
            "prior_group_job_action_by_control_bimodal_executor": False,
        },
        "statistics_contract": {
            "participant_policy_rollout_denominator": 20,
            "pooled_rollout_denominator": 200,
            "sample_standard_deviation_ddof": 1,
            "indeterminate_in_selection_denominator": True,
        },
        "paired_repeat_physical_equivalence": repeat_equivalence,
        "repeat_protocol_amendment": REPEAT_PROTOCOL_AMENDMENT,
    }
    participant_csv = csv_payload(list(participant_rows[0]), participant_rows)
    route_csv = csv_payload(
        [
            "participant_id",
            "n_L",
            "n_R",
            "n_indeterminate",
            "p_L_all_20",
            "p_R_all_20",
            "p_indeterminate_all_20",
            "p_L_minus_0p5",
            "absolute_L_deviation_from_0p5",
            "observed_complete_mode_collapse",
        ],
        [
            {key: row[key] for key in (
                "participant_id",
                "n_L",
                "n_R",
                "n_indeterminate",
                "p_L_all_20",
                "p_R_all_20",
                "p_indeterminate_all_20",
                "p_L_minus_0p5",
                "absolute_L_deviation_from_0p5",
                "observed_complete_mode_collapse",
            )}
            for row in participant_rows
        ],
    )
    rollout_csv = csv_payload(list(rollout_csv_rows[0]), rollout_csv_rows)
    comparison_csv = csv_payload(list(comparison_csv_rows[0]), comparison_csv_rows)
    video_index = {"schema_version": 1, "group": GROUP, "video_count": 200, "videos": video_rows}
    planned = {
        "final_results.json": json_bytes(final_results),
        "participant_success_rates.csv": participant_csv,
        "route_choice_summary.csv": route_csv,
        "rollout_results.csv": rollout_csv,
        "experiment_manifest.json": json_bytes(experiment_manifest),
        "route_success_summary.png": plot_bytes(
            participant_rows, pooled, comparison_rows
        ),
        "video_index.json": json_bytes(video_index),
        "factual_summary.txt": ("\n".join(summary_lines) + "\n").encode("utf-8"),
        "bimodal_comparison.json": json_bytes(bimodal_comparison),
        "bimodal_comparison.csv": comparison_csv,
    }
    validation_report = {
        "schema_version": 1,
        "group": GROUP,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "passed": True,
        "passed_under_user_authorized_amended_repeat_tolerance": True,
        "original_preregistered_repeat_gate_passed": repeat_equivalence[
            "original_gate_passed"
        ],
        "errors": [],
        "counts": {
            "pairings": 10,
            "hdf5_memberships": 600,
            "underlying_unique_control_trajectories": 300,
            "loadable_checkpoints": 10,
            "paired_specs": 10,
            "repeats_per_policy_case": 2,
            "valid_policy_rollouts": 200,
            "unique_participant_case_repeat_keys": 200,
            "unique_policy_sampling_seeds": 200,
            "complete_videos": 200,
            "participant_statistics": 10,
            "matched_bimodal_policy_comparisons": 10,
            "matched_bimodal_rollout_keys": 200,
        },
        "cross_checks": {
            "all_routes_independently_recomputed": True,
            "all_successes_rechecked_against_frozen_criterion": True,
            "all_rollouts_reference_exact_target_spec_hash": True,
            "all_rollouts_reference_correct_control_bimodal_checkpoint_hash": True,
            "no_outcome_replacement": len(infrastructure_history) == 0,
            "indeterminate_outcomes_retained": True,
            "sample_standard_deviation_ddof": 1,
            "paired_repeat_setup_contracts_exact": True,
            "paired_repeat_physical_starts_within_amended_tolerance": True,
            "original_repeat_gate_failure_disclosed": not repeat_equivalence[
                "original_gate_passed"
            ],
            "post_rollout_user_authorized_protocol_amendment_disclosed": True,
            "existing_bimodal_hashes_reverified": True,
            "matched_bimodal_policy_comparison_recomputed": True,
            "all_200_matched_keys_reuse_the_corresponding_policy_sampling_seed": True,
        },
        "paired_repeat_physical_equivalence": repeat_equivalence,
        "upstream_artifacts": artifacts,
        "planned_output_sha256": {
            name: hashlib.sha256(payload).hexdigest() for name, payload in planned.items()
        },
    }
    planned["validation_report.json"] = json_bytes(validation_report)
    temporary_analysis_root.mkdir(parents=True, exist_ok=False)
    for name in OUTPUT_NAMES:
        write_exclusive(output_paths[name], planned[name])
        if sha256(output_paths[name]) != hashlib.sha256(planned[name]).hexdigest():
            raise RuntimeError(f"Post-write final artifact hash mismatch: {name}")
    if analysis_root.exists() or analysis_root.is_symlink():
        raise FileExistsError(f"Final analysis root appeared during creation: {analysis_root}")
    os.replace(temporary_analysis_root, analysis_root)
    print(json.dumps(final_results, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
