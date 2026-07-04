#!/usr/bin/env python3
"""Read-only diagnostics for Week 2 real-human PyBullet demonstrations."""

import argparse
import csv
import json
import math
import os
import re
from collections import defaultdict
from pathlib import Path

import numpy as np
import pybullet as pb
import pybullet_data


DEFAULT_DATA_ROOT = Path("/scratch/users/k23114984/pybullet_data")
DEFAULT_OUTPUT_DIR = Path("outputs/week2_human_diagnostics")

DEFAULT_GROUPS = (
    (
        "P1_target_pre_skill1",
        DEFAULT_DATA_ROOT / "target_pooled/pooled_symlinks/target_pre_skill1",
        "target",
        "pre",
        "skill1",
    ),
    (
        "P2_target_pre_skill2",
        DEFAULT_DATA_ROOT / "target_pooled/pooled_symlinks/target_pre_skill2",
        "target",
        "pre",
        "skill2",
    ),
    (
        "P6_target_post_skill1",
        DEFAULT_DATA_ROOT / "target_pooled/pooled_symlinks/target_post_skill1",
        "target",
        "post",
        "skill1",
    ),
    (
        "P7_target_post_skill2",
        DEFAULT_DATA_ROOT / "target_pooled/pooled_symlinks/target_post_skill2",
        "target",
        "post",
        "skill2",
    ),
    (
        "P8_target_ordered",
        DEFAULT_DATA_ROOT / "phase8/phase8_target/2026-05-03-12-09-56",
        "target",
        "p8",
        "ordered",
    ),
    (
        "P8_control_ordered",
        DEFAULT_DATA_ROOT / "phase8/phase8_control/2026-05-02-16-16-44",
        "control",
        "p8",
        "ordered",
    ),
)

TIME_GRID = np.linspace(0.0, 1.0, 101)
PROGRESS_THRESHOLDS = (0.10, 0.25, 0.50, 0.75, 0.90)
PERCENTILES = (0, 25, 50, 75, 90, 95, 100)
DEFAULT_QUAT = np.asarray(pb.getQuaternionFromEuler([-math.pi, 0.0, 0.0]), dtype=float)
COORD_INDEX = {"x": 0, "y": 1, "z": 2}
KEYPOINT_PLANES = {
    "corridor_crossing": ("x", "z"),
    "pregrasp_keypoint": ("x", "y"),
}
EVENT_QUAT_PREFIXES = (
    "pregrasp_keypoint",
    "closest_grasp",
    "first_close",
)


def numeric_suffix(path):
    match = re.search(r"(\d+)$", path.name)
    return int(match.group(1)) if match else path.name


def parse_xyz(text):
    values = [float(x) for x in text.split(",")]
    if len(values) != 3:
        raise argparse.ArgumentTypeError(f"Expected three comma-separated floats, got {text!r}")
    return np.asarray(values, dtype=float)


def finite_float(value):
    value = float(value)
    return value if np.isfinite(value) else None


def load_manifest_people(manifest_path):
    people = {}
    sources = {}
    if not manifest_path.exists():
        return people, sources
    with manifest_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            demo_id = row.get("pooled_demo_id") or Path(row.get("pooled_link", "")).name
            dataset = row.get("dataset", "")
            if not demo_id or not dataset:
                continue
            key = (dataset, demo_id)
            people[key] = row.get("person", "")
            sources[key] = row.get("src_demo") or row.get("source_path") or ""
    return people, sources


class PandaFk:
    def __init__(self):
        self.client = pb.connect(pb.DIRECT)
        pb.setAdditionalSearchPath(pybullet_data.getDataPath())
        self.panda = pb.loadURDF(
            "franka_panda/panda.urdf",
            basePosition=[0, 0, 0],
            useFixedBase=True,
            flags=pb.URDF_ENABLE_CACHED_GRAPHICS_SHAPES,
        )
        self.arm_joint_indices = list(range(7))
        self.ee_link_index = 11

    def close(self):
        if self.client is not None:
            pb.disconnect(self.client)
            self.client = None

    def pose(self, joint_positions):
        for joint_index, q in zip(self.arm_joint_indices, joint_positions):
            pb.resetJointState(self.panda, joint_index, float(q))
        pos, quat = pb.getLinkState(
            self.panda,
            self.ee_link_index,
            computeForwardKinematics=True,
        )[:2]
        return np.asarray(pos, dtype=float), np.asarray(quat, dtype=float)


def list_demo_dirs(root):
    if not root.exists():
        return []
    demos = []
    for child in root.iterdir():
        if child.is_dir() and any(child.glob("frame_*/arm_joints.txt")):
            demos.append(child)
    return sorted(demos, key=numeric_suffix)


def list_frame_dirs(demo_dir):
    frames = []
    for child in demo_dir.iterdir():
        if child.is_dir() and child.name.startswith("frame_"):
            if (child / "arm_joints.txt").exists() and (child / "hand_joints.txt").exists():
                frames.append(child)
    return sorted(frames, key=numeric_suffix)


def select_frames(frame_dirs, frame_stride):
    if frame_stride <= 1:
        return frame_dirs, list(range(len(frame_dirs)))
    selected = frame_dirs[::frame_stride]
    indices = list(range(0, len(frame_dirs), frame_stride))
    if frame_dirs and selected[-1] != frame_dirs[-1]:
        selected.append(frame_dirs[-1])
        indices.append(len(frame_dirs) - 1)
    return selected, indices


