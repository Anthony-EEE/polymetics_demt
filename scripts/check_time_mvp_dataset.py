#!/usr/bin/env python3
import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path


TIME_CONDITIONS = {
    "T00": (1.00, 1.00),
    "T25": (0.75, 1.25),
    "T50": (0.50, 1.50),
    "T75": (0.25, 1.75),
    "T100": (0.00, 2.00),
}
MIN_PHASE_DURATION_FRAMES = 1

EXPECTED_PHASES = (
    "random_start",
    "open_gripper",
    "corridor_start",
    "pre_grasp",
    "pick_grasp",
    "close_gripper",
    "lift",
)

TIMED_PHASES = tuple(p for p in EXPECTED_PHASES if p != "random_start")


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


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
    expected_random_start=(0.40, 0.0, 0.40),
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
        for i, (got, exp) in enumerate(zip(random_start, expected_random_start)):
            if abs(float(got) - float(exp)) > 0.03:
                errors.append(f"{demo_dir.name}: random_start[{i}]={got}, expected near {exp}")
        if abs(float(random_start[1])) > tolerance:
            errors.append(f"{demo_dir.name}: random_start y={random_start[1]} should be 0")

    delta_start = metadata.get("corridor_start_delta")
    if delta_start is None:
        errors.append(f"{demo_dir.name}: missing corridor_start_delta")
    else:
        if vector_norm(delta_start) > 1e-8:
            errors.append(f"{demo_dir.name}: corridor_start_delta must be zero, got {delta_start}")
        if vector_norm(delta_start) > corridor_radius + 1e-8:
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

    default_quat = metadata.get("default_quat_xyzw")
    if default_quat is None or len(default_quat) != 4:
        errors.append(f"{demo_dir.name}: missing default_quat_xyzw")
    elif abs(vector_norm(default_quat) - 1.0) > 1e-6:
        errors.append(f"{demo_dir.name}: default_quat_xyzw norm={vector_norm(default_quat):.9f}, expected 1")

    applied = metadata.get("timing_applied_phases")
    if applied != list(TIMED_PHASES):
        errors.append(f"{demo_dir.name}: timing_applied_phases={applied}, expected {list(TIMED_PHASES)}")

    multipliers = metadata.get("phase_duration_multipliers", {})
    low, high = TIME_CONDITIONS.get(condition, (None, None))
    multiplier_range = metadata.get("condition_multiplier_range")
    if low is not None and multiplier_range != [float(low), float(high)]:
        errors.append(
            f"{demo_dir.name}: condition_multiplier_range={multiplier_range}, expected {[float(low), float(high)]}"
        )
    for phase in TIMED_PHASES:
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
    clamped = metadata.get("phase_duration_clamped", {})
    if min_frames != MIN_PHASE_DURATION_FRAMES:
        errors.append(f"{demo_dir.name}: min_phase_duration_frames={min_frames}, expected {MIN_PHASE_DURATION_FRAMES}")
    if min_seconds is None or float(min_seconds) <= 0.0:
        errors.append(f"{demo_dir.name}: missing positive min_phase_duration_seconds")
    if not clamp_rule:
        errors.append(f"{demo_dir.name}: missing phase_duration_clamp_rule")
    for phase in TIMED_PHASES:
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
    if condition == "T100" and abs(float(low)) > 1e-12:
        errors.append(f"{demo_dir.name}: T100 lower multiplier should be 0.00, got {low}")

    counts = phase_counts(demo_dir)
    if not counts:
        errors.append(f"{demo_dir.name}: no frame phase files found")
    for phase in EXPECTED_PHASES:
        if counts.get(phase, 0) == 0:
            errors.append(f"{demo_dir.name}: missing phase {phase!r}")

    summary = {
        "demo": demo_dir.name,
        "condition": condition,
        "frames": sum(counts.values()),
        "phase_counts": dict(counts),
        "phase_duration_multipliers": {k: float(v) for k, v in multipliers.items()},
        "final_cube_z": success.get("final_cube_z"),
    }
    return summary, errors, warnings


def main():
    parser = argparse.ArgumentParser(description="Sanity-check a temporal MVP raw dataset.")
    parser.add_argument("dataset_dir")
    parser.add_argument("--expected-demos", type=int, default=None)
    parser.add_argument("--expected-condition", choices=sorted(TIME_CONDITIONS), default=None)
    parser.add_argument("--expected-corridor-radius", type=float, default=0.05)
    parser.add_argument("--expected-pre-grasp-radius", type=float, default=0.0)
    parser.add_argument("--expected-corridor-start-y", type=float, default=0.15)
    parser.add_argument("--expected-random-start-x", type=float, default=0.40)
    parser.add_argument("--expected-random-start-z", type=float, default=0.40)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

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
