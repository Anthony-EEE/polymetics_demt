#!/usr/bin/env python3
import argparse
import time
import random
import math
import json
import shutil
import numpy as np
import pybullet as pb
import pybullet_data

from collection_io import DatasetCollectorMixin


DEFAULT_CORRIDOR_START_CENTER = (0.30, 0.0, 0.50)
LEGACY_ABLATION_RADII = {
    "P00": (0.10, 0.02),
    "P10": (0.25, 0.02),
    "P01": (0.10, 0.06),
    "P11": (0.25, 0.06),
}
SPATIAL_CONDITION_RADII = {
    "S15": (0.15, 0.036),
    "S20": (0.20, 0.048),
    "S25": (0.25, 0.060),
    "S30": (0.30, 0.072),
    "S35": (0.35, 0.084),
}
ABLATION_CONDITION_RADII = {
    **LEGACY_ABLATION_RADII,
    **SPATIAL_CONDITION_RADII,
}


class PandaSim(DatasetCollectorMixin):
    def __init__(self, gui=True, left_handed=False, gripper_orientation="default", output_dir=None, sample_hz=30.0):
        self.gui = gui
        self.left_handed = left_handed
        self.gripper_orientation = gripper_orientation
        self.client = None
        self.panda = None
        self.cube_id = None
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

        # Franka in pybullet_data has 7 arm joints + 2 finger joints
        self.arm_joint_indices = list(range(7))
        self.left_finger_joint = 9
        self.right_finger_joint = 10
        self.ee_link_index = 11  # panda_hand_tcp / end-effector-like link

        # A stable-ish default home
        self.home_q = [
            0.0,
            -0.5,
            0.0,
            -2.2,
            0.0,
            2.0,
            0.8,
        ]

        self._camera_setup()
        self.init_dataset_collection(output_dir=output_dir, sample_hz=sample_hz)

    def _gripper_quat(self, orientation=None):
        orientation = self.gripper_orientation if orientation is None else orientation
        default_quat = self.default_orientation_quat

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

    def setup(self):
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

        # Disable default velocity motors on arm, we'll use POSITION_CONTROL explicitly
        pb.setJointMotorControlArray(
            self.panda,
            self.arm_joint_indices,
            pb.VELOCITY_CONTROL,
            forces=[0.0] * len(self.arm_joint_indices),
        )

        # Spawn a cube
        self.cube_id = self._spawn_cube()

        self.reset()
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

    def _spawn_cube(self):
        # Random cube near reachable area
        # x = random.uniform(0.45, 0.55)
        # y = random.uniform(-0.10, 0.10)
        x = 0.5
        y=0.5
        z = 0.025  # half cube size

        half = 0.035
        col = pb.createCollisionShape(pb.GEOM_BOX, halfExtents=[half, half, half])
        vis = pb.createVisualShape(
            pb.GEOM_BOX, halfExtents=[half, half, half], rgbaColor=[1, 0.2, 0.2, 1]
        )
        cube_id = pb.createMultiBody(
            baseMass=0.05,
            baseCollisionShapeIndex=col,
            baseVisualShapeIndex=vis,
            basePosition=[x, y, z],
            baseOrientation=[0, 0, 0, 1],
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

    def reset(self):
        # Reset arm
        for i, j in enumerate(self.arm_joint_indices):
            pb.resetJointState(self.panda, j, self.home_q[i])

        # Open gripper
        pb.resetJointState(self.panda, self.left_finger_joint, 0.04)
        pb.resetJointState(self.panda, self.right_finger_joint, 0.04)

        for _ in range(120):
            self._apply_arm(self.home_q, force=120, max_vel=1.5)
            self._apply_gripper(0.04, force=60, max_vel=0.08)
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
        steps = max(1, int(math.ceil(float(duration) * 30)))
        for _ in range(steps):
            self._apply_gripper(0.04, force=60, max_vel=0.08)
            self._step_simulation(step_dt)
            if save:
                self.maybe_save_frame(-1.0, phase_name=phase_name, step_dt=step_dt)

    def close_gripper(self, duration=1.2, phase_name="close_gripper", save=True):
        step_dt = 1.0 / 30.0
        steps = max(1, int(math.ceil(float(duration) * 30)))
        for _ in range(steps):
            self._apply_gripper(0.0, force=120, max_vel=0.03)
            self._step_simulation(step_dt)
            if save:
                self.maybe_save_frame(1.0, phase_name=phase_name, step_dt=step_dt)

    def loosen_gripper(self, width=0.03, duration=0.8):
        steps = max(1, int(duration * 30))
        for _ in range(steps):
            self._apply_gripper(width, force=25, max_vel=0.04)
            self._step_simulation(1.0 / 30.0)

    def cube_pos(self):
        pos, _ = pb.getBasePositionAndOrientation(self.cube_id)
        return np.array(pos)

    def ee_pos(self):
        return np.asarray(
            pb.getLinkState(
                self.panda,
                self.ee_link_index,
                computeForwardKinematics=True,
            )[0],
            dtype=float,
        )

    def ik_reachable(self, pos, quat=None, max_error=0.025):
        if quat is None:
            quat = self.default_orientation_quat
        current_q = [pb.getJointState(self.panda, j)[0] for j in self.arm_joint_indices]
        q = self.solve_ik(pos, quat)
        self.reset_arm_joints(q)
        realised = self.ee_pos()
        self.reset_arm_joints(current_q)
        return float(np.linalg.norm(realised - np.asarray(pos, dtype=float))) <= max_error

    def sample_reachable_random_start(
        self,
        x_bounds=(0.20, 0.60),
        z_bounds=(0.20, 0.60),
        max_attempts=200,
        max_error=0.025,
        quat=None,
        orientation_used="default_demo_quat",
    ):
        if quat is None:
            quat = self.default_orientation_quat
        rejected = []
        for attempt in range(1, int(max_attempts) + 1):
            pos = np.array(
                [
                    np.random.uniform(float(x_bounds[0]), float(x_bounds[1])),
                    0.0,
                    np.random.uniform(float(z_bounds[0]), float(z_bounds[1])),
                ],
                dtype=float,
            )
            q = self.solve_ik(pos, quat)
            current_q = [pb.getJointState(self.panda, j)[0] for j in self.arm_joint_indices]
            self.reset_arm_joints(q)
            realised = self.ee_pos()
            self.reset_arm_joints(current_q)
            error = float(np.linalg.norm(realised - pos))
            if error <= max_error:
                return pos, q, {
                    "attempts": attempt,
                    "max_error": float(max_error),
                    "realised_error": error,
                    "rejected_count": attempt - 1,
                    "recent_rejections": rejected[-10:],
                    "orientation_used": orientation_used,
                }
            rejected.append({"pos": pos.tolist(), "error": error})
        raise RuntimeError(
            f"Could not sample reachable random start after {max_attempts} attempts "
            f"within x={x_bounds}, z={z_bounds}, max_error={max_error}."
        )

    def sample_reachable_random_start_with_quat(
        self,
        quat,
        x_bounds=(0.20, 0.60),
        z_bounds=(0.20, 0.60),
        max_attempts=200,
        max_error=0.025,
    ):
        return self.sample_reachable_random_start(
            x_bounds=x_bounds,
            z_bounds=z_bounds,
            max_attempts=max_attempts,
            max_error=max_error,
            quat=quat,
            orientation_used="sampled_demo_quat",
        )

    def reset_to_ee_pose(self, q, gripper_width=0.04):
        self.reset_arm_joints(q)
        pb.resetJointState(self.panda, self.left_finger_joint, float(gripper_width))
        pb.resetJointState(self.panda, self.right_finger_joint, float(gripper_width))
        for _ in range(30):
            self._apply_arm(q, force=120, max_vel=1.5)
            self._apply_gripper(gripper_width, force=60, max_vel=0.08)
            self._step_simulation(1.0 / 30.0)

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

    def success(self, min_cube_z=0.20):
        cube_pos = self.cube_pos()
        details = {
            "success": bool(cube_pos[2] >= min_cube_z),
            "criterion": "final_cube_z >= min_cube_z",
            "final_cube_position": cube_pos.tolist(),
            "final_cube_z": float(cube_pos[2]),
            "min_cube_z": float(min_cube_z),
        }
        return details["success"], details

    def run_pick_and_lift(
        self,
        approach_offset=None,
        approach_region_label="center",
        success_lift_height=0.20,
    ):
        cube = self.cube_pos()
        print(f"Cube at: {cube}")

        # Poses
        home = np.array([0.45, 0.00, 0.45])
        base_pre_grasp = np.array([cube[0], cube[1], 0.22])
        approach_offset = (
            np.zeros(3, dtype=float)
            if approach_offset is None
            else np.asarray(approach_offset, dtype=float)
        )
        pre_grasp = base_pre_grasp + approach_offset
        grasp = np.array([cube[0], cube[1], 0.04])
        lift = np.array([cube[0], cube[1], 0.30])
        self.write_demo_metadata(
            {
                "task": "cube_grasp_lift",
                "approach_region_label": approach_region_label,
                "cube_position": cube.tolist(),
                "base_pre_grasp": base_pre_grasp.tolist(),
                "approach_offset": approach_offset.tolist(),
                "pre_grasp": pre_grasp.tolist(),
            }
        )
        print("1) Home")
        self.move_ee(home, speed=self.motion_speed, gripper_state=-1.0, phase_name="home")

        print("2) Open gripper")
        self.open_gripper(duration=0.8, phase_name="open_gripper")

        print("3) Approach")
        self.move_ee(pre_grasp, speed=self.motion_speed, gripper_state=-1.0, phase_name="pick_approach")

        print("4) Descend")
        self.move_ee(grasp, speed=self.motion_speed, gripper_state=-1.0, phase_name="pick_grasp")

        print("5) Close gripper")
        self.close_gripper(duration=1.2, phase_name="close_gripper")

        print("6) Lift")
        self.move_ee(lift, speed=self.motion_speed, gripper_state=1.0, phase_name="lift")

        is_success, success_details = self.success(min_cube_z=success_lift_height)
        self.write_demo_metadata({"success": success_details})
        print(
            "Success check: "
            f"success={is_success}, final_cube_z={success_details['final_cube_z']:.4f} m, "
            f"min_cube_z={success_details['min_cube_z']:.4f} m",
            flush=True,
        )
        print("Done.")
        return is_success, success_details

    def run_pick_and_lift_ablation(
        self,
        condition_label="S25",
        corridor_start_radius=0.25,
        pre_grasp_radius=0.060,
        corridor_start_center=DEFAULT_CORRIDOR_START_CENTER,
        entry_dx=None,
        corridor_start_y=None,
        entry_dz=None,
        success_lift_height=0.20,
    ):
        cube = self.cube_pos()
        print(f"Cube at: {cube}")

        base_corridor_start = np.asarray(corridor_start_center, dtype=float)
        if base_corridor_start.shape != (3,):
            raise ValueError(f"corridor_start_center must contain 3 values, got {corridor_start_center!r}")
        base_pre_grasp = np.array([cube[0], cube[1], 0.22])
        delta_start = sample_xz_disk(float(corridor_start_radius))
        delta_pre = sample_xy_disk(float(pre_grasp_radius))
        corridor_start = base_corridor_start + delta_start
        pre_grasp = base_pre_grasp + delta_pre
        grasp = np.array([cube[0], cube[1], 0.04])
        lift = np.array([cube[0], cube[1], 0.30])

        current_q = [pb.getJointState(self.panda, j)[0] for j in self.arm_joint_indices]
        corridor_start_q = self.solve_ik(corridor_start, self.default_orientation_quat)
        self.reset_arm_joints(corridor_start_q)
        realised_corridor_start = self.ee_pos()
        self.reset_arm_joints(current_q)
        corridor_error = float(np.linalg.norm(realised_corridor_start - corridor_start))
        corridor_max_error = 0.025
        corridor_reachable = corridor_error <= corridor_max_error
        corridor_start_info = {
            "ik_max_error": corridor_max_error,
            "ik_realised_error": corridor_error,
            "realised_start": realised_corridor_start.tolist(),
        }

        pre_grasp_reachable = self.ik_reachable(pre_grasp)
        if not corridor_reachable or not pre_grasp_reachable:
            details = {
                "success": False,
                "criterion": "waypoint IK reachability before rollout",
                "corridor_start_reachable": bool(corridor_reachable),
                "pre_grasp_reachable": bool(pre_grasp_reachable),
            }
            self.write_ablation_metadata(
                condition_label,
                cube,
                base_corridor_start,
                corridor_start,
                corridor_start_info,
                delta_start,
                corridor_start_radius,
                base_pre_grasp,
                pre_grasp,
                delta_pre,
                pre_grasp_radius,
                grasp,
                lift,
                entry_dx,
                corridor_start_y,
                entry_dz,
                success_details=details,
            )
            return False, details

        self.reset_to_ee_pose(corridor_start_q, gripper_width=0.04)
        self.write_ablation_metadata(
            condition_label,
            cube,
            base_corridor_start,
            corridor_start,
            corridor_start_info,
            delta_start,
            corridor_start_radius,
            base_pre_grasp,
            pre_grasp,
            delta_pre,
            pre_grasp_radius,
            grasp,
            lift,
            entry_dx,
            corridor_start_y,
            entry_dz,
        )

        print("1) Save corridor start")
        self.save_frame(gripper_state=-1.0, phase_name="corridor_start")

        print("2) Open gripper")
        self.open_gripper(duration=0.8, phase_name="open_gripper")

        print("3) Pre-grasp")
        self.move_ee(pre_grasp, speed=self.motion_speed, gripper_state=-1.0, phase_name="pre_grasp")

        print("4) Descend")
        self.move_ee(grasp, speed=self.motion_speed, gripper_state=-1.0, phase_name="pick_grasp")

        print("5) Close gripper")
        self.close_gripper(duration=1.2, phase_name="close_gripper")

        print("6) Lift")
        self.move_ee(lift, speed=self.motion_speed, gripper_state=1.0, phase_name="lift")

        is_success, success_details = self.success(min_cube_z=success_lift_height)
        self.write_demo_metadata({"success": success_details})
        print(
            "Success check: "
            f"success={is_success}, final_cube_z={success_details['final_cube_z']:.4f} m, "
            f"min_cube_z={success_details['min_cube_z']:.4f} m",
            flush=True,
        )
        print("Done.")
        return is_success, success_details

    def write_ablation_metadata(
        self,
        condition_label,
        cube,
        base_corridor_start,
        corridor_start,
        corridor_start_info,
        delta_start,
        corridor_start_radius,
        base_pre_grasp,
        pre_grasp,
        delta_pre,
        pre_grasp_radius,
        grasp,
        lift,
        entry_dx,
        corridor_start_y,
        entry_dz,
        success_details=None,
    ):
        metadata = {
            "task": "cube_grasp_lift_ablation_1",
            "experiment_track": "spatial" if str(condition_label).startswith("S") else "ablation_1",
            "condition": condition_label,
            "condition_label": condition_label,
            "condition_radius_source": "spatial_S15_S35" if str(condition_label).startswith("S") else "legacy_P_2x2",
            "sample_hz": float(self.sample_hz),
            "sample_period": float(self.sample_period),
            "cube_position": cube.tolist(),
            "base_corridor_start": base_corridor_start.tolist(),
            "corridor_start": corridor_start.tolist(),
            "corridor_start_info": corridor_start_info,
            "corridor_start_delta": delta_start.tolist(),
            "corridor_start_radius": float(corridor_start_radius),
            "corridor_start_center": base_corridor_start.tolist(),
            "corridor_start_sampling_plane": "xz",
            "base_pre_grasp": base_pre_grasp.tolist(),
            "pre_grasp": pre_grasp.tolist(),
            "pre_grasp_delta": delta_pre.tolist(),
            "pre_grasp_radius": float(pre_grasp_radius),
            "grasp": grasp.tolist(),
            "lift": lift.tolist(),
            "entry_dx": None if entry_dx is None else float(entry_dx),
            "corridor_start_y": None if corridor_start_y is None else float(corridor_start_y),
            "entry_dz": None if entry_dz is None else float(entry_dz),
        }
        if success_details is not None:
            metadata["success"] = success_details
        self.write_demo_metadata(metadata)

    def run_pick_and_lift_fail(self, success_lift_height=0.20):
        cube = self.cube_pos()
        print(f"Cube at: {cube}")

        # The gripper closes on the cube edge, so the object starts to lift but
        # loses contact when the wrist moves away.
        home = np.array([0.45, 0.00, 0.45])
        edge_grasp_xy = cube[:2] + np.array([0.032, 0.0])
        pre_grasp = np.array([edge_grasp_xy[0], edge_grasp_xy[1], 0.22])
        grasp = np.array([edge_grasp_xy[0]+0.02, edge_grasp_xy[1]+0.01, 0.04])
        near_lift = np.array([edge_grasp_xy[0], edge_grasp_xy[1], 0.22])
        # slip = np.array([edge_grasp_xy[0] + 0.1, edge_grasp_xy[1], 0.26])
        print("1) Home")
        self.move_ee(home, speed=self.motion_speed, gripper_state=-1.0, phase_name="home")

        print("2) Open gripper")
        self.open_gripper(duration=0.8, phase_name="open_gripper")

        print("3) Approach cube edge")
        self.move_ee(pre_grasp, speed=self.motion_speed, gripper_state=-1.0, phase_name="pick_approach")

        print("4) Descend to off-center grasp")
        self.move_ee(grasp, speed=self.motion_speed, gripper_state=-1.0, phase_name="pick_grasp")

        print("5) Close gripper on edge")
        self.close_gripper(duration=1.2, phase_name="close_gripper")
        self.step(60, gripper_state=1.0, phase_name="hold")

        print("6) Lift nearly successfully")
        self.move_ee(near_lift, speed=self.motion_speed, gripper_state=1.0, phase_name="near_lift")

        # print("7) Edge grasp slips")
        # self.loosen_gripper(width=0.028, duration=0.6)
        # self.move_ee(slip, duration=1.4)
        # self.step(60, gripper_state=1.0, phase_name="hold")

        is_success, success_details = self.success(min_cube_z=success_lift_height)
        self.write_demo_metadata({"success": success_details})
        print(
            "Success check: "
            f"success={is_success}, final_cube_z={success_details['final_cube_z']:.4f} m, "
            f"min_cube_z={success_details['min_cube_z']:.4f} m",
            flush=True,
        )
        print("Failed: cube slipped out of the gripper.")
        return is_success, success_details

    def close(self):
        self.close_pcd_viewer()
        if self.client is not None:
            pb.disconnect()
            self.client = None


def sample_xy_disk(radius):
    radius = float(radius)
    if radius <= 0.0:
        return np.zeros(3, dtype=float)
    theta = np.random.uniform(0.0, 2.0 * math.pi)
    r = radius * math.sqrt(np.random.uniform(0.0, 1.0))
    return np.array([r * math.cos(theta), r * math.sin(theta), 0.0], dtype=float)


def sample_xz_disk(radius):
    radius = float(radius)
    if radius <= 0.0:
        return np.zeros(3, dtype=float)
    theta = np.random.uniform(0.0, 2.0 * math.pi)
    r = radius * math.sqrt(np.random.uniform(0.0, 1.0))
    return np.array([r * math.cos(theta), 0.0, r * math.sin(theta)], dtype=float)


def ablation_radii(condition):
    if condition not in ABLATION_CONDITION_RADII:
        raise ValueError(
            f"Unknown ablation condition {condition!r}; "
            f"choose one of {sorted(ABLATION_CONDITION_RADII)}"
        )
    return ABLATION_CONDITION_RADII[condition]


def approach_key(offset):
    return tuple(float(v) for v in np.round(np.asarray(offset, dtype=float), 6))


def sample_replacement_approach(mode="none", radius=0.0, attempt_index=0):
    radius = float(radius)
    if mode == "none":
        return np.zeros(3, dtype=float), "center"

    if mode in ("xz_grid", "xz_uniform"):
        offset = np.zeros(3, dtype=float)
        offset[0] = np.random.uniform(-radius, radius)
        offset[2] = np.random.uniform(0.0, radius)
        label = f"xz_retry_{attempt_index:04d}_dx_{offset[0]:+.3f}_dz_{offset[2]:+.3f}"
        return offset, label

    if mode == "xyz_uniform":
        offset = np.random.uniform(-radius, radius, size=3)
        offset[2] = abs(offset[2])
        label = (
            f"xyz_retry_{attempt_index:04d}_dx_{offset[0]:+.3f}_"
            f"dy_{offset[1]:+.3f}_dz_{offset[2]:+.3f}"
        )
        return offset, label

    raise ValueError(f"Unknown approach-noise-mode: {mode}")


def build_approach_offsets(num_demos, mode="none", radius=0.0, grid_size=3):
    if mode == "none":
        return np.zeros((num_demos, 3), dtype=float), ["center"] * num_demos

    if mode == "xz_grid":
        grid_size = max(1, int(grid_size))
        xs = np.linspace(-float(radius), float(radius), grid_size)
        zs = np.linspace(0.0, float(radius), grid_size)
        offsets = np.array([[x, 0.0, z] for z in zs for x in xs], dtype=float)
        if len(offsets) < num_demos:
            extra = np.zeros((num_demos - len(offsets), 3), dtype=float)
            extra[:, 0] = np.random.uniform(-float(radius), float(radius), size=len(extra))
            extra[:, 2] = np.random.uniform(0.0, float(radius), size=len(extra))
            offsets = np.concatenate([offsets, extra], axis=0)
        offsets = offsets[:num_demos]
        np.random.shuffle(offsets)
        labels = [f"xz_dx_{o[0]:+.3f}_dz_{o[2]:+.3f}" for o in offsets]
        return offsets, labels

    if mode == "xz_uniform":
        offsets = np.zeros((num_demos, 3), dtype=float)
        offsets[:, 0] = np.random.uniform(-float(radius), float(radius), size=num_demos)
        offsets[:, 2] = np.random.uniform(0.0, float(radius), size=num_demos)
        labels = [f"xz_uniform_dx_{o[0]:+.3f}_dz_{o[2]:+.3f}" for o in offsets]
        return offsets, labels

    if mode == "xyz_uniform":
        offsets = np.random.uniform(-float(radius), float(radius), size=(num_demos, 3))
        offsets[:, 2] = np.abs(offsets[:, 2])
        labels = [
            f"xyz_uniform_dx_{o[0]:+.3f}_dy_{o[1]:+.3f}_dz_{o[2]:+.3f}"
            for o in offsets
        ]
        return offsets, labels

    raise ValueError(f"Unknown approach-noise-mode: {mode}")


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
        choices=("ablation", "success", "fail"),
        default="ablation",
        help="Run ablation-1 corridor rollout, original successful rollout, or near-success failure rollout.",
    )
    parser.add_argument("--output-dir", default=None, help="Write raw demos under this dataset root.")
    parser.add_argument("--num-demos", type=int, default=1, help="Number of demos to collect.")
    parser.add_argument("--seed", type=int, default=1, help="Random seed for collection.")
    parser.add_argument("--sample-hz", type=float, default=30.0, help="Frame save rate for raw demos.")
    parser.add_argument(
        "--approach-noise-mode",
        choices=("none", "xz_grid", "xz_uniform", "xyz_uniform"),
        default="none",
        help="Add controlled offsets to pre_grasp for approaching-region experiments.",
    )
    parser.add_argument("--approach-noise-radius", type=float, default=0.0, help="Maximum approach offset in meters.")
    parser.add_argument("--approach-grid-size", type=int, default=3, help="Grid size for xz_grid approach offsets.")
    parser.add_argument(
        "--ablation-condition",
        choices=tuple(ABLATION_CONDITION_RADII),
        default="S25",
        help="Spatial corridor condition for --mode ablation.",
    )
    parser.add_argument(
        "--corridor-start-radius",
        type=float,
        default=None,
        help="Override condition corridor_start_radius in meters.",
    )
    parser.add_argument(
        "--pre-grasp-radius",
        type=float,
        default=None,
        help="Override condition pre_grasp_radius in meters.",
    )
    parser.add_argument(
        "--corridor-start-center-x",
        type=float,
        default=DEFAULT_CORRIDOR_START_CENTER[0],
        help="World x coordinate of the AR guidance corridor-start circle center.",
    )
    parser.add_argument(
        "--corridor-start-center-y",
        type=float,
        default=DEFAULT_CORRIDOR_START_CENTER[1],
        help="World y coordinate of the AR guidance corridor-start circle center.",
    )
    parser.add_argument(
        "--corridor-start-center-z",
        type=float,
        default=DEFAULT_CORRIDOR_START_CENTER[2],
        help="World z coordinate of the AR guidance corridor-start circle center.",
    )
    parser.add_argument("--entry-dx", type=float, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--corridor-start-y", type=float, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--entry-dz", type=float, default=None, help=argparse.SUPPRESS)
    parser.add_argument(
        "--success-lift-height",
        type=float,
        default=0.20,
        help="Minimum final cube center z in meters for a successful grasp-lift demo.",
    )
    parser.add_argument(
        "--max-collection-attempts",
        type=int,
        default=0,
        help="Maximum rollout attempts before aborting; 0 uses max(num_demos * 10, num_demos + 10).",
    )
    parser.add_argument("--no-gui", action="store_true", help="Run PyBullet in DIRECT mode.")
    parser.add_argument("--preview", action="store_true", help="Keep visualizer windows alive after rollout.")
    args = parser.parse_args()

    random.seed(args.seed)
    np.random.seed(args.seed)

    approach_offsets, approach_labels = build_approach_offsets(
        args.num_demos,
        mode=args.approach_noise_mode,
        radius=args.approach_noise_radius,
        grid_size=args.approach_grid_size,
    )
    condition_corridor_radius, condition_pre_radius = ablation_radii(args.ablation_condition)
    corridor_start_radius = (
        condition_corridor_radius
        if args.corridor_start_radius is None
        else float(args.corridor_start_radius)
    )
    pre_grasp_radius = (
        condition_pre_radius
        if args.pre_grasp_radius is None
        else float(args.pre_grasp_radius)
    )
    corridor_start_center = (
        float(args.corridor_start_center_x),
        float(args.corridor_start_center_y),
        float(args.corridor_start_center_z),
    )
    if args.entry_dx is not None or args.corridor_start_y is not None or args.entry_dz is not None:
        print(
            "[WARN] --entry-dx / --corridor-start-y / --entry-dz are deprecated "
            "and ignored for ablation mode; using explicit --corridor-start-center-*.",
            flush=True,
        )

    max_attempts = args.max_collection_attempts
    if max_attempts <= 0:
        max_attempts = max(args.num_demos * 10, args.num_demos + 10)

    success_count = 0
    attempt_count = 0
    candidate_index = 0
    successful_approach_keys = set()

    while success_count < args.num_demos:
        if attempt_count >= max_attempts:
            raise RuntimeError(
                f"Collected {success_count}/{args.num_demos} successful demos after "
                f"{attempt_count} attempts. Increase --max-collection-attempts or relax success thresholds."
            )

        while True:
            if candidate_index < len(approach_offsets):
                approach_offset = approach_offsets[candidate_index]
                approach_label = approach_labels[candidate_index]
            else:
                approach_offset, approach_label = sample_replacement_approach(
                    mode=args.approach_noise_mode,
                    radius=args.approach_noise_radius,
                    attempt_index=candidate_index,
                )
            candidate_index += 1
            key = approach_key(approach_offset)
            if args.approach_noise_mode == "none" or key not in successful_approach_keys:
                break

        demo_idx = success_count
        attempt_count += 1
        print(
            f"Collecting demo_{demo_idx}: attempt {attempt_count}/{max_attempts}, "
            f"mode={args.mode}, condition={args.ablation_condition}, approach={approach_label}",
            flush=True,
        )

        sim = PandaSim(
            gui=not args.no_gui,
            gripper_orientation=args.gripper_orientation,
            output_dir=args.output_dir,
            sample_hz=args.sample_hz,
        )
        try:
            sim.setup()
            sim.begin_demo(demo_idx)

            if sim.gui and (args.preview or args.output_dir is None):
                sim.start_pcd_viewer()
                sim.show_camera_view()
                sim.update_live_views(force=True)

            if args.mode == "ablation":
                is_success, _ = sim.run_pick_and_lift_ablation(
                    condition_label=args.ablation_condition,
                    corridor_start_radius=corridor_start_radius,
                    pre_grasp_radius=pre_grasp_radius,
                    corridor_start_center=corridor_start_center,
                    entry_dx=args.entry_dx,
                    corridor_start_y=args.corridor_start_y,
                    entry_dz=args.entry_dz,
                    success_lift_height=args.success_lift_height,
                )
            elif args.mode == "fail":
                is_success, _ = sim.run_pick_and_lift_fail(
                    success_lift_height=args.success_lift_height
                )
            else:
                is_success, _ = sim.run_pick_and_lift(
                    approach_offset=approach_offset,
                    approach_region_label=approach_label,
                    success_lift_height=args.success_lift_height,
                )

            if is_success:
                successful_approach_keys.add(key)
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
        f"Collection complete: {success_count}/{args.num_demos} successful demos "
        f"from {attempt_count} attempts.",
        flush=True,
    )
