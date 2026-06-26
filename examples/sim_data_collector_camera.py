import os
import time
import math
import random
from pathlib import Path

import numpy as np
import pybullet as pb
import pybullet_data
import open3d as o3d
from scipy.spatial.transform import Rotation
from panda_sim_constant_speed import PandaSim
import matplotlib.pyplot as plt


class DataCollectorPanda(PandaSim):
    def __init__(self, offset):
        super().__init__(offset)
        self.frequency = 30.0 # 1s capture 30 frames
        self.sample_rate = 30.0 # sampling 30 frames per second
        self.step_interval = int(self.frequency / self.sample_rate) # save 1 frame per 1/30 seconds
        self.total_steps = 0
        self.demo_dir = None
        self.vis = None
        self.vis_pcd = None
        self.frame = None
        self.init_robot_pose = None

        # Stage-A control variable setting:
        # Use Cartesian constant-speed interpolation for arm motion.
        # With speed fixed, duration is automatically computed from path length.
        self.motion_speed = 0.10  # m/s, commanded end-effector Cartesian speed

        # For diagnostic data collection, kinematic reset gives tighter control over
        # realised trajectory samples than PyBullet motor tracking. Set to False if
        # you want motor-dynamics tracking instead of strict kinematic playback.
        self.use_kinematic_reset_for_collection = True

        self._camera_setup()

    # ---------- camera ----------
    def getIntrinsicParams(self, proj_mat, w, h):
        f_x = proj_mat[0] * w / 2
        f_y = proj_mat[5] * h / 2
        c_x = (-proj_mat[2] * w + w) / 2
        c_y = (proj_mat[6] * h + h) / 2
        return np.array([w, h, f_x, f_y, c_x, c_y])

    def crop_pcd(self, pcd, min_bound, max_bound):
        pcd_pos = pcd[:, :3]
        pcd_color = pcd[:, 3:]
        mask = np.logical_and(np.all(pcd_pos >= min_bound, axis=1), np.all(pcd_pos <= max_bound, axis=1))
        return np.hstack((pcd_pos[mask], pcd_color[mask]))  

    def _camera_setup(self):
        # self.EYE    = [0.6, 0.0, 0.7]
        # self.TARGET = [0.5, 0.5, -0.1]
        self.EYE = [0.4, 0.0, 0.3]
        self.TARGET = [0.5, 0.5, -0.2]
        self.UP     = [0.0, 0.0, 1.0]

        self.IMAGE_SHAPE = [200, 200]
        self.FAR = 1.0
        self.NEAR = 0.01

        self.W, self.H = self.IMAGE_SHAPE
        self.FOV = 90.0
        self.ASPECT = 1.0
        self.PROJ_MAT = pb.computeProjectionMatrixFOV(
            fov=self.FOV, aspect=self.ASPECT, nearVal=self.NEAR, farVal=self.FAR
        )
        self.viewMat = pb.computeViewMatrix(
            cameraEyePosition=self.EYE,
            cameraTargetPosition=self.TARGET,
            cameraUpVector=self.UP,
        )
        self.intrinsic = self._get_intrinsics(self.PROJ_MAT, self.W, self.H)

    def _get_intrinsics(self, proj_mat, w, h):
        f_x = proj_mat[0] * w / 2
        f_y = proj_mat[5] * h / 2
        c_x = (-proj_mat[2] * w + w) / 2
        c_y = (proj_mat[6] * h + h) / 2
        return np.array([w, h, f_x, f_y, c_x, c_y])

    def get_rgbd_image(self, projectionMat, viewMat):
        img = pb.getCameraImage(self.W, self.H, viewMatrix=viewMat, projectionMatrix=projectionMat)
        w, h = img[0], img[1]

        rgb_buffer = np.asarray(img[2])
        if rgb_buffer.ndim == 1:
            rgb_buffer = rgb_buffer.reshape(h, w, 4)
        rgb_image = rgb_buffer[:, :, :3]

        depth_buffer = np.asarray(img[3], dtype=np.float32)
        if depth_buffer.ndim == 1:
            depth_buffer = depth_buffer.reshape(h, w)
        depth_image = self.NEAR * self.FAR / (self.FAR - (self.FAR - self.NEAR) * depth_buffer)
        depth_image = (depth_image * 1000).astype(np.uint16)
        return depth_image, rgb_image

    def get_system_virtual_pcd(self):
        depth_image, color_image = self.get_rgbd_image(self.PROJ_MAT, self.viewMat)
        pinhole = o3d.camera.PinholeCameraIntrinsic(
            int(self.intrinsic[0]), int(self.intrinsic[1]),
            float(self.intrinsic[2]), float(self.intrinsic[3]),
            float(self.intrinsic[4]), float(self.intrinsic[5])
        )
        pcd = o3d.geometry.PointCloud.create_from_depth_image(
            o3d.geometry.Image(depth_image),
            pinhole,
            depth_scale=1000.0,
            depth_trunc=self.FAR + 0.1
        )
        points = np.asarray(pcd.points) * np.array([1, -1, -1])
        colors = color_image.reshape(-1, 3) / 255.0
        pcd.points = o3d.utility.Vector3dVector(points)
        # Transform from camera to world using view matrix (invert)
        view44 = np.array(self.viewMat, dtype=np.float32).reshape(4, 4).T
        pcd.transform(np.linalg.inv(view44))
        return np.hstack((np.asarray(pcd.points), colors))

    # ---------- motion w/ capture ----------

    def move_to_pose_with_camera(
        self,
        gripper_state,
        poses,
        pose_name,
        duration=None,
        speed=None,
        min_duration=None,
        save=True,
        use_kinematic_reset=None,
    ):
        """
        Move the end-effector with controlled Cartesian speed.

        Old behaviour used a fixed duration for every segment; when the approach
        waypoint changed, this also changed the Cartesian speed. For Stage-A
        control-variable experiments, this function instead fixes commanded
        Cartesian EE speed and computes duration from path length:

            duration = path_length / speed

        Parameters
        ----------
        gripper_state : float
            -1.0 for open, 1.0 for closed; saved to hand_joints.txt.
        poses : dict
            Dictionary of Cartesian target poses.
        pose_name : str
            Target name in poses.
        duration : float or None
            If None, computed from distance/speed. If provided, kept for
            backwards compatibility, but speed is then only logged as nominal.
        speed : float or None
            Commanded Cartesian EE speed in m/s. Defaults to self.motion_speed.
        min_duration : float or None
            Lower bound on segment duration to avoid zero-step movements.
        save : bool
            Whether to save point clouds and joint states for this motion.
        use_kinematic_reset : bool or None
            If True, use resetJointState for strict diagnostic playback. If False,
            use PyBullet POSITION_CONTROL and verify actual speed post hoc.
        """
        if speed is None:
            speed = self.motion_speed
        if speed <= 0:
            raise ValueError(f"speed must be positive, got {speed}")
        if min_duration is None:
            min_duration = 1.0 / self.frequency
        if use_kinematic_reset is None:
            use_kinematic_reset = self.use_kinematic_reset_for_collection

        target_xyz = np.asarray(poses[pose_name], dtype=float)
        current_xyz = np.asarray(
            pb.getLinkState(
                self.panda,
                self.pandaEndEffectorIndex,
                computeForwardKinematics=True,
            )[0],
            dtype=float,
        )

        distance = float(np.linalg.norm(target_xyz - current_xyz))

        # Strict speed-control mode: duration varies with path length.
        # Backwards compatibility: if duration is explicitly supplied, keep it.
        if duration is None:
            duration = max(distance / speed, min_duration)
        else:
            duration = max(float(duration), min_duration)

        steps = max(1, int(np.ceil(duration * self.frequency)))
        actual_dt = duration / steps

        for step in range(steps + 1):
            alpha = step / steps
            target_pos = current_xyz + alpha * (target_xyz - current_xyz)
            target_joints = self.solve_ik(target_pos, self.default_orientation)

            if use_kinematic_reset:
                self.reset_arm_joints(target_joints)
            else:
                self.set_joint_positions(self.panda, target_joints)

            pb.stepSimulation()

            if save and pose_name != 'home':
                self.save_pcd(
                    step,
                    gripper_state,
                    phase_name=pose_name,
                    commanded_speed=speed,
                    commanded_dt=actual_dt,
                )

            # In strict kinematic mode, sleeping is unnecessary for data quality.
            # Keep it in motor mode so visual playback remains readable.
            if not use_kinematic_reset:
                time.sleep(actual_dt)

        realised_speed = distance / duration if duration > 0 else 0.0
        print(
            f"I collected {step} frames at this stage; "
            f"phase={pose_name}, distance={distance:.4f} m, "
            f"duration={duration:.3f} s, commanded_speed={realised_speed:.3f} m/s"
        )

    def reset_with_camera(self, gripper_value, poses, pose_name, duration=2.0):
        if self.hand is None:
            return
        steps = max(1, int(np.ceil(duration * self.frequency)))
        T = steps
        # gripper position
        current_pos = self._read_gripper_positions()  # 假设返回 [left, right]
        print("current_pos:", current_pos)
        # frames_number = 0
        if gripper_value == -1:  # Open gripper
            target_pos = [0.04, 0.04]
        elif gripper_value == 1:  # Closed gripper
            target_pos = [0.0, 0.0]
        else:
            raise ValueError(f"Invalid gripper value: {gripper_value}")

        # arm position
        target_xyz = poses[pose_name]
        target_joints = self.solve_ik(target_xyz, self.default_orientation)
        current_joints = []
        for joint_idx in range(pb.getNumJoints(self.panda)):
            jtype = pb.getJointInfo(self.panda, joint_idx)[2]
            if jtype in (pb.JOINT_REVOLUTE, pb.JOINT_PRISMATIC):
                current_joints.append(pb.getJointState(self.panda, joint_idx)[0])

        if len(current_joints) != len(target_joints):
            print(f"Joint count mismatch: current={len(current_joints)}, target={len(target_joints)}")
            return False
        
        for step in range(steps + 1):
            t = step / steps if steps > 0 else 1.0
            interp = [c + t*(tg - c) for c, tg in zip(current_joints, target_joints)]
            self.set_joint_positions(self.panda, interp)

            alpha = min(1.0, (step + 1) / T)  # 插值比例，0->1
            interp_pos = [
                current_pos[j] + alpha * (target_pos[j] - current_pos[j])
                for j in range(len(current_pos))
            ]
            self.set_joint_positions(self.hand, interp_pos)
            # frames_number += 1
            # self.save_pcd(step, gripper_value)
            pb.stepSimulation()
            time.sleep(1.0/self.frequency)
        print(f"I collected 0 frames at this stage")

        # for t in range(steps):
        #     init_joint_pose = self.solve_ik(self.init_robot_pose, self.default_orientation)
        #     self.set_joint_positions(self.panda, init_joint_pose)
        #     # self._set_gripper_width(hand_rp_width, force=50, max_vel=0.2)
        #     alpha = (t + 1) / T  # 插值比例，0->1
        #     interp_pos = [
        #         current_pos[j] + alpha * (target_pos[j] - current_pos[j])
        #         for j in range(len(current_pos))
        #     ]
        #     self.set_joint_positions(self.hand, interp_pos)
        #     # self.set_joint_positions(self.hand, [hand_rp_width/2, hand_rp_width/2])
        #     # if t == int(duration * self.frequency)-5:
        #     #     frames_number += 1
        #     #     self.save_pcd(t, gripper_state)
        #     frames_number += 1
        #     self.save_pcd(t, gripper_value)
        #     pb.stepSimulation()
        #     time.sleep(1.0/self.frequency)
        # print(f"I collected {frames_number} frames at this stage")

    def _read_gripper_positions(self):
        body_id = self.hand
        j_left  = self._joint_index_by_child_link(body_id, "panda_leftfinger")
        j_right = self._joint_index_by_child_link(body_id, "panda_rightfinger")
        pos_left  = pb.getJointState(body_id, j_left)[0]
        pos_right = pb.getJointState(body_id, j_right)[0]
        return [pos_left, pos_right]

    def set_gripper_state_with_camera(self, gripper_value, duration=2.0):
        """Set gripper state with smooth interpolation"""
        if self.hand is None:
            return
        T = int(duration * self.frequency)  # steps for full motion (~2 sec)
        # 获取当前gripper关节位置
        current_pos = self._read_gripper_positions()  # 假设返回 [left, right]
        print("current_pos:", current_pos)

        if gripper_value == -1:  # Open gripper
            target_pos = [0.04, 0.04]
        elif gripper_value == 1:  # Closed gripper
            target_pos = [0.0, 0.0]
        else:
            raise ValueError(f"Invalid gripper value: {gripper_value}")

        # 逐步插值
        for step in range(T):
            alpha = (step + 1) / T  # 插值比例，0->1
            interp_pos = [
                current_pos[j] + alpha * (target_pos[j] - current_pos[j])
                for j in range(len(current_pos))
            ]
            self.set_joint_positions(self.hand, interp_pos)

            # 特殊逻辑：关闭时检测抓取
            if gripper_value == 1 and self.is_grasped():
                self.attach_cube()
                break

            self.save_pcd(step, gripper_value)

            pb.stepSimulation()
            time.sleep(1.0 / self.frequency)
        print(f"I collected {step} frames at this stage")

    def close_until_grasp_and_attach_with_camera(self, gripper_state, max_open=0.04, duration=2.0,
                                    hold_force=20, max_vel=0.01):
        """
        Ramp-close the gripper; when both fingers touch and the gap is small,
        attach the cube via a fixed constraint and hold gently.
        """
        left_idx, right_idx = self._finger_indices()
    
        q = max_open
        min_gap =0.02
        steps = int(duration * self.frequency)
        
        for step in range(steps):
            # q = max_open * (1 - (step + 1) / steps)  # 0.04 -> 0.0
            alpha = (step + 1) / steps
            q = max_open - (max_open - min_gap) * alpha   # 0.04 -> 0.02
            if q < min_gap:
                q = min_gap
            self.set_joint_positions(self.hand, [q, q])
            for jid in range(pb.getNumJoints(self.hand)):
                pb.setJointMotorControl2(self.hand, jid, pb.POSITION_CONTROL,
                                        targetPosition=q, force=hold_force,
                                        maxVelocity=max_vel)
            self.save_pcd(step, gripper_state)
            pb.stepSimulation()

            if self.is_grasped():
                self.attach_cube()
                break
        print(f"I collected {step} frames at this stage")
        # Hold softly at the last q (avoid huge impulses)
        for jid in range(pb.getNumJoints(self.hand)):
            pb.setJointMotorControl2(self.hand, jid, pb.POSITION_CONTROL,
                                    targetPosition=q, force=hold_force,
                                    maxVelocity=0.01)

        # current_pos = self._read_gripper_positions()  # 假设返回 [left, right]
        # print("current_pos:", current_pos)

        # if gripper_state == -1:  # Open gripper
        #     target_pos = [0.04, 0.04]
        # elif gripper_state == 1:  # Closed gripper
        #     target_pos = [0.01, 0.01]
        # else:
        #     raise ValueError(f"Invalid gripper value: {gripper_state}")
        # T = int(duration * self.frequency)
        # # 逐步插值
        # for step in range(T):
        #     alpha = (step + 1) / T  # 插值比例，0->1
        #     interp_pos = [
        #         current_pos[j] + alpha * (target_pos[j] - current_pos[j])
        #         for j in range(len(current_pos))
        #     ]
        #     self.set_joint_positions(self.hand, interp_pos)

        #     # 特殊逻辑：关闭时检测抓取
        #     if self.is_grasped():
        #         self.attach_cube()
        #         break

        #     self.save_pcd(step, gripper_state)

        #     pb.stepSimulation()
        #     time.sleep(1.0 / self.frequency)

    def set_init_gripper_state_with_camera(self, gripper_value, duration=0.05):
        """Set gripper state with smooth interpolation"""
        if self.hand is None:
            return
        T = int(duration * self.frequency)  # steps for full motion (~2 sec)
        # 获取当前gripper关节位置
        current_pos = self._read_gripper_positions()  # 假设返回 [left, right]
        print("current_pos:", current_pos)

        if gripper_value == -1:  # Open gripper
            target_pos = [0.04, 0.04]
        elif gripper_value == 1:  # Closed gripper
            target_pos = [0.0, 0.0]
        else:
            raise ValueError(f"Invalid gripper value: {gripper_value}")

        # 逐步插值
        for step in range(T):
            alpha = (step + 1) / T  # 插值比例，0->1
            interp_pos = [
                current_pos[j] + alpha * (target_pos[j] - current_pos[j])
                for j in range(len(current_pos))
            ]
            self.set_joint_positions(self.hand, interp_pos)

            # 特殊逻辑：关闭时检测抓取
            if gripper_value == 1 and self.is_grasped():
                self.attach_cube()
                break

            if step == 5:
                self.save_pcd(step, gripper_value)

            pb.stepSimulation()
            time.sleep(1.0 / self.frequency)
        print(f"I collected {step} frames at this stage")

    def wait_for_save_init_pcd(self, gripper_value, duration=0.05):
        steps = int(duration * self.frequency)
        for step in range(steps):
            if step == 5:
                self.save_pcd(step, gripper_value)
            pb.stepSimulation()
            time.sleep(1.0/self.frequency)
        print(f"I collected {step} frames at this stage")

    def wait_for_save_pcd(self, gripper_value, duration=0.05):
        steps = int(duration * self.frequency)
        for step in range(steps):
            self.save_pcd(step, gripper_value)
            pb.stepSimulation()
            time.sleep(1.0/self.frequency)
        print(f"I collected {step} frames at this stage")
    # ---------- logging ----------

    def get_joint_positions(self, robot):
        return [pb.getJointState(robot, j)[0] for j in range(pb.getNumJoints(robot))]

    def save_pcd(
        self,
        step_in_motion,
        gripper_state,
        phase_name=None,
        commanded_speed=np.nan,
        commanded_dt=np.nan,
    ):
        self.total_steps += 1
        if self.vis is None or self.vis_pcd is None:
            return  # visualization not configured

        robot_pcd = self.get_system_virtual_pcd()
        robot_pcd = self.crop_pcd(robot_pcd, (0.1,-0.1, 0.005), (0.7,0.7,0.4))
        self.vis_pcd.points = o3d.utility.Vector3dVector(robot_pcd[:, :3])
        self.vis_pcd.colors = o3d.utility.Vector3dVector(robot_pcd[:, 3:])

        if step_in_motion == 0 and self.t == 0:
            self.vis.add_geometry(self.vis_pcd)
            if self.frame is not None:
                self.vis.add_geometry(self.frame)

        if self.total_steps % self.step_interval == 0:
            self.t += 1
            self.vis.update_geometry(self.vis_pcd)
            self.vis.poll_events()
            self.vis.update_renderer()

        if self.demo_dir is not None:
            frame_dir = self.demo_dir / f"frame_{int(self.t)}"
            frame_dir.mkdir(exist_ok=True)

            # write colored point cloud
            pcd_obj = o3d.geometry.PointCloud()
            pcd_obj.points = o3d.utility.Vector3dVector(robot_pcd[:, :3])
            pcd_obj.colors = o3d.utility.Vector3dVector(robot_pcd[:, 3:])
            o3d.io.write_point_cloud(str(frame_dir / "point_cloud.ply"), pcd_obj)

            # write joints
            arm_q = self.get_joint_positions(self.panda)
            hand_q = self.get_joint_positions(self.hand)
            np.savetxt(str(frame_dir / "arm_joints.txt"), arm_q[:7], delimiter=",")
            np.savetxt(str(frame_dir / "hand_joints.txt"), np.atleast_1d([gripper_state]), delimiter=",")

            # write end-effector pose for speed/orientation verification
            ee_pos, ee_orn = pb.getLinkState(
                self.panda,
                self.pandaEndEffectorIndex,
                computeForwardKinematics=True,
            )[:2]
            np.savetxt(str(frame_dir / "ee_pose.txt"), np.r_[ee_pos, ee_orn], delimiter=",")

            # write simple metadata for post-hoc speed checks
            np.savetxt(str(frame_dir / "time.txt"), np.atleast_1d([self.t / self.sample_rate]), delimiter=",")
            np.savetxt(str(frame_dir / "commanded_speed.txt"), np.atleast_1d([commanded_speed]), delimiter=",")
            np.savetxt(str(frame_dir / "commanded_dt.txt"), np.atleast_1d([commanded_dt]), delimiter=",")
            if self.cube_pose is not None:
                np.savetxt(str(frame_dir / "cube_pose.txt"), np.asarray(self.cube_pose, dtype=float), delimiter=",")
            with open(frame_dir / "phase.txt", "w", encoding="utf-8") as f:
                f.write("unknown" if phase_name is None else str(phase_name))

