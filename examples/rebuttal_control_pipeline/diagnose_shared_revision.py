#!/usr/bin/env python3
"""Non-formal Control probe of the combined shared setup/release revision."""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pybullet as pb


EXAMPLES_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EXAMPLES_ROOT))

RELEASE_XY_OFFSET = np.asarray([0.002, -0.002], dtype=float)
BOUNDARY_GRASP_OFFSET = np.asarray([0.004, -0.016, -0.005], dtype=float)

from main_obstacle_transport import (  # noqa: E402
    BOX_HALF_EXTENT,
    TRANSPORT_START_HEIGHT_TOLERANCE,
    ObstacleTransportSim,
)
from main_obstacle_transport_control_participants import (  # noqa: E402
    CONTROL_PARTICIPANTS,
    EXPERIMENT_GROUP,
    participant_task_spec,
)


class ProposedSharedRevisionSim(ObstacleTransportSim):
    """Diagnostic-only implementation; the shared class remains unmodified."""

    grasp_offset = np.asarray([0.004, -0.008, 0.005], dtype=float)
    boundary_grasp_offset = BOUNDARY_GRASP_OFFSET
    low_x_threshold = 0.23
    boundary_x_threshold = 0.25
    object_centered_release = False

    def reset_task_state(self, box_initial_position):
        super().reset_task_state(box_initial_position)
        self._diagnostic_release_compensation = None

    def move_ee_cartesian(
        self,
        target_pos,
        target_quat,
        speed,
        gripper_state,
        phase_name,
        save=False,
        max_segment_length=0.02,
    ):
        commanded_target = np.asarray(target_pos, dtype=float).copy()
        if phase_name == "policy_target_approach" and self.object_centered_release:
            box_xy = self.cube_pos()[:2]
            ee_xy = self.ee_pos()[:2]
            grasp_offset_xy = box_xy - ee_xy
            nominal_target = commanded_target.copy()
            commanded_target[:2] -= grasp_offset_xy
            self._diagnostic_release_compensation = {
                "nominal_release_pose": nominal_target.tolist(),
                "box_xy_before_target_approach": box_xy.tolist(),
                "ee_xy_before_target_approach": ee_xy.tolist(),
                "box_minus_ee_xy": grasp_offset_xy.tolist(),
                "commanded_object_centered_release_pose": commanded_target.tolist(),
            }
        return super().move_ee_cartesian(
            commanded_target,
            target_quat=target_quat,
            speed=speed,
            gripper_state=gripper_state,
            phase_name=phase_name,
            save=save,
            max_segment_length=max_segment_length,
        )

    def run_scripted_transport_and_release(self, *args, **kwargs):
        self._diagnostic_release_compensation = None
        success, details = super().run_scripted_transport_and_release(*args, **kwargs)
        details["diagnostic_object_centered_release"] = self._diagnostic_release_compensation
        return success, details

    def precise_initial_ik(self, position, quaternion):
        joints = pb.calculateInverseKinematics(
            self.panda,
            self.ee_link_index,
            position,
            targetOrientation=quaternion,
            maxNumIterations=1000,
            residualThreshold=1e-7,
        )
        return joints[: len(self.arm_joint_indices)]

    def precise_initial_reachable(self, position, quaternion, max_error=0.025):
        original = [pb.getJointState(self.panda, joint)[0] for joint in self.arm_joint_indices]
        q = self.precise_initial_ik(position, quaternion)
        self.reset_arm_joints(q)
        realised = self.ee_pos()
        self.reset_arm_joints(original)
        error = float(np.linalg.norm(realised - np.asarray(position, dtype=float)))
        return error <= max_error, error

    def scripted_grasp_to_transport_start(self, spec, save=False):
        box = np.asarray(spec["box_initial_position"], dtype=float)
        quaternion = self.default_orientation_quat
        initial_ee = np.asarray(spec["scripted_ee_initial_position"], dtype=float)
        pre_grasp = np.asarray([box[0], box[1], 0.16], dtype=float)
        nominal_grasp = np.asarray([box[0], box[1], 0.04], dtype=float)
        box_x = float(box[0])
        if box_x < self.low_x_threshold:
            active_grasp_offset = self.grasp_offset
            setup_strategy = "corrected_low_x"
        elif box_x < self.boundary_x_threshold:
            active_grasp_offset = self.boundary_grasp_offset
            setup_strategy = "corrected_boundary_x"
        else:
            active_grasp_offset = np.zeros(3, dtype=float)
            setup_strategy = "cartesian_nominal_non_low_x"
        grasp = nominal_grasp + active_grasp_offset
        transport_start = np.asarray([box[0], box[1], spec["transport_z"]], dtype=float)
        required = {
            "scripted_ee_initial": initial_ee,
            "pre_grasp": pre_grasp,
            "grasp": grasp,
            "transport_start": transport_start,
        }
        initial_reachable, initial_error = self.precise_initial_reachable(
            initial_ee, quaternion
        )
        unreachable = [] if initial_reachable else ["scripted_ee_initial"]
        unreachable.extend(
            name
            for name, point in required.items()
            if name != "scripted_ee_initial"
            and not self.ik_reachable(
                point,
                quaternion,
                max_error=0.04 if name == "grasp" else 0.025,
            )
        )
        if unreachable:
            return False, {
                "stage": "scripted_setup",
                "reason": "unreachable_waypoint",
                "unreachable": unreachable,
                "precise_initial_ik_error": initial_error,
                "required_waypoints": {
                    name: point.tolist() for name, point in required.items()
                },
            }

        initial_q = self.precise_initial_ik(initial_ee, quaternion)
        self.reset_to_ee_pose(initial_q, gripper_width=0.04)
        self.move_ee_cartesian(
            pre_grasp,
            target_quat=quaternion,
            speed=self.motion_speed,
            gripper_state=-1.0,
            phase_name="scripted_pre_grasp",
            save=save,
        )
        self.move_ee_cartesian(
            grasp,
            target_quat=quaternion,
            speed=0.06,
            gripper_state=-1.0,
            phase_name="scripted_grasp",
            save=save,
        )
        self.command_gripper(
            width=0.0,
            duration=1.0,
            gripper_state=1.0,
            phase_name="scripted_close",
            save=save,
        )
        self.move_ee_cartesian(
            transport_start,
            target_quat=quaternion,
            speed=0.06,
            gripper_state=1.0,
            phase_name="transport_start",
            save=save,
        )
        cube_position = self.cube_pos()
        ee_position = self.ee_pos()
        grasped = bool(cube_position[2] >= BOX_HALF_EXTENT + 0.015)
        height_error = abs(float(ee_position[2]) - float(transport_start[2]))
        height_reached = height_error <= TRANSPORT_START_HEIGHT_TOLERANCE
        setup_success = bool(grasped and height_reached)
        if not grasped:
            reason = "box_not_lifted"
        elif not height_reached:
            reason = "transport_height_not_reached"
        else:
            reason = None
        return setup_success, {
            "stage": "scripted_setup",
            "reason": reason,
            "grasped": grasped,
            "transport_height_reached": height_reached,
            "transport_height_error": height_error,
            "transport_height_tolerance": TRANSPORT_START_HEIGHT_TOLERANCE,
            "precise_initial_ik_error": initial_error,
            "setup_motion": "cartesian_segments",
            "setup_strategy": setup_strategy,
            "low_x_threshold": self.low_x_threshold,
            "boundary_x_threshold": self.boundary_x_threshold,
            "boundary_grasp_offset": self.boundary_grasp_offset.tolist(),
            "nominal_grasp": nominal_grasp.tolist(),
            "grasp_offset": active_grasp_offset.tolist(),
            "required_waypoints": {
                name: point.tolist() for name, point in required.items()
            },
            "box_position_after_lift": cube_position.tolist(),
            "ee_position_after_lift": ee_position.tolist(),
            "transport_start": transport_start.tolist(),
        }


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--participants", nargs="+", default=list(CONTROL_PARTICIPANTS))
    demos = parser.add_mutually_exclusive_group()
    demos.add_argument("--demo-indices", nargs="+", type=int)
    demos.add_argument("--all-30", action="store_true")
    parser.add_argument("--seed", type=int, default=20260806)
    parser.add_argument("--release-z", type=float, default=0.08)
    parser.add_argument("--max-attempts", type=int, default=30)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main():
    args = parse_args()
    unknown = sorted(set(args.participants) - set(CONTROL_PARTICIPANTS))
    if unknown:
        raise ValueError(f"unknown Control participants: {unknown}")
    demo_indices = list(range(30)) if args.all_30 else (args.demo_indices or [17, 18, 28])
    if any(index < 0 or index >= 30 for index in demo_indices):
        raise ValueError(f"demo indices must be in [0, 29]: {demo_indices}")

    sim = ProposedSharedRevisionSim(gui=False, output_dir=None, sample_hz=8.0)
    sim.playback_speed = 1000.0
    sim.setup()
    cases = []
    attempts = []
    try:
        for participant_id in args.participants:
            for demo_index in demo_indices:
                accepted = None
                for attempt_index in range(args.max_attempts):
                    spec = participant_task_spec(
                        participant_id,
                        demo_index,
                        attempt_index,
                        args.seed,
                    )
                    original_release_z = float(spec["release_pose"][2])
                    nominal_release_xy = list(spec["release_pose"][:2])
                    spec["release_pose"][:2] = (
                        np.asarray(spec["release_pose"][:2], dtype=float)
                        + RELEASE_XY_OFFSET
                    ).tolist()
                    spec["release_pose"][2] = float(args.release_z)
                    spec["diagnostic_override"] = {
                        "formal_data": False,
                        "shared_change_request": "SCR-001/SCR-C001",
                        "original_release_z": original_release_z,
                        "proposed_release_z": float(args.release_z),
                        "nominal_release_xy": nominal_release_xy,
                        "release_xy_offset": RELEASE_XY_OFFSET.tolist(),
                        "precise_initial_ik": True,
                        "cartesian_scripted_setup": True,
                        "grasp_offset": sim.grasp_offset.tolist(),
                        "boundary_grasp_offset": sim.boundary_grasp_offset.tolist(),
                        "adaptive_low_x_setup": True,
                        "low_x_threshold": sim.low_x_threshold,
                        "boundary_x_threshold": sim.boundary_x_threshold,
                        "object_centered_release": sim.object_centered_release,
                    }
                    sim.reset_task_state(spec["box_initial_position"])
                    success, details = sim.run_scripted_transport_and_release(
                        spec,
                        save=False,
                        demo_index=demo_index,
                    )
                    attempt = {
                        "group": EXPERIMENT_GROUP,
                        "formal_data": False,
                        "participant_id": participant_id,
                        "demo_index": demo_index,
                        "attempt_index": attempt_index,
                        "success": bool(success),
                        "spec": spec,
                        "details": details,
                    }
                    attempts.append(attempt)
                    if success:
                        accepted = attempt
                        break
                cases.append(
                    {
                        "participant_id": participant_id,
                        "route": CONTROL_PARTICIPANTS[participant_id]["route"],
                        "demo_index": demo_index,
                        "success": accepted is not None,
                        "accepted_attempt_index": (
                            accepted["attempt_index"] if accepted is not None else None
                        ),
                        "accepted": accepted,
                    }
                )
    finally:
        if sim.client is not None:
            pb.disconnect(sim.client)

    report = {
        "group": EXPERIMENT_GROUP,
        "formal_data": False,
        "diagnostic": "proposed_shared_setup_and_release_revision",
        "shared_change_request": "SCR-001/SCR-C001",
        "seed": args.seed,
        "participant_order": list(args.participants),
        "demo_indices": demo_indices,
        "release_z": args.release_z,
        "release_xy_offset": RELEASE_XY_OFFSET.tolist(),
        "precise_initial_ik": True,
        "cartesian_scripted_setup": True,
        "grasp_offset": sim.grasp_offset.tolist(),
        "boundary_grasp_offset": sim.boundary_grasp_offset.tolist(),
        "adaptive_low_x_setup": True,
        "low_x_threshold": sim.low_x_threshold,
        "boundary_x_threshold": sim.boundary_x_threshold,
        "object_centered_release": sim.object_centered_release,
        "successful_cases": sum(row["success"] for row in cases),
        "case_count": len(cases),
        "cases": cases,
        "attempts": attempts,
    }
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(output)
    print(
        f"participants={len(args.participants)} demos={len(demo_indices)} "
        f"successes={report['successful_cases']}/{report['case_count']}"
    )
    if report["successful_cases"] != report["case_count"]:
        raise SystemExit("combined shared-revision diagnostic did not pass all cases")


if __name__ == "__main__":
    main()
