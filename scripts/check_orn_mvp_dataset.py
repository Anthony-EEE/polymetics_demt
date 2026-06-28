#!/usr/bin/env python3
import argparse
import json
import math
from collections import Counter
from pathlib import Path


CONDITION_DEGREES = {
    "R00": 0.0,
    "R15": 15.0,
    "R30": 30.0,
}

EXPECTED_PHASES = (
    "random_start",
    "open_gripper",
    "corridor_start",
    "pre_grasp",
    "pick_grasp",
    "close_gripper",
    "lift",
)


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
    tolerance=1e-9,
):
    metadata_path = demo_dir / "metadata.json"
    errors = []
    warnings = []
    if not metadata_path.exists():
        return None, [f"{demo_dir}: missing metadata.json"], warnings

    metadata = load_json(metadata_path)
    condition = metadata.get("condition_label")
    if expected_condition and condition != expected_condition:
        errors.append(
            f"{demo_dir.name}: condition_label={condition!r}, expected {expected_condition!r}"
        )
    if condition not in CONDITION_DEGREES:
        errors.append(f"{demo_dir.name}: unknown condition_label={condition!r}")

    success = metadata.get("success", {})
    if success.get("success") is not True:
        errors.append(f"{demo_dir.name}: success is not true: {success}")

    if metadata.get("task") != "cube_grasp_lift_orientation_mvp":
        errors.append(f"{demo_dir.name}: unexpected task={metadata.get('task')!r}")

    corridor_radius = float(metadata.get("corridor_start_radius", -1.0))
    pre_radius = float(metadata.get("pre_grasp_radius", -1.0))
    if abs(corridor_radius - float(expected_corridor_radius)) > tolerance:
        errors.append(
            f"{demo_dir.name}: corridor_start_radius={corridor_radius}, expected {expected_corridor_radius}"
        )
    if abs(pre_radius - float(expected_pre_grasp_radius)) > tolerance:
        errors.append(
            f"{demo_dir.name}: pre_grasp_radius={pre_radius}, expected {expected_pre_grasp_radius}"
        )

    expected_degrees = CONDITION_DEGREES.get(condition)
    orientation_max = metadata.get("orientation_max_degrees")
    angle_degrees = metadata.get("orientation_angle_degrees")
    if expected_degrees is not None:
        if orientation_max is None:
            errors.append(f"{demo_dir.name}: missing orientation_max_degrees")
        elif abs(float(orientation_max) - expected_degrees) > tolerance:
            warnings.append(
                f"{demo_dir.name}: orientation_max_degrees={orientation_max}, table value={expected_degrees}"
            )
    if angle_degrees is None:
        errors.append(f"{demo_dir.name}: missing orientation_angle_degrees")
    elif orientation_max is not None and abs(float(angle_degrees)) > float(orientation_max) + 1e-8:
        errors.append(
            f"{demo_dir.name}: abs(orientation_angle_degrees)={abs(float(angle_degrees)):.6f} "
            f"exceeds orientation_max_degrees={float(orientation_max):.6f}"
        )

    axis = metadata.get("orientation_axis")
    if axis is None or len(axis) != 3:
        errors.append(f"{demo_dir.name}: missing orientation_axis")
    elif abs(vector_norm(axis) - 1.0) > 1e-6:
        errors.append(f"{demo_dir.name}: orientation_axis norm={vector_norm(axis):.9f}, expected 1")

    for key in ("default_quat_xyzw", "orientation_delta_quat_xyzw", "contact_quat_xyzw"):
        quat = metadata.get(key)
        if quat is None or len(quat) != 4:
            errors.append(f"{demo_dir.name}: missing {key}")
        elif abs(vector_norm(quat) - 1.0) > 1e-6:
            errors.append(f"{demo_dir.name}: {key} norm={vector_norm(quat):.9f}, expected 1")

    applied = metadata.get("orientation_applied_phases")
    if applied != list(EXPECTED_PHASES):
        errors.append(
            f"{demo_dir.name}: orientation_applied_phases={applied}, expected {list(EXPECTED_PHASES)}"
        )

    delta_start = metadata.get("corridor_start_delta")
    if delta_start is None:
        errors.append(f"{demo_dir.name}: missing corridor_start_delta")
    else:
        if vector_norm(delta_start) > corridor_radius + 1e-8:
            errors.append(
                f"{demo_dir.name}: ||corridor_start_delta||={vector_norm(delta_start):.6f} "
                f"exceeds corridor_start_radius={corridor_radius:.6f}"
            )
        if len(delta_start) > 1 and abs(float(delta_start[1])) > tolerance:
            errors.append(f"{demo_dir.name}: corridor_start_delta[1]={delta_start[1]} should be 0")

    delta_pre = metadata.get("pre_grasp_delta")
    if delta_pre is None:
        errors.append(f"{demo_dir.name}: missing pre_grasp_delta")
    elif vector_norm(delta_pre) > 1e-8:
        errors.append(f"{demo_dir.name}: pre_grasp_delta must be zero, got {delta_pre}")

    random_start = metadata.get("random_start")
    x_bounds = metadata.get("random_start_x_bounds")
    z_bounds = metadata.get("random_start_z_bounds")
    if random_start is None:
        errors.append(f"{demo_dir.name}: missing random_start")
    else:
        if abs(float(random_start[1])) > tolerance:
            errors.append(f"{demo_dir.name}: random_start y={random_start[1]} should be 0")
        if x_bounds and not (float(x_bounds[0]) - tolerance <= float(random_start[0]) <= float(x_bounds[1]) + tolerance):
            errors.append(f"{demo_dir.name}: random_start x={random_start[0]} outside {x_bounds}")
        if z_bounds and not (float(z_bounds[0]) - tolerance <= float(random_start[2]) <= float(z_bounds[1]) + tolerance):
            errors.append(f"{demo_dir.name}: random_start z={random_start[2]} outside {z_bounds}")

    base_corridor_start = metadata.get("base_corridor_start")
    corridor_start_y = float(metadata.get("corridor_start_y", expected_corridor_start_y))
    if abs(corridor_start_y - float(expected_corridor_start_y)) > tolerance:
        errors.append(
            f"{demo_dir.name}: corridor_start_y={corridor_start_y}, expected {expected_corridor_start_y}"
        )
    if base_corridor_start is None:
        errors.append(f"{demo_dir.name}: missing base_corridor_start")
    elif abs(float(base_corridor_start[1]) - corridor_start_y) > tolerance:
        errors.append(
            f"{demo_dir.name}: base_corridor_start y={base_corridor_start[1]} should be {corridor_start_y}"
        )

    counts = phase_counts(demo_dir)
    if not counts:
        errors.append(f"{demo_dir.name}: no frame phase files found")
    for required_phase in EXPECTED_PHASES:
        if counts.get(required_phase, 0) == 0:
            errors.append(f"{demo_dir.name}: missing phase {required_phase!r}")

    summary = {
        "demo": demo_dir.name,
        "condition": condition,
        "frames": sum(counts.values()),
        "phase_counts": dict(counts),
        "orientation_angle_degrees": angle_degrees,
        "corridor_delta_norm": vector_norm(delta_start or [0, 0, 0]),
        "pre_grasp_delta_norm": vector_norm(delta_pre or [0, 0, 0]),
        "final_cube_z": success.get("final_cube_z"),
    }
    return summary, errors, warnings


