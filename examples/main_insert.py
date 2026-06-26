#!/usr/bin/env python3
import argparse
import json
import math
import random
import shutil
import time

import numpy as np
import pybullet as pb
import pybullet_data

from collection_io import DatasetCollectorMixin


class PandaPegInsertSim(DatasetCollectorMixin):
    def __init__(self, gui=True, left_handed=False, gripper_orientation="default", output_dir=None, sample_hz=30.0):
        self.gui = gui
        self.left_handed = left_handed
        self.gripper_orientation = gripper_orientation
        self.client = None
        self.panda = None
        self.peg_id = None
        self.fixture_ids = []
        self.holding_constraint = None
        self.camera_body_id = None
        self.camera_debug_ids = []
        self.camera_fig = None
        self.camera_axes = None
        self.camera_rgb_artist = None
        self.camera_depth_artist = None
        self.pcd_vis = None
        self.pcd_geom = None
        self.pcd_frame = None
        self.pcd_added = False
        self.live_view_interval = 0.5
        self._last_live_view_update = 0.0
        self.control_hz = 240.0
        self.playback_speed = 4.0
        self.sim_dt = 1.0 / self.control_hz
        self.frequency = 30.0
        self.motion_speed = 0.10
        self.use_kinematic_reset_for_collection = False
        self.default_orientation_quat = pb.getQuaternionFromEuler([-math.pi, 0.0, 0.0])

        # Franka in pybullet_data has 7 arm joints + 2 finger joints.
        self.arm_joint_indices = list(range(7))
        self.left_finger_joint = 9
        self.right_finger_joint = 10
        self.ee_link_index = 11  # panda_hand_tcp / end-effector-like link

        self.home_q = [
            0.0,
            -0.5,
            0.0,
            -2.2,
            0.0,
            2.0,
            0.8,
        ]

        self.peg_radius = 0.018
        self.peg_height = 0.14
        self.held_peg_gripper_width = self.peg_radius + 0.006
        self.held_peg_grasp_from_top = 0.025
        self.hole_pos = np.array([0.50, 0.5, 0.0])

        self._camera_setup()
        self.init_dataset_collection(output_dir=output_dir, sample_hz=sample_hz)

    def _gripper_quat(self, orientation=None):
        orientation = self.gripper_orientation if orientation is None else orientation
        default_quat = pb.getQuaternionFromEuler([math.pi, 0.0, 0.0])

        if orientation in ("default", "down"):
            return default_quat
        if orientation in ("tilt", "tilted"):
            tilt_quat = pb.getQuaternionFromEuler([0.0, -math.pi / 4.0, math.pi / 2.0])
            _, gripper_quat = pb.multiplyTransforms(
                [0.0, 0.0, 0.0],
                tilt_quat,
                [0.0, 0.0, 0.0],
                default_quat,
            )
            return gripper_quat

        raise ValueError(
            "gripper_orientation must be 'default'/'down' or 'tilt'/'tilted'"
        )

    def setup(self, peg_in_hand=False):
        if self.client is None:
            mode = pb.GUI if self.gui else pb.DIRECT
            self.client = pb.connect(mode)

        pb.setAdditionalSearchPath(pybullet_data.getDataPath())
        pb.setGravity(0, 0, -9.81)
        pb.setTimeStep(self.sim_dt)
        pb.setPhysicsEngineParameter(numSolverIterations=200, numSubSteps=8)

        pb.loadURDF("plane.urdf")
        self.panda = pb.loadURDF(
            "franka_panda/panda.urdf",
            basePosition=[0, 0, 0],
            useFixedBase=True,
            flags=pb.URDF_ENABLE_CACHED_GRAPHICS_SHAPES,
        )

        pb.setJointMotorControlArray(
            self.panda,
            self.arm_joint_indices,
            pb.VELOCITY_CONTROL,
            forces=[0.0] * len(self.arm_joint_indices),
        )

        self._spawn_fixture()
        self.peg_id = self._spawn_peg()

        self.reset(peg_in_hand=peg_in_hand)
        self.reset_gui_camera()
        self.draw_virtual_camera()

    def _camera_setup(self):
        self.camera_eye = [0.4, 0.0, 0.3]
        self.camera_target = [0.5, 0.5, -0.2]
        self.camera_up = [0.0, 0.0, 1.0]

        self.image_width = 200
        self.image_height = 200
        self.camera_near = 0.01
        self.camera_far = 1.0
        self.camera_fov = 90.0
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

    def _get_camera_intrinsics(self, proj_mat, width, height):
        f_x = proj_mat[0] * width / 2.0
        f_y = proj_mat[5] * height / 2.0
        c_x = (-proj_mat[2] * width + width) / 2.0
        c_y = (proj_mat[6] * height + height) / 2.0
        return np.array([width, height, f_x, f_y, c_x, c_y])

    def reset_gui_camera(self):
        if self.gui:
            yaw = -135 if self.left_handed else 135
            pb.resetDebugVisualizerCamera(
                cameraDistance=1.0,
                cameraYaw=yaw,
                cameraPitch=-35,
                cameraTargetPosition=self.camera_target,
            )

    def draw_virtual_camera(self):
        if self.camera_body_id is None:
            vis = pb.createVisualShape(
                pb.GEOM_SPHERE,
                radius=0.015,
                rgbaColor=[0.05, 0.05, 0.05, 1.0],
            )
            self.camera_body_id = pb.createMultiBody(
                baseMass=0.0,
                baseVisualShapeIndex=vis,
                basePosition=self.camera_eye,
            )

        for debug_id in self.camera_debug_ids:
            pb.removeUserDebugItem(debug_id)
        self.camera_debug_ids = []

        eye = np.asarray(self.camera_eye, dtype=float)
        target = np.asarray(self.camera_target, dtype=float)
        up = np.asarray(self.camera_up, dtype=float)
        forward = target - eye
        forward = forward / np.linalg.norm(forward)
        right = np.cross(forward, up)
        right = right / np.linalg.norm(right)
        true_up = np.cross(right, forward)

        frustum_dist = 0.25
        half_h = math.tan(math.radians(self.camera_fov) / 2.0) * frustum_dist
        half_w = half_h * self.camera_aspect
        center = eye + forward * frustum_dist
        corners = [
            center + right * half_w + true_up * half_h,
            center - right * half_w + true_up * half_h,
            center - right * half_w - true_up * half_h,
            center + right * half_w - true_up * half_h,
        ]

        for corner in corners:
            self.camera_debug_ids.append(
                pb.addUserDebugLine(eye, corner, [1.0, 0.8, 0.0], lineWidth=2)
            )
        for i in range(len(corners)):
            self.camera_debug_ids.append(
                pb.addUserDebugLine(
                    corners[i],
                    corners[(i + 1) % len(corners)],
                    [1.0, 0.8, 0.0],
                    lineWidth=2,
                )
            )
        self.camera_debug_ids.append(
            pb.addUserDebugLine(eye, target, [0.0, 1.0, 0.0], lineWidth=2)
        )

    def get_rgbd_image(self):
        img = pb.getCameraImage(
            self.image_width,
            self.image_height,
            viewMatrix=self.view_mat,
            projectionMatrix=self.proj_mat,
        )
        width, height = img[0], img[1]

        rgb_buffer = np.asarray(img[2])
        if rgb_buffer.ndim == 1:
            rgb_buffer = rgb_buffer.reshape(height, width, 4)
        rgb_image = rgb_buffer[:, :, :3]

        depth_buffer = np.asarray(img[3], dtype=np.float32)
        if depth_buffer.ndim == 1:
            depth_buffer = depth_buffer.reshape(height, width)
        depth_image = self.camera_near * self.camera_far / (
            self.camera_far - (self.camera_far - self.camera_near) * depth_buffer
        )
        return depth_image, rgb_image

    def crop_pcd(self, pcd, min_bound, max_bound):
        pcd_pos = pcd[:, :3]
        pcd_color = pcd[:, 3:]
        mask = np.logical_and(
            np.all(pcd_pos >= min_bound, axis=1),
            np.all(pcd_pos <= max_bound, axis=1),
        )
        return np.hstack((pcd_pos[mask], pcd_color[mask]))

    def get_system_virtual_pcd(self):
        import open3d as o3d

        depth_image, color_image = self.get_rgbd_image()
        pinhole = o3d.camera.PinholeCameraIntrinsic(
            int(self.camera_intrinsic[0]),
            int(self.camera_intrinsic[1]),
            float(self.camera_intrinsic[2]),
            float(self.camera_intrinsic[3]),
            float(self.camera_intrinsic[4]),
            float(self.camera_intrinsic[5]),
        )
        pcd = o3d.geometry.PointCloud.create_from_depth_image(
            o3d.geometry.Image((depth_image * 1000).astype(np.uint16)),
            pinhole,
            depth_scale=1000.0,
            depth_trunc=self.camera_far + 0.1,
        )
        points = np.asarray(pcd.points) * np.array([1, -1, -1])
        colors = color_image.reshape(-1, 3) / 255.0
        pcd.points = o3d.utility.Vector3dVector(points)

        view44 = np.array(self.view_mat, dtype=np.float32).reshape(4, 4).T
        pcd.transform(np.linalg.inv(view44))
        return np.hstack((np.asarray(pcd.points), colors))

    def start_pcd_viewer(self):
        import open3d as o3d

        if self.pcd_vis is not None:
            return
        vis = o3d.visualization.Visualizer()
        if not vis.create_window(window_name="Virtual camera point cloud"):
            print("Open3D point-cloud window unavailable; continuing without live PCD view.")
            try:
                vis.destroy_window()
            except RuntimeError:
                pass
            self.pcd_vis = None
            self.pcd_geom = None
            self.pcd_frame = None
            self.pcd_added = False
            return

        self.pcd_vis = vis
        self.pcd_geom = o3d.geometry.PointCloud()
        self.pcd_frame = o3d.geometry.TriangleMesh.create_coordinate_frame(size=0.1)
        self.update_pcd_viewer()

    def update_pcd_viewer(self):
        if self.pcd_vis is None or self.pcd_geom is None:
            return

        import open3d as o3d

        robot_pcd = self.get_system_virtual_pcd()
        robot_pcd = self.crop_pcd(robot_pcd, (0.1, -0.7, 0.005), (0.8, 0.7, 0.6))
        self.pcd_geom.points = o3d.utility.Vector3dVector(robot_pcd[:, :3])
        self.pcd_geom.colors = o3d.utility.Vector3dVector(robot_pcd[:, 3:])

        if not self.pcd_added:
            self.pcd_vis.add_geometry(self.pcd_geom)
            self.pcd_vis.add_geometry(self.pcd_frame)
            self.pcd_added = True
        else:
            self.pcd_vis.update_geometry(self.pcd_geom)

        self.pcd_vis.poll_events()
        self.pcd_vis.update_renderer()

    def update_live_views(self, force=False):
        now = time.monotonic()
        if not force and now - self._last_live_view_update < self.live_view_interval:
            return

        if self.pcd_vis is not None:
            self.update_pcd_viewer()
        if self.camera_fig is not None:
            self.show_camera_view()

        self._last_live_view_update = now

    def close_pcd_viewer(self):
        if self.pcd_vis is not None:
            self.pcd_vis.destroy_window()
            self.pcd_vis = None
            self.pcd_geom = None
            self.pcd_frame = None
            self.pcd_added = False

    def show_camera_view(self, block=False):
        import matplotlib.pyplot as plt

        plt.ion()
        if self.camera_fig is not None and not plt.fignum_exists(self.camera_fig.number):
            self.camera_fig = None
            self.camera_axes = None
            self.camera_rgb_artist = None
            self.camera_depth_artist = None

        depth_image, rgb_image = self.get_rgbd_image()
        if self.camera_fig is None:
            self.camera_fig, self.camera_axes = plt.subplots(
                1,
                2,
                num="Virtual camera view",
            )
            self.camera_rgb_artist = self.camera_axes[0].imshow(rgb_image)
            self.camera_axes[0].set_title("RGB")
            self.camera_axes[0].axis("off")
            self.camera_depth_artist = self.camera_axes[1].imshow(
                depth_image,
                cmap="viridis",
                vmin=self.camera_near,
                vmax=self.camera_far,
            )
            self.camera_axes[1].set_title("Depth")
            self.camera_axes[1].axis("off")
            self.camera_fig.tight_layout()
            self.camera_fig.show()
        else:
            self.camera_rgb_artist.set_data(rgb_image)
            self.camera_depth_artist.set_data(depth_image)

        self.camera_fig.canvas.draw_idle()
        self.camera_fig.canvas.flush_events()

        if block:
            plt.show()

    def _spawn_peg(self):
        x = random.uniform(0.45, 0.55)
        y = random.uniform(0.08, 0.20)
        z = self.peg_height / 2.0

        col = pb.createCollisionShape(
            pb.GEOM_CYLINDER,
            radius=self.peg_radius,
            height=self.peg_height,
        )
        vis = pb.createVisualShape(
            pb.GEOM_CYLINDER,
            radius=self.peg_radius,
            length=self.peg_height,
            rgbaColor=[0.95, 0.25, 0.15, 1.0],
        )
        peg_id = pb.createMultiBody(
            baseMass=0.04,
            baseCollisionShapeIndex=col,
            baseVisualShapeIndex=vis,
            basePosition=[x, y, z],
            baseOrientation=[0, 0, 0, 1],
        )
        pb.changeDynamics(
            peg_id,
            -1,
            lateralFriction=1.4,
            spinningFriction=0.03,
            rollingFriction=0.0001,
            restitution=0.0,
        )
        return peg_id

    def _spawn_fixture(self):
        # Four blocks form a square guide hole. This avoids mesh booleans while
        # still giving the insertion target a physical contact boundary.
        block_height = 0.035
        block_thickness = 0.025
        outer = 0.115
        gap = 0.052
        hx, hy = self.hole_pos[:2]

        specs = [
            (
                [outer / 2.0, block_thickness / 2.0, block_height / 2.0],
                [hx, hy + gap / 2.0 + block_thickness / 2.0, block_height / 2.0],
            ),
            (
                [outer / 2.0, block_thickness / 2.0, block_height / 2.0],
                [hx, hy - gap / 2.0 - block_thickness / 2.0, block_height / 2.0],
            ),
            (
                [block_thickness / 2.0, gap / 2.0, block_height / 2.0],
                [hx + gap / 2.0 + block_thickness / 2.0, hy, block_height / 2.0],
            ),
            (
                [block_thickness / 2.0, gap / 2.0, block_height / 2.0],
                [hx - gap / 2.0 - block_thickness / 2.0, hy, block_height / 2.0],
            ),
        ]

        for half_extents, pos in specs:
            col = pb.createCollisionShape(pb.GEOM_BOX, halfExtents=half_extents)
            vis = pb.createVisualShape(
                pb.GEOM_BOX,
                halfExtents=half_extents,
                rgbaColor=[0.15, 0.35, 0.85, 1.0],
            )
            block_id = pb.createMultiBody(
                baseMass=0.0,
                baseCollisionShapeIndex=col,
                baseVisualShapeIndex=vis,
                basePosition=pos,
                baseOrientation=[0, 0, 0, 1],
            )
            pb.changeDynamics(block_id, -1, lateralFriction=1.0, restitution=0.0)
            self.fixture_ids.append(block_id)

    def reset(self, peg_in_hand=False):
        if self.holding_constraint is not None:
            self._detach_peg()

        target_q = self.home_q
        for i, j in enumerate(self.arm_joint_indices):
            pb.resetJointState(self.panda, j, target_q[i])

        gripper_width = self.held_peg_gripper_width if peg_in_hand else 0.04
        pb.resetJointState(self.panda, self.left_finger_joint, gripper_width)
        pb.resetJointState(self.panda, self.right_finger_joint, gripper_width)

        if peg_in_hand:
            self._place_peg_in_gripper()
            self._attach_peg()

        for _ in range(120):
            self._apply_arm(target_q, force=120, max_vel=1.5)
            self._apply_gripper(gripper_width, force=80 if peg_in_hand else 60, max_vel=0.08)
            self._step_simulation(1.0 / 30.0)

    def _apply_arm(self, q, force=120, max_vel=1.5):
        pb.setJointMotorControlArray(
            self.panda,
            self.arm_joint_indices,
            pb.POSITION_CONTROL,
            targetPositions=q,
            forces=[force] * len(self.arm_joint_indices),
            positionGains=[0.08] * len(self.arm_joint_indices),
            velocityGains=[1.0] * len(self.arm_joint_indices),
        )

    def _apply_gripper(self, width, force=60, max_vel=0.08):
        w = float(np.clip(width, 0.0, 0.04))
        pb.setJointMotorControl2(
            self.panda,
            self.left_finger_joint,
            pb.POSITION_CONTROL,
            targetPosition=w,
            force=force,
            maxVelocity=max_vel,
        )
        pb.setJointMotorControl2(
            self.panda,
            self.right_finger_joint,
            pb.POSITION_CONTROL,
            targetPosition=w,
            force=force,
            maxVelocity=max_vel,
        )

    def hold_gripper(self, duration=1.2, phase_name="hold_gripper", save=True):
        step_dt = 1.0 / 30.0
        steps = max(1, int(duration * 30))
        for _ in range(steps):
            self._apply_gripper(self.peg_radius, force=80, max_vel=0.03)
            self._step_simulation(step_dt)
            if save:
                self.maybe_save_frame(1.0, phase_name=phase_name, step_dt=step_dt)

    def step(self, n=1, gripper_state=None, phase_name=None):
        step_dt = 1.0 / 30.0
        for _ in range(n):
            self._step_simulation(step_dt)
            if gripper_state is not None:
                self.maybe_save_frame(gripper_state, phase_name=phase_name, step_dt=step_dt)

    def _step_simulation(self, sleep_dt):
        start = time.monotonic()
        pb.stepSimulation()
        self.update_live_views()
        remaining = sleep_dt / self.playback_speed - (time.monotonic() - start)
        if remaining > 0:
            time.sleep(remaining)

    def move_ee(
        self,
        target_pos,
        target_quat=None,
        duration=None,
        speed=None,
        min_duration=None,
        gripper_state=None,
        phase_name=None,
        save=True,
        use_kinematic_reset=None,
    ):
        if target_quat is None:
            target_quat = self.default_orientation_quat
        if speed is None:
            speed = self.motion_speed
        if speed <= 0:
            raise ValueError(f"speed must be positive, got {speed}")
        if min_duration is None:
            min_duration = 1.0 / self.frequency

        target_xyz = np.asarray(target_pos, dtype=float)
        current_xyz = np.asarray(
            pb.getLinkState(
                self.panda,
                self.ee_link_index,
                computeForwardKinematics=True,
            )[0],
            dtype=float,
        )
        distance = float(np.linalg.norm(target_xyz - current_xyz))
        if duration is None:
            duration = max(distance / speed, min_duration)
        else:
            duration = max(float(duration), min_duration)

        ik = pb.calculateInverseKinematics(
            self.panda,
            self.ee_link_index,
            target_xyz,
            targetOrientation=target_quat,
            maxNumIterations=200,
            residualThreshold=1e-4,
        )
        q_start = [pb.getJointState(self.panda, j)[0] for j in self.arm_joint_indices]
        q_goal = [ik[j] for j in self.arm_joint_indices]

        steps = max(1, int(np.ceil(duration * self.control_hz)))
        actual_dt = duration / steps
        capture_accum = 0.0

        for i in range(steps):
            alpha = (i + 1) / steps
            q_cmd = [(1.0 - alpha) * qs + alpha * qg for qs, qg in zip(q_start, q_goal)]
            self._apply_arm(q_cmd, force=120, max_vel=1.5)
            self._step_simulation(self.sim_dt)

            capture_accum += actual_dt
            self.capture_time += actual_dt
            if save and gripper_state is not None and phase_name != "home":
                while capture_accum + 1e-12 >= self.sample_period:
                    capture_accum -= self.sample_period
                    self.save_frame(
                        gripper_state=gripper_state,
                        phase_name=phase_name,
                        commanded_speed=speed,
                        commanded_dt=self.sample_period,
                    )

        realised_speed = distance / duration if duration > 0 else 0.0
        print(
            f"  move_ee phase={phase_name}, sim_steps={steps}, "
            f"distance={distance:.4f} m, duration={duration:.3f} s, "
            f"commanded_speed={realised_speed:.3f} m/s",
            flush=True,
        )

    def open_gripper(self, duration=1.0, phase_name="open_gripper", save=True):
        step_dt = 1.0 / 30.0
        steps = max(1, int(duration * 30))
        for _ in range(steps):
            self._apply_gripper(0.04, force=60, max_vel=0.08)
            self._step_simulation(step_dt)
            if save:
                self.maybe_save_frame(-1.0, phase_name=phase_name, step_dt=step_dt)

    def close_gripper(self, duration=1.2, phase_name="close_gripper", save=True):
        step_dt = 1.0 / 30.0
        steps = max(1, int(duration * 30))
        for _ in range(steps):
            self._apply_gripper(0.0, force=120, max_vel=0.03)
            self._step_simulation(step_dt)
            if save:
                self.maybe_save_frame(1.0, phase_name=phase_name, step_dt=step_dt)

    def peg_pos(self):
        pos, _ = pb.getBasePositionAndOrientation(self.peg_id)
        return np.array(pos)

    def write_demo_metadata(self, metadata, merge=True):
        if self.demo_dir is None:
            return
        if merge and (self.demo_dir / "metadata.json").exists():
            with open(self.demo_dir / "metadata.json", "r", encoding="utf-8") as f:
                existing = json.load(f)
            existing.update(metadata)
            metadata = existing
        with open(self.demo_dir / "metadata.json", "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, sort_keys=True)

    def success(
        self,
        max_xy_error=0.012,
        max_peg_center_z=0.12,
        min_vertical_dot=0.95,
    ):
        peg_pos, peg_quat = pb.getBasePositionAndOrientation(self.peg_id)
        peg_pos = np.asarray(peg_pos, dtype=float)
        peg_axis = np.asarray(pb.getMatrixFromQuaternion(peg_quat)).reshape(3, 3)[:, 2]
        vertical_dot = float(abs(np.dot(peg_axis, np.array([0.0, 0.0, 1.0]))))
        xy_error = float(np.linalg.norm(peg_pos[:2] - self.hole_pos[:2]))
        details = {
            "success": bool(
                xy_error <= max_xy_error
                and peg_pos[2] <= max_peg_center_z
                and vertical_dot >= min_vertical_dot
            ),
            "criterion": "xy_error <= max_xy_error and final_peg_center_z <= max_peg_center_z and vertical_dot >= min_vertical_dot",
            "final_peg_position": peg_pos.tolist(),
            "hole_position": self.hole_pos.tolist(),
            "xy_error": xy_error,
            "final_peg_center_z": float(peg_pos[2]),
            "vertical_dot": vertical_dot,
            "max_xy_error": float(max_xy_error),
            "max_peg_center_z": float(max_peg_center_z),
            "min_vertical_dot": float(min_vertical_dot),
        }
        return details["success"], details

    def _attach_peg(self):
        if self.holding_constraint is not None:
            return

        ee_state = pb.getLinkState(self.panda, self.ee_link_index)
        ee_pos = ee_state[4]
        ee_quat = ee_state[5]
        peg_pos, peg_quat = pb.getBasePositionAndOrientation(self.peg_id)
        if np.linalg.norm(np.array(ee_pos[:2]) - np.array(peg_pos[:2])) > 0.05:
            print(
                "Warning: gripper is not centered on peg; "
                "attaching anyway for task rollout."
            )

        inv_ee_pos, inv_ee_quat = pb.invertTransform(ee_pos, ee_quat)
        parent_frame_pos, parent_frame_quat = pb.multiplyTransforms(
            inv_ee_pos,
            inv_ee_quat,
            peg_pos,
            peg_quat,
        )

        self.holding_constraint = pb.createConstraint(
            parentBodyUniqueId=self.panda,
            parentLinkIndex=self.ee_link_index,
            childBodyUniqueId=self.peg_id,
            childLinkIndex=-1,
            jointType=pb.JOINT_FIXED,
            jointAxis=[0, 0, 0],
            parentFramePosition=parent_frame_pos,
            childFramePosition=[0.0, 0.0, 0.0],
            parentFrameOrientation=parent_frame_quat,
            childFrameOrientation=[0, 0, 0, 1],
        )
        pb.changeConstraint(self.holding_constraint, maxForce=80)

    def _detach_peg(self):
        if self.holding_constraint is not None:
            pb.removeConstraint(self.holding_constraint)
            self.holding_constraint = None

    def pre_insert_pos(self):
        hole = self.hole_pos.copy()
        return np.array([hole[0], hole[1], 0.33])

    def _place_peg_in_gripper(self):
        left_min, left_max = pb.getAABB(self.panda, self.left_finger_joint)
        right_min, right_max = pb.getAABB(self.panda, self.right_finger_joint)
        left_center = (np.asarray(left_min) + np.asarray(left_max)) / 2.0
        right_center = (np.asarray(right_min) + np.asarray(right_max)) / 2.0
        finger_mid = (left_center + right_center) / 2.0

        ee_quat = pb.getLinkState(
            self.panda,
            self.ee_link_index,
            computeForwardKinematics=True,
        )[5]
        flip_local_z = pb.getQuaternionFromEuler([math.pi, 0.0, 0.0])
        _, peg_quat = pb.multiplyTransforms(
            [0.0, 0.0, 0.0],
            ee_quat,
            [0.0, 0.0, 0.0],
            flip_local_z,
        )
        peg_axis = np.asarray(pb.getMatrixFromQuaternion(peg_quat)).reshape(3, 3)[:, 2]
        grasp_offset = self.peg_height / 2.0 - self.held_peg_grasp_from_top
        peg_pos = finger_mid - peg_axis * grasp_offset
        pb.resetBasePositionAndOrientation(self.peg_id, peg_pos, peg_quat)
        pb.stepSimulation()

    def start_with_held_peg(self):
        self.reset(peg_in_hand=True)

        if self.demo_dir is not None:
            self.frame_index = 0
            self.capture_elapsed = 0.0
            self.capture_time = 0.0

    def run_insert_only(
        self,
        success_xy_tolerance=0.012,
        success_max_peg_center_z=0.12,
        success_min_vertical_dot=0.95,
    ):
        hole = self.hole_pos.copy()
        print(f"Hole at: {hole}")

        pre_insert = self.pre_insert_pos()
        align = np.array([hole[0], hole[1], 0.19])
        insert = np.array([hole[0], hole[1], 0.105])
        self.write_demo_metadata(
            {
                "task": "peg_insert_home_held",
                "hole_position": hole.tolist(),
                "pre_insert": pre_insert.tolist(),
                "align": align.tolist(),
                "insert": insert.tolist(),
            }
        )

        if self.holding_constraint is None:
            self.start_with_held_peg()

        print("1) Move above hole")
        self.move_ee(pre_insert, speed=self.motion_speed, gripper_state=1.0, phase_name="pre_insert")

        print("2) Align with guide")
        self.move_ee(align, speed=self.motion_speed, gripper_state=1.0, phase_name="align")

        print("3) Insert peg")
        self.move_ee(insert, speed=self.motion_speed, gripper_state=1.0, phase_name="insert")

        is_success, success_details = self.success(
            max_xy_error=success_xy_tolerance,
            max_peg_center_z=success_max_peg_center_z,
            min_vertical_dot=success_min_vertical_dot,
        )
        self.write_demo_metadata({"success": success_details})
        print(
            "Success check: "
            f"success={is_success}, xy_error={success_details['xy_error']:.4f} m, "
            f"final_peg_center_z={success_details['final_peg_center_z']:.4f} m, "
            f"vertical_dot={success_details['vertical_dot']:.4f}",
            flush=True,
        )
        print("Done.")
        return is_success, success_details

    def run_peg_insertion(
        self,
        success_xy_tolerance=0.012,
        success_max_peg_center_z=0.12,
        success_min_vertical_dot=0.95,
    ):
        peg = self.peg_pos()
        hole = self.hole_pos.copy()
        print(f"Peg at: {peg}")
        print(f"Hole at: {hole}")

        home = np.array([0.45, 0.00, 0.45])
        pre_grasp = np.array([peg[0], peg[1], 0.25])
        grasp = np.array([peg[0], peg[1], 0.11])
        lift = np.array([peg[0], peg[1], 0.33])
        pre_insert = np.array([hole[0], hole[1], 0.33])
        align = np.array([hole[0], hole[1], 0.19])
        insert = np.array([hole[0], hole[1], 0.105])
        retreat = np.array([0.38, -0.10, 0.36])
        self.write_demo_metadata(
            {
                "task": "peg_insert_full",
                "initial_peg_position": peg.tolist(),
                "hole_position": hole.tolist(),
                "pre_grasp": pre_grasp.tolist(),
                "grasp": grasp.tolist(),
                "pre_insert": pre_insert.tolist(),
                "align": align.tolist(),
                "insert": insert.tolist(),
            }
        )

        print("1) Home")
        self.move_ee(home, speed=self.motion_speed, gripper_state=-1.0, phase_name="home")

        print("2) Open gripper")
        self.open_gripper(duration=0.8, phase_name="open_gripper")

        print("3) Approach peg")
        self.move_ee(pre_grasp, speed=self.motion_speed, gripper_state=-1.0, phase_name="pick_approach")

        print("4) Descend to grasp")
        self.move_ee(grasp, speed=self.motion_speed, gripper_state=-1.0, phase_name="pick_grasp")

        print("5) Hold peg")
        self.hold_gripper(duration=1.2, phase_name="hold_gripper")
        self._attach_peg()

        print("6) Lift peg")
        self.move_ee(lift, speed=self.motion_speed, gripper_state=1.0, phase_name="lift")

        print("7) Move above hole")
        self.move_ee(pre_insert, speed=self.motion_speed, gripper_state=1.0, phase_name="pre_insert")

        print("8) Align with guide")
        self.move_ee(align, speed=self.motion_speed, gripper_state=1.0, phase_name="align")

        print("9) Insert peg")
        self.move_ee(insert, speed=self.motion_speed, gripper_state=1.0, phase_name="insert")
        self.step(30, gripper_state=1.0, phase_name="insert_hold")

        print("10) Release")
        self._detach_peg()
        self.open_gripper(duration=0.8, phase_name="open_gripper")

        print("11) Retreat")
        self.move_ee(retreat, speed=self.motion_speed, gripper_state=-1.0, phase_name="retreat")

        is_success, success_details = self.success(
            max_xy_error=success_xy_tolerance,
            max_peg_center_z=success_max_peg_center_z,
            min_vertical_dot=success_min_vertical_dot,
        )
        self.write_demo_metadata({"success": success_details})
        print(
            "Success check: "
            f"success={is_success}, xy_error={success_details['xy_error']:.4f} m, "
            f"final_peg_center_z={success_details['final_peg_center_z']:.4f} m, "
            f"vertical_dot={success_details['vertical_dot']:.4f}",
            flush=True,
        )
        print("Done.")
        return is_success, success_details

    def run_peg_insertion_fail(
        self,
        success_xy_tolerance=0.012,
        success_max_peg_center_z=0.12,
        success_min_vertical_dot=0.95,
    ):
        peg = self.peg_pos()
        hole = self.hole_pos.copy()
        print(f"Peg at: {peg}")
        print(f"Hole at: {hole}")

        # The peg is carried to the fixture, but the final descent is offset
        # beyond the hole clearance so it catches on the guide edge.
        home = np.array([0.45, 0.00, 0.45])
        pre_grasp = np.array([peg[0], peg[1], 0.25])
        grasp = np.array([peg[0], peg[1], 0.11])
        lift = np.array([peg[0], peg[1], 0.33])
        pre_insert = np.array([hole[0], hole[1], 0.33])
        near_align = np.array([hole[0], hole[1], 0.19])
        edge_align = np.array([hole[0] + 0.024, hole[1] + 0.004, 0.18])
        blocked_insert = np.array([hole[0] + 0.024, hole[1] + 0.004, 0.105])
        retreat = np.array([0.38, -0.10, 0.36])

        print("1) Home")
        self.move_ee(home, speed=self.motion_speed, gripper_state=-1.0, phase_name="home")

        print("2) Open gripper")
        self.open_gripper(duration=0.8, phase_name="open_gripper")

        print("3) Approach peg")
        self.move_ee(pre_grasp, speed=self.motion_speed, gripper_state=-1.0, phase_name="pick_approach")

        print("4) Descend to grasp")
        self.move_ee(grasp, speed=self.motion_speed, gripper_state=-1.0, phase_name="pick_grasp")

        print("5) Hold peg")
        self.hold_gripper(duration=1.2, phase_name="hold_gripper")
        self._attach_peg()

        print("6) Lift peg")
        self.move_ee(lift, speed=self.motion_speed, gripper_state=1.0, phase_name="lift")

        print("7) Move above hole")
        self.move_ee(pre_insert, speed=self.motion_speed, gripper_state=1.0, phase_name="pre_insert")

        print("8) Nearly align with guide")
        self.move_ee(near_align, speed=self.motion_speed, gripper_state=1.0, phase_name="near_align")

        print("9) Drift onto hole edge")
        self.move_ee(edge_align, speed=self.motion_speed, gripper_state=1.0, phase_name="edge_align")

        print("10) Attempt insertion, blocked by edge")
        self.move_ee(blocked_insert, speed=self.motion_speed, gripper_state=1.0, phase_name="blocked_insert")
        self.step(60, gripper_state=1.0, phase_name="blocked_hold")

        print("11) Retreat after failed insertion")
        self.move_ee(retreat, speed=self.motion_speed, gripper_state=-1.0, phase_name="retreat")

        print("12) Release")
        self._detach_peg()
        self.open_gripper(duration=0.8, phase_name="open_gripper")

        is_success, success_details = self.success(
            max_xy_error=success_xy_tolerance,
            max_peg_center_z=success_max_peg_center_z,
            min_vertical_dot=success_min_vertical_dot,
        )
        self.write_demo_metadata({"success": success_details})
        print(
            "Success check: "
            f"success={is_success}, xy_error={success_details['xy_error']:.4f} m, "
            f"final_peg_center_z={success_details['final_peg_center_z']:.4f} m, "
            f"vertical_dot={success_details['vertical_dot']:.4f}",
            flush=True,
        )
        print("Failed: peg reached the fixture but was blocked by the hole edge.")
        return is_success, success_details

    def close(self):
        self.close_pcd_viewer()
        if self.client is not None:
            pb.disconnect()
            self.client = None


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--gripper-orientation",
        choices=("default", "tilt"),
        default="default",
        help="Use 'tilt' for R_xyz(0, -45, 90) left-multiplied onto the down-facing gripper.",
    )
    parser.add_argument(
        "--mode",
        choices=("success", "fail"),
        default="success",
        help="Run the normal successful rollout or a near-success failure rollout.",
    )
    parser.add_argument("--output-dir", default=None, help="Write raw demos under this dataset root.")
    parser.add_argument("--num-demos", type=int, default=1, help="Number of demos to collect.")
    parser.add_argument("--seed", type=int, default=1, help="Random seed for collection.")
    parser.add_argument("--sample-hz", type=float, default=30.0, help="Frame save rate for raw demos.")
    parser.add_argument(
        "--success-xy-tolerance",
        type=float,
        default=0.012,
        help="Maximum final peg-to-hole XY distance in meters for insertion success.",
    )
    parser.add_argument(
        "--success-max-peg-center-z",
        type=float,
        default=0.12,
        help="Maximum final peg center z in meters for insertion success.",
    )
    parser.add_argument(
        "--success-min-vertical-dot",
        type=float,
        default=0.95,
        help="Minimum absolute dot product between peg axis and world z for insertion success.",
    )
    parser.add_argument(
        "--max-collection-attempts",
        type=int,
        default=0,
        help="Maximum rollout attempts before aborting; 0 uses max(num_demos * 10, num_demos + 10).",
    )
    parser.add_argument("--no-gui", action="store_true", help="Run PyBullet in DIRECT mode.")
    parser.add_argument("--preview", action="store_true", help="Keep visualizer windows alive after rollout.")
    parser.add_argument("--start-with-peg", action="store_true", help="Start with the peg already held and collect insertion-only data.")
    args = parser.parse_args()

    random.seed(args.seed)
    np.random.seed(args.seed)

    max_attempts = args.max_collection_attempts
    if max_attempts <= 0:
        max_attempts = max(args.num_demos * 10, args.num_demos + 10)

    success_count = 0
    attempt_count = 0

    while success_count < args.num_demos:
        if attempt_count >= max_attempts:
            raise RuntimeError(
                f"Collected {success_count}/{args.num_demos} successful insertion demos after "
                f"{attempt_count} attempts. Increase --max-collection-attempts or relax success thresholds."
            )

        demo_idx = success_count
        attempt_count += 1
        print(
            f"Collecting demo_{demo_idx}: attempt {attempt_count}/{max_attempts}",
            flush=True,
        )

        sim = PandaPegInsertSim(
            gui=not args.no_gui,
            gripper_orientation=args.gripper_orientation,
            output_dir=args.output_dir,
            sample_hz=args.sample_hz,
        )
        try:
            sim.setup(peg_in_hand=args.start_with_peg)
            sim.begin_demo(demo_idx)

            if sim.gui and (args.preview or args.output_dir is None):
                sim.start_pcd_viewer()
                sim.show_camera_view()
                sim.update_live_views(force=True)

            if args.start_with_peg:
                is_success, _ = sim.run_insert_only(
                    success_xy_tolerance=args.success_xy_tolerance,
                    success_max_peg_center_z=args.success_max_peg_center_z,
                    success_min_vertical_dot=args.success_min_vertical_dot,
                )
            elif args.mode == "fail":
                is_success, _ = sim.run_peg_insertion_fail(
                    success_xy_tolerance=args.success_xy_tolerance,
                    success_max_peg_center_z=args.success_max_peg_center_z,
                    success_min_vertical_dot=args.success_min_vertical_dot,
                )
            else:
                is_success, _ = sim.run_peg_insertion(
                    success_xy_tolerance=args.success_xy_tolerance,
                    success_max_peg_center_z=args.success_max_peg_center_z,
                    success_min_vertical_dot=args.success_min_vertical_dot,
                )

            if is_success:
                if args.output_dir is not None:
                    print(f"Saved demo_{demo_idx} with {sim.frame_index} frames to {sim.demo_dir}")
                success_count += 1
            else:
                failed_dir = sim.demo_dir
                if failed_dir is not None and failed_dir.exists():
                    shutil.rmtree(failed_dir)
                    print(f"Deleted failed demo directory: {failed_dir}", flush=True)
                print(
                    f"Retrying demo_{demo_idx}; collected {success_count}/{args.num_demos} successes.",
                    flush=True,
                )

            if args.preview or args.output_dir is None:
                sim.update_live_views(force=True)
                while True:
                    sim.step(1)
        except KeyboardInterrupt:
            print("Interrupted.")
            break
        finally:
            sim.close()

    print(
        f"Insertion collection complete: {success_count}/{args.num_demos} successful demos "
        f"from {attempt_count} attempts.",
        flush=True,
    )
