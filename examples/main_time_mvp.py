#!/usr/bin/env python3
import argparse
import math
import random
import shutil

import numpy as np

from main_abla_1 import PandaSim


TIME_CONDITIONS = {
    "T00": (1.00, 1.00),
    "T25": (0.75, 1.25),
    "T50": (0.50, 1.50),
    "T75": (0.25, 1.75),
    "T100": (0.00, 2.00),
}
MIN_PHASE_DURATION_FRAMES = 1

PHASES = (
    "open_gripper",
    "corridor_start",
    "pre_grasp",
    "pick_grasp",
    "close_gripper",
    "lift",
)

BASE_DURATIONS = {
    "open_gripper": 0.8,
    "corridor_start": 2.4,
    "pre_grasp": 3.2,
    "pick_grasp": 1.75,
    "close_gripper": 1.2,
    "lift": 2.5,
}


def sample_phase_multipliers(condition):
    low, high = TIME_CONDITIONS[condition]
    if abs(low - high) <= 1e-12:
        return {phase: 1.0 for phase in PHASES}
    return {phase: float(np.random.uniform(low, high)) for phase in PHASES}


def phase_duration_plan(multipliers, sample_period):
    min_duration = float(MIN_PHASE_DURATION_FRAMES) * float(sample_period)
    before = {
        phase: float(BASE_DURATIONS[phase] * multipliers[phase])
        for phase in PHASES
    }
    after = {
        phase: max(duration, min_duration)
        for phase, duration in before.items()
    }
    before_frames = {
        phase: 0 if duration <= 0.0 else int(math.ceil(duration / float(sample_period) - 1e-12))
        for phase, duration in before.items()
    }
    after_frames = {
        phase: max(MIN_PHASE_DURATION_FRAMES, int(math.ceil(duration / float(sample_period) - 1e-12)))
        for phase, duration in after.items()
    }
    clamped = {
        phase: after[phase] > before[phase] + 1e-12
        for phase in PHASES
    }
    return before, after, before_frames, after_frames, clamped, min_duration