if __name__ == "__main__":
    seed = 1
    random.seed(seed)
    np.random.seed(seed)

    panda = DataCollectorPanda([0, 0, 0])

    # Open3D live viewer (optional)
    vis = o3d.visualization.Visualizer()
    vis.create_window()
    vis_pcd = o3d.geometry.PointCloud()
    frame = o3d.geometry.TriangleMesh.create_coordinate_frame(size=0.1)
    panda.vis = vis
    panda.vis_pcd = vis_pcd
    panda.frame = frame

    # dataset generation parameters 1.(300, 15) 2.(200, 12) 3.(100, 8) 4.(50, 5)
    n_demos = 1 # Total number of demos/poses to be collected
    n_sample_1d = 1 # Number of samples along one dimension for the uniform grid
    n_uniform_samples = n_sample_1d ** 2 # Total number of uniform grid samples (15*15 = 225)
    n_random_samples = n_demos - n_uniform_samples # Remaining random samples (300 - 225 = 75)

    # Constant-speed control for Stage-A path-geometry diagnosis.
    # All Cartesian arm movement segments use this commanded EE speed.
    controlled_ee_speed = 0.10  # m/s
    panda.motion_speed = controlled_ee_speed
    panda.use_kinematic_reset_for_collection = True

    # dataset root
    # root_string = f"//rds.er.kcl.ac.uk/prj/eng_human_training_for_robot_learnin/test_data_0116_{n_demos}_{n_sample_1d}"
    root_string = "/home/endongsun/Documents/Data_collection_Diffusion_Policy/data"
    demo_dir_root = Path(root_string)
    # demo_dir_root = Path(r"C:\Users\11424\Documents\ARCap_customised-standalone\Model_test\fix_data")
    os.makedirs(demo_dir_root, exist_ok=True)
    
    # n_demos = 30
    # all_cube_poses = [[0.5, 0.5, 0.3]] * n_demos
    # ranges & offsets
    offset = np.array([0.0, 0.0, 0.23])
    x_range = (0.3, 0.5)
    y_range = (0.3, 0.5)



    # --- 1. Generate Uniform Grid Samples (Deterministic) ---
    xs = []
    ys = []
    for i in range(n_sample_1d):
        # Calculate step size for 1D range (0.5 - 0.3) / (15 - 1)
        x = x_range[0] + i * (x_range[1] - x_range[0]) / (n_sample_1d - 1)
        y = y_range[0] + i * (y_range[1] - y_range[0]) / (n_sample_1d - 1)
        xs.append(x)
        ys.append(y)

    # Create a list of all cube poses
    all_cube_poses = []

    # Generate uniform grid poses
    for i in range(n_uniform_samples):
        # i % n_sample_1d cycles through xs (0, 1, ..., 14, 0, 1, ...)
        x = xs[i % n_sample_1d] 
        # i // n_sample_1d cycles through ys (0, ..., 0, 1, ..., 1, ...)
        y = ys[i // n_sample_1d] 
        cube_pose = [x, y, 0.3]
        all_cube_poses.append(cube_pose)
        
    # --- 2. Generate Remaining Random Samples ---
    for i in range(n_random_samples):
        x = random.uniform(*x_range)
        y = random.uniform(*y_range)
        cube_pose = [x, y, 0.3]
        all_cube_poses.append(cube_pose)

    # Ensure the total number of poses is correct
    print(f"Total poses generated: {len(all_cube_poses)}") 

    # --- 3. Shuffle the Poses for Non-Repeating, Randomised Order ---
    # This mixes the uniform and random samples, ensuring you sample non-repeatedly 
    # from the entire set in a random order.
    random.shuffle(all_cube_poses)
    # plot the cube poses
    plt.scatter([pose[0] for pose in all_cube_poses], [pose[1] for pose in all_cube_poses])
    plt.xlabel('X')
    plt.ylabel('Y')
    plt.title('Cube Poses')
    plt.grid(True)
    # figure_destination = r"C:\Users\11424\Documents\Data_collection_Diffusion_Policy\data_200_consistency"
    figure_destination = "/home/endongsun/Documents/Data_collection_Diffusion_Policy/"
    plt.savefig(os.path.join(figure_destination, f'cube_poses_{n_demos}_{n_sample_1d}.png'))

    for i in range(0, n_demos):
    # randomize initial EE hover & cube pose
        x_n, y_n, z_n = np.random.normal(loc=0.0, scale=0.05, size=3)

        panda.init_robot_pose = [0.2, 0.2, 0.5]
        # panda.init_robot_pose = [0.4, 0.3, 0.5]
        print("init_robot_pose:", panda.init_robot_pose)
        cube_pose = all_cube_poses[i]
        print("cube_pose:", cube_pose)
        panda.cube_pose = cube_pose.copy()
        # panda.cube_pose = [0.5, 0.5, 0.3]
        panda.set_up()

        cartesian_poses = {
            'home': np.array(panda.init_robot_pose),
            'pick_approach': np.array([panda.cube_pose[0] + x_n, panda.cube_pose[1] + y_n, 0.2+ np.abs(z_n)]) + offset,
            'pick_grasp': np.array([panda.cube_pose[0], panda.cube_pose[1], 0.0]) + offset,
            'lift': np.array([panda.cube_pose[0]+0.01, panda.cube_pose[1]+0.01, 0.03]) + offset, # best is 0.05
        }

        demo_dir = demo_dir_root / f"demo_{i}"
        demo_dir.mkdir(exist_ok=True)
        panda.demo_dir = demo_dir

        # ---- per-trajectory world reset (robust) ----
        # gripper will close: close is 1, open is -1
        gripper_state = 1.0

        print(f"[Demo {i}] 1) Move to initial position, gripper remain open...")
        
        panda.reset_with_camera(
            gripper_state, 
            cartesian_poses, 
            'home', 
            duration=0.2
            ) # best is duration=0.5
        # panda.move_to_pose_with_camera(gripper_state, cartesian_poses, 'home', duration=0.2)
        # time.sleep(1.0)
        panda.set_init_gripper_state_with_camera(gripper_state, duration=0.8)
        # panda.move_to_pose_with_camera(gripper_state, cartesian_poses, 'home', duration=0.05)

        ee_pos = pb.getLinkState(panda.panda, panda.pandaEndEffectorIndex)[0]
        print("   EE at:", ee_pos)

        print(f"[Demo {i}] 2) Approach cube, gripper remain open...")
        panda.move_to_pose_with_camera(
            gripper_state,
            cartesian_poses,
            'pick_approach',
            speed=controlled_ee_speed,
        )
        # panda.wait_for_save_pcd(gripper_state, duration=0.2) # best is duration<=0.5

        print(f"[Demo {i}] 3) Open gripper...")
        gripper_state = -1.0 # open
        panda.set_gripper_state_with_camera(gripper_state, duration=1.0) # best is duration=1.0


        print(f"[Demo {i}] 4) Descend to grasp, gripper remain open...")
        panda.move_to_pose_with_camera(
            gripper_state,
            cartesian_poses,
            'pick_grasp',
            speed=controlled_ee_speed,
        )
        # panda.wait_for_save_pcd(gripper_state, duration=0.2) # best is duration<=0.5

        gripper_state = 1.0 # close
        print(f"[Demo {i}] 5) Close & attach if grasped, gripper close here...")
        # panda.close_until_grasp_and_attach_with_camera(gripper_state, duration=0.8) # best is duration=1.0
        panda.set_gripper_state_with_camera(gripper_state, duration=1.0)
        
        # panda.wait_for_save_pcd(gripper_state, duration=0.2) # best is duration<=0.5

        print(f"[Demo {i}] 6) Lift, gripper remain close...")
        panda.move_to_pose_with_camera(
            gripper_state,
            cartesian_poses,
            'lift',
            speed=controlled_ee_speed,
        )

        # gripper_state = -1.0 # open
        # print(f"[Demo {i}] 7) Release, gripper open here...")
        # panda.detach_cube()
        # panda.set_gripper_state_with_camera(gripper_state, duration=0.4)
        # panda.wait_for_save_pcd(gripper_state, duration=0.1)

        print(f"✓ Processed: demo_{i}")


    vis.destroy_window()
    pb.disconnect()
