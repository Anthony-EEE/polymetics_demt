#!/usr/bin/env python3
"""Scripted obstacle-transport demonstrations for the CoRL rebuttal.

The learned-policy portion of this task starts *after* a scripted, fixed-
orientation grasp.  This collector nevertheless executes the complete task so
that every retained transport/release trajectory is known to be successful.
"""

import argparse
import json
import math
import shutil
from pathlib import Path

import numpy as np
import pybullet as pb

from main_abla_1 import PandaSim


CONDITIONS = ("L", "R")
EXPERIMENT_GROUP = "simulation_target_group"
BOX_HALF_EXTENT = 0.035
BOX_INITIAL_Z = 0.025
BOX_START_X_BOUNDS = (0.20, 0.80)
BOX_START_Y_BOUNDS = (-0.01, 0.01)
OBSTACLE_XY = (0.50, 0.25)
OBSTACLE_RADIUS = 0.04
OBSTACLE_HEIGHT = 0.30
TARGET_XY = (0.50, 0.50)
WAYPOINT_X_CENTERS = {"L": 0.20, "R": 0.80}
WAYPOINT_X_NOISE = 0.10
TRANSPORT_Z_CENTER = 0.24
TRANSPORT_Z_NOISE = 0.05
RELEASE_Z = 0.08
TARGET_XY_TOLERANCE = 0.03
CYLINDER_UPRIGHT_TOLERANCE_DEGREES = 10.0
TRANSPORT_START_HEIGHT_TOLERANCE = 0.015
WAYPOINT_REACH_TOLERANCE = 0.04
PANDA_BASE_POSITION = (0.0, 0.15, 0.0)
FIXED_GRIPPER_PITCH_DEGREES = -10.0


def sample_area_uniform_ellipse(rng, x_radius=WAYPOINT_X_NOISE, z_radius=TRANSPORT_Z_NOISE):
    """Sample an area-uniform point in the requested x-z ellipse."""
    radius = math.sqrt(float(rng.uniform(0.0, 1.0)))
    theta = float(rng.uniform(0.0, 2.0 * math.pi))
    return {
        "radial_latent": radius,
        "theta_rad": theta,
        "x_delta": float(x_radius) * radius * math.cos(theta),
        "z_delta": float(z_radius) * radius * math.sin(theta),
    }


def sample_task_spec(rng, condition, attempt_index):
    if condition not in CONDITIONS:
        raise ValueError(f"Unknown condition {condition!r}; choose from {CONDITIONS}")
    ellipse = sample_area_uniform_ellipse(rng)
    waypoint_x_center = WAYPOINT_X_CENTERS[condition]
    box_x = float(rng.uniform(*BOX_START_X_BOUNDS))
    box_y = float(rng.uniform(*BOX_START_Y_BOUNDS))
    transport_z = TRANSPORT_Z_CENTER + ellipse["z_delta"]
    return {
        "attempt_index": int(attempt_index),
        "condition": condition,
        "box_initial_position": [box_x, box_y, BOX_INITIAL_Z],
        # Initialise directly above the sampled cube. There is no horizontal
        # x/y offset; the only offset is +0.10 m in z.
        "scripted_ee_initial_position": [box_x, box_y, BOX_INITIAL_Z + 0.10],
        "waypoint_x_center": float(waypoint_x_center),
        "waypoint_sampling": ellipse,
        "middle_waypoint": [
            waypoint_x_center + ellipse["x_delta"],
            OBSTACLE_XY[1],
            transport_z,
        ],
        "transport_z": float(transport_z),
        "release_pose": [TARGET_XY[0], TARGET_XY[1], RELEASE_Z],
    }


def quaternion_upright_error_degrees(quat_xyzw):
    rotation = pb.getMatrixFromQuaternion(quat_xyzw)
    local_z_world = np.asarray([rotation[2], rotation[5], rotation[8]], dtype=float)
    cosine = float(np.clip(local_z_world[2] / max(np.linalg.norm(local_z_world), 1e-12), -1.0, 1.0))
    return math.degrees(math.acos(cosine))


