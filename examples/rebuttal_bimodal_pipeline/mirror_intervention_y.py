#!/usr/bin/env python3
"""Mirror intervention trajectories across world y=0 and resolve new Panda joints.

For each source joint row, the tool computes the end-effector pose with the
frozen simulation base at y=+0.15 m, changes only position y to -y, moves the
PyBullet Panda base to y=-0.15 m, and solves the mirrored Cartesian path with
sequential IK. Extra Cartesian interpolation points slow and smooth the replay.
The gripper command/width sequence is interpolated without changing semantics.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pybullet as pb


REPO = Path(__file__).resolve().parents[2]
EXAMPLES_DIR = REPO / "examples"
if str(EXAMPLES_DIR) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_DIR))

from main_abla_1 import PandaSim  # noqa: E402


CSV_FIELDS = [
    "t",
    "dt",
    "step",
    "state_seq",
    "control_mode",
    "drive_mode",
    "gripper_cmd",
    "gripper_width",
    "q0",
    "q1",
    "q2",
    "q3",
    "q4",
    "q5",
    "q6",
]
DEFAULT_INPUTS = [
    REPO / "bimodal_target_replays/seed_20260809/L/intervention.csv",
    REPO / "bimodal_target_replays/seed_20260809/R/intervention.csv",
]
SOURCE_BASE_POSITION = np.asarray([0.0, 0.15, 0.0], dtype=float)
MIRRORED_BASE_POSITION = np.asarray([0.0, -0.15, 0.0], dtype=float)


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_rows(path):
    with Path(path).open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != CSV_FIELDS:
            raise ValueError(f"Unexpected intervention schema in {path}: {reader.fieldnames}")
        rows = list(reader)
    if len(rows) < 2:
        raise ValueError(f"Need at least two intervention rows: {path}")
    for index, row in enumerate(rows):
        if int(row["step"]) != index or int(row["state_seq"]) != index:
            raise ValueError(f"Non-contiguous row sequence at {path}:{index + 2}")
        numeric = [
            float(row[key])
            for key in ("t", "dt", "gripper_cmd", "gripper_width")
            + tuple(f"q{joint}" for joint in range(7))
        ]
        if not np.isfinite(numeric).all():
            raise ValueError(f"Non-finite intervention value at {path}:{index + 2}")
    return rows


def slerp(quat_a, quat_b, fraction):
    """Shortest-path quaternion interpolation in xyzw order."""

    a = np.asarray(quat_a, dtype=float)
    b = np.asarray(quat_b, dtype=float)
    a /= np.linalg.norm(a)
    b /= np.linalg.norm(b)
    dot = float(np.dot(a, b))
    if dot < 0.0:
        b = -b
        dot = -dot
    dot = float(np.clip(dot, -1.0, 1.0))
    if dot > 0.9995:
        result = a + float(fraction) * (b - a)
        return result / np.linalg.norm(result)
    theta = math.acos(dot)
    sin_theta = math.sin(theta)
    return (
        math.sin((1.0 - float(fraction)) * theta) / sin_theta * a
        + math.sin(float(fraction) * theta) / sin_theta * b
    )


def interpolate_scalar(a, b, fraction):
    return (1.0 - float(fraction)) * float(a) + float(fraction) * float(b)


def set_robot_base(sim, position):
    pb.resetBasePositionAndOrientation(
        sim.panda, np.asarray(position, dtype=float).tolist(), [0.0, 0.0, 0.0, 1.0]
    )


def fk_source_poses(sim, rows):
    set_robot_base(sim, SOURCE_BASE_POSITION)
    poses = []
    for row in rows:
        q = [float(row[f"q{joint}"]) for joint in range(7)]
        sim.reset_arm_joints(q)
        state = pb.getLinkState(
            sim.panda, sim.ee_link_index, computeForwardKinematics=True
        )
        position = np.asarray(state[0], dtype=float)
        quaternion = np.asarray(state[1], dtype=float)
        mirrored_position = position.copy()
        mirrored_position[1] = -mirrored_position[1]
        poses.append(
            {
                "source_position": position,
                "target_position": mirrored_position,
                "quaternion": quaternion,
                "gripper_cmd": float(row["gripper_cmd"]),
                "gripper_width": float(row["gripper_width"]),
            }
        )
    return poses


def solve_pose(sim, position, quaternion):
    q = np.asarray(sim.solve_ik(position, quaternion), dtype=float)
    if q.shape != (7,) or not np.isfinite(q).all():
        raise RuntimeError(f"Invalid IK solution for {position}: {q}")
    sim.reset_arm_joints(q)
    realised = pb.getLinkState(
        sim.panda, sim.ee_link_index, computeForwardKinematics=True
    )
    position_error = float(
        np.linalg.norm(np.asarray(realised[0], dtype=float) - np.asarray(position))
    )
    quat_dot = abs(float(np.dot(np.asarray(realised[1]), np.asarray(quaternion))))
    orientation_error = math.degrees(
        2.0 * math.acos(float(np.clip(quat_dot, -1.0, 1.0)))
    )
    return q, position_error, orientation_error


def candidate_transition(sim, start, end, start_q, subdivisions):
    sim.reset_arm_joints(start_q)
    candidates = []
    previous_q = np.asarray(start_q, dtype=float)
    max_joint_step = 0.0
    max_position_error = 0.0
    max_orientation_error = 0.0
    for sub_index in range(1, int(subdivisions) + 1):
        fraction = float(sub_index) / float(subdivisions)
        position = (
            (1.0 - fraction) * start["target_position"]
            + fraction * end["target_position"]
        )
        quaternion = slerp(start["quaternion"], end["quaternion"], fraction)
        q, position_error, orientation_error = solve_pose(sim, position, quaternion)
        joint_step = float(np.max(np.abs(q - previous_q)))
        max_joint_step = max(max_joint_step, joint_step)
        max_position_error = max(max_position_error, position_error)
        max_orientation_error = max(max_orientation_error, orientation_error)
        candidates.append(
            {
                "target_position": position,
                "target_quaternion": quaternion,
                "q": q,
                "gripper_cmd": interpolate_scalar(
                    start["gripper_cmd"], end["gripper_cmd"], fraction
                ),
                "gripper_width": interpolate_scalar(
                    start["gripper_width"], end["gripper_width"], fraction
                ),
                "source_transition_fraction": fraction,
                "ik_position_error": position_error,
                "ik_orientation_error_degrees": orientation_error,
            }
        )
        previous_q = q
    return (
        candidates,
        max_joint_step,
        max_position_error,
        max_orientation_error,
    )


def plan_mirrored_path(
    sim,
    poses,
    interpolation_factor,
    max_planned_joint_step,
    max_subdivisions,
    max_ik_position_error,
):
    set_robot_base(sim, MIRRORED_BASE_POSITION)
    # Seed the first IK call from the original first joint state already in sim.
    first_q, first_error, first_orientation_error = solve_pose(
        sim, poses[0]["target_position"], poses[0]["quaternion"]
    )
    if first_error > max_ik_position_error:
        raise RuntimeError(f"First mirrored waypoint IK error is {first_error:.6f} m")
    planned = [
        {
            "target_position": poses[0]["target_position"],
            "target_quaternion": poses[0]["quaternion"],
            "q": first_q,
            "gripper_cmd": poses[0]["gripper_cmd"],
            "gripper_width": poses[0]["gripper_width"],
            "source_transition_fraction": 0.0,
            "ik_position_error": first_error,
            "ik_orientation_error_degrees": first_orientation_error,
        }
    ]
    subdivisions_used = []
    for source_index in range(1, len(poses)):
        subdivisions = int(interpolation_factor)
        start_q = np.asarray(planned[-1]["q"], dtype=float)
        while True:
            candidates, joint_step, position_error, _ = candidate_transition(
                sim,
                poses[source_index - 1],
                poses[source_index],
                start_q,
                subdivisions,
            )
            if (
                joint_step <= max_planned_joint_step
                and position_error <= max_ik_position_error
            ):
                break
            subdivisions *= 2
            if subdivisions > max_subdivisions:
                raise RuntimeError(
                    f"Could not smoothly solve source transition {source_index - 1}->"
                    f"{source_index}: joint_step={joint_step:.6f} rad, "
                    f"IK_error={position_error:.6f} m"
                )
        planned.extend(candidates)
        subdivisions_used.append(subdivisions)
    return planned, subdivisions_used


def replay_and_record(sim, planned, output_hz, arm_max_velocity):
    set_robot_base(sim, MIRRORED_BASE_POSITION)
    steps_per_output = int(round(float(sim.control_hz) / float(output_hz)))
    if not math.isclose(
        steps_per_output * float(output_hz), float(sim.control_hz), abs_tol=1e-12
    ):
        raise ValueError("output_hz must divide PyBullet control_hz")

    sim.reset_arm_joints(planned[0]["q"])
    initial_finger_width = float(planned[0]["gripper_width"]) / 2.0
    pb.resetJointState(sim.panda, sim.left_finger_joint, initial_finger_width)
    pb.resetJointState(sim.panda, sim.right_finger_joint, initial_finger_width)
    rows = []
    tracking_errors = []
    for index, waypoint in enumerate(planned):
        if index > 0:
            finger_width = float(waypoint["gripper_width"]) / 2.0
            for _ in range(steps_per_output):
                sim._apply_arm(
                    waypoint["q"], force=120, max_vel=float(arm_max_velocity)
                )
                sim._apply_gripper(finger_width, force=120, max_vel=0.08)
                sim._step_simulation(sim.sim_dt)
        actual_q = [
            float(pb.getJointState(sim.panda, joint)[0])
            for joint in sim.arm_joint_indices
        ]
        actual_gripper_width = sum(
            float(pb.getJointState(sim.panda, joint)[0])
            for joint in (sim.left_finger_joint, sim.right_finger_joint)
        )
        state = pb.getLinkState(
            sim.panda, sim.ee_link_index, computeForwardKinematics=True
        )
        tracking_error = float(
            np.linalg.norm(
                np.asarray(state[0], dtype=float) - waypoint["target_position"]
            )
        )
        tracking_errors.append(tracking_error)
        t = float(index) / float(output_hz)
        row = {
            "t": t,
            "dt": 0.0 if index == 0 else 1.0 / float(output_hz),
            "step": index,
            "state_seq": index,
            "control_mode": "takeover",
            "drive_mode": "cartesian_freedrive",
            "gripper_cmd": float(waypoint["gripper_cmd"]),
            "gripper_width": actual_gripper_width,
        }
        row.update({f"q{joint}": q for joint, q in enumerate(actual_q)})
        rows.append(row)
    return rows, tracking_errors


def write_csv_exclusive(path, rows):
    path = Path(path)
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    with path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
        stream.flush()
        os.fsync(stream.fileno())


def write_json_exclusive(path, payload):
    path = Path(path)
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def trajectory_stats(rows):
    q = np.asarray(
        [[float(row[f"q{joint}"]) for joint in range(7)] for row in rows],
        dtype=float,
    )
    dt = np.asarray([float(row["dt"]) for row in rows], dtype=float)
    joint_steps = np.abs(np.diff(q, axis=0))
    velocities = joint_steps / dt[1:, None]
    return {
        "row_count": len(rows),
        "duration_seconds": float(rows[-1]["t"]),
        "max_adjacent_joint_step_rad": float(np.max(joint_steps)),
        "max_implied_joint_velocity_rad_s": float(np.max(velocities)),
        "joint_min_rad": np.min(q, axis=0).tolist(),
        "joint_max_rad": np.max(q, axis=0).tolist(),
    }


def transform_one(sim, source_path, args, temporary_path):
    source_rows = load_rows(source_path)
    source_sha = sha256(source_path)
    poses = fk_source_poses(sim, source_rows)
    # Retain the original first q as the null-space seed before changing bases.
    sim.reset_arm_joints(
        [float(source_rows[0][f"q{joint}"]) for joint in range(7)]
    )
    planned, subdivisions = plan_mirrored_path(
        sim,
        poses,
        args.interpolation_factor,
        args.max_planned_joint_step,
        args.max_subdivisions,
        args.max_ik_position_error,
    )
    rows, tracking_errors = replay_and_record(
        sim, planned, args.output_hz, args.arm_max_velocity
    )
    if max(tracking_errors) > args.max_tracking_error:
        raise RuntimeError(
            f"Mirrored replay tracking error {max(tracking_errors):.6f} m exceeds "
            f"{args.max_tracking_error:.6f} m for {source_path}"
        )
    write_csv_exclusive(temporary_path, rows)
    source_y = [float(pose["source_position"][1]) for pose in poses]
    target_y = [float(pose["target_position"][1]) for pose in poses]
    metadata = {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_csv": str(source_path.resolve()),
        "source_csv_sha256": source_sha,
        "output_csv_sha256": sha256(temporary_path),
        "transform": {
            "position": "world Cartesian y := -y; x and z unchanged",
            "orientation": "unchanged world quaternion; shortest-path SLERP between samples",
            "source_robot_base_position": SOURCE_BASE_POSITION.tolist(),
            "mirrored_robot_base_position": MIRRORED_BASE_POSITION.tolist(),
            "base_position_is_mirrored_with_the_workspace": True,
        },
        "source": {
            "row_count": len(source_rows),
            "duration_seconds": float(source_rows[-1]["t"]),
            "ee_y_start_m": source_y[0],
            "ee_y_end_m": source_y[-1],
            "ee_y_min_m": min(source_y),
            "ee_y_max_m": max(source_y),
        },
        "mirrored_targets": {
            "ee_y_start_m": target_y[0],
            "ee_y_end_m": target_y[-1],
            "ee_y_min_m": min(target_y),
            "ee_y_max_m": max(target_y),
        },
        "interpolation": {
            "minimum_subdivisions_per_source_transition": args.interpolation_factor,
            "maximum_subdivisions_used": max(subdivisions),
            "transitions_with_extra_adaptive_subdivision": sum(
                value > args.interpolation_factor for value in subdivisions
            ),
            "max_planned_joint_step_rad": args.max_planned_joint_step,
        },
        "pybullet_replay": {
            "output_hz": args.output_hz,
            "arm_max_velocity_argument_rad_s": args.arm_max_velocity,
            "max_ee_tracking_error_m": max(tracking_errors),
            "mean_ee_tracking_error_m": float(np.mean(tracking_errors)),
        },
        "output": trajectory_stats(rows),
        "gripper": "command and width interpolated from source; actual PyBullet width recorded",
    }
    return metadata


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="*", type=Path, default=DEFAULT_INPUTS)
    parser.add_argument("--in-place", action="store_true")
    parser.add_argument("--interpolation-factor", type=int, default=4)
    parser.add_argument("--max-planned-joint-step", type=float, default=0.02)
    parser.add_argument("--max-subdivisions", type=int, default=256)
    parser.add_argument("--max-ik-position-error", type=float, default=0.002)
    parser.add_argument("--max-tracking-error", type=float, default=0.015)
    parser.add_argument("--output-hz", type=float, default=30.0)
    parser.add_argument("--arm-max-velocity", type=float, default=0.5)
    return parser.parse_args()


def main():
    args = parse_args()
    if args.interpolation_factor < 2:
        raise ValueError("interpolation-factor must be at least 2")
    input_paths = [path.resolve() for path in args.inputs]
    if not input_paths or len(set(input_paths)) != len(input_paths):
        raise ValueError("Expected one or more distinct intervention CSVs")
    for path in input_paths:
        if not path.is_file():
            raise FileNotFoundError(path)
        if args.in_place:
            reserved = (
                path.with_name("intervention_y_positive_original.csv"),
                path.with_name("intervention_y_mirror.json"),
            )
        else:
            reserved = (
                path.with_name("intervention_mirrored_y.csv"),
                path.with_name("intervention_mirrored_y.json"),
            )
        for output in reserved:
            if output.exists() or output.is_symlink():
                raise FileExistsError(f"Refusing to overwrite output: {output}")

    sim = PandaSim(gui=False, output_dir=None, sample_hz=args.output_hz)
    sim.playback_speed = 1000.0
    sim.setup()
    prepared = []
    try:
        for source_path in input_paths:
            temporary = source_path.with_name(
                f".{source_path.name}.mirror_y.inprogress.{os.getpid()}"
            )
            if temporary.exists() or temporary.is_symlink():
                raise FileExistsError(temporary)
            metadata = transform_one(sim, source_path, args, temporary)
            prepared.append((source_path, temporary, metadata))
    finally:
        if sim.client is not None:
            pb.disconnect(sim.client)

    for source_path, temporary, metadata in prepared:
        if args.in_place:
            backup = source_path.with_name("intervention_y_positive_original.csv")
            metadata_path = source_path.with_name("intervention_y_mirror.json")
            shutil.copy2(source_path, backup)
            os.replace(temporary, source_path)
            metadata["source_csv"] = str(backup.resolve())
            metadata["activated_output_csv"] = str(source_path.resolve())
            metadata["backup_csv"] = str(backup.resolve())
            write_json_exclusive(metadata_path, metadata)
        else:
            output = source_path.with_name("intervention_mirrored_y.csv")
            metadata_path = source_path.with_name("intervention_mirrored_y.json")
            os.replace(temporary, output)
            metadata["output_csv"] = str(output.resolve())
            write_json_exclusive(metadata_path, metadata)
        print(json.dumps(metadata, indent=2, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
