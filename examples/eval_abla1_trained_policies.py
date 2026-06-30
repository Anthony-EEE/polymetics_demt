#!/usr/bin/env python3
import argparse
import json
import random
import sys
from collections import deque
from pathlib import Path

import numpy as np
import pybullet as pb

from main_abla_1 import DEFAULT_CORRIDOR_START_CENTER, PandaSim, sample_xz_disk


ARCAP_ROOT = Path("/users/k23114984/code/arcap_policy/STEP2_train_policy")
DEFAULT_MODEL_ROOT = ARCAP_ROOT / "trained_models"
DEFAULT_OUTPUT = Path(
    "/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full/policy_rollouts_seed628"
)
DEFAULT_VIDEO_DIR = DEFAULT_OUTPUT / "videos"

CONDITIONS = {
    "P00": {"corridor_start_radius": 0.10, "pre_grasp_radius": 0.02},
    "P01": {"corridor_start_radius": 0.10, "pre_grasp_radius": 0.06},
    "P10": {"corridor_start_radius": 0.25, "pre_grasp_radius": 0.02},
    "P11": {"corridor_start_radius": 0.25, "pre_grasp_radius": 0.06},
}


def add_robomimic_to_path():
    root = str(ARCAP_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)


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


def latest_checkpoint(model_root, condition, epoch, experiment_template="abla1_{condition}_d30_seed1_2gap"):
    exp_root = Path(model_root) / experiment_template.format(condition=condition)
    run_dirs = [p for p in exp_root.iterdir() if p.is_dir()]
    if not run_dirs:
        raise FileNotFoundError(f"No run directories found under {exp_root}")
    run_dir = sorted(run_dirs)[-1]
    ckpt = run_dir / "models" / f"model_epoch_{epoch}.pth"
    if not ckpt.exists():
        def checkpoint_epoch(path):
            try:
                return int(path.stem.rsplit("_", 1)[1])
            except (IndexError, ValueError):
                return -1

        candidates = sorted((run_dir / "models").glob("model_epoch_*.pth"), key=checkpoint_epoch)
        if not candidates:
            raise FileNotFoundError(f"No checkpoints found under {run_dir / 'models'}")
        ckpt = candidates[-1]
    return ckpt


def load_policy(ckpt_path, cuda):
    add_robomimic_to_path()
    import robomimic.utils.file_utils as FileUtils
    import robomimic.utils.torch_utils as TorchUtils

    device = TorchUtils.get_torch_device(try_to_use_cuda=bool(cuda))
    policy, _ = FileUtils.policy_from_checkpoint(
        ckpt_path=str(ckpt_path),
        device=device,
        verbose=False,
    )
    return policy, str(device)


def maybe_add_text(frame, lines):
    try:
        import cv2
    except ImportError:
        return frame

    out = np.ascontiguousarray(frame.copy())
    x, y = 8, 18
    for line in lines:
        cv2.putText(out, line, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 3, cv2.LINE_AA)
        cv2.putText(out, line, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)
        y += 18
    return out


def render_rgb(sim):
    width = int(getattr(sim, "video_width", sim.image_width))
    height = int(getattr(sim, "video_height", sim.image_height))
    img = pb.getCameraImage(
        width,
        height,
        viewMatrix=sim.view_mat,
        projectionMatrix=sim.proj_mat,
    )
    rgb_buffer = np.asarray(img[2])
    if rgb_buffer.ndim == 1:
        rgb_buffer = rgb_buffer.reshape(height, width, 4)
    return np.asarray(rgb_buffer[:, :, :3], dtype=np.uint8)


class RolloutVideoRecorder:
    def __init__(self, path, fps):
        import imageio

        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.writer = imageio.get_writer(str(self.path), fps=int(fps))
        self.last_frame = None

    def append(self, frame, lines=None):
        if lines:
            frame = maybe_add_text(frame, lines)
        self.writer.append_data(frame)
        self.last_frame = frame

    def separator(self, n_frames=8):
        if self.last_frame is None:
            return
        blank = np.zeros_like(self.last_frame)
        for _ in range(int(n_frames)):
            self.writer.append_data(blank)

    def close(self):
        self.writer.close()


