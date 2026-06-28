#!/usr/bin/env python3
import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import numpy as np
import matplotlib.pyplot as plt


DEFAULT_DATASET_ROOT = Path(
    "/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full"
)
CONDITIONS = ("P00", "P10", "P01", "P11")


def frame_index(frame_dir):
    return int(frame_dir.name.split("_", 1)[1])


def load_demo_xyz(demo_dir, stride):
    points = []
    frame_dirs = sorted(demo_dir.glob("frame_*"), key=frame_index)[::stride]
    for frame_dir in frame_dirs:
        pose_path = frame_dir / "ee_pose.txt"
        if not pose_path.exists():
            continue
        pose = np.loadtxt(pose_path, delimiter=",")
        points.append(np.asarray(pose[:3], dtype=float))
    if not points:
        raise ValueError(f"No ee_pose.txt frames found in {demo_dir}")
    return np.vstack(points)


def load_condition_trajectories(condition_dir, stride):
    trajectories = []
    demo_dirs = sorted(condition_dir.glob("demo_*"), key=frame_index)
    for demo_dir in demo_dirs:
        trajectories.append((demo_dir.name, load_demo_xyz(demo_dir, stride)))
    if not trajectories:
        raise ValueError(f"No demos found in {condition_dir}")
    return trajectories


def plot_condition(condition, trajectories, output_path):
    all_xyz = np.vstack([xyz for _, xyz in trajectories])

    fig = plt.figure(figsize=(14, 4.8), constrained_layout=True)
    fig.suptitle(f"{condition} EE xyz trajectories from ee_pose.txt", fontsize=14)

    ax3d = fig.add_subplot(1, 3, 1, projection="3d")
    ax_xy = fig.add_subplot(1, 3, 2)
    ax_xz = fig.add_subplot(1, 3, 3)

    for demo_name, xyz in trajectories:
        ax3d.plot(xyz[:, 0], xyz[:, 1], xyz[:, 2], linewidth=0.9, alpha=0.55)
        ax_xy.plot(xyz[:, 0], xyz[:, 1], linewidth=0.9, alpha=0.55)
        ax_xz.plot(xyz[:, 0], xyz[:, 2], linewidth=0.9, alpha=0.55)

        for ax, cols in ((ax_xy, (0, 1)), (ax_xz, (0, 2))):
            ax.scatter(xyz[0, cols[0]], xyz[0, cols[1]], s=12, color="tab:green", alpha=0.75)
            ax.scatter(xyz[-1, cols[0]], xyz[-1, cols[1]], s=12, color="tab:red", alpha=0.75)

        ax3d.scatter(xyz[0, 0], xyz[0, 1], xyz[0, 2], s=10, color="tab:green", alpha=0.75)
        ax3d.scatter(xyz[-1, 0], xyz[-1, 1], xyz[-1, 2], s=10, color="tab:red", alpha=0.75)

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
    ax3d.set_title("3D")

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

    for ax in (ax_xy, ax_xz):
        ax.scatter([], [], s=20, color="tab:green", label="start")
        ax.scatter([], [], s=20, color="tab:red", label="end")
        ax.legend(loc="best", fontsize=8)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=220)
    plt.close(fig)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Plot ablation-1 end-effector xyz trajectories from saved ee_pose.txt files."
    )
    parser.add_argument("--dataset-root", type=Path, default=DEFAULT_DATASET_ROOT)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--conditions", nargs="+", default=list(CONDITIONS))
    parser.add_argument(
        "--dataset-template",
        default="abla1_{condition}_d30_seed1",
        help="Condition directory name template under --dataset-root.",
    )
    parser.add_argument("--stride", type=int, default=3, help="Plot every Nth frame.")
    return parser.parse_args()


def main():
    args = parse_args()
    output_dir = args.output_dir or (args.dataset_root / "trajectory_plots")
    if args.stride <= 0:
        raise ValueError(f"--stride must be positive, got {args.stride}")

    for condition in args.conditions:
        condition_dir = args.dataset_root / args.dataset_template.format(condition=condition)
        trajectories = load_condition_trajectories(condition_dir, args.stride)
        output_path = output_dir / f"abla1_{condition}_ee_xyz_trajectories.png"
        plot_condition(condition, trajectories, output_path)
        print(f"{condition}: saved {output_path} ({len(trajectories)} demos)", flush=True)


if __name__ == "__main__":
    main()