class ObstacleTransportSim(PandaSim):
    """Panda task with a dynamic upright cylinder and drop target."""

    def __init__(self, gui=False, output_dir=None, sample_hz=8.0):
        self.obstacle_id = None
        self.target_marker_id = None
        self._box_initial_position = np.asarray([0.40, 0.0, BOX_INITIAL_Z], dtype=float)
        self._obstacle_initial_position = np.asarray(
            [OBSTACLE_XY[0], OBSTACLE_XY[1], OBSTACLE_HEIGHT / 2.0], dtype=float
        )
        self._sim_step_count = 0
        self._video_writer = None
        self._video_every_sim_steps = 24
        self._box_obstacle_contact_steps = 0
        self._robot_obstacle_contact_steps = 0
        self._maximum_cylinder_tilt_degrees = 0.0
        self._box_trace = []
        self._ee_trace = []
        super().__init__(
            gui=gui,
            left_handed=False,
            gripper_orientation="default",
            output_dir=output_dir,
            sample_hz=sample_hz,
        )
        self.default_orientation_quat = pb.getQuaternionFromEuler(
            [-math.pi, math.radians(FIXED_GRIPPER_PITCH_DEGREES), 0.0]
        )
        # The rebuttal task extends farther toward x=0 and y=0.8 than the old
        # pick-and-lift crop.
        self.crop_min = np.asarray([0.10, -0.20, 0.005], dtype=float)
        self.crop_max = np.asarray([0.90, 0.65, 0.50], dtype=float)

    def _camera_setup(self):
        self.camera_eye = [-0.35, 0.25, 0.70]
        self.camera_target = [0.48, 0.25, 0.05]
        self.camera_up = [0.0, 0.0, 1.0]
        self.image_width = 240
        self.image_height = 240
        self.camera_near = 0.01
        self.camera_far = 1.60
        self.camera_fov = 75.0
        self.camera_aspect = 1.0
        self.proj_mat = pb.computeProjectionMatrixFOV(
            fov=self.camera_fov,
            aspect=self.camera_aspect,
            nearVal=self.camera_near,
            farVal=self.camera_far,
        )
        self.view_mat = pb.computeViewMatrix(
            cameraEyePosition=self.camera_eye,
            cameraTargetPosition=self.camera_target,
            cameraUpVector=self.camera_up,
        )
        self.camera_intrinsic = self._get_camera_intrinsics(
            self.proj_mat,
            self.image_width,
            self.image_height,
        )

    def _spawn_cube(self):
        collision = pb.createCollisionShape(
            pb.GEOM_BOX,
            halfExtents=[BOX_HALF_EXTENT] * 3,
        )
        visual = pb.createVisualShape(
            pb.GEOM_BOX,
            halfExtents=[BOX_HALF_EXTENT] * 3,
            rgbaColor=[0.95, 0.20, 0.12, 1.0],
        )
        cube_id = pb.createMultiBody(
            baseMass=0.05,
            baseCollisionShapeIndex=collision,
            baseVisualShapeIndex=visual,
            basePosition=self._box_initial_position.tolist(),
            baseOrientation=[0.0, 0.0, 0.0, 1.0],
        )
        pb.changeDynamics(
            cube_id,
            -1,
            lateralFriction=1.2,
            spinningFriction=0.02,
            rollingFriction=0.0001,
            restitution=0.0,
        )
        return cube_id

    def setup(self):
        super().setup()
        pb.resetBasePositionAndOrientation(
            self.panda,
            PANDA_BASE_POSITION,
            [0.0, 0.0, 0.0, 1.0],
        )
        obstacle_collision = pb.createCollisionShape(
            pb.GEOM_CYLINDER,
            radius=OBSTACLE_RADIUS,
            height=OBSTACLE_HEIGHT,
        )
        obstacle_visual = pb.createVisualShape(
            pb.GEOM_CYLINDER,
            radius=OBSTACLE_RADIUS,
            length=OBSTACLE_HEIGHT,
            rgbaColor=[0.15, 0.35, 0.95, 1.0],
        )
        self.obstacle_id = pb.createMultiBody(
            baseMass=0.08,
            baseCollisionShapeIndex=obstacle_collision,
            baseVisualShapeIndex=obstacle_visual,
            basePosition=self._obstacle_initial_position.tolist(),
            baseOrientation=[0.0, 0.0, 0.0, 1.0],
        )
        pb.changeDynamics(
            self.obstacle_id,
            -1,
            lateralFriction=0.70,
            spinningFriction=0.01,
            rollingFriction=0.0001,
            restitution=0.0,
        )
        target_visual = pb.createVisualShape(
            pb.GEOM_CYLINDER,
            radius=TARGET_XY_TOLERANCE,
            length=0.004,
            rgbaColor=[0.10, 0.85, 0.20, 0.55],
        )
        self.target_marker_id = pb.createMultiBody(
            baseMass=0.0,
            baseVisualShapeIndex=target_visual,
            basePosition=[TARGET_XY[0], TARGET_XY[1], 0.002],
        )
        self.reset_task_state(self._box_initial_position)

    def reset_task_state(self, box_initial_position):
        self._box_initial_position = np.asarray(box_initial_position, dtype=float)
        self.reset()
        pb.resetBasePositionAndOrientation(
            self.cube_id,
            self._box_initial_position.tolist(),
            [0.0, 0.0, 0.0, 1.0],
        )
        pb.resetBaseVelocity(self.cube_id, [0.0, 0.0, 0.0], [0.0, 0.0, 0.0])
        if self.obstacle_id is not None:
            pb.resetBasePositionAndOrientation(
                self.obstacle_id,
                self._obstacle_initial_position.tolist(),
                [0.0, 0.0, 0.0, 1.0],
            )
            pb.resetBaseVelocity(self.obstacle_id, [0.0, 0.0, 0.0], [0.0, 0.0, 0.0])
        self._box_obstacle_contact_steps = 0
        self._robot_obstacle_contact_steps = 0
        self._maximum_cylinder_tilt_degrees = 0.0
        self._box_trace = []
        self._ee_trace = []
        self._phase_final_errors = {}
        for _ in range(120):
            self._apply_arm(self.home_q, force=120, max_vel=1.5)
            self._apply_gripper(0.04, force=60, max_vel=0.08)
            self._step_simulation(self.sim_dt)

    def _step_simulation(self, sleep_dt):
        super()._step_simulation(sleep_dt)
        self._sim_step_count += 1
        if self.obstacle_id is not None:
            if pb.getContactPoints(bodyA=self.cube_id, bodyB=self.obstacle_id):
                self._box_obstacle_contact_steps += 1
            if pb.getContactPoints(bodyA=self.panda, bodyB=self.obstacle_id):
                self._robot_obstacle_contact_steps += 1
            _, obstacle_quat = pb.getBasePositionAndOrientation(self.obstacle_id)
            self._maximum_cylinder_tilt_degrees = max(
                self._maximum_cylinder_tilt_degrees,
                quaternion_upright_error_degrees(obstacle_quat),
            )
        if self.panda is not None and self.cube_id is not None:
            self._box_trace.append(self.cube_pos().tolist())
            self._ee_trace.append(self.ee_pos().tolist())
        if self._video_writer is not None and self._sim_step_count % self._video_every_sim_steps == 0:
            self._video_writer.append_data(self.render_overview())

    def render_overview(self, width=480, height=480):
        view = pb.computeViewMatrixFromYawPitchRoll(
            cameraTargetPosition=[0.48, 0.25, 0.06],
            distance=0.95,
            yaw=0.0,
            pitch=-62.0,
            roll=0.0,
            upAxisIndex=2,
        )
        projection = pb.computeProjectionMatrixFOV(
            fov=62.0,
            aspect=float(width) / float(height),
            nearVal=0.01,
            farVal=2.0,
        )
        image = pb.getCameraImage(
            width,
            height,
            viewMatrix=view,
            projectionMatrix=projection,
            renderer=pb.ER_TINY_RENDERER,
        )
        rgba = np.asarray(image[2], dtype=np.uint8).reshape(height, width, 4)
        return rgba[:, :, :3]

    def start_video(self, path, fps=10):
        import imageio.v2 as imageio

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._video_writer = imageio.get_writer(str(path), fps=int(fps))
        self._video_writer.append_data(self.render_overview())

    def close_video(self):
        if self._video_writer is not None:
            self._video_writer.append_data(self.render_overview())
            self._video_writer.close()
            self._video_writer = None

    def command_gripper(self, width, duration, gripper_state, phase_name, save=False):
        steps = max(1, int(math.ceil(float(duration) * self.control_hz)))
        capture_accum = 0.0
        for _ in range(steps):
            max_velocity = 0.08 if float(width) >= 0.03 else 0.04
            self._apply_gripper(width, force=120, max_vel=max_velocity)
            self._step_simulation(self.sim_dt)
            capture_accum += self.sim_dt
            self.capture_time += self.sim_dt
            if save and self.demo_dir is not None:
                while capture_accum + 1e-12 >= self.sample_period:
                    capture_accum -= self.sample_period
                    self.save_frame(
                        gripper_state=gripper_state,
                        phase_name=phase_name,
                        commanded_dt=self.sample_period,
                    )

    def hold_pose(self, target_pos, target_quat, width, duration, gripper_state, phase_name, save=False):
        q = self.solve_ik(target_pos, target_quat)
        steps = max(1, int(math.ceil(float(duration) * self.control_hz)))
        capture_accum = 0.0
        for _ in range(steps):
            self._apply_arm(q, force=120, max_vel=1.5)
            self._apply_gripper(width, force=120, max_vel=0.08)
            self._step_simulation(self.sim_dt)
            capture_accum += self.sim_dt
            self.capture_time += self.sim_dt
            if save and self.demo_dir is not None:
                while capture_accum + 1e-12 >= self.sample_period:
                    capture_accum -= self.sample_period
                    self.save_frame(
                        gripper_state=gripper_state,
                        phase_name=phase_name,
                        commanded_dt=self.sample_period,
                    )

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
        """Approximate a straight Cartesian segment with short sequential IK moves."""
        target_pos = np.asarray(target_pos, dtype=float)
        start_pos = self.ee_pos()
        distance = float(np.linalg.norm(target_pos - start_pos))
        segment_count = max(1, int(math.ceil(distance / float(max_segment_length))))
        capture_accum = 0.0
        gripper_width = 0.0 if float(gripper_state) >= 0.0 else 0.04
        for segment_index in range(segment_count):
            alpha = float(segment_index + 1) / float(segment_count)
            segment_target = (1.0 - alpha) * start_pos + alpha * target_pos
            q_goal = self.solve_ik(segment_target, target_quat)
            q_start = [pb.getJointState(self.panda, joint)[0] for joint in self.arm_joint_indices]
            segment_distance = float(np.linalg.norm(segment_target - self.ee_pos()))
            segment_duration = max(segment_distance / float(speed), 1.0 / self.frequency)
            steps = max(1, int(math.ceil(segment_duration * self.control_hz)))
            for step_index in range(steps):
                beta = float(step_index + 1) / float(steps)
                q_command = [
                    (1.0 - beta) * q0 + beta * q1
                    for q0, q1 in zip(q_start, q_goal)
                ]
                self._apply_arm(q_command, force=120, max_vel=1.5)
                self._apply_gripper(gripper_width, force=120, max_vel=0.08)
                self._step_simulation(self.sim_dt)
                capture_accum += self.sim_dt
                self.capture_time += self.sim_dt
                if save and self.demo_dir is not None:
                    while capture_accum + 1e-12 >= self.sample_period:
                        capture_accum -= self.sample_period
                        self.save_frame(
                            gripper_state=gripper_state,
                            phase_name=phase_name,
                            commanded_speed=speed,
                            commanded_dt=self.sample_period,
                        )
        realised_error = float(np.linalg.norm(self.ee_pos() - target_pos))
        self._phase_final_errors[phase_name] = realised_error
        print(
            f"  move_ee_cartesian phase={phase_name}, segments={segment_count}, "
            f"distance={distance:.4f} m, final_error={realised_error:.5f} m",
            flush=True,
        )

    def scripted_grasp_to_transport_start(self, spec, save=False):
        box = np.asarray(spec["box_initial_position"], dtype=float)
        quat = self.default_orientation_quat
        initial_ee = np.asarray(spec["scripted_ee_initial_position"], dtype=float)
        pre_grasp = np.asarray([box[0], box[1], 0.16], dtype=float)
        grasp = np.asarray([box[0], box[1], 0.04], dtype=float)
        transport_start = np.asarray([box[0], box[1], spec["transport_z"]], dtype=float)

        required = {
            "scripted_ee_initial": initial_ee,
            "pre_grasp": pre_grasp,
            "grasp": grasp,
            "transport_start": transport_start,
        }
        unreachable = [
            name
            for name, point in required.items()
            if not self.ik_reachable(point, quat, max_error=0.04 if name == "grasp" else 0.025)
        ]
        if unreachable:
            return False, {
                "stage": "scripted_setup",
                "reason": "unreachable_waypoint",
                "unreachable": unreachable,
                "required_waypoints": {name: point.tolist() for name, point in required.items()},
            }

        initial_q = self.solve_ik(initial_ee, quat)
        self.reset_to_ee_pose(initial_q, gripper_width=0.04)
        self.move_ee(
            pre_grasp,
            target_quat=quat,
            speed=self.motion_speed,
            gripper_state=-1.0,
            phase_name="scripted_pre_grasp",
            save=save,
        )
        self.move_ee(
            grasp,
            target_quat=quat,
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
        self.move_ee(
            transport_start,
            target_quat=quat,
            speed=0.06,
            gripper_state=1.0,
            phase_name="transport_start",
            save=save,
        )
        cube_pos = self.cube_pos()
        ee_pos = self.ee_pos()
        grasped = bool(cube_pos[2] >= BOX_HALF_EXTENT + 0.015)
        transport_height_error = abs(float(ee_pos[2]) - float(transport_start[2]))
        transport_height_reached = transport_height_error <= TRANSPORT_START_HEIGHT_TOLERANCE
        setup_success = bool(grasped and transport_height_reached)
        if not grasped:
            reason = "box_not_lifted"
        elif not transport_height_reached:
            reason = "transport_height_not_reached"
        else:
            reason = None
        return setup_success, {
            "stage": "scripted_setup",
            "reason": reason,
            "grasped": grasped,
            "transport_height_reached": transport_height_reached,
            "transport_height_error": transport_height_error,
            "transport_height_tolerance": TRANSPORT_START_HEIGHT_TOLERANCE,
            "required_waypoints": {name: point.tolist() for name, point in required.items()},
            "box_position_after_lift": cube_pos.tolist(),
            "ee_position_after_lift": ee_pos.tolist(),
            "transport_start": transport_start.tolist(),
        }

    def run_scripted_transport_and_release(
        self,
        spec,
        save=False,
        demo_index=None,
        settle_seconds=1.5,
    ):
        # Dataset collection is strictly gated: the scripted approach, grasp,
        # close, and lift are never saved as policy-learning data.
        self.demo_dir = None
        setup_success, setup_details = self.scripted_grasp_to_transport_start(spec, save=False)
        if not setup_success:
            return False, {"setup_success": False, "setup_details": setup_details}

        if save:
            if demo_index is None:
                raise ValueError("demo_index is required when save=True")
            self.begin_demo(demo_index)
            # begin_demo resets frame_index and capture_time. Frame zero is the
            # exact state from which a learned policy will start inference.
            self.save_frame(
                gripper_state=1.0,
                phase_name="policy_inference_start",
                commanded_speed=0.0,
                commanded_dt=0.0,
            )

        quat = self.default_orientation_quat
        middle = np.asarray(spec["middle_waypoint"], dtype=float)
        release = np.asarray(spec["release_pose"], dtype=float)

        if not self.ik_reachable(middle, quat, max_error=WAYPOINT_REACH_TOLERANCE):
            return False, {
                "setup_success": True,
                "setup_details": setup_details,
                "failure_stage": "middle_waypoint_reachability",
                "policy_inference_started": False,
                "middle_waypoint": middle.tolist(),
                "middle_waypoint_tolerance": WAYPOINT_REACH_TOLERANCE,
            }

        # Policy inference will begin at transport_start in the learned-policy
        # evaluator.  The scripted smoke continues from the same state.
        policy_start_box_pose = pb.getBasePositionAndOrientation(self.cube_id)
        policy_start_ee_pose = pb.getLinkState(
            self.panda,
            self.ee_link_index,
            computeForwardKinematics=True,
        )[:2]

        self.move_ee_cartesian(
            middle,
            target_quat=quat,
            speed=self.motion_speed,
            gripper_state=1.0,
            phase_name="policy_transport_waypoint",
            save=save,
        )
        self.move_ee_cartesian(
            release,
            target_quat=quat,
            speed=self.motion_speed,
            gripper_state=1.0,
            phase_name="policy_target_approach",
            save=save,
        )
        self.command_gripper(
            width=0.04,
            duration=1.0,
            gripper_state=-1.0,
            phase_name="policy_release",
            save=save,
        )
        retract = release.copy()
        retract[2] = max(float(release[2]) + 0.12, 0.24)
        self.move_ee(
            retract,
            target_quat=quat,
            speed=0.12,
            gripper_state=-1.0,
            phase_name="post_release_retract",
            save=False,
        )
        self.hold_pose(
            retract,
            target_quat=quat,
            width=0.04,
            duration=settle_seconds,
            gripper_state=-1.0,
            phase_name="settle",
            save=save,
        )
        success, success_details = self.transport_success()
        waypoint_error = float(
            self._phase_final_errors.get("policy_transport_waypoint", float("inf"))
        )
        waypoint_reached = waypoint_error <= WAYPOINT_REACH_TOLERANCE
        success_details["middle_waypoint_error"] = waypoint_error
        success_details["middle_waypoint_tolerance"] = WAYPOINT_REACH_TOLERANCE
        success_details["middle_waypoint_reached"] = waypoint_reached
        if not waypoint_reached:
            success = False
            success_details["success"] = False
            success_details["failure_reasons"].append("middle_waypoint_not_reached")
        return success, {
            "setup_success": True,
            "setup_details": setup_details,
            "policy_inference_start": {
                "box_position": list(policy_start_box_pose[0]),
                "box_quaternion_xyzw": list(policy_start_box_pose[1]),
                "ee_position": list(policy_start_ee_pose[0]),
                "ee_quaternion_xyzw": list(policy_start_ee_pose[1]),
                "gripper_state": 1.0,
            },
            "success": success_details,
        }

    def transport_success(self):
        box_pos, box_quat = pb.getBasePositionAndOrientation(self.cube_id)
        box_linear_velocity, box_angular_velocity = pb.getBaseVelocity(self.cube_id)
        obstacle_pos, obstacle_quat = pb.getBasePositionAndOrientation(self.obstacle_id)
        obstacle_tilt = quaternion_upright_error_degrees(obstacle_quat)
        target_error_xy = float(np.linalg.norm(np.asarray(box_pos[:2]) - np.asarray(TARGET_XY)))
        target_reached = target_error_xy <= TARGET_XY_TOLERANCE
        box_settled = (
            float(np.linalg.norm(box_linear_velocity)) <= 0.02
            and float(np.linalg.norm(box_angular_velocity)) <= 0.10
            and abs(float(box_pos[2]) - BOX_HALF_EXTENT) <= 0.015
        )
        cylinder_upright = obstacle_tilt <= CYLINDER_UPRIGHT_TOLERANCE_DEGREES
        success = bool(target_reached and box_settled and cylinder_upright)
        failure_reasons = []
        if not target_reached:
            failure_reasons.append("target_miss")
        if not box_settled:
            failure_reasons.append("box_not_settled")
        if not cylinder_upright:
            failure_reasons.append("cylinder_toppled")
        return success, {
            "success": success,
            "criterion": "target_xy_error<=0.03 and box_settled and cylinder_tilt<=10deg",
            "failure_reasons": failure_reasons,
            "target_xy": list(TARGET_XY),
            "target_xy_tolerance": TARGET_XY_TOLERANCE,
            "target_xy_error": target_error_xy,
            "final_box_position": list(box_pos),
            "final_box_quaternion_xyzw": list(box_quat),
            "final_box_linear_velocity": list(box_linear_velocity),
            "final_box_angular_velocity": list(box_angular_velocity),
            "final_cylinder_position": list(obstacle_pos),
            "final_cylinder_quaternion_xyzw": list(obstacle_quat),
            "final_cylinder_tilt_degrees": obstacle_tilt,
            "maximum_cylinder_tilt_degrees": self._maximum_cylinder_tilt_degrees,
            "box_obstacle_contact_steps": self._box_obstacle_contact_steps,
            "robot_obstacle_contact_steps": self._robot_obstacle_contact_steps,
        }


def write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_trajectory_plot(path, result, box_trace, ee_trace):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    box_trace = np.asarray(box_trace, dtype=float)
    ee_trace = np.asarray(ee_trace, dtype=float)
    figure, axis = plt.subplots(figsize=(7, 7))
    axis.add_patch(plt.Circle(OBSTACLE_XY, OBSTACLE_RADIUS, color="royalblue", alpha=0.7, label="cylinder"))
    axis.add_patch(plt.Circle(TARGET_XY, TARGET_XY_TOLERANCE, color="limegreen", alpha=0.45, label="target"))
    if len(box_trace):
        axis.plot(box_trace[:, 0], box_trace[:, 1], color="firebrick", linewidth=2.0, label="box centroid")
        axis.scatter(box_trace[0, 0], box_trace[0, 1], color="black", marker="o", label="box start")
        axis.scatter(box_trace[-1, 0], box_trace[-1, 1], color="firebrick", marker="x", s=80, label="box final")
    if len(ee_trace):
        axis.plot(ee_trace[:, 0], ee_trace[:, 1], color="darkorange", linewidth=1.0, alpha=0.65, label="EE")
    middle = result["spec"]["middle_waypoint"]
    axis.scatter(middle[0], middle[1], color="purple", marker="*", s=130, label="sampled waypoint")
    axis.set_xlim(0.10, 0.90)
    axis.set_ylim(-0.16, 0.62)
    axis.set_aspect("equal", adjustable="box")
    axis.set_xlabel("x (m)")
    axis.set_ylabel("y (m)")
    participant_prefix = (
        f"{result['participant_id']} " if result.get("participant_id") is not None else ""
    )
    axis.set_title(
        f"{participant_prefix}obstacle transport {result['condition']} | success={result['success']} | "
        f"target error={result['details'].get('success', {}).get('target_xy_error', float('nan')):.3f} m"
    )
    axis.grid(alpha=0.25)
    axis.legend(loc="best")
    figure.tight_layout()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, dpi=170)
    plt.close(figure)


