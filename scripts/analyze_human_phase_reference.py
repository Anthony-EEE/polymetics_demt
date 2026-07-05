#!/usr/bin/env python3
"""Build an after-training human temporal reference from detected demo events.

The raw P6/P7 human demos do not have manual phase labels. This script uses the
event columns exported by scripts/analyze_week2_human_data.py and turns them
into a conservative event-based phase reference:

  start -> nearest-to-corridor-plane -> pregrasp keypoint -> first close -> end

The output is intended to define a data-derived v_ref timing scaffold before
any new temporal collection is run.
"""

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

import numpy as np


DEFAULT_DEMO_METRICS = Path("outputs/week2_human_phase_reference_p6p7_stride1/demo_metrics.csv")
DEFAULT_OUTPUT_DIR = Path("outputs/week2_human_phase_reference_p6p7_stride1")
DEFAULT_GROUPS = ("P6_target_post_skill1", "P7_target_post_skill2")
PHASES = (
    "start_to_corridor",
    "corridor_to_pregrasp",
    "pregrasp_to_first_close",
    "first_close_to_end",
)
PERCENTILES = (0, 25, 50, 75, 90, 95, 100)


def finite_float(value):
    value = float(value)
    return value if np.isfinite(value) else None


def parse_float(value, default=np.nan):
    if value is None or value == "":
        return default
    try:
        value = float(value)
    except ValueError:
        return default
    return value if np.isfinite(value) else default


def parse_int(value, default=None):
    value = parse_float(value, np.nan)
    if not np.isfinite(value):
        return default
    return int(round(float(value)))


def summarize(values):
    arr = np.asarray([float(x) for x in values if np.isfinite(float(x))], dtype=float)
    if arr.size == 0:
        result = {f"p{p}": None for p in PERCENTILES}
        result.update({"mean": None, "std": None, "n": 0})
        return result
    result = {f"p{p}": finite_float(np.percentile(arr, p)) for p in PERCENTILES}
    result["mean"] = finite_float(np.mean(arr))
    result["std"] = finite_float(np.std(arr))
    result["n"] = int(arr.size)
    return result


def clamp_event(value, low, high):
    if value is None:
        return None
    return int(min(max(int(value), int(low)), int(high)))


def build_demo_reference(row, sample_hz):
    frame_count = parse_int(row.get("frame_count"), default=None)
    if frame_count is None or frame_count < 2:
        return None, "missing_or_too_short_frame_count"

    end = frame_count - 1
    corridor = clamp_event(parse_int(row.get("corridor_crossing_frame")), 0, end)
    pregrasp = clamp_event(parse_int(row.get("pregrasp_keypoint_frame")), 0, end)
    first_close = clamp_event(parse_int(row.get("first_close_frame")), 0, end)

    if corridor is None:
        return None, "missing_corridor_crossing_frame"
    if pregrasp is None:
        return None, "missing_pregrasp_keypoint_frame"
    if first_close is None:
        return None, "missing_first_close_frame"

    raw_events = {
        "start": 0,
        "corridor": corridor,
        "pregrasp": pregrasp,
        "first_close": first_close,
        "end": end,
    }

    repaired = []
    corridor_m = corridor
    pregrasp_m = pregrasp
    first_close_m = first_close
    if corridor_m < 0:
        corridor_m = 0
        repaired.append("corridor<start")
    if pregrasp_m < corridor_m:
        pregrasp_m = corridor_m
        repaired.append("pregrasp<corridor")
    if first_close_m < pregrasp_m:
        first_close_m = pregrasp_m
        repaired.append("first_close<pregrasp")
    if end < first_close_m:
        first_close_m = end
        repaired.append("first_close>end")

    events = {
        "start": 0,
        "corridor": corridor_m,
        "pregrasp": pregrasp_m,
        "first_close": first_close_m,
        "end": end,
    }
    phase_frames = {
        "start_to_corridor": events["corridor"] - events["start"],
        "corridor_to_pregrasp": events["pregrasp"] - events["corridor"],
        "pregrasp_to_first_close": events["first_close"] - events["pregrasp"],
        "first_close_to_end": events["end"] - events["first_close"],
    }
    total_phase_frames = sum(phase_frames.values())
    if total_phase_frames <= 0:
        return None, "non_positive_total_phase_frames"

    out = {
        "group": row.get("group", ""),
        "demo": row.get("demo", ""),
        "person": row.get("person", ""),
        "source_demo": row.get("source_demo", ""),
        "frame_count": frame_count,
        "sample_hz": float(sample_hz),
        "duration_s": total_phase_frames / float(sample_hz),
        "raw_start_frame": raw_events["start"],
        "raw_corridor_frame": raw_events["corridor"],
        "raw_pregrasp_frame": raw_events["pregrasp"],
        "raw_first_close_frame": raw_events["first_close"],
        "raw_end_frame": raw_events["end"],
        "start_frame": events["start"],
        "corridor_frame": events["corridor"],
        "pregrasp_frame": events["pregrasp"],
        "first_close_frame": events["first_close"],
        "end_frame": events["end"],
        "repaired_event_order": bool(repaired),
        "repair_notes": ";".join(repaired),
        "closest_grasp_norm_time": parse_float(row.get("closest_grasp_norm_time")),
        "closest_grasp_frame_estimate": parse_float(row.get("closest_grasp_norm_time")) * end,
    }
    for phase, count in phase_frames.items():
        out[f"{phase}_frames"] = int(count)
        out[f"{phase}_proportion"] = float(count) / float(total_phase_frames)
        out[f"{phase}_duration_s"] = float(count) / float(sample_hz)
    for event, frame in events.items():
        out[f"{event}_norm_time"] = float(frame) / float(end) if end > 0 else 0.0
    return out, ""


