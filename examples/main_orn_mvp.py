#!/usr/bin/env python3
import argparse
import math
import random
import shutil

import numpy as np
import pybullet as pb

from main_abla_1 import PandaSim, sample_xz_disk


ORN_CONDITIONS = {
    "R00": 0.0,
    "R15": 15.0,
    "R30": 30.0,
}


def sample_unit_vector():
    vec = np.random.normal(size=3)
    norm = float(np.linalg.norm(vec))
    if norm <= 1e-12:
        return np.array([0.0, 0.0, 1.0], dtype=float)
    return vec / norm


def sample_orientation_delta(max_degrees):
    max_degrees = float(max_degrees)
    if max_degrees <= 0.0:
        return np.array([0.0, 0.0, 1.0], dtype=float), 0.0, [0.0, 0.0, 0.0, 1.0]
    axis = sample_unit_vector()
    angle_rad = np.random.uniform(-math.radians(max_degrees), math.radians(max_degrees))
    quat = pb.getQuaternionFromAxisAngle(axis.tolist(), angle_rad)
    return axis, math.degrees(angle_rad), list(quat)


class OrientationMvpSim(PandaSim):
    def sample_reachable_random_start_with_quat(
        self,
        quat,
        x_bounds=(0.20, 0.60),
        z_bounds=(0.20, 0.60),
        max_attempts=200,
        max_error=0.025,
    ):
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
                    "orientation_used": "sampled_demo_quat",
                }
            rejected.append({"pos": pos.tolist(), "error": error})
        raise RuntimeError(
            f"Could not sample reachable random start after {max_attempts} attempts "
            f"within x={x_bounds}, z={z_bounds}, max_error={max_error}."
        )

    def run_pick_and_lift_orientation_mvp(
        self,
        condition_label="R00",
        orientation_max_degrees=0.0,
        corridor_start_radius=0.05,
        pre_grasp_radius=0.0,
        entry_dx=0.20,
        corridor_start_y=0.15,
        entry_dz=0.06,
        random_start_x_bounds=(0.20, 0.60),
        random_start_z_bounds=(0.20, 0.60),
        random_start_max_attempts=200,
        success_lift_height=0.20,
    ):
        cube = self.cube_pos()
        print(f"Cube at: {cube}")

        default_quat = self.default_orientation_quat
        axis, angle_degrees, delta_quat = sample_orientation_delta(orientation_max_degrees)
        _, contact_quat = pb.multiplyTransforms(
            [0.0, 0.0, 0.0],
            delta_quat,
            [0.0, 0.0, 0.0],
            default_quat,
        )

        random_start, random_start_q, random_start_info = self.sample_reachable_random_start_with_quat(
            contact_quat,
            x_bounds=random_start_x_bounds,
            z_bounds=random_start_z_bounds,
            max_attempts=random_start_max_attempts,
        )
        self.reset_to_ee_pose(random_start_q, gripper_width=0.04)

        base_pre_grasp = np.array([cube[0], cube[1], 0.22])
        base_corridor_start = np.array(
            [cube[0] - float(entry_dx), float(corridor_start_y), base_pre_grasp[2] + float(entry_dz)]
        )
        delta_start = sample_xz_disk(float(corridor_start_radius))
        delta_pre = np.zeros(3, dtype=float)
        if float(pre_grasp_radius) > 0.0:
            raise ValueError("Orientation MVP baseline requires pre_grasp_radius=0.0")
        corridor_start = base_corridor_start + delta_start
        pre_grasp = base_pre_grasp + delta_pre
        grasp = np.array([cube[0], cube[1], 0.04])
        lift = np.array([cube[0], cube[1], 0.30])

        corridor_reachable = self.ik_reachable(corridor_start, contact_quat)
        pre_grasp_reachable = self.ik_reachable(pre_grasp, contact_quat)
        grasp_reachable = self.ik_reachable(grasp, contact_quat)
        lift_reachable = self.ik_reachable(lift, contact_quat)
        if not all((corridor_reachable, pre_grasp_reachable, grasp_reachable, lift_reachable)):
            details = {
                "success": False,
                "criterion": "waypoint IK reachability before rollout",
                "corridor_start_reachable": bool(corridor_reachable),
                "pre_grasp_reachable": bool(pre_grasp_reachable),
                "grasp_reachable": bool(grasp_reachable),
                "lift_reachable": bool(lift_reachable),
            }
            self.write_orientation_metadata(
                condition_label,
                orientation_max_degrees,
                axis,
                angle_degrees,
                default_quat,
                delta_quat,
                contact_quat,
                cube,
                random_start,
                random_start_info,
                base_corridor_start,
                corridor_start,
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
                random_start_x_bounds,
                random_start_z_bounds,
                success_details=details,
            )
            return False, details

        self.write_orientation_metadata(
            condition_label,
            orientation_max_degrees,
            axis,
            angle_degrees,
            default_quat,
            delta_quat,
            contact_quat,
            cube,
            random_start,
            random_start_info,
            base_corridor_start,
            corridor_start,
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
            random_start_x_bounds,
            random_start_z_bounds,
        )

        print("1) Save random start")
        self.save_frame(gripper_state=-1.0, phase_name="random_start")

        print("2) Open gripper")
        self.open_gripper(duration=0.8, phase_name="open_gripper")

        print("3) Corridor start")
        self.move_ee(
            corridor_start,
            target_quat=contact_quat,
            speed=self.motion_speed,
            gripper_state=-1.0,
            phase_name="corridor_start",
        )

        print("4) Pre-grasp with sampled contact orientation")
        self.move_ee(
            pre_grasp,
            target_quat=contact_quat,
            speed=self.motion_speed,
            gripper_state=-1.0,
            phase_name="pre_grasp",
        )

        print("5) Descend with sampled contact orientation")
        self.move_ee(
            grasp,
            target_quat=contact_quat,
            speed=self.motion_speed,
            gripper_state=-1.0,
            phase_name="pick_grasp",
        )

        print("6) Close gripper")
        self.close_gripper(duration=1.2, phase_name="close_gripper")

        print("7) Lift with sampled contact orientation")
        self.move_ee(
            lift,
            target_quat=contact_quat,
            speed=self.motion_speed,
            gripper_state=1.0,
            phase_name="lift",
        )

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

    def write_orientation_metadata(
        self,
        condition_label,
        orientation_max_degrees,
        axis,
        angle_degrees,
        default_quat,
        delta_quat,
        contact_quat,
        cube,
        random_start,
        random_start_info,
        base_corridor_start,
        corridor_start,
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
        random_start_x_bounds,
        random_start_z_bounds,
        success_details=None,
    ):
        metadata = {
            "task": "cube_grasp_lift_orientation_mvp",
            "condition_label": condition_label,
            "orientation_max_degrees": float(orientation_max_degrees),
            "orientation_axis": np.asarray(axis, dtype=float).tolist(),
            "orientation_angle_degrees": float(angle_degrees),
            "default_quat_xyzw": list(default_quat),
            "orientation_delta_quat_xyzw": list(delta_quat),
            "contact_quat_xyzw": list(contact_quat),
            "orientation_applied_phases": [
                "random_start",
                "open_gripper",
                "corridor_start",
                "pre_grasp",
                "pick_grasp",
                "close_gripper",
                "lift",
            ],
            "cube_position": cube.tolist(),
            "random_start": random_start.tolist(),
            "random_start_info": random_start_info,
            "base_corridor_start": base_corridor_start.tolist(),
            "corridor_start": corridor_start.tolist(),
            "corridor_start_delta": delta_start.tolist(),
            "corridor_start_radius": float(corridor_start_radius),
            "base_pre_grasp": base_pre_grasp.tolist(),
            "pre_grasp": pre_grasp.tolist(),
            "pre_grasp_delta": delta_pre.tolist(),
            "pre_grasp_radius": float(pre_grasp_radius),
            "grasp": grasp.tolist(),
            "lift": lift.tolist(),
            "entry_dx": float(entry_dx),
            "corridor_start_y": float(corridor_start_y),
            "entry_dz": float(entry_dz),
            "random_start_x_bounds": [float(v) for v in random_start_x_bounds],
            "random_start_z_bounds": [float(v) for v in random_start_z_bounds],
        }
        if success_details is not None:
            metadata["success"] = success_details
        self.write_demo_metadata(metadata)