class TimeMvpSim(PandaSim):
    def run_pick_and_lift_time_mvp(
        self,
        condition_label="T00",
        corridor_start_radius=0.05,
        pre_grasp_radius=0.0,
        entry_dx=0.20,
        corridor_start_y=0.15,
        entry_dz=0.06,
        random_start=(0.40, 0.0, 0.40),
        random_start_max_attempts=200,
        success_lift_height=0.20,
    ):
        if condition_label not in TIME_CONDITIONS:
            raise ValueError(f"Unknown temporal condition {condition_label!r}")
        if abs(float(pre_grasp_radius)) > 1e-12:
            raise ValueError("Temporal MVP fixes pre_grasp_radius at 0.0.")

        cube = self.cube_pos()
        print(f"Cube at: {cube}")

        random_start = np.asarray(random_start, dtype=float)
        random_start, random_start_q, random_start_info = self.sample_reachable_random_start(
            x_bounds=(random_start[0], random_start[0]),
            z_bounds=(random_start[2], random_start[2]),
            max_attempts=random_start_max_attempts,
        )
        self.reset_to_ee_pose(random_start_q, gripper_width=0.04)

        base_pre_grasp = np.array([cube[0], cube[1], 0.22])
        base_corridor_start = np.array(
            [cube[0] - float(entry_dx), float(corridor_start_y), base_pre_grasp[2] + float(entry_dz)]
        )
        delta_start = np.zeros(3, dtype=float)
        delta_pre = np.zeros(3, dtype=float)
        corridor_start = base_corridor_start + delta_start
        pre_grasp = base_pre_grasp + delta_pre
        grasp = np.array([cube[0], cube[1], 0.04])
        lift = np.array([cube[0], cube[1], 0.30])

        waypoints_ok = {
            "corridor_start": self.ik_reachable(corridor_start),
            "pre_grasp": self.ik_reachable(pre_grasp),
            "grasp": self.ik_reachable(grasp),
            "lift": self.ik_reachable(lift),
        }
        multipliers = sample_phase_multipliers(condition_label)
        (
            target_durations_before_clamp,
            target_durations,
            target_duration_frames_before_clamp,
            target_duration_frames,
            phase_duration_clamped,
            min_phase_duration_seconds,
        ) = phase_duration_plan(multipliers, self.sample_period)

        self.write_time_metadata(
            condition_label=condition_label,
            cube=cube,
            random_start=random_start,
            random_start_info=random_start_info,
            base_corridor_start=base_corridor_start,
            corridor_start=corridor_start,
            delta_start=delta_start,
            corridor_start_radius=corridor_start_radius,
            base_pre_grasp=base_pre_grasp,
            pre_grasp=pre_grasp,
            delta_pre=delta_pre,
            pre_grasp_radius=pre_grasp_radius,
            grasp=grasp,
            lift=lift,
            entry_dx=entry_dx,
            corridor_start_y=corridor_start_y,
            entry_dz=entry_dz,
            phase_duration_multipliers=multipliers,
            base_phase_durations=BASE_DURATIONS,
            target_phase_durations_before_clamp=target_durations_before_clamp,
            target_phase_durations=target_durations,
            target_phase_duration_frames_before_clamp=target_duration_frames_before_clamp,
            target_phase_duration_frames=target_duration_frames,
            phase_duration_clamped=phase_duration_clamped,
            min_phase_duration_frames=MIN_PHASE_DURATION_FRAMES,
            min_phase_duration_seconds=min_phase_duration_seconds,
            condition_multiplier_range=TIME_CONDITIONS[condition_label],
            waypoint_reachability=waypoints_ok,
        )
        if not all(waypoints_ok.values()):
            details = {
                "success": False,
                "criterion": "waypoint IK reachability before rollout",
                "waypoint_reachability": waypoints_ok,
            }
            self.write_demo_metadata({"success": details})
            return False, details

        print("1) Save random start")
        self.save_frame(gripper_state=-1.0, phase_name="random_start")

        print("2) Open gripper")
        self.open_gripper(duration=target_durations["open_gripper"], phase_name="open_gripper")

        print("3) Corridor start")
        self.move_ee(
            corridor_start,
            duration=target_durations["corridor_start"],
            gripper_state=-1.0,
            phase_name="corridor_start",
        )

        print("4) Pre-grasp")
        self.move_ee(
            pre_grasp,
            duration=target_durations["pre_grasp"],
            gripper_state=-1.0,
            phase_name="pre_grasp",
        )

        print("5) Descend")
        self.move_ee(
            grasp,
            duration=target_durations["pick_grasp"],
            gripper_state=-1.0,
            phase_name="pick_grasp",
        )

        print("6) Close gripper")
        self.close_gripper(duration=target_durations["close_gripper"], phase_name="close_gripper")

        print("7) Lift")
        self.move_ee(
            lift,
            duration=target_durations["lift"],
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
        return is_success, success_details

    def write_time_metadata(
        self,
        condition_label,
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
        phase_duration_multipliers,
        base_phase_durations,
        target_phase_durations_before_clamp,
        target_phase_durations,
        target_phase_duration_frames_before_clamp,
        target_phase_duration_frames,
        phase_duration_clamped,
        min_phase_duration_frames,
        min_phase_duration_seconds,
        condition_multiplier_range,
        waypoint_reachability,
    ):
        metadata = {
            "task": "cube_grasp_lift_time_mvp",
            "experiment_track": "temporal",
            "condition": condition_label,
            "condition_label": condition_label,
            "sample_hz": float(self.sample_hz),
            "sample_period": float(self.sample_period),
            "condition_multiplier_range": [float(v) for v in condition_multiplier_range],
            "phase_duration_multipliers": {k: float(v) for k, v in phase_duration_multipliers.items()},
            "base_phase_durations": {k: float(v) for k, v in base_phase_durations.items()},
            "target_phase_durations_before_clamp": {
                k: float(v) for k, v in target_phase_durations_before_clamp.items()
            },
            "target_phase_durations": {k: float(v) for k, v in target_phase_durations.items()},
            "target_phase_duration_frames_before_clamp": {
                k: int(v) for k, v in target_phase_duration_frames_before_clamp.items()
            },
            "target_phase_duration_frames": {k: int(v) for k, v in target_phase_duration_frames.items()},
            "phase_duration_clamped": {k: bool(v) for k, v in phase_duration_clamped.items()},
            "min_phase_duration_frames": int(min_phase_duration_frames),
            "min_phase_duration_seconds": float(min_phase_duration_seconds),
            "phase_duration_clamp_rule": "target_phase_duration_seconds = max(raw_duration_seconds, min_phase_duration_frames / sample_hz)",
            "timing_applied_phases": list(PHASES),
            "orientation_mode": "default_full_trajectory",
            "default_quat_xyzw": list(self.default_orientation_quat),
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
            "waypoint_reachability": waypoint_reachability,
        }
        self.write_demo_metadata(metadata)


def parse_args():
    parser = argparse.ArgumentParser(description="Collect cube pick-and-lift temporal-threshold MVP data.")
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--num-demos", type=int, default=1)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--sample-hz", type=float, default=30.0)
    parser.add_argument("--time-condition", choices=sorted(TIME_CONDITIONS), default="T00")
    parser.add_argument("--corridor-start-radius", type=float, default=0.05)
    parser.add_argument("--pre-grasp-radius", type=float, default=0.0)
    parser.add_argument("--entry-dx", type=float, default=0.20)
    parser.add_argument("--corridor-start-y", type=float, default=0.15)
    parser.add_argument("--entry-dz", type=float, default=0.06)
    parser.add_argument("--random-start-x", type=float, default=0.40)
    parser.add_argument("--random-start-z", type=float, default=0.40)
    parser.add_argument("--random-start-max-attempts", type=int, default=200)
    parser.add_argument("--success-lift-height", type=float, default=0.20)
    parser.add_argument("--max-collection-attempts", type=int, default=0)
    parser.add_argument("--no-gui", action="store_true")
    parser.add_argument("--preview", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    if abs(float(args.pre_grasp_radius)) > 1e-12:
        raise ValueError("Temporal MVP intentionally fixes --pre-grasp-radius at 0.0.")

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
                f"Collected {success_count}/{args.num_demos} successful demos after "
                f"{attempt_count} attempts."
            )

        demo_idx = success_count
        attempt_count += 1
        print(
            f"Collecting demo_{demo_idx}: attempt {attempt_count}/{max_attempts}, "
            f"condition={args.time_condition}",
            flush=True,
        )

        sim = TimeMvpSim(
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

            is_success, _ = sim.run_pick_and_lift_time_mvp(
                condition_label=args.time_condition,
                corridor_start_radius=args.corridor_start_radius,
                pre_grasp_radius=args.pre_grasp_radius,
                entry_dx=args.entry_dx,
                corridor_start_y=args.corridor_start_y,
                entry_dz=args.entry_dz,
                random_start=(args.random_start_x, 0.0, args.random_start_z),
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
        finally:
            sim.close()

    print(
        f"Collection complete: {success_count}/{args.num_demos} successful demos "
        f"from {attempt_count} attempts.",
        flush=True,
    )


if __name__ == "__main__":
    main()