def fixed_size_pointcloud(sim, num_points, rng):
    pcd = sim.get_system_virtual_pcd()
    pcd = sim.crop_pcd(pcd, sim.crop_min, sim.crop_max)
    if pcd.shape[0] == 0:
        raise RuntimeError("Cropped point cloud is empty.")
    if pcd.shape[0] < num_points:
        repeats = num_points // pcd.shape[0] + 1
        pcd = np.tile(pcd, (repeats, 1))[:num_points]
    elif pcd.shape[0] > num_points:
        indices = rng.choice(pcd.shape[0], num_points, replace=False)
        pcd = pcd[indices]
    return pcd.astype(np.float32)


def current_obs(sim, gripper_state, num_points, pcd_rng):
    arm_q = np.asarray(
        [pb.getJointState(sim.panda, j)[0] for j in sim.arm_joint_indices],
        dtype=np.float32,
    )
    hand_q = np.asarray([gripper_state], dtype=np.float32)
    pointcloud = fixed_size_pointcloud(sim, num_points=num_points, rng=pcd_rng)

    return {
        "robot0_arm_joints": arm_q,
        "robot0_hand_joints": hand_q,
        "pointcloud": pointcloud,
    }


def stack_obs_history(obs_history):
    keys = obs_history[0].keys()
    return {key: np.stack([obs[key] for obs in obs_history], axis=0) for key in keys}


def reset_cube(sim):
    pb.resetBasePositionAndOrientation(sim.cube_id, [0.5, 0.5, 0.025], [0.0, 0.0, 0.0, 1.0])
    pb.resetBaseVelocity(sim.cube_id, [0.0, 0.0, 0.0], [0.0, 0.0, 0.0])
    for _ in range(30):
        sim._step_simulation(1.0 / 30.0)


def apply_policy_action(sim, action, action_dt):
    action = np.asarray(action, dtype=float)
    target_q = action[:7]
    gripper_state = float(np.clip(action[7], -1.0, 1.0))
    gripper_width = float(np.clip((1.0 - gripper_state) * 0.02, 0.0, 0.04))

    steps = max(1, int(round(float(action_dt) * sim.control_hz)))
    for _ in range(steps):
        sim._apply_arm(target_q, force=120, max_vel=1.5)
        sim._apply_gripper(gripper_width, force=120, max_vel=0.08)
        sim._step_simulation(sim.sim_dt)
    return gripper_state