def parse_args():
    parser = argparse.ArgumentParser(description="Collect scripted L/R obstacle-transport demonstrations.")
    parser.add_argument("--condition", choices=CONDITIONS, required=True)
    parser.add_argument("--num-demos", type=int, default=1)
    parser.add_argument("--max-attempts", type=int, default=50)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--sample-hz", type=float, default=8.0)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--save-videos", action="store_true")
    parser.add_argument("--save-raw-frames", action="store_true")
    parser.add_argument("--gui", action="store_true")
    parser.add_argument("--playback-speed", type=float, default=1000.0)
    return parser.parse_args()


def main():
    args = parse_args()
    if args.num_demos <= 0:
        raise ValueError("--num-demos must be positive")
    if args.max_attempts < args.num_demos:
        raise ValueError("--max-attempts must be at least --num-demos")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(args.seed)
    sim = ObstacleTransportSim(
        gui=args.gui,
        output_dir=args.output_dir if args.save_raw_frames else None,
        sample_hz=args.sample_hz,
    )
    sim.playback_speed = args.playback_speed
    sim.setup()

    successes = []
    attempts = []
    try:
        for attempt_index in range(args.max_attempts):
            if len(successes) >= args.num_demos:
                break
            spec = sample_task_spec(rng, args.condition, attempt_index)
            sim.reset_task_state(spec["box_initial_position"])
            if args.save_raw_frames:
                sim.demo_dir = None
            video_path = args.output_dir / "videos" / f"attempt_{attempt_index:03d}.mp4"
            if args.save_videos:
                sim.start_video(video_path)
            try:
                success, details = sim.run_scripted_transport_and_release(
                    spec,
                    save=args.save_raw_frames,
                    demo_index=len(successes),
                )
            finally:
                sim.close_video()
            result = {
                "group": EXPERIMENT_GROUP,
                "condition": args.condition,
                "attempt_index": attempt_index,
                "success": bool(success),
                "spec": spec,
                "details": details,
                "video_path": str(video_path) if args.save_videos else None,
            }
            attempts.append(result)
            write_json(args.output_dir / "attempts" / f"attempt_{attempt_index:03d}.json", result)
            write_trajectory_plot(
                args.output_dir / "plots" / f"attempt_{attempt_index:03d}.png",
                result,
                sim._box_trace,
                sim._ee_trace,
            )
            print(
                f"[{args.condition}] attempt={attempt_index} success={success} "
                f"box={np.round(spec['box_initial_position'], 4).tolist()} "
                f"mid={np.round(spec['middle_waypoint'], 4).tolist()} "
                f"details={details.get('success', details)}",
                flush=True,
            )
            if success:
                demo_index = len(successes)
                result["demo_index"] = demo_index
                successes.append(result)
                write_json(args.output_dir / f"demo_{demo_index:03d}.json", result)
                if args.save_raw_frames:
                    sim.write_demo_metadata(
                        {
                            "group": EXPERIMENT_GROUP,
                            "condition": args.condition,
                            "attempt_index": attempt_index,
                            "demo_index": demo_index,
                            "collection_boundary": "after_validated_scripted_grasp_and_lift",
                            "first_saved_phase": "policy_inference_start",
                            "scripted_setup_saved": False,
                            "frame_count": sim.frame_index,
                            "spec": spec,
                            "setup_details": details["setup_details"],
                        },
                        merge=False,
                    )
            elif args.save_raw_frames and sim.demo_dir is not None and sim.demo_dir.exists():
                # A failed policy segment is retained in attempt JSON/plots but
                # must not contaminate the successful training dataset.
                failed_demo_dir = sim.demo_dir
                shutil.rmtree(failed_demo_dir)
                sim.demo_dir = None
                print(f"Deleted failed raw demo directory: {failed_demo_dir}", flush=True)
        summary = {
            "group": EXPERIMENT_GROUP,
            "task": "scripted_fixed_orientation_grasp_then_obstacle_transport_and_release",
            "condition": args.condition,
            "seed": args.seed,
            "requested_successful_demos": args.num_demos,
            "successful_demos": len(successes),
            "attempt_count": len(attempts),
            "success_rate_over_attempts": len(successes) / max(len(attempts), 1),
            "constants": {
                "box_start_x_bounds": list(BOX_START_X_BOUNDS),
                "box_start_y_bounds": list(BOX_START_Y_BOUNDS),
                "obstacle_xy": list(OBSTACLE_XY),
                "obstacle_radius": OBSTACLE_RADIUS,
                "obstacle_height": OBSTACLE_HEIGHT,
                "target_xy": list(TARGET_XY),
                "target_xy_tolerance": TARGET_XY_TOLERANCE,
                "waypoint_x_centers": WAYPOINT_X_CENTERS,
                "waypoint_x_noise": WAYPOINT_X_NOISE,
                "transport_z_center": TRANSPORT_Z_CENTER,
                "transport_z_noise": TRANSPORT_Z_NOISE,
                "transport_start_height_tolerance": TRANSPORT_START_HEIGHT_TOLERANCE,
            },
            "successful_attempt_indices": [row["attempt_index"] for row in successes],
        }
        write_json(args.output_dir / "summary.json", summary)
        if len(successes) != args.num_demos:
            raise RuntimeError(
                f"Collected only {len(successes)}/{args.num_demos} successful demos "
                f"after {len(attempts)} attempts"
            )
        print(json.dumps(summary, indent=2, sort_keys=True))
    finally:
        sim.close_video()
        if sim.client is not None:
            pb.disconnect(sim.client)


if __name__ == "__main__":
    main()
