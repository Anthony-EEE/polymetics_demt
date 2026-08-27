#!/usr/bin/env python3
"""Evaluate a trained obstacle-transport policy after a scripted grasp/lift.

The policy is never queried during reset, approach, grasp, close, or lift.  A
rollout begins only after ``scripted_grasp_to_transport_start`` confirms both
that the cube is lifted and that the end effector reached the sampled transport
height.
"""

import argparse
import json
import random
import sys
from collections import deque
from pathlib import Path

import numpy as np
import pybullet as pb

from main_obstacle_transport import (
    CONDITIONS,
    EXPERIMENT_GROUP,
    ObstacleTransportSim,
    sample_task_spec,
)
from rollout_contract import file_sha256, stream_seed, write_json


ARCAP_ROOT = Path("/users/k23114984/code/arcap_policy/STEP2_train_policy")


def set_all_seeds(seed):
    np.random.seed(seed)
    random.seed(seed)
    try:
        import torch
    except ImportError:
        return
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def load_policy(checkpoint, cuda):
    arcap_root = str(ARCAP_ROOT)
    if arcap_root not in sys.path:
        sys.path.insert(0, arcap_root)
    import robomimic.utils.file_utils as FileUtils
    import robomimic.utils.torch_utils as TorchUtils

    device = TorchUtils.get_torch_device(try_to_use_cuda=bool(cuda))
    policy, _ = FileUtils.policy_from_checkpoint(
        ckpt_path=str(checkpoint),
        device=device,
        verbose=False,
    )
    return policy, str(device)


def fixed_size_pointcloud(sim, num_points, rng):
    pointcloud = sim.get_system_virtual_pcd()
    pointcloud = sim.crop_pcd(pointcloud, sim.crop_min, sim.crop_max)
    if pointcloud.shape[0] == 0:
        raise RuntimeError("Cropped point cloud is empty")
    if pointcloud.shape[0] < num_points:
        repeats = num_points // pointcloud.shape[0] + 1
        pointcloud = np.tile(pointcloud, (repeats, 1))[:num_points]
    elif pointcloud.shape[0] > num_points:
        indices = rng.choice(pointcloud.shape[0], num_points, replace=False)
        pointcloud = pointcloud[indices]
    return pointcloud.astype(np.float32)


def current_obs(sim, gripper_state, num_points, pointcloud_rng):
    arm_q = np.asarray(
        [pb.getJointState(sim.panda, joint)[0] for joint in sim.arm_joint_indices],
        dtype=np.float32,
    )
    return {
        "robot0_arm_joints": arm_q,
        "robot0_hand_joints": np.asarray([gripper_state], dtype=np.float32),
        "pointcloud": fixed_size_pointcloud(sim, num_points, pointcloud_rng),
    }


def stacked_obs(obs_history):
    return {
        key: np.stack([observation[key] for observation in obs_history], axis=0)
        for key in obs_history[0]
    }


def apply_policy_action(sim, action, action_dt):
    action = np.asarray(action, dtype=float).reshape(-1)
    if action.size < 8:
        raise ValueError(f"Expected at least 8 policy action values, received {action.size}")
    target_q = action[:7]
    gripper_state = float(np.clip(action[7], -1.0, 1.0))
    gripper_width = float(np.clip((1.0 - gripper_state) * 0.02, 0.0, 0.04))
    steps = max(1, int(round(float(action_dt) * sim.control_hz)))
    for _ in range(steps):
        sim._apply_arm(target_q, force=120, max_vel=1.5)
        sim._apply_gripper(gripper_width, force=120, max_vel=0.08)
        sim._step_simulation(sim.sim_dt)
    return gripper_state


def capture_policy_start_state(sim):
    box_pose = pb.getBasePositionAndOrientation(sim.cube_id)
    ee_state = pb.getLinkState(sim.panda, sim.ee_link_index, computeForwardKinematics=True)
    return {
        "sim_step": int(sim._sim_step_count),
        "box_position": list(box_pose[0]),
        "box_quaternion_xyzw": list(box_pose[1]),
        "ee_position": list(ee_state[0]),
        "ee_quaternion_xyzw": list(ee_state[1]),
        "gripper_state": 1.0,
    }