def load_demo_trajectory(demo_dir, fk, frame_stride):
    positions = []
    quats = []
    hands = []
    frame_ids = []
    all_frame_dirs = list_frame_dirs(demo_dir)
    selected_frame_dirs, sample_indices = select_frames(all_frame_dirs, frame_stride)
    for frame_dir in selected_frame_dirs:
        arm = np.loadtxt(frame_dir / "arm_joints.txt", delimiter=",", dtype=float).reshape(-1)
        hand = np.loadtxt(frame_dir / "hand_joints.txt", delimiter=",", dtype=float).reshape(-1)
        if arm.size < 7:
            raise ValueError(f"{frame_dir}: expected at least 7 arm joints, got {arm.size}")
        pos, quat = fk.pose(arm[:7])
        positions.append(pos)
        quats.append(quat)
        hands.append(float(hand[0]) if hand.size else np.nan)
        frame_ids.append(numeric_suffix(frame_dir))
    if not positions:
        raise ValueError(f"{demo_dir}: no readable frames")
    return {
        "positions": np.vstack(positions),
        "quats": np.vstack(quats),
        "hands": np.asarray(hands, dtype=float),
        "frame_ids": np.asarray(frame_ids, dtype=int),
        "sample_indices": np.asarray(sample_indices, dtype=int),
        "raw_frame_count": len(all_frame_dirs),
        "frame_stride": int(frame_stride),
    }


def cumulative_progress(positions):
    if len(positions) < 2:
        return np.zeros(len(positions), dtype=float), 0.0
    steps = np.linalg.norm(np.diff(positions, axis=0), axis=1)
    arc = np.r_[0.0, np.cumsum(steps)]
    total = float(arc[-1])
    if total <= 1e-12:
        return np.zeros(len(positions), dtype=float), total
    return arc / total, total


def interpolate_rows(x, y, x_new):
    if len(x) == 1:
        return np.repeat(y, len(x_new), axis=0)
    cols = [np.interp(x_new, x, y[:, i]) for i in range(y.shape[1])]
    return np.stack(cols, axis=1)


def time_at_progress(progress, norm_time, threshold):
    if progress[-1] <= 1e-12:
        return np.nan
    progress = np.maximum.accumulate(progress)
    uniq, idx = np.unique(progress, return_index=True)
    if len(uniq) < 2:
        return np.nan
    return float(np.interp(threshold, uniq, norm_time[idx]))


def quaternion_angle_degrees(quats, reference_quat):
    q = np.asarray(quats, dtype=float)
    q_norm = np.linalg.norm(q, axis=1, keepdims=True)
    q_norm[q_norm <= 1e-12] = 1.0
    q = q / q_norm
    ref = np.asarray(reference_quat, dtype=float)
    ref = ref / max(np.linalg.norm(ref), 1e-12)
    dots = np.clip(np.abs(q @ ref), 0.0, 1.0)
    return np.degrees(2.0 * np.arccos(dots))


def normalize_quat(quat):
    q = np.asarray(quat, dtype=float)
    norm = np.linalg.norm(q)
    if norm <= 1e-12:
        return np.full(4, np.nan)
    return q / norm


def average_quaternion(quats):
    clean = []
    for quat in quats:
        q = normalize_quat(quat)
        if np.all(np.isfinite(q)):
            clean.append(q)
    if not clean:
        return np.full(4, np.nan)
    arr = np.vstack(clean)
    # Markley's eigenvector average handles antipodal quaternion signs.
    accum = arr.T @ arr
    eigvals, eigvecs = np.linalg.eigh(accum)
    mean = eigvecs[:, int(np.argmax(eigvals))]
    if mean[3] < 0:
        mean = -mean
    return normalize_quat(mean)


def quaternion_distances_to_mean_degrees(quats):
    mean = average_quaternion(quats)
    if not np.all(np.isfinite(mean)):
        return mean, np.asarray([], dtype=float)
    angles = quaternion_angle_degrees(np.asarray(quats, dtype=float), mean)
    angles = angles[np.isfinite(angles)]
    return mean, angles


def first_index(mask):
    idx = np.flatnonzero(mask)
    return int(idx[0]) if idx.size else None


def future_index(frame_ids, start_index, target_frame):
    for j in range(start_index + 1, len(frame_ids)):
        if frame_ids[j] >= target_frame:
            return j
    return None


def detect_pregrasp_keypoint(
    positions,
    frame_ids,
    min_frame,
    lookahead_frames,
    drop_threshold,
    short_lookahead_frames,
    short_drop_threshold,
):
    frame_ids = np.asarray(frame_ids, dtype=int)
    z = positions[:, 2]
    candidates = []
    scored = []
    for i, frame_id in enumerate(frame_ids):
        if frame_id < min_frame:
            continue
        j = future_index(frame_ids, i, frame_id + lookahead_frames)
        if j is None:
            continue
        k = future_index(frame_ids, i, frame_id + short_lookahead_frames)
        long_drop = z[j] - z[i]
        short_drop = z[k] - z[i] if k is not None else long_drop
        scored.append((long_drop, i))
        if long_drop <= -drop_threshold and short_drop <= -short_drop_threshold:
            candidates.append(i)
    if candidates:
        return candidates[0], "first_sustained_z_drop"
    if scored:
        scored.sort(key=lambda item: item[0])
        return scored[0][1], "fallback_largest_future_z_drop"
    valid = np.flatnonzero(frame_ids >= min_frame)
    if valid.size:
        local = valid[np.argmin(z[valid])]
        return int(local), "fallback_min_z_after_min_frame"
    return int(np.argmin(z)), "fallback_global_min_z"


