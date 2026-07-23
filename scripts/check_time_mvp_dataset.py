#!/usr/bin/env python3
import argparse
import hashlib
import json
import math
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path


TIME_CONDITIONS = {
    "T00": (1.00, 1.00),
    "T25": (0.75, 1.25),
    "T50": (0.50, 1.50),
    "T75": (0.25, 1.75),
    "T100": (0.00, 2.00),
    "V075_150": (0.75, 1.50),
    "V050_200": (0.50, 2.00),
    "V025_250": (0.25, 2.50),
    "VR1P5": (float(Fraction(2, 3)), float(Fraction(3, 2))),
    "VR3": (float(Fraction(1, 3)), 3.0),
    "VR4": (0.25, 4.0),
}
MIN_PHASE_DURATION_FRAMES = 1

LADDER_EXPECTED_PHASES = (
    "random_start",
    "open_gripper",
    "corridor_start",
    "pre_grasp",
    "pick_grasp",
    "close_gripper",
    "lift",
)

VREF_EXPECTED_PHASES = (
    "random_start",
    "corridor_start",
    "pre_grasp",
    "pick_grasp",
    "close_gripper",
    "lift",
)

LADDER_TIMED_PHASES = tuple(p for p in LADDER_EXPECTED_PHASES if p != "random_start")
VREF_TIMED_PHASES = (
    "start_to_corridor",
    "corridor_to_pregrasp",
    "pregrasp_to_first_close",
    "first_close_to_end",
)
VREF_CONDITIONS = {"V075_150", "V050_200", "V025_250", "VR1P5", "VR3", "VR4"}
NEW_RECIPROCAL_SPECS = {
    "VR1P5": Fraction(3, 2),
    "V050_200": Fraction(2, 1),
    "VR3": Fraction(3, 1),
    "VR4": Fraction(4, 1),
}
VREF_GROUP = "P6P7_post_valid_order"


def is_vref_condition(condition):
    return condition in VREF_CONDITIONS


def expected_phases_for_condition(condition):
    if is_vref_condition(condition):
        return VREF_EXPECTED_PHASES
    return LADDER_EXPECTED_PHASES


def timed_phases_for_condition(condition):
    if is_vref_condition(condition):
        return VREF_TIMED_PHASES
    return LADDER_TIMED_PHASES


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def file_sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def vector_norm(values):
    return math.sqrt(sum(float(v) * float(v) for v in values))


def frame_sort_key(path):
    try:
        return int(path.parent.name.split("_", 1)[1])
    except (IndexError, ValueError):
        return path.parent.name


def demo_sort_key(path):
    try:
        return int(path.name.split("_", 1)[1])
    except (IndexError, ValueError):
        return path.name


def phase_counts(demo_dir):
    counts = Counter()
    for phase_path in sorted(demo_dir.glob("frame_*/phase.txt"), key=frame_sort_key):
        counts[phase_path.read_text(encoding="utf-8").strip()] += 1
    return counts