def run_one_rollout(sim, policy, rollout_index, spec, args):
    sim.reset_task_state(spec["box_initial_position"])
    video_path = args.output_dir / "videos" / f"rollout_{rollout_index:03d}.mp4"
    if args.save_videos:
        sim.start_video(video_path, fps=args.video_fps)

    try:
        # No policy method is called before this entire scripted phase succeeds.
        setup_success, setup_details = sim.scripted_grasp_to_transport_start(spec, save=False)
        setup_end_sim_step = int(sim._sim_step_count)
        if not setup_success:
            return {
                "group": EXPERIMENT_GROUP,
                "rollout_index": rollout_index,
                "success": False,
                "failure_stage": "scripted_setup",
                "policy_started": False,
                "policy_call_count": 0,
                "spec": spec,
                "setup_details": setup_details,
                "video_path": str(video_path) if args.save_videos else None,
            }

        policy_start_state = capture_policy_start_state(sim)
        policy.start_episode()
        pointcloud_rng = np.random.default_rng(
            stream_seed(args.seed, rollout_index, 0x504344)
        )
        obs_horizon = int(policy.policy.global_config.algo.horizon.observation_horizon)
        first_obs = current_obs(sim, 1.0, args.num_points, pointcloud_rng)
        obs_history = deque([first_obs] * obs_horizon, maxlen=obs_horizon)

        gripper_state = 1.0
        policy_call_count = 0
        first_policy_call_sim_step = None
        last_action = None
        success = False
        success_details = None
        for step in range(args.horizon):
            if first_policy_call_sim_step is None:
                first_policy_call_sim_step = int(sim._sim_step_count)
            action = policy(ob=stacked_obs(obs_history))
            policy_call_count += 1
            last_action = np.asarray(action, dtype=float)
            gripper_state = apply_policy_action(sim, last_action, args.action_dt)
            obs_history.append(
                current_obs(sim, gripper_state, args.num_points, pointcloud_rng)
            )
            success, success_details = sim.transport_success()
            if success and args.terminate_on_success:
                break

        if last_action is not None and not success:
            apply_policy_action(sim, last_action, args.settle_seconds)
            success, success_details = sim.transport_success()

        execution_order_valid = bool(
            setup_details["grasped"]
            and setup_details["transport_height_reached"]
            and first_policy_call_sim_step >= setup_end_sim_step
        )
        if not execution_order_valid:
            raise RuntimeError("Policy was invoked before successful scripted grasp/lift")
        return {
            "group": EXPERIMENT_GROUP,
            "rollout_index": rollout_index,
            "success": bool(success),
            "failure_stage": None if success else "policy_transport_or_release",
            "steps": step + 1,
            "policy_started": True,
            "policy_call_count": policy_call_count,
            "execution_order": [
                "sample_box_start",
                "reset_scene",
                "scripted_fixed_orientation_approach",
                "scripted_grasp",
                "scripted_lift_to_sampled_transport_height",
                "policy_start_episode",
                "policy_inference",
            ],
            "execution_order_valid": execution_order_valid,
            "scripted_setup_end_sim_step": setup_end_sim_step,
            "first_policy_call_sim_step": first_policy_call_sim_step,
            "policy_inference_start": policy_start_state,
            "spec": spec,
            "setup_details": setup_details,
            "success_details": success_details,
            "video_path": str(video_path) if args.save_videos else None,
        }
    finally:
        sim.close_video()


def parse_args():
    parser = argparse.ArgumentParser(
        description="Roll out an obstacle-transport policy after scripted grasp and lift"
    )
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--condition", default="policy", help="Policy label, e.g. L, R, or combined")
    parser.add_argument("--num-rollouts", type=int, default=10)
    parser.add_argument("--seed", type=int, default=628)
    parser.add_argument("--horizon", type=int, default=200)
    parser.add_argument("--sample-hz", type=float, default=8.0)
    parser.add_argument("--action-gap", type=int, default=2)
    parser.add_argument("--action-dt", type=float, default=None)
    parser.add_argument("--num-points", type=int, default=10000)
    parser.add_argument("--settle-seconds", type=float, default=1.5)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--cuda", action="store_true")
    parser.add_argument("--gui", action="store_true")
    parser.add_argument("--save-videos", action="store_true")
    parser.add_argument("--video-fps", type=int, default=10)
    parser.add_argument("--terminate-on-success", action="store_true")
    parser.add_argument("--playback-speed", type=float, default=1000.0)
    return parser.parse_args()


def main():
    args = parse_args()
    if not args.checkpoint.is_file():
        raise FileNotFoundError(args.checkpoint)
    if args.num_rollouts <= 0 or args.horizon <= 0:
        raise ValueError("--num-rollouts and --horizon must be positive")
    if args.action_dt is None:
        args.action_dt = float(args.action_gap) / float(args.sample_hz)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    policy, device = load_policy(args.checkpoint, args.cuda)
    sim = ObstacleTransportSim(gui=args.gui, output_dir=None, sample_hz=args.sample_hz)
    sim.playback_speed = args.playback_speed
    sim.setup()
    results = []
    try:
        for rollout_index in range(args.num_rollouts):
            rollout_seed = stream_seed(args.seed, rollout_index, 0x52554E)
            set_all_seeds(rollout_seed)
            rng = np.random.default_rng(rollout_seed)
            # L/R have exactly the same rollout-start distribution. The route
            # waypoint is not used by the policy evaluator.
            spec = sample_task_spec(rng, CONDITIONS[0], rollout_index)
            spec["rollout_seed"] = rollout_seed
            spec["route_waypoint_used_during_rollout"] = False
            result = run_one_rollout(sim, policy, rollout_index, spec, args)
            results.append(result)
            write_json(
                args.output_dir / "rollouts" / f"rollout_{rollout_index:03d}.json",
                result,
            )
            print(
                f"rollout={rollout_index:03d} success={result['success']} "
                f"setup={result['setup_details'].get('reason')} "
                f"policy_calls={result['policy_call_count']}",
                flush=True,
            )
    finally:
        sim.close_video()
        if sim.client is not None:
            pb.disconnect(sim.client)

    success_count = sum(int(row["success"]) for row in results)
    summary = {
        "group": EXPERIMENT_GROUP,
        "task": "scripted_grasp_and_lift_then_policy_obstacle_transport",
        "condition": args.condition,
        "checkpoint": str(args.checkpoint),
        "checkpoint_sha256": file_sha256(args.checkpoint),
        "device": device,
        "seed": args.seed,
        "num_rollouts": len(results),
        "success_count": success_count,
        "success_rate": success_count / max(len(results), 1),
        "protocol": {
            "policy_boundary": "after successful scripted fixed-orientation grasp and sampled-height lift",
            "horizon": args.horizon,
            "sample_hz": args.sample_hz,
            "action_gap": args.action_gap,
            "action_dt": args.action_dt,
            "num_points": args.num_points,
            "settle_seconds": args.settle_seconds,
        },
        "rollouts": results,
    }
    summary_path = args.output_dir / "summary.json"
    write_json(summary_path, summary)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