def analyze_demo(
    demo_dir,
    group_spec,
    fk,
    refs,
    sample_hz,
    frame_stride,
    mirror_y,
    pregrasp_min_frame,
    pregrasp_lookahead_frames,
    pregrasp_drop_threshold,
    pregrasp_short_lookahead_frames,
    pregrasp_short_drop_threshold,
    manifest_people,
    manifest_sources,
):
    traj = load_demo_trajectory(demo_dir, fk, frame_stride)
    pos = traj["positions"]
    if mirror_y:
        pos = pos.copy()
        pos[:, 1] *= -1.0
    quats = traj["quats"]
    hands = traj["hands"]
    n = len(pos)
    raw_n = int(traj["raw_frame_count"])
    if raw_n > 1:
        norm_time = traj["sample_indices"] / float(raw_n - 1)
    else:
        norm_time = np.zeros(n, dtype=float)
    progress, path_length = cumulative_progress(pos)

    close_idx = first_index(hands > 0.0)
    corridor_idx = int(np.argmin(np.abs(pos[:, 1])))
    pregrasp_idx, pregrasp_method = detect_pregrasp_keypoint(
        pos,
        traj["frame_ids"],
        pregrasp_min_frame,
        pregrasp_lookahead_frames,
        pregrasp_drop_threshold,
        pregrasp_short_lookahead_frames,
        pregrasp_short_drop_threshold,
    )
    closest_pre_idx = int(np.argmin(np.linalg.norm(pos - refs["pregrasp"], axis=1)))
    closest_grasp_idx = int(np.argmin(np.linalg.norm(pos - refs["grasp"], axis=1)))
    orient = quaternion_angle_degrees(quats, DEFAULT_QUAT)

    start_delta = pos[0] - refs["corridor"]
    first_close_pos = pos[close_idx] if close_idx is not None else np.full(3, np.nan)
    first_close_pre = np.linalg.norm(first_close_pos - refs["pregrasp"])
    first_close_grasp = np.linalg.norm(first_close_pos - refs["grasp"])

    dataset_key = group_spec["dataset_key"]
    person = manifest_people.get((dataset_key, demo_dir.name), "")
    source_demo = manifest_sources.get((dataset_key, demo_dir.name), "")

    metrics = {
        "group": group_spec["name"],
        "root": str(group_spec["root"]),
        "demo": demo_dir.name,
        "cohort": group_spec["cohort"],
        "phase": group_spec["phase"],
        "skill": group_spec["skill"],
        "person": person,
        "source_demo": source_demo,
        "frame_count": raw_n,
        "sampled_frame_count": n,
        "frame_stride": int(frame_stride),
        "mirror_y_applied": bool(mirror_y),
        "duration_s_assuming_sample_hz": (raw_n - 1) / sample_hz if sample_hz > 0 else np.nan,
        "path_length_m": path_length,
        "start_x": pos[0, 0],
        "start_y": pos[0, 1],
        "start_z": pos[0, 2],
        "end_x": pos[-1, 0],
        "end_y": pos[-1, 1],
        "end_z": pos[-1, 2],
        "max_z": float(np.max(pos[:, 2])),
        "corridor_crossing_frame": int(traj["frame_ids"][corridor_idx]),
        "corridor_crossing_norm_time": float(norm_time[corridor_idx]),
        "corridor_crossing_x": float(pos[corridor_idx, 0]),
        "corridor_crossing_y": float(pos[corridor_idx, 1]),
        "corridor_crossing_z": float(pos[corridor_idx, 2]),
        "pregrasp_keypoint_method": pregrasp_method,
        "pregrasp_keypoint_frame": int(traj["frame_ids"][pregrasp_idx]),
        "pregrasp_keypoint_norm_time": float(norm_time[pregrasp_idx]),
        "pregrasp_keypoint_x": float(pos[pregrasp_idx, 0]),
        "pregrasp_keypoint_y": float(pos[pregrasp_idx, 1]),
        "pregrasp_keypoint_z": float(pos[pregrasp_idx, 2]),
        "start_to_corridor_center_xz_m": float(np.linalg.norm(start_delta[[0, 2]])),
        "start_to_corridor_center_xyz_m": float(np.linalg.norm(start_delta)),
        "min_pregrasp_dist_m": float(np.min(np.linalg.norm(pos - refs["pregrasp"], axis=1))),
        "min_grasp_dist_m": float(np.min(np.linalg.norm(pos - refs["grasp"], axis=1))),
        "min_object_xy_dist_m": float(np.min(np.linalg.norm(pos[:, :2] - refs["grasp"][:2], axis=1))),
        "closest_pregrasp_norm_time": float(norm_time[closest_pre_idx]),
        "closest_grasp_norm_time": float(norm_time[closest_grasp_idx]),
        "closed_fraction": float(np.mean(hands > 0.0)),
        "first_close_frame": int(traj["frame_ids"][close_idx]) if close_idx is not None else "",
        "first_close_norm_time": float(norm_time[close_idx]) if close_idx is not None else np.nan,
        "first_close_x": float(first_close_pos[0]),
        "first_close_y": float(first_close_pos[1]),
        "first_close_z": float(first_close_pos[2]),
        "first_close_to_pregrasp_m": float(first_close_pre),
        "first_close_to_grasp_m": float(first_close_grasp),
        "orientation_from_default_deg_mean": float(np.mean(orient)),
        "orientation_from_default_deg_p50": float(np.percentile(orient, 50)),
        "orientation_from_default_deg_p90": float(np.percentile(orient, 90)),
        "orientation_from_default_deg_p95": float(np.percentile(orient, 95)),
    }
    event_indices = {
        "pregrasp_keypoint": pregrasp_idx,
        "closest_grasp": closest_grasp_idx,
        "first_close": close_idx,
    }
    for prefix, idx in event_indices.items():
        quat = normalize_quat(quats[idx]) if idx is not None else np.full(4, np.nan)
        metrics[f"{prefix}_orientation_from_default_deg"] = (
            float(quaternion_angle_degrees(quat[None, :], DEFAULT_QUAT)[0])
            if np.all(np.isfinite(quat))
            else np.nan
        )
        for name, value in zip(("qx", "qy", "qz", "qw"), quat):
            metrics[f"{prefix}_{name}"] = float(value) if np.isfinite(value) else np.nan
    for threshold in PROGRESS_THRESHOLDS:
        metrics[f"time_at_progress_{int(threshold * 100):02d}"] = time_at_progress(
            progress,
            norm_time,
            threshold,
        )

    return metrics, {
        "group": group_spec["name"],
        "demo": demo_dir.name,
        "positions_time": interpolate_rows(norm_time, pos, TIME_GRID),
        "progress_time": np.interp(TIME_GRID, norm_time, progress),
        "first_close_pos": first_close_pos,
    }


