#!/usr/bin/env python3
"""Validate and summarize the complete Target participant-policy pipeline."""

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


GROUP = "simulation_target_group"
SEED = 20260806
EVALUATION_SEED = 20260807
TARGET_XY_TOLERANCE = 0.10
PARTICIPANTS = [f"T{index:02d}" for index in range(1, 11)]
ROUTES = {participant: ("L" if int(participant[1:]) <= 5 else "R") for participant in PARTICIPANTS}
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


def write_exclusive_bytes(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(payload)


def q(value):
    return round(float(value), 6)


def finite_tree(value):
    if isinstance(value, dict):
        return all(finite_tree(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return all(finite_tree(item) for item in value)
    if isinstance(value, float):
        return math.isfinite(value)
    return True


def statistics(values):
    values = np.asarray(values, dtype=float)
    if values.size < 2:
        raise ValueError("Sample standard deviation requires at least two participants")
    return {
        "n_participants": int(values.size),
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


def primary_failure(row, labels):
    if not row.get("policy_started"):
        return "grasp_setup_infrastructure_issue"
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


def failure_labels(row):
    if row["success"]:
        return []
    labels = list(row["success_details"].get("failure_reasons", []))
    termination = row.get("termination_reason")
    if termination == "policy_timeout" and "policy_timeout" not in labels:
        labels.append("policy_timeout")
    if termination == "nonfinite_or_malformed_policy_action" and termination not in labels:
        labels.append(termination)
    if not row.get("policy_started"):
        labels.append("grasp_setup_infrastructure_issue")
    return sorted(set(labels))


def plot_bytes(participant_rows, overall):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    buffer = io.BytesIO()
    figure, axis = plt.subplots(figsize=(9.2, 4.8))
    colors = ["#4c78a8" if row["route"] == "L" else "#f58518" for row in participant_rows]
    axis.bar([row["participant_id"] for row in participant_rows], [row["edsr"] for row in participant_rows], color=colors)
    axis.axhline(overall["mean"], color="black", linestyle="--", linewidth=1.2, label=f"mean={overall['mean']:.3f}")
    axis.set_ylim(0.0, 1.05)
    axis.set_ylabel("EDSR (successes / 10 paired rollouts)")
    axis.set_xlabel("Participant-level policy")
    axis.set_title("Target participant-level policy EDSR")
    axis.grid(axis="y", alpha=0.25)
    axis.legend(loc="best")
    figure.tight_layout()
    figure.savefig(buffer, format="png", dpi=180)
    plt.close(figure)
    return buffer.getvalue()


def artifact_record(path):
    path = Path(path).resolve()
    return {"path": str(path), "sha256": sha256(path), "size_bytes": path.stat().st_size}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-root", type=Path, required=True)
    parser.add_argument("--raw-root", type=Path, required=True)
    parser.add_argument("--helper-root", type=Path, required=True)
    args = parser.parse_args()
    target_root = args.target_root.resolve()
    raw_root = args.raw_root.resolve()
    analysis_root = target_root / "analysis"
    hdf5_root = target_root / "hdf5"
    models_root = target_root / "models"
    rollout_root = target_root / "policy_rollouts"
    output_paths = {name: analysis_root / name for name in OUTPUT_NAMES}
    existing = [str(path) for path in output_paths.values() if path.exists()]
    if existing:
        raise FileExistsError(f"Refusing to overwrite final analysis artifacts: {existing}")

    required = {
        "raw_validation": raw_root / "validation_report.json",
        "hdf5_validation": hdf5_root / "validation_report.json",
        "raw_to_hdf5_manifest": hdf5_root / "raw_to_hdf5_manifest.json",
        "training_manifest": models_root / "training_experiment_manifest.json",
        "model_validation": models_root / "model_validation_report.json",
        "checkpoints": models_root / "selected_checkpoints_manifest.json",
        "rollout_specs": analysis_root / "paired_rollout_specs.json",
        "rollout_specs_hash": analysis_root / "paired_rollout_specs.sha256.json",
    }
    for path in required.values():
        if not path.is_file():
            raise FileNotFoundError(path)
    artifacts = {name: artifact_record(path) for name, path in required.items()}
    raw_validation = load_json(required["raw_validation"])
    hdf5_validation = load_json(required["hdf5_validation"])
    model_validation = load_json(required["model_validation"])
    checkpoint_manifest = load_json(required["checkpoints"])
    specs = load_json(required["rollout_specs"])
    specs_sidecar = load_json(required["rollout_specs_hash"])
    errors = []
    if not raw_validation.get("passed") or raw_validation.get("counts", {}).get("successful_demos") != 300:
        errors.append("raw_validation_not_passed_300")
    if raw_validation.get("counts", {}).get("participants") != 10:
        errors.append("raw_validation_not_10_participants")
    if raw_validation.get("counts", {}).get("scripted_frames_in_success_raw") != 0:
        errors.append("raw_validation_contains_scripted_frames")
    if not hdf5_validation.get("passed") or hdf5_validation.get("counts", {}).get("trajectories") != 300:
        errors.append("hdf5_validation_not_passed_300")
    if hdf5_validation.get("counts", {}).get("participant_hdf5") != 10:
        errors.append("hdf5_validation_not_10_files")
    if not model_validation.get("passed") or model_validation.get("checkpoint_count") != 10:
        errors.append("model_validation_not_passed_10")
    if checkpoint_manifest.get("participant_order") != PARTICIPANTS:
        errors.append("checkpoint_participant_order_mismatch")
    if specs.get("group") != GROUP or specs.get("evaluation_seed") != EVALUATION_SEED:
        errors.append("rollout_spec_identity_or_seed_mismatch")
    if specs.get("frozen_task", {}).get("target_xy_tolerance_m") != TARGET_XY_TOLERANCE:
        errors.append("rollout_spec_target_tolerance_not_0p10")
    if len(specs.get("eval_cases", [])) != 10:
        errors.append("rollout_spec_count_not_10")
    if specs_sidecar.get("file_sha256") != sha256(required["rollout_specs"]):
        errors.append("rollout_spec_file_hash_mismatch")
    spec_hash = sha256(required["rollout_specs"])
    spec_by_id = {int(row["eval_case_id"]): row for row in specs.get("eval_cases", [])}
    if set(spec_by_id) != set(range(10)):
        errors.append("rollout_spec_ids_not_0_through_9")

    actual_participant_dirs = sorted(
        path.name for path in rollout_root.iterdir() if path.is_dir() and path.name.startswith("T")
    ) if rollout_root.is_dir() else []
    if actual_participant_dirs != PARTICIPANTS:
        errors.append(f"rollout_participant_dirs_mismatch:{actual_participant_dirs}")
    all_rows = []
    participant_summaries = {}
    infrastructure_history = []
    for participant in PARTICIPANTS:
        participant_dir = rollout_root / participant
        summary_path = participant_dir / "summary.json"
        if not summary_path.is_file():
            errors.append(f"missing_participant_summary:{participant}")
            continue
        summary = load_json(summary_path)
        participant_summaries[participant] = summary
        expected_names = {f"rollout_{case_id:02d}.json" for case_id in range(10)}
        rollout_dir = participant_dir / "rollouts"
        actual_names = {path.name for path in rollout_dir.glob("*.json")} if rollout_dir.is_dir() else set()
        if actual_names != expected_names:
            errors.append(
                f"rollout_json_set_mismatch:{participant}:missing={sorted(expected_names-actual_names)}:extra={sorted(actual_names-expected_names)}"
            )
        rows = []
        for case_id in range(10):
            path = rollout_dir / f"rollout_{case_id:02d}.json"
            if not path.is_file():
                continue
            row = load_json(path)
            rows.append(row)
            all_rows.append(row)
            prefix = f"{participant}:{case_id}"
            if row.get("group") != GROUP or row.get("participant_id") != participant:
                errors.append(f"identity_mismatch:{prefix}")
            if row.get("eval_case_id") != case_id or row.get("participant_route") != ROUTES[participant]:
                errors.append(f"case_or_route_mismatch:{prefix}")
            if not row.get("valid_scientific_result") or not row.get("policy_started"):
                errors.append(f"invalid_scientific_result:{prefix}")
            if not row.get("execution_order_valid") or row.get("scripted_transport_used"):
                errors.append(f"execution_boundary_violation:{prefix}")
            if row.get("policy_call_count", 0) <= 0:
                errors.append(f"no_policy_calls:{prefix}")
            if row.get("paired_manifest_sha256") != spec_hash or row.get("paired_spec") != spec_by_id.get(case_id):
                errors.append(f"paired_spec_mismatch:{prefix}")
            checkpoint = checkpoint_manifest.get("checkpoints", {}).get(participant, {})
            if row.get("checkpoint_sha256") != checkpoint.get("sha256"):
                errors.append(f"checkpoint_hash_mismatch:{prefix}")
            if row.get("success") != row.get("success_details", {}).get("success"):
                errors.append(f"success_detail_mismatch:{prefix}")
            for metric in (
                "target_xy_error",
                "final_cylinder_tilt_degrees",
                "maximum_cylinder_tilt_degrees",
                "box_obstacle_contact_steps",
                "robot_obstacle_contact_steps",
            ):
                value = row.get(metric)
                if not isinstance(value, (int, float)) or not math.isfinite(float(value)):
                    errors.append(f"missing_or_nonfinite_metric:{prefix}:{metric}:{value}")
            if row.get("success") and (
                row.get("target_xy_error", float("inf")) > TARGET_XY_TOLERANCE
                or row.get("final_cylinder_tilt_degrees", float("inf")) > 10.0
            ):
                errors.append(f"successful_result_violates_threshold:{prefix}")
            route_behavior = row.get("route_behavior", {})
            if (
                route_behavior.get("realised_route") not in {"L", "R", "indeterminate"}
                or not isinstance(route_behavior.get("minimum_box_cylinder_xy_distance"), (int, float))
                or not math.isfinite(route_behavior["minimum_box_cylinder_xy_distance"])
            ):
                errors.append(f"invalid_route_behavior_diagnostic:{prefix}")
            if not finite_tree(row):
                errors.append(f"nonfinite_rollout_json:{prefix}")
            video_path = Path(row.get("video_path", ""))
            if not video_path.is_file() or video_path.stat().st_size <= 48:
                errors.append(f"missing_or_partial_rollout_video:{prefix}:{video_path}")
        if summary.get("group") != GROUP or summary.get("participant_id") != participant:
            errors.append(f"summary_identity_mismatch:{participant}")
        if summary.get("valid_rollout_count") != 10 or summary.get("rollouts") != rows:
            errors.append(f"summary_rollout_content_mismatch:{participant}")
        success_count = sum(int(row.get("success", False)) for row in rows)
        if summary.get("success_count") != success_count or summary.get("edsr") != success_count / 10.0:
            errors.append(f"summary_edsr_mismatch:{participant}")
        failure_dir = participant_dir / "infrastructure_failures"
        if failure_dir.is_dir():
            for path in sorted(failure_dir.glob("*.json")):
                record = load_json(path)
                infrastructure_history.append(record)
                if record.get("classification") == "UNREVIEWED_INFRASTRUCTURE_OR_EXECUTION_FAILURE":
                    errors.append(f"unreviewed_infrastructure_failure:{path}")
    pairs = [(row.get("participant_id"), row.get("eval_case_id")) for row in all_rows]
    if len(all_rows) != 100 or len(set(pairs)) != 100:
        errors.append(f"rollout_pair_count_or_uniqueness_failed:{len(all_rows)}:{len(set(pairs))}")
    if errors:
        raise RuntimeError("Final Target validation failed:\n" + "\n".join(errors))

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
    edsr_values = [row["edsr"] for row in participant_rows]
    overall = statistics(edsr_values)
    left = statistics([row["edsr"] for row in participant_rows if row["route"] == "L"])
    right = statistics([row["edsr"] for row in participant_rows if row["route"] == "R"])

    primary_taxonomy = Counter(
        {
            "target_miss": 0,
            "cylinder_topple": 0,
            "policy_timeout": 0,
            "grasp_setup_infrastructure_issue": 0,
            "nonfinite_policy_action": 0,
            "box_not_settled": 0,
            "other_policy_failure": 0,
        }
    )
    multilabel_taxonomy = Counter(
        {
            "target_miss": 0,
            "cylinder_toppled": 0,
            "policy_timeout": 0,
            "grasp_setup_infrastructure_issue": 0,
            "box_not_settled": 0,
            "nonfinite_or_malformed_policy_action": 0,
        }
    )
    rollout_csv_rows = []
    video_rows = []
    representative_success = set()
    for row in sorted(all_rows, key=lambda item: (item["participant_id"], item["eval_case_id"])):
        labels = failure_labels(row)
        primary = "success" if row["success"] else primary_failure(row, labels)
        if not row["success"]:
            primary_taxonomy[primary] += 1
            multilabel_taxonomy.update(labels)
        participant = row["participant_id"]
        if row["success"] and participant not in representative_success:
            representative = True
            representative_success.add(participant)
        else:
            representative = not row["success"]
        route_behavior = row["route_behavior"]
        rollout_csv_rows.append(
            {
                "participant_id": participant,
                "participant_route": row["participant_route"],
                "eval_case_id": row["eval_case_id"],
                "success": int(row["success"]),
                "termination_reason": row["termination_reason"],
                "primary_failure": primary,
                "failure_labels": ";".join(labels),
                "target_xy_error": q(row["target_xy_error"]),
                "final_cylinder_tilt_degrees": q(row["final_cylinder_tilt_degrees"]),
                "maximum_cylinder_tilt_degrees": q(row["maximum_cylinder_tilt_degrees"]),
                "box_obstacle_contact_steps": row["box_obstacle_contact_steps"],
                "robot_obstacle_contact_steps": row["robot_obstacle_contact_steps"],
                "realised_route": route_behavior["realised_route"],
                "crossed_obstacle_y_band": int(route_behavior.get("crossed_obstacle_y_band", False)),
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
                "primary_failure": primary,
                "representative": representative,
                "path": row["video_path"],
                "sha256": sha256(row["video_path"]),
            }
        )

    target_errors = np.asarray([row["target_xy_error"] for row in all_rows], dtype=float)
    cylinder_tilts = np.asarray([row["final_cylinder_tilt_degrees"] for row in all_rows], dtype=float)
    route_counts = Counter(row["route_behavior"]["realised_route"] for row in all_rows)
    diagnostics = {
        "target_xy_error_m": {
            "mean": q(np.mean(target_errors)),
            "median": q(np.median(target_errors)),
            "min": q(np.min(target_errors)),
            "max": q(np.max(target_errors)),
        },
        "final_cylinder_tilt_degrees": {
            "mean": q(np.mean(cylinder_tilts)),
            "median": q(np.median(cylinder_tilts)),
            "min": q(np.min(cylinder_tilts)),
            "max": q(np.max(cylinder_tilts)),
        },
        "contact_steps": {
            "box_obstacle_total": int(sum(row["box_obstacle_contact_steps"] for row in all_rows)),
            "robot_obstacle_total": int(sum(row["robot_obstacle_contact_steps"] for row in all_rows)),
            "contacts_are_diagnostic_only": True,
        },
        "realised_route_counts": dict(sorted(route_counts.items())),
    }
    final_results = {
        "schema_version": 1,
        "group": GROUP,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "inferential_unit": "participant-level policy",
        "rollouts_are_raw_paired_outcomes_not_independent_participant_samples": True,
        "success_protocol": {
            "scope": GROUP,
            "target_xy_tolerance_m": TARGET_XY_TOLERANCE,
            "criterion": "target_xy_error<=0.10 and box_settled and cylinder_tilt<=10deg",
            "shared_control_visible_target_xy_tolerance_m_unchanged": 0.03,
            "control_protocol_was_not_modified": True,
        },
        "participant_results": participant_rows,
        "participant_edsr_statistics": {"overall": overall, "L": left, "R": right},
        "raw_rollout_counts": {
            "total": 100,
            "successes": sum(int(row["success"]) for row in all_rows),
            "failures": sum(int(not row["success"]) for row in all_rows),
        },
        "failure_taxonomy": {
            "primary_exclusive": dict(sorted(primary_taxonomy.items())),
            "multi_label": dict(sorted(multilabel_taxonomy.items())),
            "invalid_infrastructure_history_count": len(infrastructure_history),
        },
        "diagnostics": diagnostics,
    }
    summary_text = (
        f"Target participant-level EDSR (n=10 policies): {overall['mean']:.6f} ± "
        f"{overall['sample_standard_deviation']:.6f} sample SD (ddof=1).\n"
        f"L participants (T01–T05, n=5): {left['mean']:.6f} ± "
        f"{left['sample_standard_deviation']:.6f}.\n"
        f"R participants (T06–T10, n=5): {right['mean']:.6f} ± "
        f"{right['sample_standard_deviation']:.6f}.\n"
        f"Raw paired rollout outcomes: {final_results['raw_rollout_counts']['successes']}/100 successful; "
        "these 100 outcomes are not treated as independent participant-level significance samples.\n"
        "Target outcomes use the user-authorised 0.10 m target-XY radius; the already-running "
        "Control protocol was not modified and retained its shared 0.03 m radius.\n"
        f"Primary failure counts: {json.dumps(dict(sorted(primary_taxonomy.items())), sort_keys=True)}.\n"
        "No Target-versus-Control claim is made here because this file reports Target results only.\n"
    )

    helper_records = {}
    for name in (
        "target_protocol.py",
        "validate_raw_collection.py",
        "convert_target_hdf5.py",
        "validate_target_hdf5.py",
        "prepare_target_training.py",
        "train_target_one.py",
        "validate_target_models.py",
        "freeze_target_rollout_specs.py",
        "evaluate_target_policy.py",
        "analyze_target_results.py",
    ):
        path = args.helper_root.resolve() / name
        helper_records[name] = artifact_record(path)
    experiment_manifest = {
        "schema_version": 1,
        "group": GROUP,
        "collection_seed": SEED,
        "evaluation_seed": EVALUATION_SEED,
        "participant_order": PARTICIPANTS,
        "routes": ROUTES,
        "success_protocol": final_results["success_protocol"],
        "comparability_limitation": (
            "By explicit user instruction, Target uses a 0.10 m target-XY success radius while "
            "the already-running Control protocol was not modified and retains 0.03 m."
        ),
        "stage_artifacts": artifacts,
        "helpers": helper_records,
        "software_sources": {
            name: artifact_record(path)
            for name, path in {
                "target_collector": args.helper_root.resolve().parent
                / "main_obstacle_transport_target_participants.py",
                "shared_task": args.helper_root.resolve().parent / "main_obstacle_transport.py",
                "shared_policy_evaluator_reference": args.helper_root.resolve().parent
                / "eval_obstacle_transport_trained_policy.py",
                "robomimic_train_entrypoint": Path(
                    "/users/k23114984/code/arcap_policy/STEP2_train_policy/robomimic/scripts/train.py"
                ),
                "robomimic_training_template": Path(
                    "/users/k23114984/code/arcap_policy/STEP2_train_policy/robomimic/"
                    "training_config/sim_test_00.json"
                ),
            }.items()
        },
        "raw_root": str(raw_root),
        "hdf5_root": str(hdf5_root),
        "models_root": str(models_root),
        "policy_rollout_root": str(rollout_root),
        "analysis_root": str(analysis_root),
        "statistics_contract": {
            "unit": "participant-level policy",
            "edsr_denominator_per_participant": 10,
            "sample_standard_deviation_ddof": 1,
        },
    }
    participant_csv = csv_payload(
        ["participant_id", "route", "success_count", "rollout_count", "edsr"],
        participant_rows,
    )
    rollout_fields = list(rollout_csv_rows[0])
    rollout_csv = csv_payload(rollout_fields, rollout_csv_rows)
    video_index = {
        "group": GROUP,
        "representative_rule": "first success per participant plus every failed rollout",
        "videos": video_rows,
    }
    plot = plot_bytes(participant_rows, overall)

    planned_payloads = {
        "final_results.json": json_bytes(final_results),
        "participant_edsr.csv": participant_csv,
        "rollout_results.csv": rollout_csv,
        "experiment_manifest.json": json_bytes(experiment_manifest),
        "participant_edsr.png": plot,
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
            "json_csv_participant_rows_equal": True,
            "statistics_recomputed_from_ten_saved_edsr": True,
            "sample_standard_deviation_ddof": 1,
            "all_rollouts_reference_one_shared_manifest_hash": True,
            "all_rollouts_reference_correct_participant_checkpoint_hash": True,
            "all_rollout_videos_present_nonempty": True,
            "no_scripted_transport_in_policy_rollouts": True,
            "target_success_radius_m": TARGET_XY_TOLERANCE,
            "control_protocol_not_modified": True,
        },
        "upstream_artifacts": artifacts,
        "planned_output_sha256": {
            name: hashlib.sha256(payload).hexdigest() for name, payload in planned_payloads.items()
        },
    }
    planned_payloads["validation_report.json"] = json_bytes(validation_report)
    for name in OUTPUT_NAMES:
        write_exclusive_bytes(output_paths[name], planned_payloads[name])
    print(json.dumps(final_results, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
