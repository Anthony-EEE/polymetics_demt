#!/usr/bin/env python3
import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np


DEFAULT_DATASET_ROOT = Path(
    "/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/ar_guidance_temporal_T00_T100"
)
CONDITIONS = ("T00", "T25", "T50", "T75", "T100")
LADDER_PHASE_ORDER = (
    "random_start",
    "open_gripper",
    "corridor_start",
    "pre_grasp",
    "pick_grasp",
    "close_gripper",
    "lift",
)
VREF_SAVED_PHASE_ORDER = (
    "random_start",
    "corridor_start",
    "pre_grasp",
    "pick_grasp",
    "close_gripper",
    "lift",
)
VREF_PHASE_ORDER = (
    "start_to_corridor",
    "corridor_to_pregrasp",
    "pregrasp_to_first_close",
    "first_close_to_end",
)
TIMED_PHASES = tuple(p for p in LADDER_PHASE_ORDER if p != "random_start")
PHASE_COLORS = {
    "random_start": "#7f7f7f",
    "open_gripper": "#4c78a8",
    "corridor_start": "#59a14f",
    "pre_grasp": "#f28e2b",
    "pick_grasp": "#e15759",
    "close_gripper": "#b07aa1",
    "lift": "#edc948",
    "start_to_corridor": "#59a14f",
    "corridor_to_pregrasp": "#f28e2b",
    "pregrasp_to_first_close": "#e15759",
    "first_close_to_end": "#edc948",
}


def index_from_name(path):
    try:
        return int(path.name.split("_", 1)[1])
    except (IndexError, ValueError):
        return path.name


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def read_scalar(path, default):
    if not path.exists():
        return default
    return float(np.asarray(np.loadtxt(path)).reshape(-1)[0])


def load_demo(demo_dir, stride=1):
    metadata = load_json(demo_dir / "metadata.json")
    rows = []
    frame_dirs = sorted(demo_dir.glob("frame_*"), key=index_from_name)[::stride]
    for frame_dir in frame_dirs:
        pose_path = frame_dir / "ee_pose.txt"
        if not pose_path.exists():
            continue
        pose = np.asarray(np.loadtxt(pose_path), dtype=float).reshape(-1)
        if pose.shape[0] < 3:
            raise ValueError(f"{pose_path} has {pose.shape[0]} values, expected at least xyz")
        phase_path = frame_dir / "phase.txt"
        phase = phase_path.read_text(encoding="utf-8").strip() if phase_path.exists() else ""
        rows.append(
            {
                "frame": index_from_name(frame_dir),
                "time": read_scalar(frame_dir / "time.txt", float(index_from_name(frame_dir))),
                "xyz": pose[:3],
                "phase": phase,
            }
        )
    if not rows:
        raise ValueError(f"No usable frames found in {demo_dir}")
    time = np.asarray([r["time"] for r in rows], dtype=float)
    time = time - time[0]
    return {
        "name": demo_dir.name,
        "metadata": metadata,
        "time": time,
        "xyz": np.vstack([r["xyz"] for r in rows]),
        "phase": [r["phase"] for r in rows],
        "frame": np.asarray([r["frame"] for r in rows], dtype=int),
    }


def load_condition(condition_dir, stride=1):
    demos = []
    for demo_dir in sorted(condition_dir.glob("demo_*"), key=index_from_name):
        if demo_dir.is_dir():
            demos.append(load_demo(demo_dir, stride=stride))
    if not demos:
        raise ValueError(f"No demo_* directories found in {condition_dir}")
    return demos


def phase_counts(demo):
    return Counter(demo["phase"])


def is_vref_demo(demo):
    return demo["metadata"].get("time_condition_family") == "v_ref_p6p7_event_phases"


def saved_phase_order(demos):
    base_order = VREF_SAVED_PHASE_ORDER if demos and is_vref_demo(demos[0]) else LADDER_PHASE_ORDER
    observed = []
    seen = set()
    for phase in base_order:
        observed.append(phase)
        seen.add(phase)
    for demo in demos:
        for phase in demo["phase"]:
            if phase and phase not in seen:
                observed.append(phase)
                seen.add(phase)
    return tuple(observed)


