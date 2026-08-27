#!/usr/bin/env python3
"""Non-formal Control probe for the two frozen low-x scripted-setup failures."""

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
import pybullet as pb


EXAMPLES_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EXAMPLES_ROOT))

from main_obstacle_transport import BOX_HALF_EXTENT, ObstacleTransportSim  # noqa: E402
from main_obstacle_transport_control_participants import participant_task_spec  # noqa: E402


GROUP = "simulation_control_group"
SEED = 20260806


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def pose(sim):
    cube_position, cube_quaternion = pb.getBasePositionAndOrientation(sim.cube_id)
    link = pb.getLinkState(sim.panda, sim.ee_link_index, computeForwardKinematics=True)
    finger_positions = {
        "left": list(pb.getLinkState(sim.panda, sim.left_finger_joint)[0]),
        "right": list(pb.getLinkState(sim.panda, sim.right_finger_joint)[0]),
    }
    return {
        "cube_position": cube_position,
        "cube_quaternion_xyzw": list(cube_quaternion),
        "ee_position": list(link[0]),
        "ee_quaternion_xyzw": list(link[1]),
        "finger_positions": finger_positions,
        "cube_robot_contact_count": len(pb.getContactPoints(bodyA=sim.cube_id, bodyB=sim.panda)),
    }


def quaternion_error_degrees(left, right):
    dot = abs(float(np.dot(np.asarray(left, dtype=float), np.asarray(right, dtype=float))))
    return math.degrees(2.0 * math.acos(float(np.clip(dot, -1.0, 1.0))))


def evaluate_q(sim, q, target_position, target_quaternion):
    original = [pb.getJointState(sim.panda, joint)[0] for joint in sim.arm_joint_indices]
    sim.reset_arm_joints(q)
    realised = pb.getLinkState(sim.panda, sim.ee_link_index, computeForwardKinematics=True)
    result = {
        "q": [float(value) for value in q],
        "realised_position": list(realised[0]),
        "realised_quaternion_xyzw": list(realised[1]),
        "position_error": float(
            np.linalg.norm(np.asarray(realised[0], dtype=float) - np.asarray(target_position, dtype=float))
        ),
        "orientation_error_degrees": quaternion_error_degrees(realised[1], target_quaternion),
    }
    sim.reset_arm_joints(original)
    return result


def ik_landscape(sim, target_position, target_quaternion, rng):
    sim.get_joint_limits()
    current_full = [pb.getJointState(sim.panda, joint)[0] for joint in sim.ik_joint_indices]
    candidates = []

    unconstrained = pb.calculateInverseKinematics(
        sim.panda,
        sim.ee_link_index,
        target_position,
        targetOrientation=target_quaternion,
        maxNumIterations=1000,
        residualThreshold=1e-7,
    )
    row = evaluate_q(sim, unconstrained[: len(sim.arm_joint_indices)], target_position, target_quaternion)
    row["candidate"] = "unconstrained_1000"
    candidates.append(row)

    rest_poses = [("current", current_full)]
    midpoint = [
        (float(lower) + float(upper)) / 2.0
        for lower, upper in zip(sim.ik_lower_limits, sim.ik_upper_limits)
    ]
    rest_poses.append(("joint_limit_midpoint", midpoint))
    home = list(sim.home_q) + [0.04, 0.04]
    rest_poses.append(("home", home))
    for index in range(32):
        sampled = [
            float(rng.uniform(lower, upper))
            for lower, upper in zip(sim.ik_lower_limits, sim.ik_upper_limits)
        ]
        rest_poses.append((f"random_{index:02d}", sampled))

    for name, rest in rest_poses:
        q = pb.calculateInverseKinematics(
            sim.panda,
            sim.ee_link_index,
            target_position,
            target_quaternion,
            lowerLimits=sim.ik_lower_limits,
            upperLimits=sim.ik_upper_limits,
            jointRanges=sim.ik_joint_ranges,
            restPoses=rest,
            jointDamping=[0.2] * len(sim.ik_joint_indices),
            maxNumIterations=1000,
            residualThreshold=1e-7,
        )
        row = evaluate_q(sim, q[: len(sim.arm_joint_indices)], target_position, target_quaternion)
        row["candidate"] = name
        candidates.append(row)
    candidates.sort(key=lambda row: (row["position_error"], row["orientation_error_degrees"]))
    return {
        "target_position": list(target_position),
        "target_quaternion_xyzw": list(target_quaternion),
        "candidate_count": len(candidates),
        "best": candidates[0],
        "within_original_0.025_tolerance": candidates[0]["position_error"] <= 0.025,
        "candidates": candidates,
    }


