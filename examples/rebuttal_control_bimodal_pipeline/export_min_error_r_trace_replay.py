#!/usr/bin/env python3
"""Build a mirrored joint replay from the best formal Control-Bimodal R trace."""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pybullet as pb


REPO = Path(__file__).resolve().parents[2]
EXAMPLES = REPO / "examples"
if str(EXAMPLES) not in sys.path:
    sys.path.insert(0, str(EXAMPLES))

import main_obstacle_transport as task  # noqa: E402
from rebuttal_bimodal_pipeline import export_success_replays as replay  # noqa: E402
from rebuttal_control_bimodal_pipeline import (  # noqa: E402
    export_min_error_r_replay as selection,
)


MIRRORED_BASE = np.asarray([0.0, -0.15, 0.0], dtype=float)
MIRRORED_OBSTACLE = np.asarray([task.OBSTACLE_XY[0], -task.OBSTACLE_XY[1]], dtype=float)
MIRRORED_TARGET = np.asarray([task.TARGET_XY[0], -task.TARGET_XY[1]], dtype=float)
# Collision-free Panda null-space branch found deterministically for the
# post-obstacle section of the mirrored formal EE trace.  A smooth IK-rest
# blend moves the elbow onto this branch before the cylinder crossing.
POST_OBSTACLE_IK_REST = np.asarray(
    [0.35, 0.61, -0.84, -1.81, 0.70, 2.30, -0.03], dtype=float
)


def mirror_position(position):
    result = np.asarray(position, dtype=float).copy()
    result[1] = -result[1]
    return result


def mirror_quaternion(quaternion):
    """Reflect a frame orientation with R' = S R S, S=diag(1,-1,1)."""

    x, y, z, w = np.asarray(quaternion, dtype=float)
    result = np.asarray([-x, y, -z, w], dtype=float)
    return result / np.linalg.norm(result)


def mirror_trace_position(position):
    """Mirror an EE sample and keep a post-obstacle elbow-clearance corridor."""

    result = mirror_position(position)
    forward_y = -float(result[1])
    if 0.32 <= forward_y <= 0.48:
        safe_x = 0.70
        safe_z = 0.18
    elif 0.48 < forward_y <= 0.505:
        safe_x = 0.70 - 8.0 * (forward_y - 0.48)
        safe_z = 0.18 - 4.2 * (forward_y - 0.48)
    else:
        safe_x = -float("inf")
        safe_z = -float("inf")
    result[0] = max(float(result[0]), safe_x)
    result[2] = max(float(result[2]), safe_z)
    return result


def mirrored_spec(source):
    result = deepcopy(source)
    for key in (
        "box_initial_position",
        "scripted_ee_initial_position",
        "middle_waypoint",
        "release_pose",
    ):
        result[key] = mirror_position(result[key]).tolist()
    return result


def configure_mirrored_scene(sim):
    pb.resetBasePositionAndOrientation(
        sim.panda, MIRRORED_BASE.tolist(), [0.0, 0.0, 0.0, 1.0]
    )
    obstacle_z = task.OBSTACLE_HEIGHT / 2.0
    pb.resetBasePositionAndOrientation(
        sim.obstacle_id,
        [MIRRORED_OBSTACLE[0], MIRRORED_OBSTACLE[1], obstacle_z],
        [0.0, 0.0, 0.0, 1.0],
    )
    pb.resetBaseVelocity(sim.obstacle_id, [0.0] * 3, [0.0] * 3)


def solve_pose(sim, position, quaternion, rest_arm=None):
    if rest_arm is None:
        q = np.asarray(sim.solve_ik(position, quaternion), dtype=float)
    else:
        sim.get_joint_limits()
        finger_rest = [
            float(pb.getJointState(sim.panda, joint)[0])
            for joint in (sim.left_finger_joint, sim.right_finger_joint)
        ]
        rest = np.asarray(list(rest_arm) + finger_rest, dtype=float)
        q = np.asarray(
            pb.calculateInverseKinematics(
                sim.panda,
                sim.ee_link_index,
                position,
                quaternion,
                lowerLimits=sim.ik_lower_limits,
                upperLimits=sim.ik_upper_limits,
                jointRanges=sim.ik_joint_ranges,
                restPoses=rest.tolist(),
                jointDamping=[0.2] * len(rest),
                maxNumIterations=500,
                residualThreshold=1e-6,
            )[:7],
            dtype=float,
        )
    if q.shape != (7,) or not np.isfinite(q).all():
        raise RuntimeError(f"Invalid IK result: {q}")
    sim.reset_arm_joints(q)
    realised = pb.getLinkState(
        sim.panda, sim.ee_link_index, computeForwardKinematics=True
    )
    error = float(np.linalg.norm(np.asarray(realised[0]) - np.asarray(position)))
    return q, error