def timed_phase_order(demos):
    if demos and is_vref_demo(demos[0]):
        return tuple(demos[0]["metadata"].get("v_ref_phase_order", VREF_PHASE_ORDER))
    return tuple(p for p in saved_phase_order(demos) if p != "random_start")


def multiplier_map(metadata):
    return metadata.get("sampled_phase_multipliers") or metadata.get("phase_duration_multipliers", {})


def phase_duration_data(demos):
    phases = timed_phase_order(demos)
    if demos and is_vref_demo(demos[0]):
        rows = []
        refs = demos[0]["metadata"].get("v_ref_phase_durations_s", {})
        for demo in demos:
            target = demo["metadata"].get("target_phase_durations_s", {})
            rows.append([float(target[p]) for p in phases])
        return phases, [list(col) for col in zip(*rows)], refs, "target v_ref phase duration [s]"

    by_phase = defaultdict(list)
    for demo in demos:
        counts = phase_counts(demo)
        sample_period = float(demo["metadata"].get("sample_period", 1.0))
        for phase in phases:
            by_phase[phase].append(float(counts.get(phase, 0)) * sample_period)
    return phases, [by_phase[p] for p in phases], {}, "observed phase duration [s]"


def phase_segments(demo):
    phases = demo["phase"]
    time = demo["time"]
    if not phases:
        return []
    segments = []
    start = 0
    current = phases[0]
    for i, phase in enumerate(phases[1:], start=1):
        if phase != current:
            segments.append((current, time[start], time[i - 1]))
            start = i
            current = phase
    segments.append((current, time[start], time[-1]))
    return segments