def check_demo(
    demo_dir,
    expected_condition=None,
    expected_corridor_radius=0.05,
    expected_pre_grasp_radius=0.0,
    expected_corridor_start_y=0.15,
    expected_random_start=None,
    tolerance=1e-9,
):
    metadata_path = demo_dir / "metadata.json"
    errors = []
    warnings = []
    if not metadata_path.exists():
        return None, [f"{demo_dir}: missing metadata.json"], warnings

    metadata = load_json(metadata_path)
    condition = metadata.get("condition_label")
    condition_alias = metadata.get("condition")
    if expected_condition and condition != expected_condition:
        errors.append(f"{demo_dir.name}: condition_label={condition!r}, expected {expected_condition!r}")
    if condition_alias is not None and condition_alias != condition:
        errors.append(f"{demo_dir.name}: condition={condition_alias!r} differs from condition_label={condition!r}")
    if condition not in TIME_CONDITIONS:
        errors.append(f"{demo_dir.name}: unknown condition_label={condition!r}")

    if metadata.get("task") != "cube_grasp_lift_time_mvp":
        errors.append(f"{demo_dir.name}: unexpected task={metadata.get('task')!r}")
    success = metadata.get("success", {})
    if success.get("success") is not True:
        errors.append(f"{demo_dir.name}: success is not true: {success}")

    corridor_radius = float(metadata.get("corridor_start_radius", -1.0))
    pre_radius = float(metadata.get("pre_grasp_radius", -1.0))
    if abs(corridor_radius - float(expected_corridor_radius)) > tolerance:
        errors.append(f"{demo_dir.name}: corridor_start_radius={corridor_radius}, expected {expected_corridor_radius}")
    if abs(pre_radius - float(expected_pre_grasp_radius)) > tolerance:
        errors.append(f"{demo_dir.name}: pre_grasp_radius={pre_radius}, expected {expected_pre_grasp_radius}")

    random_start = metadata.get("random_start")
    if random_start is None:
        errors.append(f"{demo_dir.name}: missing random_start")
    else:
        if condition in NEW_RECIPROCAL_SPECS:
            if not (0.2 - tolerance <= float(random_start[0]) <= 0.6 + tolerance):
                errors.append(f"{demo_dir.name}: random_start x outside [0.2,0.6]")
            if not (0.2 - tolerance <= float(random_start[2]) <= 0.6 + tolerance):
                errors.append(f"{demo_dir.name}: random_start z outside [0.2,0.6]")
        elif expected_random_start is not None:
            for i, (got, exp) in enumerate(zip(random_start, expected_random_start)):
                if abs(float(got) - float(exp)) > 0.03:
                    errors.append(f"{demo_dir.name}: random_start[{i}]={got}, expected near {exp}")
        if abs(float(random_start[1])) > tolerance:
            errors.append(f"{demo_dir.name}: random_start y={random_start[1]} should be 0")

    delta_start = metadata.get("corridor_start_delta")
    if delta_start is None:
        errors.append(f"{demo_dir.name}: missing corridor_start_delta")
    else:
        if abs(float(delta_start[1])) > tolerance:
            errors.append(f"{demo_dir.name}: corridor_start_delta y must be zero")
        if math.hypot(float(delta_start[0]), float(delta_start[2])) > corridor_radius + 1e-8:
            errors.append(f"{demo_dir.name}: corridor_start_delta exceeds radius")

    delta_pre = metadata.get("pre_grasp_delta")
    if delta_pre is None:
        errors.append(f"{demo_dir.name}: missing pre_grasp_delta")
    elif vector_norm(delta_pre) > 1e-8:
        errors.append(f"{demo_dir.name}: pre_grasp_delta must be zero, got {delta_pre}")

    base_corridor_start = metadata.get("base_corridor_start")
    corridor_start_y = float(metadata.get("corridor_start_y", expected_corridor_start_y))
    if abs(corridor_start_y - float(expected_corridor_start_y)) > tolerance:
        errors.append(f"{demo_dir.name}: corridor_start_y={corridor_start_y}, expected {expected_corridor_start_y}")
    if base_corridor_start is None:
        errors.append(f"{demo_dir.name}: missing base_corridor_start")
    elif abs(float(base_corridor_start[1]) - corridor_start_y) > tolerance:
        errors.append(f"{demo_dir.name}: base_corridor_start y={base_corridor_start[1]} should be {corridor_start_y}")
    corridor_start = metadata.get("corridor_start")
    if base_corridor_start is not None and delta_start is not None and corridor_start is not None:
        resolved = [float(base_corridor_start[i]) + float(delta_start[i]) for i in range(3)]
        if any(abs(resolved[i] - float(corridor_start[i])) > tolerance for i in range(3)):
            errors.append(f"{demo_dir.name}: corridor_start != base_corridor_start + delta")

    default_quat = metadata.get("default_quat_xyzw")
    if default_quat is None or len(default_quat) != 4:
        errors.append(f"{demo_dir.name}: missing default_quat_xyzw")
    elif abs(vector_norm(default_quat) - 1.0) > 1e-6:
        errors.append(f"{demo_dir.name}: default_quat_xyzw norm={vector_norm(default_quat):.9f}, expected 1")

    expected_timed_phases = timed_phases_for_condition(condition)
    expected_saved_phases = expected_phases_for_condition(condition)
    applied = metadata.get("timing_applied_phases")
    if applied != list(expected_timed_phases):
        errors.append(
            f"{demo_dir.name}: timing_applied_phases={applied}, expected {list(expected_timed_phases)}"
        )
    if is_vref_condition(condition):
        if metadata.get("experiment_track") != "temporal_v_ref":
            errors.append(f"{demo_dir.name}: expected experiment_track='temporal_v_ref'")
        if metadata.get("v_ref_group") != VREF_GROUP:
            errors.append(f"{demo_dir.name}: v_ref_group={metadata.get('v_ref_group')!r}, expected {VREF_GROUP!r}")
        if not metadata.get("v_ref_source_json"):
            errors.append(f"{demo_dir.name}: missing v_ref_source_json")
        for required_key in (
            "v_ref_phase_durations_s",
            "sampled_phase_multipliers",
            "target_phase_durations_s",
            "target_simulator_phase_durations_s",
            "simulator_phase_mapping",
        ):
            if not metadata.get(required_key):
                errors.append(f"{demo_dir.name}: missing {required_key}")
        reciprocal_n = NEW_RECIPROCAL_SPECS.get(condition)
        if reciprocal_n is not None:
            expected_low = 1 / reciprocal_n
            expected_exact = [str(expected_low), str(reciprocal_n)]
            expected_rational = [
                {"numerator": expected_low.numerator, "denominator": expected_low.denominator},
                {
                    "numerator": reciprocal_n.numerator,
                    "denominator": reciprocal_n.denominator,
                },
            ]
            if metadata.get("reciprocal_n_exact") != str(reciprocal_n):
                errors.append(
                    f"{demo_dir.name}: reciprocal_n_exact={metadata.get('reciprocal_n_exact')!r}, "
                    f"expected {str(reciprocal_n)!r}"
                )
            if metadata.get("condition_multiplier_range_exact") != expected_exact:
                errors.append(
                    f"{demo_dir.name}: condition_multiplier_range_exact="
                    f"{metadata.get('condition_multiplier_range_exact')!r}, expected {expected_exact!r}"
                )
            if metadata.get("condition_multiplier_range_rational") != expected_rational:
                errors.append(f"{demo_dir.name}: incorrect exact rational multiplier metadata")
            if not math.isclose(float(metadata.get("reciprocal_n", -1.0)), float(reciprocal_n)):
                errors.append(f"{demo_dir.name}: incorrect reciprocal_n")
            if not math.isclose(float(metadata.get("reciprocal_range_product", -1.0)), 1.0):
                errors.append(f"{demo_dir.name}: reciprocal range product is not 1")
            manifest_record = metadata.get("collection_manifest")
            if not isinstance(manifest_record, dict) or not manifest_record.get("sha256"):
                errors.append(f"{demo_dir.name}: missing collection manifest identity")
            if not metadata.get("candidate_id"):
                errors.append(f"{demo_dir.name}: missing candidate_id")
            disk_latents = metadata.get("corridor_disk_latents", {})
            u_radius = disk_latents.get("u_radius")
            u_theta = disk_latents.get("u_theta")
            if u_radius is None or u_theta is None:
                errors.append(f"{demo_dir.name}: missing corridor disk latent values")
            elif not (0.0 <= float(u_radius) < 1.0 and 0.0 <= float(u_theta) < 1.0):
                errors.append(f"{demo_dir.name}: corridor disk latent values outside [0,1)")
            elif delta_start is not None:
                radius = float(expected_corridor_radius) * math.sqrt(float(u_radius))
                theta = 2.0 * math.pi * float(u_theta)
                expected_delta = [radius * math.cos(theta), 0.0, radius * math.sin(theta)]
                if any(
                    not math.isclose(
                        float(delta_start[index]), expected_delta[index], rel_tol=0.0, abs_tol=1e-12
                    )
                    for index in range(3)
                ):
                    errors.append(f"{demo_dir.name}: corridor delta does not map as r=0.05*sqrt(U)")
            uniforms = metadata.get("common_uniforms", {})
            group_multipliers = metadata.get("sampled_group_multipliers", {})
            low_float = float(expected_low)
            high_float = float(reciprocal_n)
            for group in ("P6", "P7"):
                common_u = uniforms.get(group)
                multiplier = group_multipliers.get(group)
                if common_u is None or not (0.0 <= float(common_u) < 1.0):
                    errors.append(f"{demo_dir.name}: invalid common U for {group}")
                    continue
                expected_multiplier = low_float + float(common_u) * (high_float - low_float)
                if multiplier is None or not math.isclose(
                    float(multiplier), expected_multiplier, rel_tol=0.0, abs_tol=1e-12
                ):
                    errors.append(f"{demo_dir.name}: {group} multiplier does not map from common U")
                elif not (low_float <= float(multiplier) <= high_float):
                    errors.append(f"{demo_dir.name}: {group} multiplier outside exact bounds")
            if uniforms.get("P6") == uniforms.get("P7"):
                errors.append(f"{demo_dir.name}: P6 and P7 uniforms must be independently generated")

    multipliers = metadata.get("sampled_phase_multipliers") or metadata.get("phase_duration_multipliers", {})
    low, high = TIME_CONDITIONS.get(condition, (None, None))
    if condition in NEW_RECIPROCAL_SPECS and not math.isclose(low * high, 1.0, abs_tol=1e-12):
        errors.append(f"{demo_dir.name}: configured reciprocal range product is {low * high}, not 1")
    multiplier_range = metadata.get("condition_multiplier_range")
    if low is not None and multiplier_range != [float(low), float(high)]:
        errors.append(
            f"{demo_dir.name}: condition_multiplier_range={multiplier_range}, expected {[float(low), float(high)]}"
        )
    for phase in expected_timed_phases:
        value = multipliers.get(phase)
        if value is None:
            errors.append(f"{demo_dir.name}: missing multiplier for {phase}")
        elif low is not None and not (low - 1e-8 <= float(value) <= high + 1e-8):
            errors.append(f"{demo_dir.name}: multiplier {phase}={value} outside [{low}, {high}]")

    min_frames = metadata.get("min_phase_duration_frames")
    min_seconds = metadata.get("min_phase_duration_seconds")
    clamp_rule = metadata.get("phase_duration_clamp_rule")
    target_frames = metadata.get("target_phase_duration_frames", {})
    target_before = metadata.get("target_phase_duration_frames_before_clamp", {})
    if is_vref_condition(condition):
        target_before = target_frames
    clamped = metadata.get("phase_duration_clamped", {})
    if min_frames != MIN_PHASE_DURATION_FRAMES:
        errors.append(f"{demo_dir.name}: min_phase_duration_frames={min_frames}, expected {MIN_PHASE_DURATION_FRAMES}")
    if min_seconds is None or float(min_seconds) <= 0.0:
        errors.append(f"{demo_dir.name}: missing positive min_phase_duration_seconds")
    if not clamp_rule:
        errors.append(f"{demo_dir.name}: missing phase_duration_clamp_rule")
    for phase in expected_timed_phases:
        frames = target_frames.get(phase)
        before_frames = target_before.get(phase)
        was_clamped = clamped.get(phase)
        if frames is None:
            errors.append(f"{demo_dir.name}: missing target_phase_duration_frames for {phase}")
        elif int(frames) < MIN_PHASE_DURATION_FRAMES:
            errors.append(f"{demo_dir.name}: target_phase_duration_frames[{phase}]={frames} is not positive")
        if before_frames is None:
            errors.append(f"{demo_dir.name}: missing target_phase_duration_frames_before_clamp for {phase}")
        elif int(before_frames) < MIN_PHASE_DURATION_FRAMES and was_clamped is not True:
            errors.append(f"{demo_dir.name}: {phase} should be marked clamped when before_frames={before_frames}")
    if is_vref_condition(condition):
        simulator_frames = metadata.get("target_simulator_phase_duration_frames", {})
        for phase in expected_saved_phases:
            if phase == "random_start":
                continue
            frames = simulator_frames.get(phase)
            if frames is None:
                errors.append(f"{demo_dir.name}: missing target_simulator_phase_duration_frames for {phase}")
            elif int(frames) < MIN_PHASE_DURATION_FRAMES:
                errors.append(f"{demo_dir.name}: simulator phase {phase} has non-positive target frames")
    if condition == "T100" and abs(float(low)) > 1e-12:
        errors.append(f"{demo_dir.name}: T100 lower multiplier should be 0.00, got {low}")

    counts = phase_counts(demo_dir)
    if not counts:
        errors.append(f"{demo_dir.name}: no frame phase files found")
    for phase in expected_saved_phases:
        if counts.get(phase, 0) == 0:
            errors.append(f"{demo_dir.name}: missing phase {phase!r}")

    summary = {
        "demo": demo_dir.name,
        "condition": condition,
        "frames": sum(counts.values()),
        "phase_counts": dict(counts),
        "phase_duration_multipliers": {k: float(v) for k, v in multipliers.items()},
        "final_cube_z": success.get("final_cube_z"),
        "candidate_id": metadata.get("candidate_id"),
        "random_start": metadata.get("random_start"),
        "base_corridor_start": metadata.get("base_corridor_start"),
        "corridor_start": metadata.get("corridor_start"),
        "corridor_start_delta": metadata.get("corridor_start_delta"),
        "pre_grasp_delta": metadata.get("pre_grasp_delta"),
        "common_uniforms": metadata.get("common_uniforms"),
        "sampled_group_multipliers": metadata.get("sampled_group_multipliers"),
        "collection_manifest": metadata.get("collection_manifest"),
    }
    return summary, errors, warnings


