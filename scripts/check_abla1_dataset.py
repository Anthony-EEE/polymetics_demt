#!/usr/bin/env python3
import argparse
import json
import math
from collections import Counter
from pathlib import Path


CONDITION_RADII = {
    "P00": (0.10, 0.02),
    "P10": (0.25, 0.02),
    "P01": (0.10, 0.06),
    "P11": (0.25, 0.06),
}


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def vector_norm(values):
    return math.sqrt(sum(float(v) * float(v) for v in values))


def phase_counts(demo_dir):
    counts = Counter()
    for phase_path in sorted(demo_dir.glob("frame_*/phase.txt"), key=frame_sort_key):
        counts[phase_path.read_text(encoding="utf-8").strip()] += 1
    return counts


def frame_sort_key(path):
    try:
        return int(path.parent.name.split("_", 1)[1])
    except (IndexError, ValueError):
        return path.parent.name


def check_demo(demo_dir, expected_condition=None, tolerance=1e-9):
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
    if condition not in CONDITION_RADII:
        errors.append(f"{demo_dir.name}: unknown condition_label={condition!r}")

    success = metadata.get("success", {})
    if success.get("success") is not True:
        errors.append(f"{demo_dir.name}: success is not true: {success}")

    corridor_radius = metadata.get("corridor_start_radius")
    pre_radius = metadata.get("pre_grasp_radius")
    if condition in CONDITION_RADII:
        expected_corridor, expected_pre = CONDITION_RADII[condition]
        if corridor_radius is not None and abs(float(corridor_radius) - expected_corridor) > tolerance:
            warnings.append(
                f"{demo_dir.name}: corridor_start_radius={corridor_radius}, table value={expected_corridor}"
            )
        if pre_radius is not None and abs(float(pre_radius) - expected_pre) > tolerance:
            warnings.append(
                f"{demo_dir.name}: pre_grasp_radius={pre_radius}, table value={expected_pre}"
            )

    for key, radius_key, fixed_index in (
        ("corridor_start_delta", "corridor_start_radius", 1),
        ("pre_grasp_delta", "pre_grasp_radius", 2),
    ):
        delta = metadata.get(key)
        radius = metadata.get(radius_key)
        if delta is None or radius is None:
            errors.append(f"{demo_dir.name}: missing {key} or {radius_key}")
            continue
        norm = vector_norm(delta)
        if norm > float(radius) + 1e-8:
            errors.append(
                f"{demo_dir.name}: ||{key}||={norm:.6f} exceeds {radius_key}={float(radius):.6f}"
            )
        if len(delta) > fixed_index and abs(float(delta[fixed_index])) > tolerance:
            errors.append(
                f"{demo_dir.name}: {key}[{fixed_index}]={delta[fixed_index]} should be fixed at 0"
            )

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
    corridor_start_y = float(metadata.get("corridor_start_y", 0.15))
    if base_corridor_start is None:
        errors.append(f"{demo_dir.name}: missing base_corridor_start")
    elif abs(float(base_corridor_start[1]) - corridor_start_y) > tolerance:
        errors.append(
            f"{demo_dir.name}: base_corridor_start y={base_corridor_start[1]} should be {corridor_start_y}"
        )

    counts = phase_counts(demo_dir)
    if not counts:
        errors.append(f"{demo_dir.name}: no frame phase files found")
    for required_phase in (
        "random_start",
        "open_gripper",
        "corridor_start",
        "pre_grasp",
        "pick_grasp",
        "close_gripper",
        "lift",
    ):
        if counts.get(required_phase, 0) == 0:
            errors.append(f"{demo_dir.name}: missing phase {required_phase!r}")

    summary = {
        "demo": demo_dir.name,
        "condition": condition,
        "frames": sum(counts.values()),
        "phase_counts": dict(counts),
        "random_start": random_start,
        "corridor_delta_norm": vector_norm(metadata.get("corridor_start_delta", [0, 0, 0])),
        "pre_grasp_delta_norm": vector_norm(metadata.get("pre_grasp_delta", [0, 0, 0])),
        "final_cube_z": success.get("final_cube_z"),
    }
    return summary, errors, warnings


def main():
    parser = argparse.ArgumentParser(description="Sanity-check an Ablation 1 raw dataset.")
    parser.add_argument("dataset_dir", help="Directory containing demo_<idx> folders.")
    parser.add_argument("--expected-demos", type=int, default=None)
    parser.add_argument("--expected-condition", choices=sorted(CONDITION_RADII), default=None)
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON summary.")
    args = parser.parse_args()

    root = Path(args.dataset_dir)
    demo_dirs = sorted(
        [p for p in root.glob("demo_*") if p.is_dir()],
        key=lambda p: int(p.name.split("_", 1)[1]) if p.name.split("_", 1)[1].isdigit() else p.name,
    )

    all_errors = []
    all_warnings = []
    summaries = []

    if not root.exists():
        all_errors.append(f"dataset directory does not exist: {root}")
    if args.expected_demos is not None and len(demo_dirs) != args.expected_demos:
        all_errors.append(
            f"found {len(demo_dirs)} demo dirs, expected {args.expected_demos}"
        )

    for demo_dir in demo_dirs:
        summary, errors, warnings = check_demo(
            demo_dir,
            expected_condition=args.expected_condition,
        )
        if summary is not None:
            summaries.append(summary)
        all_errors.extend(errors)
        all_warnings.extend(warnings)

    frame_counts = [s["frames"] for s in summaries]
    conditions = Counter(s["condition"] for s in summaries)
    report = {
        "dataset_dir": str(root),
        "num_demos": len(demo_dirs),
        "conditions": dict(conditions),
        "frame_count_min": min(frame_counts) if frame_counts else 0,
        "frame_count_max": max(frame_counts) if frame_counts else 0,
        "frame_count_mean": sum(frame_counts) / len(frame_counts) if frame_counts else 0.0,
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
        if all_warnings:
            print("\nWarnings:")
            for warning in all_warnings:
                print(f"  - {warning}")
        if all_errors:
            print("\nErrors:")
            for error in all_errors:
                print(f"  - {error}")
        else:
            print("\nOK: dataset passed Ablation 1 sanity checks.")

    return 1 if all_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