def write_csv(path, rows):
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            clean = {}
            for key, value in row.items():
                if isinstance(value, float) and not np.isfinite(value):
                    clean[key] = ""
                else:
                    clean[key] = value
            writer.writerow(clean)


def build_summary(rows, sample_hz, source_demo_metrics):
    groups = defaultdict(list)
    for row in rows:
        groups[row["group"]].append(row)
    groups["P6P7_post_pooled"] = list(rows)
    groups["P6P7_post_valid_order"] = [
        row for row in rows if not row["repaired_event_order"]
    ]
    for group in sorted({row["group"] for row in rows}):
        groups[f"{group}_valid_order"] = [
            row for row in rows
            if row["group"] == group and not row["repaired_event_order"]
        ]

    summary_rows = []
    reference = {
        "method": "event-based after-training P6/P7 phase reference",
        "source_demo_metrics": str(source_demo_metrics),
        "sample_hz": float(sample_hz),
        "phase_order": list(PHASES),
        "phase_boundary_events": [
            "start",
            "nearest_to_corridor_plane",
            "pregrasp_keypoint",
            "first_close",
            "end",
        ],
        "groups": {},
    }

    for group, group_rows in groups.items():
        if not group_rows:
            continue
        group_ref = {
            "n": len(group_rows),
            "mean_total_duration_s": summarize([r["duration_s"] for r in group_rows])["mean"],
            "mean_total_frames_excluding_last_index": summarize(
                [r["end_frame"] - r["start_frame"] for r in group_rows]
            )["mean"],
            "repaired_event_order_count": int(sum(bool(r["repaired_event_order"]) for r in group_rows)),
            "phase_mean_frames": {},
            "phase_mean_proportions": {},
            "phase_mean_durations_s": {},
            "event_mean_norm_times": {},
        }
        for event in ("corridor", "pregrasp", "first_close", "end"):
            group_ref["event_mean_norm_times"][event] = summarize(
                [r[f"{event}_norm_time"] for r in group_rows]
            )["mean"]
        for phase in PHASES:
            for suffix, label in (
                ("frames", "frames"),
                ("proportion", "proportion"),
                ("duration_s", "duration_s"),
            ):
                stats = summarize([r[f"{phase}_{suffix}"] for r in group_rows])
                for stat, value in stats.items():
                    summary_rows.append(
                        {
                            "group": group,
                            "phase": phase,
                            "metric": label,
                            "stat": stat,
                            "value": "" if value is None else value,
                        }
                    )
                if suffix == "frames":
                    group_ref["phase_mean_frames"][phase] = stats["mean"]
                elif suffix == "proportion":
                    group_ref["phase_mean_proportions"][phase] = stats["mean"]
                elif suffix == "duration_s":
                    group_ref["phase_mean_durations_s"][phase] = stats["mean"]
        reference["groups"][group] = group_ref

    return summary_rows, reference


def parse_args():
    parser = argparse.ArgumentParser(
        description="Summarize P6/P7 after-training phase proportions for a temporal v_ref."
    )
    parser.add_argument("--demo-metrics", type=Path, default=DEFAULT_DEMO_METRICS)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--groups", nargs="+", default=list(DEFAULT_GROUPS))
    parser.add_argument("--sample-hz", type=float, default=30.0)
    return parser.parse_args()


def main():
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    with args.demo_metrics.open("r", encoding="utf-8", newline="") as f:
        source_rows = [r for r in csv.DictReader(f) if r.get("group") in set(args.groups)]

    rows = []
    errors = []
    for row in source_rows:
        item, error = build_demo_reference(row, args.sample_hz)
        if item is None:
            errors.append({"group": row.get("group", ""), "demo": row.get("demo", ""), "error": error})
        else:
            rows.append(item)

    summary_rows, reference = build_summary(rows, args.sample_hz, args.demo_metrics)
    reference["source_n"] = len(source_rows)
    reference["used_n"] = len(rows)
    reference["errors"] = errors
    reference["source_frame_stride_values"] = sorted(
        {
            parse_int(row.get("frame_stride"), default=-1)
            for row in source_rows
            if parse_int(row.get("frame_stride"), default=-1) is not None
        }
    )
    reference["notes"] = [
        "Human demos do not contain manual phase labels; phases are event-based.",
        "This reference inherits the event-detection frame stride from the input demo_metrics.csv.",
        "closest_grasp is exported only as a diagnostic because it often occurs after first_close in these post-training demos.",
        "Use P6P7_post_valid_order as the strict v_ref timing scaffold; P6P7_post_pooled includes repaired event-order rows for completeness.",
    ]

    write_csv(args.output_dir / "phase_reference_per_demo.csv", rows)
    write_csv(args.output_dir / "phase_reference_summary.csv", summary_rows)
    (args.output_dir / "v_ref_phase_reference.json").write_text(
        json.dumps(reference, indent=2),
        encoding="utf-8",
    )

    print(f"[INFO] source rows: {len(source_rows)}", flush=True)
    print(f"[INFO] usable rows: {len(rows)}", flush=True)
    print(f"[INFO] errors: {len(errors)}", flush=True)
    print(f"[INFO] wrote {args.output_dir / 'phase_reference_per_demo.csv'}", flush=True)
    print(f"[INFO] wrote {args.output_dir / 'phase_reference_summary.csv'}", flush=True)
    print(f"[INFO] wrote {args.output_dir / 'v_ref_phase_reference.json'}", flush=True)


if __name__ == "__main__":
    main()