def candidate_segment(
    sim,
    start_position,
    end_position,
    quaternion,
    start_q,
    start_gripper,
    end_gripper,
    subdivisions,
):
    sim.reset_arm_joints(start_q)
    previous_q = np.asarray(start_q, dtype=float)
    planned = []
    max_step = 0.0
    max_error = 0.0
    for index in range(1, subdivisions + 1):
        fraction = index / float(subdivisions)
        position = (
            (1.0 - fraction) * np.asarray(start_position)
            + fraction * np.asarray(end_position)
        )
        forward_y = -float(position[1])
        blend = float(np.clip((forward_y - 0.10) / 0.20, 0.0, 1.0))
        blend = blend * blend * (3.0 - 2.0 * blend)
        rest_arm = (1.0 - blend) * previous_q + blend * POST_OBSTACLE_IK_REST
        q, error = solve_pose(sim, position, quaternion, rest_arm=rest_arm)
        max_step = max(max_step, float(np.max(np.abs(q - previous_q))))
        max_error = max(max_error, error)
        planned.append(
            {
                "position": position,
                "q": q,
                "gripper_cmd": (1.0 - fraction) * float(start_gripper)
                + fraction * float(end_gripper),
            }
        )
        previous_q = q
    return planned, max_step, max_error


def plan_formal_trace(
    sim,
    formal_trace,
    quaternion,
    start_q,
    minimum_subdivisions,
    max_joint_step,
    max_subdivisions,
    max_ik_error,
):
    positions = [mirror_trace_position(row["ee_position"]) for row in formal_trace]
    grippers = [float(row["gripper_state"]) for row in formal_trace]
    planned = [
        {
            "position": positions[0],
            "q": np.asarray(start_q, dtype=float),
            "gripper_cmd": grippers[0],
        }
    ]
    subdivisions_used = []
    for trace_index in range(1, len(formal_trace)):
        subdivisions = int(minimum_subdivisions)
        while True:
            segment, joint_step, ik_error = candidate_segment(
                sim,
                positions[trace_index - 1],
                positions[trace_index],
                quaternion,
                planned[-1]["q"],
                grippers[trace_index - 1],
                grippers[trace_index],
                subdivisions,
            )
            if joint_step <= max_joint_step and ik_error <= max_ik_error:
                break
            subdivisions *= 2
            if subdivisions > max_subdivisions:
                raise RuntimeError(
                    f"Trace transition {trace_index - 1}->{trace_index} cannot be "
                    f"resolved smoothly: joint_step={joint_step:.6f}, "
                    f"ik_error={ik_error:.6f}"
                )
        planned.extend(segment)
        subdivisions_used.append(subdivisions)
    return planned, subdivisions_used


def replay_planned(sim, planned, output_hz, arm_max_velocity, settle_seconds):
    steps_per_output = int(round(sim.control_hz / float(output_hz)))
    if not math.isclose(steps_per_output * output_hz, sim.control_hz):
        raise ValueError("output-hz must divide simulator control_hz")
    tracking_errors = []
    first_contact = None
    for waypoint_index, waypoint in enumerate(planned[1:], start=1):
        finger_width = float(np.clip((1.0 - waypoint["gripper_cmd"]) * 0.02, 0.0, 0.04))
        for _ in range(steps_per_output):
            sim._apply_arm(
                waypoint["q"], force=120, max_vel=float(arm_max_velocity)
            )
            sim._apply_gripper(finger_width, force=120, max_vel=0.08)
            sim._step_simulation(sim.sim_dt)
        realised = pb.getLinkState(
            sim.panda, sim.ee_link_index, computeForwardKinematics=True
        )[0]
        tracking_errors.append(
            float(np.linalg.norm(np.asarray(realised) - waypoint["position"]))
        )
        contacts = pb.getContactPoints(bodyA=sim.panda, bodyB=sim.obstacle_id)
        if contacts and first_contact is None:
            first_contact = {
                "planned_waypoint_index": waypoint_index,
                "target_ee_position": waypoint["position"].tolist(),
                "robot_link_indices": sorted({int(contact[3]) for contact in contacts}),
            }
            print(f"First robot-obstacle contact: {first_contact}", flush=True)
    final = planned[-1]
    final_width = float(np.clip((1.0 - final["gripper_cmd"]) * 0.02, 0.0, 0.04))
    for _ in range(int(round(float(settle_seconds) * sim.control_hz))):
        sim._apply_arm(final["q"], force=120, max_vel=float(arm_max_velocity))
        sim._apply_gripper(final_width, force=120, max_vel=0.08)
        sim._step_simulation(sim.sim_dt)
    return tracking_errors, first_contact