def main():
    parser = argparse.ArgumentParser(description="Sanity-check an orientation MVP raw dataset.")
    parser.add_argument("dataset_dir", help="Directory containing demo_<idx> folders.")
    parser.add_argument("--expected-demos", type=int, default=None)
    parser.add_argument("--expected-condition", choices=sorted(CONDITION_DEGREES), default=None)
    parser.add_argument("--expected-corridor-radius", type=float, default=0.05)
    parser.add_argument("--expected-pre-grasp-radius", type=float, default=0.0)
    parser.add_argument("--expected-corridor-start-y", type=float, default=0.15)
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON summary.")
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

    for demo_dir in demo_dirs:
        summary, errors, warnings = check_demo(
            demo_dir,
            expected_condition=args.expected_condition,
            expected_corridor_radius=args.expected_corridor_radius,
            expected_pre_grasp_radius=args.expected_pre_grasp_radius,
            expected_corridor_start_y=args.expected_corridor_start_y,
        )
        if summary is not None:
            summaries.append(summary)
        all_errors.extend(errors)
        all_warnings.extend(warnings)

    frame_counts = [s["frames"] for s in summaries]
    conditions = Counter(s["condition"] for s in summaries)
    angles = [float(s["orientation_angle_degrees"]) for s in summaries if s["orientation_angle_degrees"] is not None]
    report = {
        "dataset_dir": str(root),
        "num_demos": len(demo_dirs),
        "conditions": dict(conditions),
        "frame_count_min": min(frame_counts) if frame_counts else 0,
        "frame_count_max": max(frame_counts) if frame_counts else 0,
        "frame_count_mean": sum(frame_counts) / len(frame_counts) if frame_counts else 0.0,
        "angle_degrees_min": min(angles) if angles else None,
        "angle_degrees_max": max(angles) if angles else None,
        "warnings": all_warnings,
        "errors": all_errors,
        "demos": summaries,
    }

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"Dataset: {root}")
        print(f"Demos: {len(demo_dirs)}")
        print(f"Conditions: {dict(conditions)}")
        print(
            "Frames: "
            f"min={report['frame_count_min']}, "
            f"mean={report['frame_count_mean']:.1f}, "
            f"max={report['frame_count_max']}"
        )
        print(f"Angle degrees: min={report['angle_degrees_min']}, max={report['angle_degrees_max']}")
        if all_warnings:
            print("\nWarnings:")
            for warning in all_warnings:
                print(f"  - {warning}")
        if all_errors:
            print("\nErrors:")
            for error in all_errors:
                print(f"  - {error}")
        else:
            print("\nOK: dataset passed orientation MVP sanity checks.")

    return 1 if all_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