def check_reciprocal_group(root, conditions, dataset_template, expected_demos, manifest_path):
    errors = []
    by_condition = {}
    expected_manifest_sha = file_sha256(manifest_path) if manifest_path else None
    manifest_candidates = {}
    if manifest_path:
        manifest = load_json(manifest_path)
        manifest_candidates = {
            candidate["candidate_id"]: candidate for candidate in manifest.get("candidates", [])
        }
    for condition in conditions:
        dataset_dir = root / dataset_template.format(condition=condition)
        demo_dirs = sorted(
            [path for path in dataset_dir.glob("demo_*") if path.is_dir()], key=demo_sort_key
        )
        if len(demo_dirs) != expected_demos:
            errors.append(f"{condition}: found {len(demo_dirs)} demos, expected {expected_demos}")
        summaries = []
        for demo_dir in demo_dirs:
            summary, demo_errors, _ = check_demo(
                demo_dir,
                expected_condition=condition,
                expected_corridor_radius=0.05,
                expected_pre_grasp_radius=0.0,
                expected_corridor_start_y=0.15,
            )
            errors.extend(demo_errors)
            if summary is not None:
                summaries.append(summary)
        by_condition[condition] = summaries

    reference = by_condition.get(conditions[0], [])
    reference_ids = [row["candidate_id"] for row in reference]
    for condition, rows in by_condition.items():
        ids = [row["candidate_id"] for row in rows]
        if ids != reference_ids:
            errors.append(f"{condition}: candidate ID set/order differs from {conditions[0]}")
        for field in (
            "random_start",
            "base_corridor_start",
            "corridor_start",
            "corridor_start_delta",
            "pre_grasp_delta",
            "common_uniforms",
        ):
            if [row[field] for row in rows] != [row[field] for row in reference]:
                errors.append(f"{condition}: candidate-wise {field} differs from {conditions[0]}")
        if expected_manifest_sha is not None:
            for row in rows:
                if (row.get("collection_manifest") or {}).get("sha256") != expected_manifest_sha:
                    errors.append(f"{condition}/{row['demo']}: collection manifest hash mismatch")
                candidate = manifest_candidates.get(row["candidate_id"])
                if candidate is None:
                    errors.append(f"{condition}/{row['demo']}: candidate ID absent from manifest")
                    continue
                for field in (
                    "random_start",
                    "base_corridor_start",
                    "corridor_start",
                    "corridor_start_delta",
                    "pre_grasp_delta",
                    "common_uniforms",
                ):
                    if row[field] != candidate[field]:
                        errors.append(
                            f"{condition}/{row['demo']}: {field} differs from manifest candidate"
                        )

    if reference:
        starts = [tuple(float(v) for v in row["random_start"]) for row in reference]
        deltas = [tuple(float(v) for v in row["corridor_start_delta"]) for row in reference]
        if len(set(starts)) != expected_demos:
            errors.append(f"empirical random starts are not {expected_demos} distinct points")
        if len(set(deltas)) != expected_demos:
            errors.append(f"empirical corridor deltas are not {expected_demos} distinct points")
        if expected_demos >= 30:
            for axis, label in ((0, "x"), (2, "z")):
                values = [delta[axis] for delta in deltas]
                mean = sum(values) / len(values)
                variance = sum((value - mean) ** 2 for value in values) / len(values)
                if variance <= 0.0:
                    errors.append(f"corridor delta {label} variance is zero")
        if any(any(float(v) != 0.0 for v in row["pre_grasp_delta"]) for row in reference):
            errors.append("pre_grasp deltas are not exactly all zero")

    paired_count = min((len(rows) for rows in by_condition.values()), default=0)
    for candidate_index in range(paired_count):
        p6_values = []
        p7_values = []
        for condition in conditions:
            row = by_condition[condition][candidate_index]
            p6_values.append(float(row["common_uniforms"]["P6"]))
            p7_values.append(float(row["common_uniforms"]["P7"]))
        if len(set(p6_values)) != 1 or len(set(p7_values)) != 1:
            errors.append(f"candidate {candidate_index}: common P6/P7 U is not shared")
    if reference and [row["common_uniforms"]["P6"] for row in reference] == [
        row["common_uniforms"]["P7"] for row in reference
    ]:
        errors.append("P6 and P7 empirical uniform streams are identical")

    report = {
        "root": str(root),
        "conditions": list(conditions),
        "expected_demos": expected_demos,
        "candidate_ids": reference_ids,
        "random_start_distinct": len({tuple(row["random_start"]) for row in reference}),
        "corridor_delta_distinct": len({tuple(row["corridor_start_delta"]) for row in reference}),
        "errors": errors,
    }
    return report