def run_one_rollout(
    sim,
    policy,
    rollout_index,
    seed,
    condition,
    horizon,
    action_dt,
    success_lift_height,
    corridor_start_center,
    num_points,
    terminate_on_success,
    video_recorder=None,
    video_every_n_actions=2,
):
    reset_cube(sim)
    sim.reset()
    reset_cube(sim)

    base_corridor_start = np.asarray(corridor_start_center, dtype=float)
    delta_start = sample_xz_disk(CONDITIONS[condition]["corridor_start_radius"])
    corridor_start = base_corridor_start + delta_start
    corridor_start_q = sim.solve_ik(corridor_start, sim.default_orientation_quat)
    current_q = [pb.getJointState(sim.panda, j)[0] for j in sim.arm_joint_indices]
    sim.reset_arm_joints(corridor_start_q)
    realised = sim.ee_pos()
    sim.reset_arm_joints(current_q)
    corridor_error = float(np.linalg.norm(realised - corridor_start))
    if corridor_error > 0.025:
        raise RuntimeError(
            f"Sampled corridor_start is not reachable: target={corridor_start.tolist()}, "
            f"realised={realised.tolist()}, error={corridor_error:.6f}"
        )
    sim.reset_to_ee_pose(corridor_start_q, gripper_width=0.04)
    corridor_start_info = {
        "base_corridor_start": base_corridor_start.tolist(),
        "corridor_start_delta": delta_start.tolist(),
        "ik_realised_error": corridor_error,
        "realised_start": realised.tolist(),
    }

    gripper_state = -1.0
    pcd_rng = np.random.default_rng(seed + rollout_index)
    policy.start_episode()
    obs_horizon = int(policy.policy.global_config.algo.horizon.observation_horizon)
    first_obs = current_obs(sim, gripper_state, num_points=num_points, pcd_rng=pcd_rng)
    obs_history = deque([first_obs] * obs_horizon, maxlen=obs_horizon)

    if video_recorder is not None:
        video_recorder.append(
            render_rgb(sim),
            [
                f"{condition} rollout {rollout_index:02d}",
                "corridor_start",
            ],
        )

    for step in range(int(horizon)):
        obs = stack_obs_history(obs_history)
        action = policy(ob=obs)
        gripper_state = apply_policy_action(sim, action, action_dt=action_dt)
        obs_history.append(current_obs(sim, gripper_state, num_points=num_points, pcd_rng=pcd_rng))
        if video_recorder is not None and step % int(video_every_n_actions) == 0:
            video_recorder.append(
                render_rgb(sim),
                [
                    f"{condition} rollout {rollout_index:02d}",
                    f"step {step + 1:03d}",
                ],
            )
        if terminate_on_success and sim.cube_pos()[2] >= success_lift_height:
            break

    is_success, details = sim.success(min_cube_z=success_lift_height)
    if video_recorder is not None:
        video_recorder.append(
            render_rgb(sim),
            [
                f"{condition} rollout {rollout_index:02d}",
                f"success={bool(is_success)} z={details['final_cube_z']:.3f}",
            ],
        )
        video_recorder.separator()
    return {
        "condition": condition,
        "rollout_index": rollout_index,
        "success": bool(is_success),
        "steps": step + 1,
        "corridor_start": corridor_start.tolist(),
        "corridor_start_info": corridor_start_info,
        "final_cube_z": details["final_cube_z"],
        "success_details": details,
    }


def evaluate_condition(args, condition, ckpt):
    policy, device = load_policy(ckpt, cuda=args.cuda)
    print(f"[{condition}] checkpoint={ckpt}")
    print(f"[{condition}] device={device}")

    set_all_seeds(args.seed)

    sim = PandaSim(gui=args.gui, output_dir=None, sample_hz=args.sample_hz)
    sim.playback_speed = args.playback_speed
    sim.video_width = int(args.video_width)
    sim.video_height = int(args.video_height)
    sim.setup()

    results = []
    video_recorder = None
    if args.save_videos:
        video_path = args.video_dir / f"abla1_{condition}_seed{args.seed}_n{args.num_rollouts}.mp4"
        video_recorder = RolloutVideoRecorder(video_path, fps=args.video_fps)
        print(f"[{condition}] writing video={video_path}")
    try:
        for i in range(args.num_rollouts):
            result = run_one_rollout(
                sim=sim,
                policy=policy,
                rollout_index=i,
                seed=args.seed,
                condition=condition,
                horizon=args.horizon,
                action_dt=args.action_dt,
                success_lift_height=args.success_lift_height,
                corridor_start_center=args.corridor_start_center,
                num_points=args.num_points,
                terminate_on_success=args.terminate_on_success,
                video_recorder=video_recorder,
                video_every_n_actions=args.video_every_n_actions,
            )
            results.append(result)
            print(
                f"[{condition}] rollout {i:02d}: success={result['success']} "
                f"final_cube_z={result['final_cube_z']:.4f} "
                f"steps={result['steps']} corridor_start={np.round(result['corridor_start'], 4).tolist()}",
                flush=True,
            )
    finally:
        if video_recorder is not None:
            video_recorder.close()
        if sim.client is not None:
            pb.disconnect(sim.client)

    success_count = sum(int(r["success"]) for r in results)
    return {
        "condition": condition,
        "checkpoint": str(ckpt),
        "device": device,
        "num_rollouts": len(results),
        "success_count": success_count,
        "success_rate": success_count / max(1, len(results)),
        "condition_config": CONDITIONS[condition],
        "video_path": (
            str(args.video_dir / f"abla1_{condition}_seed{args.seed}_n{args.num_rollouts}.mp4")
            if args.save_videos
            else None
        ),
        "rollouts": results,
    }