def trajectory_stats(rows):
    q = np.asarray(
        [[float(row[f"q{joint}"]) for joint in range(7)] for row in rows]
    )
    dt = np.asarray([float(row["dt"]) for row in rows])
    steps = np.abs(np.diff(q, axis=0))
    return {
        "row_count": len(rows),
        "duration_seconds": float(rows[-1]["t"]),
        "max_adjacent_joint_step_rad": float(np.max(steps)),
        "max_implied_joint_velocity_rad_s": float(np.max(steps / dt[1:, None])),
        "gripper_cmd_min": min(float(row["gripper_cmd"]) for row in rows),
        "gripper_cmd_max": max(float(row["gripper_cmd"]) for row in rows),
        "gripper_width_min_m": min(float(row["gripper_width"]) for row in rows),
        "gripper_width_max_m": max(float(row["gripper_width"]) for row in rows),
    }


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-root",
        type=Path,
        default=REPO / "control_bimodal_replay/min_error_R",
    )
    parser.add_argument("--output-hz", type=float, default=30.0)
    parser.add_argument("--minimum-subdivisions", type=int, default=30)
    parser.add_argument("--max-planned-joint-step", type=float, default=0.015)
    parser.add_argument("--max-subdivisions", type=int, default=480)
    parser.add_argument("--max-ik-error", type=float, default=0.005)
    parser.add_argument("--arm-max-velocity", type=float, default=0.30)
    parser.add_argument("--settle-seconds", type=float, default=1.5)
    return parser.parse_args()