def summarize_metric(values):
    clean = []
    for value in values:
        if value is None or value == "":
            continue
        clean.append(float(value))
    arr = np.asarray(clean, dtype=float)
    arr = arr[np.isfinite(arr)]
    if arr.size == 0:
        result = {f"p{p}": None for p in PERCENTILES}
        result.update({"mean": None, "std": None, "n": 0})
        return result
    result = {f"p{p}": finite_float(np.percentile(arr, p)) for p in PERCENTILES}
    result["mean"] = finite_float(np.mean(arr))
    result["std"] = finite_float(np.std(arr))
    result["n"] = int(arr.size)
    return result


def build_group_summaries(demo_metrics, resampled):
    numeric_fields = [
        "frame_count",
        "sampled_frame_count",
        "duration_s_assuming_sample_hz",
        "path_length_m",
        "corridor_crossing_frame",
        "corridor_crossing_norm_time",
        "corridor_crossing_x",
        "corridor_crossing_y",
        "corridor_crossing_z",
        "pregrasp_keypoint_frame",
        "pregrasp_keypoint_norm_time",
        "pregrasp_keypoint_x",
        "pregrasp_keypoint_y",
        "pregrasp_keypoint_z",
        "start_to_corridor_center_xz_m",
        "start_to_corridor_center_xyz_m",
        "min_pregrasp_dist_m",
        "min_grasp_dist_m",
        "min_object_xy_dist_m",
        "closest_pregrasp_norm_time",
        "first_close_norm_time",
        "first_close_to_pregrasp_m",
        "first_close_to_grasp_m",
        "closed_fraction",
        "max_z",
        "orientation_from_default_deg_mean",
        "orientation_from_default_deg_p95",
    ] + [
        f"{prefix}_orientation_from_default_deg" for prefix in EVENT_QUAT_PREFIXES
    ] + [f"time_at_progress_{int(t * 100):02d}" for t in PROGRESS_THRESHOLDS]

    by_group = defaultdict(list)
    resampled_by_group = defaultdict(list)
    for row in demo_metrics:
        by_group[row["group"]].append(row)
    for item in resampled:
        resampled_by_group[item["group"]].append(item)

    flat_summary_rows = []
    json_summary = {}
    for group, rows in by_group.items():
        group_summary = {
            "n_demos": len(rows),
            "metrics": {},
            "keypoint_spread": {},
            "spatial_dispersion": {},
            "temporal_progress": {},
        }
        for field in numeric_fields:
            values = [r.get(field, np.nan) for r in rows]
            stats = summarize_metric(values)
            group_summary["metrics"][field] = stats
            for stat, value in stats.items():
                flat_summary_rows.append(
                    {
                        "group": group,
                        "metric": field,
                        "stat": stat,
                        "value": "" if value is None else value,
                    }
                )

        for prefix, plane_axes in KEYPOINT_PLANES.items():
            points = np.asarray(
                [
                    [
                        float(r[f"{prefix}_x"]),
                        float(r[f"{prefix}_y"]),
                        float(r[f"{prefix}_z"]),
                    ]
                    for r in rows
                    if all(np.isfinite(float(r[f"{prefix}_{axis}"])) for axis in ("x", "y", "z"))
                ],
                dtype=float,
            )
            if points.size:
                center = np.mean(points, axis=0)
                plane_indices = [COORD_INDEX[axis] for axis in plane_axes]
                plane_points = points[:, plane_indices]
                plane_center = np.mean(plane_points, axis=0)
                plane_radius = np.linalg.norm(plane_points - plane_center[None, :], axis=1)
                group_summary["keypoint_spread"][prefix] = {
                    "plane_axes": list(plane_axes),
                    "mean_xyz": [finite_float(x) for x in center],
                    "std_xyz": [finite_float(x) for x in np.std(points, axis=0)],
                    "min_xyz": [finite_float(x) for x in np.min(points, axis=0)],
                    "max_xyz": [finite_float(x) for x in np.max(points, axis=0)],
                    "mean_plane": [finite_float(x) for x in plane_center],
                    "std_plane": [finite_float(x) for x in np.std(plane_points, axis=0)],
                    "min_plane": [finite_float(x) for x in np.min(plane_points, axis=0)],
                    "max_plane": [finite_float(x) for x in np.max(plane_points, axis=0)],
                    "plane_radius_to_group_mean": summarize_metric(plane_radius),
                }
            else:
                group_summary["keypoint_spread"][prefix] = {}

        items = resampled_by_group[group]
        if items:
            positions = np.stack([x["positions_time"] for x in items], axis=0)
            mean_positions = np.mean(positions, axis=0)
            dist = np.linalg.norm(positions - mean_positions[None, :, :], axis=2)
            progress = np.stack([x["progress_time"] for x in items], axis=0)
            progress_var = np.var(progress, axis=0)

            group_summary["spatial_dispersion"] = summarize_metric(dist.reshape(-1))
            group_summary["spatial_dispersion"]["mean_by_time"] = [
                finite_float(x) for x in np.mean(dist, axis=0)
            ]
            group_summary["temporal_progress"] = {
                "mean_progress_variance": finite_float(np.mean(progress_var)),
                "max_progress_variance": finite_float(np.max(progress_var)),
                "mean_progress_by_time": [finite_float(x) for x in np.mean(progress, axis=0)],
                "std_progress_by_time": [finite_float(x) for x in np.std(progress, axis=0)],
            }

            close_positions = np.stack(
                [
                    x["first_close_pos"]
                    for x in items
                    if np.all(np.isfinite(x["first_close_pos"]))
                ],
                axis=0,
            ) if any(np.all(np.isfinite(x["first_close_pos"])) for x in items) else np.empty((0, 3))
            if close_positions.size:
                center = np.mean(close_positions, axis=0)
                close_dist = np.linalg.norm(close_positions - center[None, :], axis=1)
                group_summary["first_close_spatial_dispersion"] = summarize_metric(close_dist)
                group_summary["first_close_center_xyz"] = [finite_float(x) for x in center]
            else:
                group_summary["first_close_spatial_dispersion"] = summarize_metric([])
                group_summary["first_close_center_xyz"] = []

        json_summary[group] = group_summary
    return json_summary, flat_summary_rows


