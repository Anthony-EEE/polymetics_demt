#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np


DEFAULT_DATASET_ROOT = Path(
    "/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/orn_mvp_full"
)
CONDITIONS = ("R00", "R15", "R30")


def index_from_name(path):
    try:
        return int(path.name.split("_", 1)[1])
    except (IndexError, ValueError):
        return path.name


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def normalize_quat_xyzw(quat):
    quat = np.asarray(quat, dtype=float)
    norm = float(np.linalg.norm(quat))
    if norm <= 1e-12:
        raise ValueError(f"Invalid zero-norm quaternion: {quat}")
    return quat / norm


def quat_angle_degrees(a, b):
    a = normalize_quat_xyzw(a)
    b = normalize_quat_xyzw(b)
    # q and -q represent the same rotation, so use abs(dot).
    dot = float(np.clip(abs(np.dot(a, b)), -1.0, 1.0))
    return float(np.degrees(2.0 * np.arccos(dot)))


def load_demo(demo_dir, stride):
    metadata_path = demo_dir / "metadata.json"
    metadata = load_json(metadata_path) if metadata_path.exists() else {}
    default_quat = metadata.get("default_quat_xyzw")
    target_quat = metadata.get("contact_quat_xyzw")

    rows = []
    frame_dirs = sorted(demo_dir.glob("frame_*"), key=index_from_name)[::stride]
    for frame_dir in frame_dirs:
        pose_path = frame_dir / "ee_pose.txt"
        if not pose_path.exists():
            continue
        pose = np.loadtxt(pose_path, delimiter=",")
        pose = np.asarray(pose, dtype=float).reshape(-1)
        if pose.shape[0] < 7:
            raise ValueError(f"{pose_path} has {pose.shape[0]} values, expected at least 7")

        time_path = frame_dir / "time.txt"
        if time_path.exists():
            time_value = float(np.asarray(np.loadtxt(time_path, delimiter=",")).reshape(-1)[0])
        else:
            time_value = float(index_from_name(frame_dir))

        phase_path = frame_dir / "phase.txt"
        phase = phase_path.read_text(encoding="utf-8").strip() if phase_path.exists() else ""

        quat = normalize_quat_xyzw(pose[3:7])
        rows.append(
            {
                "time": time_value,
                "xyz": pose[:3],
                "quat": quat,
                "angle_from_default": quat_angle_degrees(quat, default_quat)
                if default_quat is not None
                else np.nan,
                "angle_error_to_target": quat_angle_degrees(quat, target_quat)
                if target_quat is not None
                else np.nan,
                "phase": phase,
            }
        )

    if not rows:
        raise ValueError(f"No usable ee_pose.txt frames found in {demo_dir}")

    return {
        "name": demo_dir.name,
        "metadata": metadata,
        "time": np.asarray([r["time"] for r in rows], dtype=float),
        "xyz": np.vstack([r["xyz"] for r in rows]),
        "quat": np.vstack([r["quat"] for r in rows]),
        "angle_from_default": np.asarray([r["angle_from_default"] for r in rows], dtype=float),
        "angle_error_to_target": np.asarray([r["angle_error_to_target"] for r in rows], dtype=float),
        "phase": [r["phase"] for r in rows],
    }


def load_condition(condition_dir, stride):
    demos = []
    for demo_dir in sorted(condition_dir.glob("demo_*"), key=index_from_name):
        if demo_dir.is_dir():
            demos.append(load_demo(demo_dir, stride))
    if not demos:
        raise ValueError(f"No demo_* directories found in {condition_dir}")
    return demos


def scatter_waypoints(ax, metadata):
    labels = [
        ("random_start", "tab:green", "random"),
        ("corridor_start", "tab:blue", "corridor"),
        ("pre_grasp", "tab:orange", "pre"),
        ("grasp", "tab:red", "grasp"),
        ("lift", "tab:purple", "lift"),
    ]
    for key, color, label in labels:
        if key not in metadata:
            continue
        point = np.asarray(metadata[key], dtype=float)
        ax.scatter(point[0], point[1], point[2], s=24, color=color, marker="o", label=label)


