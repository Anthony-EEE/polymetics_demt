from pathlib import Path

import numpy as np
import pybullet as pb


class DatasetCollectorMixin:
    def init_dataset_collection(
        self,
        output_dir=None,
        sample_hz=30.0,
        crop_min=(0.1, -0.1, 0.005),
        crop_max=(0.7, 0.7, 0.4),
    ):
        self.output_dir = Path(output_dir).expanduser() if output_dir else None
        self.sample_hz = float(sample_hz)
        if self.sample_hz <= 0:
            raise ValueError(f"sample_hz must be positive, got {sample_hz}")
        self.sample_period = 1.0 / self.sample_hz
        self.capture_elapsed = 0.0
        self.capture_time = 0.0
        self.demo_dir = None
        self.frame_index = 0
        self.crop_min = np.asarray(crop_min, dtype=float)
        self.crop_max = np.asarray(crop_max, dtype=float)

    def begin_demo(self, demo_index):
        if self.output_dir is None:
            self.demo_dir = None
            return
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.demo_dir = self.output_dir / f"demo_{demo_index}"
        self.demo_dir.mkdir(parents=True, exist_ok=True)
        self.frame_index = 0
        self.capture_elapsed = 0.0
        self.capture_time = 0.0

    def maybe_save_frame(
        self,
        gripper_state,
        phase_name=None,
        step_dt=None,
        commanded_speed=np.nan,
        commanded_dt=np.nan,
        force=False,
    ):
        if self.demo_dir is None:
            return
        if step_dt is None:
            step_dt = self.sample_period
        self.capture_elapsed += float(step_dt)
        self.capture_time += float(step_dt)
        if not force and self.capture_elapsed + 1e-12 < self.sample_period:
            return
        while self.capture_elapsed >= self.sample_period:
            self.capture_elapsed -= self.sample_period
        self.save_frame(
            gripper_state=gripper_state,
            phase_name=phase_name,
            commanded_speed=commanded_speed,
            commanded_dt=commanded_dt,
        )


    def get_movable_joint_indices(self):
        movable = []
        for joint_index in range(pb.getNumJoints(self.panda)):
            joint_type = pb.getJointInfo(self.panda, joint_index)[2]
            if joint_type in (pb.JOINT_REVOLUTE, pb.JOINT_PRISMATIC):
                movable.append(joint_index)
        return movable

    def get_joint_limits(self):
        lower_limits = []
        upper_limits = []
        joint_ranges = []
        movable = self.get_movable_joint_indices()
        for joint_index in movable:
            info = pb.getJointInfo(self.panda, joint_index)
            lower, upper = info[8], info[9]
            lower_limits.append(lower)
            upper_limits.append(upper)
            joint_ranges.append(upper - lower)
        self.ik_joint_indices = movable
        self.ik_lower_limits = lower_limits
        self.ik_upper_limits = upper_limits
        self.ik_joint_ranges = joint_ranges

    def solve_ik(self, pos, orn_quat):
        self.get_joint_limits()
        rest_poses = [pb.getJointState(self.panda, j)[0] for j in self.ik_joint_indices]
        joint_damping = [0.2] * len(self.ik_joint_indices)
        target_joints = pb.calculateInverseKinematics(
            self.panda,
            self.ee_link_index,
            pos,
            orn_quat,
            lowerLimits=self.ik_lower_limits,
            upperLimits=self.ik_upper_limits,
            jointRanges=self.ik_joint_ranges,
            restPoses=rest_poses,
            jointDamping=joint_damping,
            maxNumIterations=200,
            residualThreshold=1e-5,
        )
        return target_joints[: len(self.arm_joint_indices)]

    def reset_arm_joints(self, joint_positions):
        for joint_index, q in zip(self.arm_joint_indices, joint_positions):
            pb.resetJointState(self.panda, joint_index, float(q))

    def save_frame(
        self,
        gripper_state,
        phase_name=None,
        commanded_speed=np.nan,
        commanded_dt=np.nan,
    ):
        if self.demo_dir is None:
            return

        import open3d as o3d

        robot_pcd = self.get_system_virtual_pcd()
        robot_pcd = self.crop_pcd(robot_pcd, self.crop_min, self.crop_max)

        frame_dir = self.demo_dir / f"frame_{self.frame_index}"
        frame_dir.mkdir(exist_ok=True)
        self.frame_index += 1

        pcd_obj = o3d.geometry.PointCloud()
        pcd_obj.points = o3d.utility.Vector3dVector(robot_pcd[:, :3])
        pcd_obj.colors = o3d.utility.Vector3dVector(robot_pcd[:, 3:])
        o3d.io.write_point_cloud(str(frame_dir / "point_cloud.ply"), pcd_obj)

        arm_q = [pb.getJointState(self.panda, j)[0] for j in self.arm_joint_indices]
        np.savetxt(str(frame_dir / "arm_joints.txt"), np.asarray(arm_q), delimiter=",")
        np.savetxt(
            str(frame_dir / "hand_joints.txt"),
            np.atleast_1d([float(gripper_state)]),
            delimiter=",",
        )

        ee_pos, ee_orn = pb.getLinkState(
            self.panda,
            self.ee_link_index,
            computeForwardKinematics=True,
        )[:2]
        np.savetxt(str(frame_dir / "ee_pose.txt"), np.r_[ee_pos, ee_orn], delimiter=",")
        np.savetxt(str(frame_dir / "time.txt"), np.atleast_1d([self.capture_time]), delimiter=",")
        np.savetxt(str(frame_dir / "commanded_speed.txt"), np.atleast_1d([commanded_speed]), delimiter=",")
        np.savetxt(str(frame_dir / "commanded_dt.txt"), np.atleast_1d([commanded_dt]), delimiter=",")
        with open(frame_dir / "phase.txt", "w", encoding="utf-8") as f:
            f.write("unknown" if phase_name is None else str(phase_name))

        if getattr(self, "cube_id", None) is not None:
            cube_pos, cube_orn = pb.getBasePositionAndOrientation(self.cube_id)
            np.savetxt(str(frame_dir / "cube_pose.txt"), np.r_[cube_pos, cube_orn], delimiter=",")
        if getattr(self, "peg_id", None) is not None:
            peg_pos, peg_orn = pb.getBasePositionAndOrientation(self.peg_id)
            np.savetxt(str(frame_dir / "peg_pose.txt"), np.r_[peg_pos, peg_orn], delimiter=",")
        if getattr(self, "hole_pos", None) is not None:
            np.savetxt(str(frame_dir / "hole_pose.txt"), np.asarray(self.hole_pos), delimiter=",")