def keypoint_summary_rows(group_summary):
    rows = []
    for group, summary in group_summary.items():
        for keypoint, stats in summary.get("keypoint_spread", {}).items():
            if not stats:
                continue
            plane_axes = stats.get("plane_axes", [])
            for coord_name, values in (
                ("x", [stats["mean_xyz"][0], stats["std_xyz"][0], stats["min_xyz"][0], stats["max_xyz"][0]]),
                ("y", [stats["mean_xyz"][1], stats["std_xyz"][1], stats["min_xyz"][1], stats["max_xyz"][1]]),
                ("z", [stats["mean_xyz"][2], stats["std_xyz"][2], stats["min_xyz"][2], stats["max_xyz"][2]]),
            ):
                for stat, value in zip(("mean", "std", "min", "max"), values):
                    rows.append(
                        {
                            "group": group,
                            "keypoint": keypoint,
                            "coordinate": coord_name,
                            "stat": stat,
                            "value_m": value,
                        }
                    )
            for axis, mean, std, min_value, max_value in zip(
                plane_axes,
                stats.get("mean_plane", []),
                stats.get("std_plane", []),
                stats.get("min_plane", []),
                stats.get("max_plane", []),
            ):
                for stat, value in (
                    ("mean", mean),
                    ("std", std),
                    ("min", min_value),
                    ("max", max_value),
                ):
                    rows.append(
                        {
                            "group": group,
                            "keypoint": keypoint,
                            "coordinate": f"plane_{axis}",
                            "stat": stat,
                            "value_m": value,
                        }
                    )
            radius = stats.get("plane_radius_to_group_mean", {})
            for stat in ("mean", "std", "p50", "p75", "p90", "p95", "p100"):
                rows.append(
                    {
                        "group": group,
                        "keypoint": keypoint,
                        "coordinate": "plane_radius_to_group_mean",
                        "stat": stat,
                        "value_m": radius.get(stat),
                    }
                )
    return rows


def orientation_event_summary_rows(demo_metrics):
    rows = []
    by_group = defaultdict(list)
    for row in demo_metrics:
        by_group[row["group"]].append(row)

    for group, group_rows in by_group.items():
        for event in EVENT_QUAT_PREFIXES:
            quats = []
            default_angles = []
            for row in group_rows:
                quat = [
                    row.get(f"{event}_qx", np.nan),
                    row.get(f"{event}_qy", np.nan),
                    row.get(f"{event}_qz", np.nan),
                    row.get(f"{event}_qw", np.nan),
                ]
                quat = normalize_quat(quat)
                if np.all(np.isfinite(quat)):
                    quats.append(quat)
                    value = row.get(f"{event}_orientation_from_default_deg", np.nan)
                    if value != "" and np.isfinite(float(value)):
                        default_angles.append(float(value))

            mean_quat, angles = quaternion_distances_to_mean_degrees(quats)
            angle_stats = summarize_metric(angles)
            default_stats = summarize_metric(default_angles)
            n = int(angles.size)
            rows.append(
                {
                    "group": group,
                    "event": event,
                    "n": n,
                    "mean_qx": mean_quat[0],
                    "mean_qy": mean_quat[1],
                    "mean_qz": mean_quat[2],
                    "mean_qw": mean_quat[3],
                    "angle_to_group_mean_mean_deg": angle_stats["mean"],
                    "angle_to_group_mean_p50_deg": angle_stats["p50"],
                    "angle_to_group_mean_p75_deg": angle_stats["p75"],
                    "angle_to_group_mean_p90_deg": angle_stats["p90"],
                    "angle_to_group_mean_p95_deg": angle_stats["p95"],
                    "angle_to_group_mean_max_deg": angle_stats["p100"],
                    "coverage_15deg": float(np.mean(angles <= 15.0)) if n else "",
                    "coverage_30deg": float(np.mean(angles <= 30.0)) if n else "",
                    "default_angle_mean_deg": default_stats["mean"],
                    "default_angle_p50_deg": default_stats["p50"],
                    "default_angle_p95_deg": default_stats["p95"],
                }
            )
    return rows