def condition_degrees(condition):
    if condition not in ORN_CONDITIONS:
        raise ValueError(f"Unknown orientation condition {condition!r}; choose one of {sorted(ORN_CONDITIONS)}")
    return ORN_CONDITIONS[condition]


def parse_args():
    parser = argparse.ArgumentParser(description="Collect cube pick-and-lift orientation/grasp-cue MVP data.")
    parser.add_argument("--output-dir", default=None, help="Write raw demos under this dataset root.")
    parser.add_argument("--num-demos", type=int, default=1, help="Number of successful demos to collect.")
    parser.add_argument("--seed", type=int, default=1, help="Random seed for collection.")
    parser.add_argument("--sample-hz", type=float, default=30.0, help="Frame save rate for raw demos.")
    parser.add_argument(
        "--orientation-condition",
        choices=sorted(ORN_CONDITIONS),
        default="R00",
        help="Orientation variation level for the MVP.",
    )
    parser.add_argument(
        "--orientation-max-degrees",
        type=float,
        default=None,
        help="Override the condition orientation range in degrees.",
    )
    parser.add_argument(
        "--corridor-start-radius",
        type=float,
        default=0.05,
        help="Spatial baseline entry radius in meters. MVP default is 0.05.",
    )
    parser.add_argument(
        "--pre-grasp-radius",
        type=float,
        default=0.0,
        help="Must stay 0.0 for the MVP baseline.",
    )
    parser.add_argument("--entry-dx", type=float, default=0.20)
    parser.add_argument("--corridor-start-y", type=float, default=0.15)
    parser.add_argument("--entry-dz", type=float, default=0.06)
    parser.add_argument("--random-start-x-min", type=float, default=0.20)
    parser.add_argument("--random-start-x-max", type=float, default=0.60)
    parser.add_argument("--random-start-z-min", type=float, default=0.20)
    parser.add_argument("--random-start-z-max", type=float, default=0.60)
    parser.add_argument("--random-start-max-attempts", type=int, default=200)
    parser.add_argument("--success-lift-height", type=float, default=0.20)
    parser.add_argument("--max-collection-attempts", type=int, default=0)
    parser.add_argument("--no-gui", action="store_true")
    parser.add_argument("--preview", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    if abs(float(args.pre_grasp_radius)) > 1e-12:
        raise ValueError("This MVP intentionally fixes --pre-grasp-radius at 0.0.")

    random.seed(args.seed)
    np.random.seed(args.seed)

    orientation_max_degrees = (
        condition_degrees(args.orientation_condition)
        if args.orientation_max_degrees is None
        else float(args.orientation_max_degrees)
    )
    max_attempts = args.max_collection_attempts
    if max_attempts <= 0:
        max_attempts = max(args.num_demos * 10, args.num_demos + 10)

    success_count = 0
    attempt_count = 0
    while success_count < args.num_demos:
        if attempt_count >= max_attempts:
            raise RuntimeError(
                f"Collected {success_count}/{args.num_demos} successful demos after "
                f"{attempt_count} attempts. Increase --max-collection-attempts or relax success thresholds."
            )

        demo_idx = success_count
        attempt_count += 1
        print(
            f"Collecting demo_{demo_idx}: attempt {attempt_count}/{max_attempts}, "
            f"condition={args.orientation_condition}, max_degrees={orientation_max_degrees}",
            flush=True,
        )

        sim = OrientationMvpSim(
            gui=not args.no_gui,
            gripper_orientation="default",
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

            is_success, _ = sim.run_pick_and_lift_orientation_mvp(
                condition_label=args.orientation_condition,
                orientation_max_degrees=orientation_max_degrees,
                corridor_start_radius=args.corridor_start_radius,
                pre_grasp_radius=args.pre_grasp_radius,
                entry_dx=args.entry_dx,
                corridor_start_y=args.corridor_start_y,
                entry_dz=args.entry_dz,
                random_start_x_bounds=(args.random_start_x_min, args.random_start_x_max),
                random_start_z_bounds=(args.random_start_z_min, args.random_start_z_max),
                random_start_max_attempts=args.random_start_max_attempts,
                success_lift_height=args.success_lift_height,
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
        f"Collection complete: {success_count}/{args.num_demos} successful demos "
        f"from {attempt_count} attempts.",
        flush=True,
    )


if __name__ == "__main__":
    main()