def main():
    args = parse_args()
    selection.configure_control_adapter()
    selected = selection.successful_r_candidates()[0]
    checkpoint_manifest, spec_manifest, spec_hash = replay.validate_manifests()
    participant = selected["participant_id"]
    checkpoint_record = checkpoint_manifest["checkpoints"][participant]
    original_path, original = replay.validate_selected_formal_result(
        "R", selected, checkpoint_record, spec_hash
    )
    spec = mirrored_spec(original["paired_spec"]["spec"])
    output_root = args.output_root.resolve()
    if output_root.exists() or output_root.is_symlink():
        raise FileExistsError(output_root)
    output_root.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_root.with_name(f".{output_root.name}.inprogress.{os.getpid()}")
    temporary.mkdir()
    route_dir = temporary / "R"
    route_dir.mkdir()

    sim = replay.JointTrajectoryRecordingSim(
        gui=False,
        output_dir=None,
        sample_hz=args.output_hz,
        record_hz=args.output_hz,
    )
    sim.playback_speed = 1000.0
    sim.setup()
    sim.default_orientation_quat = mirror_quaternion(
        sim.default_orientation_quat
    ).tolist()
    try:
        # First pass obtains the mirrored scripted-setup IK branch used as the
        # seed for sequential IK along the formal task-space trace.
        sim.reset_task_state(spec["box_initial_position"])
        configure_mirrored_scene(sim)
        setup_ok, setup_details = sim.scripted_grasp_to_transport_start(spec, save=False)
        if not setup_ok:
            raise RuntimeError(f"Mirrored scripted setup failed: {setup_details}")
        start_q = [
            float(pb.getJointState(sim.panda, joint)[0])
            for joint in sim.arm_joint_indices
        ]
        quaternion = mirror_quaternion(
            original["policy_inference_start"]["ee_quaternion_xyzw"]
        )
        planned, subdivisions = plan_formal_trace(
            sim,
            original["policy_step_trace"],
            quaternion,
            start_q,
            args.minimum_subdivisions,
            args.max_planned_joint_step,
            args.max_subdivisions,
            args.max_ik_error,
        )

        # Second pass is the authoritative PyBullet replay and joint/gripper
        # recording, beginning at the mirrored scripted initial EE pose.
        sim.reset_task_state(spec["box_initial_position"])
        configure_mirrored_scene(sim)
        sim.arm_recording_at_scripted_initial_pose()
        setup_ok, setup_details = sim.scripted_grasp_to_transport_start(spec, save=False)
        if not setup_ok:
            raise RuntimeError(f"Recorded mirrored scripted setup failed: {setup_details}")
        tracking_errors, first_contact = replay_planned(
            sim,
            planned,
            args.output_hz,
            args.arm_max_velocity,
            args.settle_seconds,
        )
        rows = sim.finish_recording()
        box_position = np.asarray(sim.cube_pos(), dtype=float)
        target_error = float(np.linalg.norm(box_position[:2] - MIRRORED_TARGET))
        _, obstacle_quat = pb.getBasePositionAndOrientation(sim.obstacle_id)
        cylinder_tilt = task.quaternion_upright_error_degrees(obstacle_quat)
        box_obstacle_contact_steps = int(sim._box_obstacle_contact_steps)
        robot_obstacle_contact_steps = int(sim._robot_obstacle_contact_steps)
    finally:
        if sim.client is not None:
            pb.disconnect(sim.client)

    if target_error > 0.10:
        raise RuntimeError(f"Mirrored task-space replay missed target: {target_error:.6f} m")
    if cylinder_tilt > task.CYLINDER_UPRIGHT_TOLERANCE_DEGREES:
        raise RuntimeError(
            f"Mirrored replay toppled cylinder: {cylinder_tilt:.6f} deg; "
            f"box contacts={box_obstacle_contact_steps}, "
            f"robot contacts={robot_obstacle_contact_steps}, "
            f"target_error={target_error:.6f} m"
        )
    csv_path = route_dir / "intervention.csv"
    replay.write_csv(csv_path, rows)
    stats = trajectory_stats(rows)
    metadata = {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "group": selection.GROUP,
        "selection": {
            "rule": "minimum target_xy_error among formal successful realised R rows",
            "participant_id": participant,
            "eval_case_id": int(selected["eval_case_id"]),
            "repeat_index": int(selected["repeat_index"]),
            "formal_target_xy_error_m": float(original["target_xy_error"]),
            "successful_r_candidate_count": len(selection.successful_r_candidates()),
        },
        "source": {
            "formal_result": str(original_path.resolve()),
            "formal_result_sha256": replay.sha256(original_path),
            "formal_policy_trace_samples": len(original["policy_step_trace"]),
            "formal_route": original["route_behavior"]["realised_route"],
            "checkpoint_sha256": checkpoint_record["sha256"],
            "paired_manifest_sha256": spec_hash,
        },
        "transform": {
            "position": (
                "formal world Cartesian EE position y := -y, followed by the "
                "documented post-obstacle x/z safety-corridor adjustment"
            ),
            "collision_clearance_adjustment": (
                "after crossing the cylinder, x is kept in a smooth >=0.70 m "
                "and z>=0.18 m clearance corridor, then blended back to the "
                "formal target pose after y=-0.48 m"
            ),
            "orientation": (
                "formal policy-start quaternion reflected as R'=S R S with "
                "S=diag(1,-1,1), then held constant because the formal trace "
                "stores EE position but not per-step EE quaternion"
            ),
            "robot_base_position": MIRRORED_BASE.tolist(),
            "obstacle_xy": MIRRORED_OBSTACLE.tolist(),
            "target_xy": MIRRORED_TARGET.tolist(),
        },
        "interpolation": {
            "output_hz": args.output_hz,
            "minimum_subdivisions_per_formal_transition": args.minimum_subdivisions,
            "maximum_subdivisions_used": max(subdivisions),
            "max_planned_joint_step_rad": args.max_planned_joint_step,
            "arm_max_velocity_rad_s": args.arm_max_velocity,
        },
        "pybullet_replay": {
            "mirrored_final_box_position": box_position.tolist(),
            "mirrored_target_xy_error_m": target_error,
            "final_cylinder_tilt_degrees": cylinder_tilt,
            "box_obstacle_contact_steps": box_obstacle_contact_steps,
            "robot_obstacle_contact_steps": robot_obstacle_contact_steps,
            "first_robot_obstacle_contact": first_contact,
            "max_ee_tracking_error_m": max(tracking_errors),
            "mean_ee_tracking_error_m": float(np.mean(tracking_errors)),
        },
        "output": {
            "intervention_csv": "R/intervention.csv",
            "intervention_csv_sha256": replay.sha256(csv_path),
            **stats,
        },
        "gripper": (
            "formal gripper_state interpolated as command; actual two-finger "
            "PyBullet joint-width sum recorded"
        ),
    }
    replay.write_json(route_dir / "reproduction.json", metadata)
    replay.write_json(temporary / "manifest.json", metadata)
    os.replace(temporary, output_root)
    print(json.dumps(metadata, indent=2, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