def parse_args():
    parser = argparse.ArgumentParser(
        description="Evaluate ablation-1 trained diffusion policies in the PyBullet cube lift task."
    )
    parser.add_argument("--model-root", type=Path, default=DEFAULT_MODEL_ROOT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--experiment-template",
        default="abla1_{condition}_d30_seed1_2gap",
        help="Experiment directory template under --model-root. Must include {condition}.",
    )
    parser.add_argument("--conditions", nargs="+", default=["P00", "P01", "P10", "P11"], choices=sorted(CONDITIONS))
    parser.add_argument("--epoch", type=int, default=40)
    parser.add_argument("--seed", type=int, default=628)
    parser.add_argument("--num-rollouts", type=int, default=10)
    parser.add_argument("--horizon", type=int, default=80)
    parser.add_argument("--sample-hz", type=float, default=8.0)
    parser.add_argument("--action-gap", type=int, default=2)
    parser.add_argument("--action-dt", type=float, default=None)
    parser.add_argument("--num-points", type=int, default=10000)
    parser.add_argument("--success-lift-height", type=float, default=0.20)
    parser.add_argument(
        "--corridor-start-center",
        type=float,
        nargs=3,
        default=DEFAULT_CORRIDOR_START_CENTER,
        metavar=("X", "Y", "Z"),
    )
    parser.add_argument("--playback-speed", type=float, default=10.0)
    parser.add_argument("--cuda", action="store_true", help="Use CUDA if available.")
    parser.add_argument("--gui", action="store_true")
    parser.add_argument("--terminate-on-success", action="store_true")
    parser.add_argument("--save-videos", action="store_true")
    parser.add_argument("--video-dir", type=Path, default=DEFAULT_VIDEO_DIR)
    parser.add_argument("--video-fps", type=int, default=20)
    parser.add_argument("--video-every-n-actions", type=int, default=2)
    parser.add_argument("--video-width", type=int, default=320)
    parser.add_argument("--video-height", type=int, default=320)
    return parser.parse_args()


def main():
    args = parse_args()
    if args.action_dt is None:
        args.action_dt = float(args.action_gap) / float(args.sample_hz)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    summaries = []
    for condition in args.conditions:
        ckpt = latest_checkpoint(args.model_root, condition, args.epoch, args.experiment_template)
        summary = evaluate_condition(args, condition, ckpt)
        summaries.append(summary)
        out_path = args.output_dir / f"abla1_{condition}_seed{args.seed}_n{args.num_rollouts}.json"
        out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    aggregate = {
        "seed": args.seed,
        "num_rollouts": args.num_rollouts,
        "horizon": args.horizon,
        "action_dt": args.action_dt,
        "success_lift_height": args.success_lift_height,
        "summaries": summaries,
    }
    aggregate_path = args.output_dir / f"summary_seed{args.seed}_n{args.num_rollouts}.json"
    aggregate_path.write_text(json.dumps(aggregate, indent=2), encoding="utf-8")

    print("\nSuccess rates")
    for s in summaries:
        print(f"{s['condition']}: {s['success_count']}/{s['num_rollouts']} = {s['success_rate']:.3f}")
    print(f"\nWrote {aggregate_path}")


if __name__ == "__main__":
    main()