def plot_condition(condition, demos, output_path):
    fig = plt.figure(figsize=(17, 12), constrained_layout=True)
    fig.suptitle(f"{condition} temporal MVP: EE position and phase timing", fontsize=14)
    gs = fig.add_gridspec(3, 3)

    ax_x = fig.add_subplot(gs[0, 0])
    ax_y = fig.add_subplot(gs[0, 1])
    ax_z = fig.add_subplot(gs[0, 2])
    ax_phase = fig.add_subplot(gs[1, 0])
    ax_mult = fig.add_subplot(gs[1, 1])
    ax_total = fig.add_subplot(gs[1, 2])
    ax3d = fig.add_subplot(gs[2, 0], projection="3d")
    ax_xy = fig.add_subplot(gs[2, 1])
    ax_xz = fig.add_subplot(gs[2, 2])

    coord_axes = ((ax_x, 0, "x [m]"), (ax_y, 1, "y [m]"), (ax_z, 2, "z [m]"))
    all_xyz = []
    total_frames = []
    multipliers_by_phase = defaultdict(list)
    total_seconds = []

    for demo_idx, demo in enumerate(demos):
        color = plt.cm.viridis(demo_idx / max(1, len(demos) - 1))
        time = demo["time"]
        xyz = demo["xyz"]
        all_xyz.append(xyz)
        total_frames.append(len(time))
        total_seconds.append(float(time[-1]) if len(time) else 0.0)
        for phase, value in multiplier_map(demo["metadata"]).items():
            multipliers_by_phase[phase].append(float(value))

        for ax, col, ylabel in coord_axes:
            ax.plot(time, xyz[:, col], linewidth=0.9, alpha=0.5, color=color)

        ax3d.plot(xyz[:, 0], xyz[:, 1], xyz[:, 2], linewidth=0.8, alpha=0.45, color=color)
        ax_xy.plot(xyz[:, 0], xyz[:, 1], linewidth=0.8, alpha=0.45, color=color)
        ax_xz.plot(xyz[:, 0], xyz[:, 2], linewidth=0.8, alpha=0.45, color=color)

    representative = demos[0]
    for ax, _, _ in coord_axes:
        for phase, t0, t1 in phase_segments(representative):
            ax.axvspan(t0, t1, color=PHASE_COLORS.get(phase, "0.8"), alpha=0.08)

    for ax, _, ylabel in coord_axes:
        ax.set_xlabel("time [s]")
        ax.set_ylabel(ylabel)
        ax.grid(True, alpha=0.25)
    ax_x.set_title("EE x vs time")
    ax_y.set_title("EE y vs time")
    ax_z.set_title("EE z vs time")

    duration_phases, data, reference_durations, duration_ylabel = phase_duration_data(demos)
    positions = np.arange(len(duration_phases))
    box = ax_phase.boxplot(data, positions=positions, patch_artist=True, showfliers=True)
    for patch, phase in zip(box["boxes"], duration_phases):
        patch.set_facecolor(PHASE_COLORS.get(phase, "0.8"))
        patch.set_alpha(0.55)
    for pos, phase in zip(positions, duration_phases):
        if phase in reference_durations:
            ax_phase.plot(
                [pos - 0.32, pos + 0.32],
                [float(reference_durations[phase]), float(reference_durations[phase])],
                color="black",
                linewidth=1.4,
                alpha=0.75,
            )
    ax_phase.set_xticks(positions)
    ax_phase.set_xticklabels(duration_phases, rotation=35, ha="right")
    ax_phase.set_ylabel(duration_ylabel)
    ax_phase.set_title("phase duration distribution")
    ax_phase.grid(True, axis="y", alpha=0.25)

    multiplier_phases = tuple(multipliers_by_phase.keys()) or timed_phase_order(demos)
    mult_data = [multipliers_by_phase[p] for p in multiplier_phases]
    mult_pos = np.arange(len(multiplier_phases))
    box = ax_mult.boxplot(mult_data, positions=mult_pos, patch_artist=True, showfliers=True)
    for patch, phase in zip(box["boxes"], multiplier_phases):
        patch.set_facecolor(PHASE_COLORS.get(phase, "0.8"))
        patch.set_alpha(0.55)
    ax_mult.axhline(1.0, color="black", linewidth=1.0, alpha=0.45)
    ax_mult.set_xticks(mult_pos)
    ax_mult.set_xticklabels(multiplier_phases, rotation=35, ha="right")
    ax_mult.set_ylabel("duration multiplier")
    ax_mult.set_title("metadata duration multipliers")
    ax_mult.grid(True, axis="y", alpha=0.25)

    ax_total.hist(total_seconds, bins=min(12, max(3, int(np.sqrt(len(total_seconds))))), color="0.35", alpha=0.85)
    if demos and is_vref_demo(demos[0]):
        v_ref_total = sum(float(v) for v in demos[0]["metadata"].get("v_ref_phase_durations_s", {}).values())
        ax_total.axvline(v_ref_total, color="black", linewidth=1.4, alpha=0.75, label="v_ref mean total")
        ax_total.legend()
    ax_total.set_xlabel("total duration [s]")
    ax_total.set_ylabel("demo count")
    ax_total.set_title(
        f"total duration: min={min(total_seconds):.2f}, mean={np.mean(total_seconds):.2f}, max={max(total_seconds):.2f} s"
    )
    ax_total.grid(True, axis="y", alpha=0.25)

    all_xyz = np.vstack(all_xyz)
    mins = all_xyz.min(axis=0)
    maxs = all_xyz.max(axis=0)
    centers = 0.5 * (mins + maxs)
    span = max(maxs - mins)
    half = max(0.05, 0.55 * span)
    ax3d.set_xlim(centers[0] - half, centers[0] + half)
    ax3d.set_ylim(centers[1] - half, centers[1] + half)
    ax3d.set_zlim(centers[2] - half, centers[2] + half)
    ax3d.set_xlabel("x [m]")
    ax3d.set_ylabel("y [m]")
    ax3d.set_zlabel("z [m]")
    ax3d.set_title("3D EE path")

    ax_xy.set_xlabel("x [m]")
    ax_xy.set_ylabel("y [m]")
    ax_xy.set_title("top view x-y")
    ax_xy.axis("equal")
    ax_xy.grid(True, alpha=0.25)

    ax_xz.set_xlabel("x [m]")
    ax_xz.set_ylabel("z [m]")
    ax_xz.set_title("side view x-z")
    ax_xz.axis("equal")
    ax_xz.grid(True, alpha=0.25)

    handles = [
        plt.Line2D([0], [0], color=PHASE_COLORS[p], linewidth=6, alpha=0.45, label=p)
        for p in saved_phase_order(demos)
    ]
    fig.legend(handles=handles, loc="outside lower center", ncol=max(1, len(handles)), fontsize=8)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=220)
    plt.close(fig)