def main():
    parser = argparse.ArgumentParser(description="Sanity-check a temporal MVP raw dataset.")
    parser.add_argument("dataset_dir", nargs="?")
    parser.add_argument("--root", type=Path, default=None)
    parser.add_argument(
        "--conditions", nargs="+", default=["VR1P5", "V050_200", "VR3", "VR4"]
    )
    parser.add_argument("--dataset-template", default="temporal_{condition}_d30_seed1")
    parser.add_argument("--manifest", type=Path, default=None)
    parser.add_argument("--expected-demos", type=int, default=None)
    parser.add_argument("--expected-condition", choices=sorted(TIME_CONDITIONS), default=None)
    parser.add_argument("--expected-corridor-radius", type=float, default=0.05)
    parser.add_argument("--expected-pre-grasp-radius", type=float, default=0.0)
    parser.add_argument("--expected-corridor-start-y", type=float, default=0.15)
    parser.add_argument("--expected-random-start-x", type=float, default=0.40)
    parser.add_argument("--expected-random-start-z", type=float, default=0.40)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.root is not None:
        if args.dataset_dir is not None:
            parser.error("dataset_dir and --root are mutually exclusive")
        expected_demos = 30 if args.expected_demos is None else args.expected_demos
        report = check_reciprocal_group(
            args.root,
            tuple(args.conditions),
            args.dataset_template,
            expected_demos,
            args.manifest,
        )
        if args.json:
            print(json.dumps(report, indent=2, sort_keys=True))
        else:
            print(f"Reciprocal group: {args.root}")
            print(f"Conditions: {report['conditions']}")
            print(f"Candidate IDs: {len(report['candidate_ids'])}")
            print(f"Distinct random starts: {report['random_start_distinct']}")
            print(f"Distinct corridor deltas: {report['corridor_delta_distinct']}")
            if report["errors"]:
                print("\nErrors:")
                for error in report["errors"]:
                    print(f"  - {error}")
            else:
                print("\nOK: reciprocal four-condition empirical group checks passed.")
        return 1 if report["errors"] else 0
    if args.dataset_dir is None:
        parser.error("dataset_dir is required unless --root is supplied")

    root = Path(args.dataset_dir)
    demo_dirs = sorted([p for p in root.glob("demo_*") if p.is_dir()], key=demo_sort_key)
    all_errors = []
    all_warnings = []
    summaries = []

    if not root.exists():
        all_errors.append(f"dataset directory does not exist: {root}")
    if args.expected_demos is not None and len(demo_dirs) != args.expected_demos:
        all_errors.append(f"found {len(demo_dirs)} demo dirs, expected {args.expected_demos}")

    expected_random_start = (args.expected_random_start_x, 0.0, args.expected_random_start_z)
    for demo_dir in demo_dirs:
        summary, errors, warnings = check_demo(
            demo_dir,
            expected_condition=args.expected_condition,
            expected_corridor_radius=args.expected_corridor_radius,
            expected_pre_grasp_radius=args.expected_pre_grasp_radius,
            expected_corridor_start_y=args.expected_corridor_start_y,
            expected_random_start=expected_random_start,
        )
        if summary is not None:
            summaries.append(summary)
        all_errors.extend(errors)
        all_warnings.extend(warnings)

    frame_counts = [s["frames"] for s in summaries]
    phase_stats = defaultdict(list)
    for s in summaries:
        for phase, count in s["phase_counts"].items():
            phase_stats[phase].append(int(count))
    phase_report = {
        phase: {
            "min": min(values),
            "mean": sum(values) / len(values),
            "max": max(values),
        }
        for phase, values in sorted(phase_stats.items())
    }
    report = {
        "dataset_dir": str(root),
        "num_demos": len(demo_dirs),
        "conditions": dict(Counter(s["condition"] for s in summaries)),
        "frame_count_min": min(frame_counts) if frame_counts else 0,
        "frame_count_max": max(frame_counts) if frame_counts else 0,
        "frame_count_mean": sum(frame_counts) / len(frame_counts) if frame_counts else 0.0,
        "phase_count_stats": phase_report,
        "warnings": all_warnings,
        "errors": all_errors,
        "demos": summaries,
    }

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"Dataset: {root}")
        print(f"Demos: {len(demo_dirs)}")
        print(f"Conditions: {report['conditions']}")
        print(
            "Frames: "
            f"min={report['frame_count_min']}, "
            f"mean={report['frame_count_mean']:.1f}, "
            f"max={report['frame_count_max']}"
        )
        print("Phase counts:")
        for phase, stats in phase_report.items():
            print(f"  {phase}: min={stats['min']}, mean={stats['mean']:.1f}, max={stats['max']}")
        if all_warnings:
            print("\nWarnings:")
            for warning in all_warnings:
                print(f"  - {warning}")
        if all_errors:
            print("\nErrors:")
            for error in all_errors:
                print(f"  - {error}")
        else:
            print("\nOK: dataset passed temporal MVP sanity checks.")

    return 1 if all_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