def custom_setup(sim, spec, initial_q, grasp_offset, motion_method="joint_interpolation"):
    box = np.asarray(spec["box_initial_position"], dtype=float)
    quaternion = sim.default_orientation_quat
    initial = np.asarray(spec["scripted_ee_initial_position"], dtype=float)
    pre_grasp = np.asarray([box[0], box[1], 0.16], dtype=float)
    grasp = np.asarray([box[0], box[1], 0.04], dtype=float) + np.asarray(grasp_offset, dtype=float)
    transport = np.asarray([box[0], box[1], spec["transport_z"]], dtype=float)
    sim.reset_task_state(box)
    if initial_q is None:
        initial_q = sim.solve_ik(initial, quaternion)
    sim.reset_to_ee_pose(initial_q, gripper_width=0.04)
    trace = {"after_initial_reset": pose(sim)}
    if motion_method == "joint_interpolation":
        move = sim.move_ee
    elif motion_method == "cartesian_segments":
        move = sim.move_ee_cartesian
    else:
        raise ValueError(f"unknown motion method: {motion_method}")
    move(
        pre_grasp,
        target_quat=quaternion,
        speed=sim.motion_speed,
        gripper_state=-1.0,
        phase_name="probe_pre_grasp",
        save=False,
    )
    trace["after_pre_grasp"] = pose(sim)
    move(
        grasp,
        target_quat=quaternion,
        speed=0.06,
        gripper_state=-1.0,
        phase_name="probe_grasp",
        save=False,
    )
    trace["before_close"] = pose(sim)
    sim.command_gripper(
        width=0.0,
        duration=1.0,
        gripper_state=1.0,
        phase_name="probe_close",
        save=False,
    )
    trace["after_close"] = pose(sim)
    move(
        transport,
        target_quat=quaternion,
        speed=0.06,
        gripper_state=1.0,
        phase_name="probe_transport_start",
        save=False,
    )
    trace["after_lift"] = pose(sim)
    cube_height = float(trace["after_lift"]["cube_position"][2])
    return {
        "motion_method": motion_method,
        "grasp_offset": list(grasp_offset),
        "initial_target": initial.tolist(),
        "pre_grasp_target": pre_grasp.tolist(),
        "grasp_target": grasp.tolist(),
        "transport_target": transport.tolist(),
        "box_lifted": cube_height >= BOX_HALF_EXTENT + 0.015,
        "cube_height_after_lift": cube_height,
        "trace": trace,
    }


def main():
    args = parse_args()
    sim = ObstacleTransportSim(gui=False, output_dir=None, sample_hz=8.0)
    sim.playback_speed = 1000.0
    sim.setup()
    rng = np.random.default_rng(SEED)
    report = {
        "group": GROUP,
        "formal_data": False,
        "diagnostic": "low_x_scripted_setup_probe",
        "seed": SEED,
        "shared_change_request": "SCR-001/SCR-C001",
        "preserved": {
            "fixed_orientation": True,
            "scripted_timing": True,
            "cube_starts": True,
            "initial_ee_target": True,
        },
    }
    try:
        specifications = {
            str(demo_index): participant_task_spec("C01", demo_index, 0, SEED)
            for demo_index in (18, 28)
        }
        landscapes = {}
        for demo_index in (18, 28):
            spec = specifications[str(demo_index)]
            sim.reset_task_state(spec["box_initial_position"])
            landscapes[str(demo_index)] = ik_landscape(
                sim,
                spec["scripted_ee_initial_position"],
                sim.default_orientation_quat,
                rng,
            )
        report["initial_ee_ik_landscapes"] = landscapes

        setup_trials = {"18": [], "28": []}
        for demo_index in (18, 28):
            spec = specifications[str(demo_index)]
            best_q = landscapes[str(demo_index)]["best"]["q"]
            setup_trials[str(demo_index)].append(
                {
                    "initial_ik": "original",
                    **custom_setup(
                        sim,
                        spec,
                        initial_q=None,
                        grasp_offset=[0.0, 0.0, 0.0],
                    ),
                }
            )
            setup_trials[str(demo_index)].append(
                {
                    "initial_ik": "best_multistart",
                    **custom_setup(sim, spec, initial_q=best_q, grasp_offset=[0.0, 0.0, 0.0]),
                }
            )
            setup_trials[str(demo_index)].append(
                {
                    "initial_ik": "best_multistart",
                    **custom_setup(
                        sim,
                        spec,
                        initial_q=best_q,
                        grasp_offset=[0.0, 0.0, 0.0],
                        motion_method="cartesian_segments",
                    ),
                }
            )
            for y_offset in (-0.012, -0.008, -0.004, 0.004, 0.008, 0.012):
                for z_offset in (-0.010, -0.005, 0.0, 0.005):
                    setup_trials[str(demo_index)].append(
                        {
                            "initial_ik": "best_multistart",
                            **custom_setup(
                                sim,
                                spec,
                                initial_q=best_q,
                                grasp_offset=[0.0, y_offset, z_offset],
                            ),
                        }
                    )
            for x_offset in (0.004, 0.008, 0.012):
                for y_offset in (-0.016, -0.012, -0.008):
                    for z_offset in (-0.005, 0.0, 0.005):
                        setup_trials[str(demo_index)].append(
                            {
                                "initial_ik": "best_multistart",
                                **custom_setup(
                                    sim,
                                    spec,
                                    initial_q=best_q,
                                    grasp_offset=[x_offset, y_offset, z_offset],
                                    motion_method="cartesian_segments",
                                ),
                            }
                        )
        report["setup_trials"] = setup_trials
        report["successful_setup_trials"] = {
            demo_index: [
                {
                    "initial_ik": row["initial_ik"],
                    "motion_method": row["motion_method"],
                    "grasp_offset": row["grasp_offset"],
                    "cube_height_after_lift": row["cube_height_after_lift"],
                }
                for row in rows
                if row["box_lifted"]
            ]
            for demo_index, rows in setup_trials.items()
        }
    finally:
        if sim.client is not None:
            pb.disconnect(sim.client)

    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(output)
    print(json.dumps(report["successful_setup_trials"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