def plot_summary(condition_to_demos, output_path):
    fig, axes = plt.subplots(1, 3, figsize=(16, 5), constrained_layout=True)
    fig.suptitle("Temporal MVP summary across conditions", fontsize=14)

    total_data = []
    phase_mean_rows = []
    labels = []
    for condition, demos in condition_to_demos.items():
        labels.append(condition)
        totals = [float(d["time"][-1]) if len(d["time"]) else 0.0 for d in demos]
        total_data.append(totals)
        phases, durations, _, _ = phase_duration_data(demos)
        phase_mean_rows.append([float(np.mean(values)) for values in durations])

    axes[0].boxplot(total_data, labels=labels, patch_artist=True, showfliers=True)
    axes[0].set_ylabel("total duration [s]")
    axes[0].set_title("total sequence duration")
    axes[0].grid(True, axis="y", alpha=0.25)

    summary_phases = timed_phase_order(next(iter(condition_to_demos.values())))
    x = np.arange(len(summary_phases))
    width = 0.24
    offsets = np.linspace(-width, width, len(labels))
    for offset, label, row in zip(offsets, labels, phase_mean_rows):
        axes[1].bar(x + offset, row, width=width, label=label, alpha=0.85)
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(summary_phases, rotation=35, ha="right")
    axes[1].set_ylabel("mean duration [s]")
    axes[1].set_title("mean phase durations")
    axes[1].legend()
    axes[1].grid(True, axis="y", alpha=0.25)

    for condition, demos in condition_to_demos.items():
        for demo in demos:
            xyz = demo["xyz"]
            time = demo["time"]
            dist = np.linalg.norm(np.diff(xyz, axis=0), axis=1)
            progress = np.concatenate([[0.0], np.cumsum(dist)])
            if progress[-1] > 1e-12:
                progress = progress / progress[-1]
            denom = time[-1] if time[-1] > 1e-12 else 1.0
            axes[2].plot(time / denom, progress, linewidth=0.8, alpha=0.35, label=condition)
    axes[2].set_xlabel("normalized time")
    axes[2].set_ylabel("normalized EE path progress")
    axes[2].set_title("path progress vs normalized time")
    axes[2].grid(True, alpha=0.25)
    handles = [
        plt.Line2D([0], [0], color=axes[2].lines[next(i for i, line in enumerate(axes[2].lines) if line.get_label() == label)].get_color(), label=label)
        for label in labels
    ]
    axes[2].legend(handles=handles)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=220)
    plt.close(fig)


def parse_args():
    parser = argparse.ArgumentParser(description="Plot temporal MVP EE position and phase timing.")
    parser.add_argument("--dataset-root", type=Path, default=DEFAULT_DATASET_ROOT)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--conditions", nargs="+", default=list(CONDITIONS))
    parser.add_argument("--dataset-template", default="temporal_{condition}_d30_seed1")
    parser.add_argument("--stride", type=int, default=1)
    return parser.parse_args()


def main():
    args = parse_args()
    if args.stride <= 0:
        raise ValueError(f"--stride must be positive, got {args.stride}")
    output_dir = args.output_dir or (args.dataset_root / "temporal_plots")

    condition_to_demos = {}
    for condition in args.conditions:
        condition_dir = args.dataset_root / args.dataset_template.format(condition=condition)
        demos = load_condition(condition_dir, stride=args.stride)
        condition_to_demos[condition] = demos
        output_path = output_dir / f"temporal_{condition}_temporal_xyz_phase.png"
        plot_condition(condition, demos, output_path)
        print(f"{condition}: saved {output_path} ({len(demos)} demos)", flush=True)

    summary_path = output_dir / f"temporal_{args.conditions[0]}_{args.conditions[-1]}_summary.png"
    plot_summary(condition_to_demos, summary_path)
    print(f"summary: saved {summary_path}", flush=True)


if __name__ == "__main__":
    main()