def temporal_summary_rows(demo_metrics):
    rows = []
    by_group = defaultdict(list)
    for row in demo_metrics:
        by_group[row["group"]].append(row)

    for group, group_rows in by_group.items():
        durations = []
        speeds = []
        progress_times = defaultdict(list)
        for row in group_rows:
            duration = row.get("duration_s_assuming_sample_hz", np.nan)
            path_length = row.get("path_length_m", np.nan)
            if duration != "" and np.isfinite(float(duration)) and float(duration) > 0:
                duration = float(duration)
                durations.append(duration)
                if path_length != "" and np.isfinite(float(path_length)):
                    speeds.append(float(path_length) / duration)
            for threshold in PROGRESS_THRESHOLDS:
                key = f"time_at_progress_{int(threshold * 100):02d}"
                value = row.get(key, np.nan)
                if value != "" and np.isfinite(float(value)):
                    progress_times[key].append(float(value))

        duration_stats = summarize_metric(durations)
        speed_stats = summarize_metric(speeds)
        duration_arr = np.asarray(durations, dtype=float)
        speed_arr = np.asarray(speeds, dtype=float)
        duration_median = duration_stats["p50"]
        speed_median = speed_stats["p50"]
        duration_ratio = duration_arr / duration_median if duration_median else np.asarray([])
        speed_ratio = speed_arr / speed_median if speed_median else np.asarray([])
        row = {
            "group": group,
            "n": int(duration_arr.size),
            "duration_mean_s": duration_stats["mean"],
            "duration_p50_s": duration_stats["p50"],
            "duration_p90_s": duration_stats["p90"],
            "duration_p95_s": duration_stats["p95"],
            "duration_ratio_to_median_p05": finite_float(np.percentile(duration_ratio, 5)) if duration_ratio.size else "",
            "duration_ratio_to_median_p95": finite_float(np.percentile(duration_ratio, 95)) if duration_ratio.size else "",
            "duration_ratio_coverage_0p5_2p0": float(np.mean((duration_ratio >= 0.5) & (duration_ratio <= 2.0))) if duration_ratio.size else "",
            "duration_ratio_coverage_0p8_1p25": float(np.mean((duration_ratio >= 0.8) & (duration_ratio <= 1.25))) if duration_ratio.size else "",
            "mean_speed_mean_mps": speed_stats["mean"],
            "mean_speed_p50_mps": speed_stats["p50"],
            "mean_speed_p90_mps": speed_stats["p90"],
            "mean_speed_ratio_to_median_p05": finite_float(np.percentile(speed_ratio, 5)) if speed_ratio.size else "",
            "mean_speed_ratio_to_median_p95": finite_float(np.percentile(speed_ratio, 95)) if speed_ratio.size else "",
            "mean_speed_ratio_coverage_0p5_2p0": float(np.mean((speed_ratio >= 0.5) & (speed_ratio <= 2.0))) if speed_ratio.size else "",
        }
        for key, values in progress_times.items():
            stats = summarize_metric(values)
            row[f"{key}_p50"] = stats["p50"]
            row[f"{key}_p90"] = stats["p90"]
            row[f"{key}_p95"] = stats["p95"]
        rows.append(row)
    return rows


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