def plot_condition(condition, demos, output_path):
    all_xyz = np.vstack([demo["xyz"] for demo in demos])
    sampled_angles = np.asarray(
        [
            float(demo["metadata"].get("orientation_angle_degrees", np.nan))
            for demo in demos
        ],
        dtype=float,
    )
    max_degrees = demos[0]["metadata"].get("orientation_max_degrees", None)

    finite_abs_angles = np.abs(sampled_angles[np.isfinite(sampled_angles)])
    vmax = max(float(np.nanmax(finite_abs_angles)) if finite_abs_angles.size else 1.0, 1.0)
    cmap = plt.get_cmap("coolwarm")
    norm = plt.Normalize(vmin=-vmax, vmax=vmax)

    fig = plt.figure(figsize=(16, 9.2), constrained_layout=True)
    title = f"{condition} EE xyz + orientation"
    if max_degrees is not None:
        title += f" (sampled within +/-{float(max_degrees):g} deg)"
    fig.suptitle(title, fontsize=14)

    gs = fig.add_gridspec(2, 3)
    ax3d = fig.add_subplot(gs[0, 0], projection="3d")
    ax_xy = fig.add_subplot(gs[0, 1])
    ax_xz = fig.add_subplot(gs[0, 2])
    ax_default = fig.add_subplot(gs[1, 0])
    ax_target = fig.add_subplot(gs[1, 1])
    ax_hist = fig.add_subplot(gs[1, 2])

    for demo, sampled_angle in zip(demos, sampled_angles):
        color = cmap(norm(sampled_angle)) if np.isfinite(sampled_angle) else "0.5"
        xyz = demo["xyz"]
        time = demo["time"] - demo["time"][0]
        ax3d.plot(xyz[:, 0], xyz[:, 1], xyz[:, 2], linewidth=0.8, alpha=0.55, color=color)
        ax_xy.plot(xyz[:, 0], xyz[:, 1], linewidth=0.8, alpha=0.55, color=color)
        ax_xz.plot(xyz[:, 0], xyz[:, 2], linewidth=0.8, alpha=0.55, color=color)
        ax_default.plot(time, demo["angle_from_default"], linewidth=0.8, alpha=0.55, color=color)
        ax_target.plot(time, demo["angle_error_to_target"], linewidth=0.8, alpha=0.55, color=color)

        for ax, cols in ((ax_xy, (0, 1)), (ax_xz, (0, 2))):
            ax.scatter(xyz[0, cols[0]], xyz[0, cols[1]], s=10, color="tab:green", alpha=0.75)
            ax.scatter(xyz[-1, cols[0]], xyz[-1, cols[1]], s=10, color="tab:red", alpha=0.75)
        ax3d.scatter(xyz[0, 0], xyz[0, 1], xyz[0, 2], s=10, color="tab:green", alpha=0.75)
        ax3d.scatter(xyz[-1, 0], xyz[-1, 1], xyz[-1, 2], s=10, color="tab:red", alpha=0.75)

    scatter_waypoints(ax3d, demos[0]["metadata"])

    mins = all_xyz.min(axis=0)
    maxs = all_xyz.max(axis=0)
    centers = 0.5 * (mins + maxs)
    span = max(maxs - mins)
    if span <= 0:
        span = 0.1
    half = 0.55 * span

    ax3d.set_xlim(centers[0] - half, centers[0] + half)
    ax3d.set_ylim(centers[1] - half, centers[1] + half)
    ax3d.set_zlim(centers[2] - half, centers[2] + half)
    ax3d.set_xlabel("x [m]")
    ax3d.set_ylabel("y [m]")
    ax3d.set_zlabel("z [m]")
    ax3d.set_title("3D EE path")
    ax3d.legend(loc="best", fontsize=7)

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

    ax_default.set_xlabel("time [s]")
    ax_default.set_ylabel("angle [deg]")
    ax_default.set_title("EE orientation angle from default quat")
    ax_default.grid(True, alpha=0.25)

    ax_target.set_xlabel("time [s]")
    ax_target.set_ylabel("angle error [deg]")
    ax_target.set_title("EE orientation error to demo target quat")
    ax_target.grid(True, alpha=0.25)

    finite_angles = sampled_angles[np.isfinite(sampled_angles)]
    if finite_angles.size:
        bins = min(12, max(3, int(np.sqrt(finite_angles.size))))
        ax_hist.hist(finite_angles, bins=bins, color="0.35", alpha=0.8)
        ax_hist.axvline(0.0, color="black", linewidth=1.0, alpha=0.5)
        if max_degrees is not None:
            max_degrees = float(max_degrees)
            ax_hist.axvline(-max_degrees, color="tab:red", linestyle="--", linewidth=1.0, alpha=0.75)
            ax_hist.axvline(max_degrees, color="tab:red", linestyle="--", linewidth=1.0, alpha=0.75)
    ax_hist.set_xlabel("sampled metadata angle [deg]")
    ax_hist.set_ylabel("demo count")
    ax_hist.set_title("sampled orientation angles")
    ax_hist.grid(True, axis="y", alpha=0.25)

    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    fig.colorbar(sm, ax=[ax3d, ax_xy, ax_xz, ax_default, ax_target], shrink=0.72, label="sampled angle [deg]")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=220)
    plt.close(fig)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Plot orientation MVP EE xyz trajectories and quaternion-derived angle traces."
    )
    parser.add_argument("--dataset-root", type=Path, default=DEFAULT_DATASET_ROOT)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--conditions", nargs="+", default=list(CONDITIONS))
    parser.add_argument(
        "--dataset-template",
        default="orn_mvp_{condition}_d30_seed1",
        help="Condition directory name template under --dataset-root.",
    )
    parser.add_argument("--stride", type=int, default=3, help="Plot every Nth frame.")
    return parser.parse_args()


def main():
    args = parse_args()
    if args.stride <= 0:
        raise ValueError(f"--stride must be positive, got {args.stride}")

    output_dir = args.output_dir or (args.dataset_root / "orientation_plots")
    for condition in args.conditions:
        condition_dir = args.dataset_root / args.dataset_template.format(condition=condition)
        demos = load_condition(condition_dir, args.stride)
        output_path = output_dir / f"orn_mvp_{condition}_ee_xyz_orientation.png"
        plot_condition(condition, demos, output_path)
        print(f"{condition}: saved {output_path} ({len(demos)} demos)", flush=True)


if __name__ == "__main__":
    main()