def make_plots(output_dir, demo_metrics, group_summary):
    os.environ.setdefault("MPLCONFIGDIR", str(output_dir / ".matplotlib"))
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    groups = list(group_summary.keys())
    metrics_by_group = defaultdict(list)
    for row in demo_metrics:
        metrics_by_group[row["group"]].append(row)

    def boxplot_metric(metric, ylabel, filename):
        data = []
        labels = []
        for group in groups:
            values = [
                float(r[metric])
                for r in metrics_by_group[group]
                if r.get(metric, "") != "" and np.isfinite(float(r[metric]))
            ]
            if values:
                data.append(values)
                labels.append(group)
        if not data:
            return
        fig, ax = plt.subplots(figsize=(max(9, len(labels) * 1.4), 4.8))
        ax.boxplot(data, labels=labels, showfliers=True)
        ax.set_ylabel(ylabel)
        ax.tick_params(axis="x", rotation=25)
        ax.grid(True, axis="y", alpha=0.25)
        fig.tight_layout()
        fig.savefig(output_dir / filename, dpi=180)
        plt.close(fig)

    boxplot_metric("frame_count", "frames", "frame_counts_by_group.png")
    boxplot_metric("start_to_corridor_center_xz_m", "start radius to AR center, x-z (m)", "start_corridor_radius_by_group.png")
    boxplot_metric("min_pregrasp_dist_m", "closest distance to pre-grasp reference (m)", "min_pregrasp_distance_by_group.png")
    boxplot_metric("first_close_to_pregrasp_m", "first close distance to pre-grasp ref (m)", "first_close_pregrasp_distance_by_group.png")
    boxplot_metric("orientation_from_default_deg_p95", "per-demo p95 orientation angle from default (deg)", "orientation_p95_by_group.png")

    def scatter_keypoint(prefix, title, filename):
        plane_axes = KEYPOINT_PLANES[prefix]
        a0, a1 = plane_axes
        fig, ax = plt.subplots(figsize=(7.2, 5.8))
        for group in groups:
            rows = metrics_by_group[group]
            u = [
                float(r[f"{prefix}_{a0}"])
                for r in rows
                if np.isfinite(float(r[f"{prefix}_{a0}"])) and np.isfinite(float(r[f"{prefix}_{a1}"]))
            ]
            v = [
                float(r[f"{prefix}_{a1}"])
                for r in rows
                if np.isfinite(float(r[f"{prefix}_{a0}"])) and np.isfinite(float(r[f"{prefix}_{a1}"]))
            ]
            if not u:
                continue
            ax.scatter(u, v, s=16, alpha=0.55, label=group)
            ax.scatter([np.mean(u)], [np.mean(v)], s=90, marker="x", linewidths=2.0)
        ax.set_xlabel(f"{a0} (m)")
        ax.set_ylabel(f"{a1} (m)")
        ax.set_title(title)
        ax.grid(True, alpha=0.25)
        ax.legend(fontsize=8, ncol=1)
        fig.tight_layout()
        fig.savefig(output_dir / filename, dpi=180)
        plt.close(fig)

    def circle_keypoint(prefix, title, filename):
        plane_axes = KEYPOINT_PLANES[prefix]
        a0, a1 = plane_axes
        ncols = 3
        nrows = int(np.ceil(len(groups) / ncols))
        fig, axes = plt.subplots(nrows, ncols, figsize=(14.0, 4.2 * nrows), squeeze=False)

        all_u = []
        all_v = []
        for group in groups:
            for r in metrics_by_group[group]:
                u = float(r[f"{prefix}_{a0}"])
                v = float(r[f"{prefix}_{a1}"])
                if np.isfinite(u) and np.isfinite(v):
                    all_u.append(u)
                    all_v.append(v)
        if all_u:
            umin, umax = min(all_u), max(all_u)
            vmin, vmax = min(all_v), max(all_v)
            upad = max(0.02, 0.08 * (umax - umin))
            vpad = max(0.02, 0.08 * (vmax - vmin))
        else:
            umin, umax, vmin, vmax, upad, vpad = 0.0, 1.0, 0.0, 1.0, 0.02, 0.02

        for ax, group in zip(axes.flat, groups):
            rows = metrics_by_group[group]
            u = np.asarray(
                [
                    float(r[f"{prefix}_{a0}"])
                    for r in rows
                    if np.isfinite(float(r[f"{prefix}_{a0}"])) and np.isfinite(float(r[f"{prefix}_{a1}"]))
                ],
                dtype=float,
            )
            v = np.asarray(
                [
                    float(r[f"{prefix}_{a1}"])
                    for r in rows
                    if np.isfinite(float(r[f"{prefix}_{a0}"])) and np.isfinite(float(r[f"{prefix}_{a1}"]))
                ],
                dtype=float,
            )
            ax.scatter(u, v, s=16, alpha=0.45)

            stats = group_summary[group].get("keypoint_spread", {}).get(prefix, {})
            center = stats.get("mean_plane")
            radius_stats = stats.get("plane_radius_to_group_mean", {})
            if center and radius_stats:
                cu, cv = float(center[0]), float(center[1])
                ax.scatter([cu], [cv], s=120, marker="x", linewidths=2.5, color="black")
                circles = (
                    ("mean", radius_stats.get("mean"), "--", "0.35"),
                    ("p90", radius_stats.get("p90"), "-.", "tab:orange"),
                    ("p95", radius_stats.get("p95"), "-", "tab:red"),
                    ("max", radius_stats.get("p100"), ":", "0.20"),
                )
                for label, radius, linestyle, color in circles:
                    if radius is None:
                        continue
                    circle = plt.Circle(
                        (cu, cv),
                        float(radius),
                        fill=False,
                        linestyle=linestyle,
                        linewidth=1.5,
                        color=color,
                        alpha=0.95,
                        label=f"{label}={float(radius) * 100:.1f}cm",
                    )
                    ax.add_patch(circle)
                ax.text(
                    0.02,
                    0.98,
                    f"center=({cu * 100:.1f}, {cv * 100:.1f})cm",
                    transform=ax.transAxes,
                    va="top",
                    ha="left",
                    fontsize=8,
                    bbox={"facecolor": "white", "alpha": 0.75, "edgecolor": "none"},
                )

            ax.set_title(group, fontsize=10)
            ax.set_xlabel(f"{a0} (m)")
            ax.set_ylabel(f"{a1} (m)")
            ax.set_xlim(umin - upad, umax + upad)
            ax.set_ylim(vmin - vpad, vmax + vpad)
            ax.set_aspect("equal", adjustable="box")
            ax.grid(True, alpha=0.25)
            ax.legend(fontsize=7, loc="lower right")

        for ax in axes.flat[len(groups) :]:
            ax.axis("off")
        fig.suptitle(title, fontsize=14)
        fig.tight_layout()
        fig.savefig(output_dir / filename, dpi=180)
        plt.close(fig)

    scatter_keypoint(
        "corridor_crossing",
        "Detected corridor-crossing keypoints: closest trajectory point to y=0",
        "corridor_crossing_xz_scatter_by_group.png",
    )
    scatter_keypoint(
        "pregrasp_keypoint",
        "Detected pre-grasp keypoints in x-y: first sustained z drop after frame 70",
        "pregrasp_keypoint_xy_scatter_by_group.png",
    )
    circle_keypoint(
        "corridor_crossing",
        "Corridor-crossing keypoint centers and radius bands",
        "corridor_crossing_xz_center_radius_by_group.png",
    )
    circle_keypoint(
        "pregrasp_keypoint",
        "Pre-grasp keypoint centers and radius bands in x-y",
        "pregrasp_keypoint_xy_center_radius_by_group.png",
    )

    fig, ax = plt.subplots(figsize=(9.5, 5.2))
    for group in groups:
        temporal = group_summary[group].get("temporal_progress", {})
        mean = temporal.get("mean_progress_by_time")
        std = temporal.get("std_progress_by_time")
        if not mean or not std:
            continue
        mean = np.asarray(mean, dtype=float)
        std = np.asarray(std, dtype=float)
        ax.plot(TIME_GRID, mean, label=group)
        ax.fill_between(TIME_GRID, mean - std, mean + std, alpha=0.12)
    ax.set_xlabel("normalized time")
    ax.set_ylabel("normalized path progress")
    ax.set_xlim(0.0, 1.0)
    ax.set_ylim(0.0, 1.0)
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=8, ncol=2)
    fig.tight_layout()
    fig.savefig(output_dir / "path_progress_by_group.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(9.5, 4.8))
    means = []
    labels = []
    for group in groups:
        stats = group_summary[group].get("spatial_dispersion", {})
        value = stats.get("mean")
        if value is not None:
            labels.append(group)
            means.append(float(value))
    if means:
        ax.bar(labels, means)
        ax.set_ylabel("mean distance to group mean trajectory (m)")
        ax.tick_params(axis="x", rotation=25)
        ax.grid(True, axis="y", alpha=0.25)
        fig.tight_layout()
        fig.savefig(output_dir / "spatial_dispersion_mean_by_group.png", dpi=180)
    plt.close(fig)


def default_group_specs():
    specs = []
    dataset_key_map = {
        "P1_target_pre_skill1": "target_pre_skill1",
        "P2_target_pre_skill2": "target_pre_skill2",
        "P6_target_post_skill1": "target_post_skill1",
        "P7_target_post_skill2": "target_post_skill2",
    }
    for name, root, cohort, phase, skill in DEFAULT_GROUPS:
        specs.append(
            {
                "name": name,
                "root": root,
                "cohort": cohort,
                "phase": phase,
                "skill": skill,
                "dataset_key": dataset_key_map.get(name, name),
            }
        )
    return specs


def parse_group_override(values):
    specs = []
    for raw in values or []:
        parts = raw.split("=", 1)
        if len(parts) != 2:
            raise argparse.ArgumentTypeError(f"Expected NAME=PATH, got {raw!r}")
        name, path = parts
        specs.append(
            {
                "name": name,
                "root": Path(path),
                "cohort": "custom",
                "phase": "custom",
                "skill": "custom",
                "dataset_key": name,
            }
        )
    return specs


def parse_args():
    parser = argparse.ArgumentParser(
        description="Compute read-only Week 2 diagnostics for real-human PyBullet demos."
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--group", action="append", default=[], help="Optional NAME=PATH group override. If set, defaults are not used.")
    parser.add_argument("--max-demos-per-group", type=int, default=None)
    parser.add_argument("--frame-stride", type=int, default=1, help="Use every Nth frame for FK; last frame is always included.")
    parser.add_argument("--sample-hz", type=float, default=30.0, help="Only used for the derived duration_s column.")
    parser.add_argument("--pregrasp-min-frame", type=int, default=70)
    parser.add_argument("--pregrasp-lookahead-frames", type=int, default=30)
    parser.add_argument("--pregrasp-drop-threshold", type=float, default=0.04)
    parser.add_argument("--pregrasp-short-lookahead-frames", type=int, default=10)
    parser.add_argument("--pregrasp-short-drop-threshold", type=float, default=0.005)
    parser.add_argument("--corridor-center", type=parse_xyz, default=np.asarray([0.3, 0.0, 0.5], dtype=float))
    parser.add_argument("--pregrasp-ref", type=parse_xyz, default=np.asarray([0.5, 0.5, 0.22], dtype=float))
    parser.add_argument("--grasp-ref", type=parse_xyz, default=np.asarray([0.5, 0.5, 0.08], dtype=float))
    parser.add_argument(
        "--no-mirror-y",
        dest="mirror_y",
        action="store_false",
        help="Do not mirror FK y positions. By default human left-handed coordinates are aligned to the paper/simulation frame with y = -y.",
    )
    parser.set_defaults(mirror_y=True)
    parser.add_argument("--no-plots", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    group_specs = parse_group_override(args.group) if args.group else default_group_specs()
    manifest_people, manifest_sources = load_manifest_people(
        DEFAULT_DATA_ROOT / "target_pooled/manifests/target_pooled_manifest.csv"
    )
    refs = {
        "corridor": args.corridor_center,
        "pregrasp": args.pregrasp_ref,
        "grasp": args.grasp_ref,
    }

    fk = PandaFk()
    demo_metrics = []
    resampled = []
    errors = []
    try:
        for spec in group_specs:
            demos = list_demo_dirs(spec["root"])
            if args.max_demos_per_group is not None:
                demos = demos[: args.max_demos_per_group]
            print(f"[INFO] {spec['name']}: {len(demos)} demos from {spec['root']}", flush=True)
            for demo_dir in demos:
                try:
                    metrics, sampled = analyze_demo(
                        demo_dir,
                        spec,
                        fk,
                        refs,
                        args.sample_hz,
                        args.frame_stride,
                        args.mirror_y,
                        args.pregrasp_min_frame,
                        args.pregrasp_lookahead_frames,
                        args.pregrasp_drop_threshold,
                        args.pregrasp_short_lookahead_frames,
                        args.pregrasp_short_drop_threshold,
                        manifest_people,
                        manifest_sources,
                    )
                    demo_metrics.append(metrics)
                    resampled.append(sampled)
                except Exception as exc:
                    message = f"{spec['name']}/{demo_dir.name}: {exc}"
                    print(f"[WARN] {message}", flush=True)
                    errors.append(message)
    finally:
        fk.close()

    group_summary, summary_rows = build_group_summaries(demo_metrics, resampled)
    keypoint_rows = keypoint_summary_rows(group_summary)
    orientation_rows = orientation_event_summary_rows(demo_metrics)
    temporal_rows = temporal_summary_rows(demo_metrics)

    write_csv(args.output_dir / "demo_metrics.csv", demo_metrics)
    write_csv(args.output_dir / "group_summary_long.csv", summary_rows)
    write_csv(args.output_dir / "keypoint_spread_summary.csv", keypoint_rows)
    write_csv(args.output_dir / "orientation_event_summary.csv", orientation_rows)
    write_csv(args.output_dir / "temporal_human_summary.csv", temporal_rows)
    (args.output_dir / "human_diagnostics_summary.json").write_text(
        json.dumps(
            {
                "note": "Read-only diagnostics. Raw human data under /scratch/users/k23114984/pybullet_data was not modified.",
                "sample_hz_for_duration_only": args.sample_hz,
                "frame_stride": args.frame_stride,
                "pregrasp_detection": {
                    "min_frame": args.pregrasp_min_frame,
                    "lookahead_frames": args.pregrasp_lookahead_frames,
                    "drop_threshold_m": args.pregrasp_drop_threshold,
                    "short_lookahead_frames": args.pregrasp_short_lookahead_frames,
                    "short_drop_threshold_m": args.pregrasp_short_drop_threshold,
                },
                "references": {k: [float(x) for x in v] for k, v in refs.items()},
                "mirror_y_applied": args.mirror_y,
                "groups": group_summary,
                "orientation_event_summary": orientation_rows,
                "temporal_human_summary": temporal_rows,
                "errors": errors,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    if not args.no_plots and demo_metrics:
        make_plots(args.output_dir, demo_metrics, group_summary)

    print(f"[INFO] Wrote {args.output_dir / 'demo_metrics.csv'}", flush=True)
    print(f"[INFO] Wrote {args.output_dir / 'group_summary_long.csv'}", flush=True)
    print(f"[INFO] Wrote {args.output_dir / 'keypoint_spread_summary.csv'}", flush=True)
    print(f"[INFO] Wrote {args.output_dir / 'orientation_event_summary.csv'}", flush=True)
    print(f"[INFO] Wrote {args.output_dir / 'temporal_human_summary.csv'}", flush=True)
    print(f"[INFO] Wrote {args.output_dir / 'human_diagnostics_summary.json'}", flush=True)
    if errors:
        print(f"[WARN] Completed with {len(errors)} skipped demos/frames; see JSON errors.", flush=True)


if __name__ == "__main__":
    main()
