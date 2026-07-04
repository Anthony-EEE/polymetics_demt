#!/usr/bin/env python3
import argparse
import json
import random
from collections import deque
from pathlib import Path

import numpy as np
import pybullet as pb

from eval_abla1_trained_policies import (
    RolloutVideoRecorder,
    apply_policy_action,
    current_obs,
    load_policy,
    render_rgb,
    reset_cube,
    set_all_seeds,
    stack_obs_history,
)
from main_time_mvp import TIME_CONDITIONS, TimeMvpSim


DEFAULT_MODEL_ROOT = Path(
    "/scratch/prj/eng_demt_robot_learning/trained_models/ar_guidance_temporal_T00_T100"
)
DEFAULT_OUTPUT = Path(
    "/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/ar_guidance_temporal_T00_T100/policy_rollouts_seed628_latest"
)
DEFAULT_VIDEO_DIR = DEFAULT_OUTPUT / "videos"


def checkpoint_epoch(path):
    try:
        return int(path.stem.rsplit("_", 1)[-1])
    except (IndexError, ValueError):
        return -1


def latest_checkpoint(
    model_root,
    condition,
    epoch,
    use_latest=False,
    experiment_template="{condition}/temporal_{condition}_d30_seed1_2gap",
):
    exp_root = Path(model_root) / experiment_template.format(condition=condition)
    run_dirs = [p for p in exp_root.iterdir() if p.is_dir()]
    if not run_dirs:
        raise FileNotFoundError(f"No run directories found under {exp_root}")
    run_dir = sorted(run_dirs)[-1]
    candidates = sorted((run_dir / "models").glob("model_epoch_*.pth"), key=checkpoint_epoch)
    if not candidates:
        raise FileNotFoundError(f"No checkpoints found under {run_dir / 'models'}")
    if use_latest:
        return candidates[-1]
    ckpt = run_dir / "models" / f"model_epoch_{epoch}.pth"
    if not ckpt.exists():
        ckpt = candidates[-1]
    return ckpt


def run_one_rollout(
    sim,
    policy,
    rollout_index,
    seed,
    condition,
    horizon,
    action_dt,
    success_lift_height,
    random_start,
    random_start_max_attempts,
    num_points,
    terminate_on_success,
    video_recorder=None,
    video_every_n_actions=2,
):
    reset_cube(sim)
    sim.reset()
    reset_cube(sim)

    random.seed(seed + rollout_index)
    np.random.seed(seed + rollout_index)

    random_start = np.asarray(random_start, dtype=float)
    random_start, random_start_q, random_start_info = sim.sample_reachable_random_start(
        x_bounds=(random_start[0], random_start[0]),
        z_bounds=(random_start[2], random_start[2]),
        max_attempts=random_start_max_attempts,
    )
    sim.reset_to_ee_pose(random_start_q, gripper_width=0.04)

    gripper_state = -1.0
    pcd_rng = np.random.default_rng(seed + rollout_index)
    policy.start_episode()
    obs_horizon = int(policy.policy.global_config.algo.horizon.observation_horizon)
    first_obs = current_obs(sim, gripper_state, num_points=num_points, pcd_rng=pcd_rng)
    obs_history = deque([first_obs] * obs_horizon, maxlen=obs_horizon)

    if video_recorder is not None:
        video_recorder.append(
            render_rgb(sim),
            [f"{condition} rollout {rollout_index:02d}", "fixed temporal eval start"],
        )

    for step in range(int(horizon)):
        obs = stack_obs_history(obs_history)
        action = policy(ob=obs)
        gripper_state = apply_policy_action(sim, action, action_dt=action_dt)
        obs_history.append(current_obs(sim, gripper_state, num_points=num_points, pcd_rng=pcd_rng))
        if video_recorder is not None and step % int(video_every_n_actions) == 0:
            video_recorder.append(
                render_rgb(sim),
                [f"{condition} rollout {rollout_index:02d}", f"step {step + 1:03d}"],
            )
        if terminate_on_success and sim.cube_pos()[2] >= success_lift_height:
            break

    is_success, details = sim.success(min_cube_z=success_lift_height)
    if video_recorder is not None:
        video_recorder.append(
            render_rgb(sim),
            [f"{condition} rollout {rollout_index:02d}", f"success={bool(is_success)} z={details['final_cube_z']:.3f}"],
        )
        video_recorder.separator()
    return {
        "condition": condition,
        "rollout_index": rollout_index,
        "success": bool(is_success),
        "steps": step + 1,
        "random_start": random_start.tolist(),
        "random_start_info": random_start_info,
        "final_cube_z": details["final_cube_z"],
        "success_details": details,
    }


def evaluate_condition(args, condition, ckpt):
    policy, device = load_policy(ckpt, cuda=args.cuda)
    print(f"[{condition}] checkpoint={ckpt}")
    print(f"[{condition}] device={device}")
    set_all_seeds(args.seed)

    sim = TimeMvpSim(gui=args.gui, output_dir=None, sample_hz=args.sample_hz)
    sim.playback_speed = args.playback_speed
    sim.video_width = int(args.video_width)
    sim.video_height = int(args.video_height)
    sim.setup()

    results = []
    video_path = args.video_dir / f"temporal_{condition}_seed{args.seed}_n{args.num_rollouts}.mp4"
    video_recorder = None
    if args.save_videos:
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
                random_start=(args.random_start_x, 0.0, args.random_start_z),
                random_start_max_attempts=args.random_start_max_attempts,
                num_points=args.num_points,
                terminate_on_success=args.terminate_on_success,
                video_recorder=video_recorder,
                video_every_n_actions=args.video_every_n_actions,
            )
            results.append(result)
            print(
                f"[{condition}] rollout {i:02d}: success={result['success']} "
                f"final_cube_z={result['final_cube_z']:.4f} steps={result['steps']} "
                f"random_start={np.round(result['random_start'], 4).tolist()}",
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
        "condition_config": {"duration_multiplier_range": TIME_CONDITIONS[condition]},
        "evaluation_distribution": "common_fixed_start",
        "video_path": str(video_path) if args.save_videos else None,
        "rollouts": results,
    }


def parse_args():
    parser = argparse.ArgumentParser(
        description="Evaluate temporal-MVP trained diffusion policies in the PyBullet cube lift task."
    )
    parser.add_argument("--model-root", type=Path, default=DEFAULT_MODEL_ROOT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--experiment-template",
        default="{condition}/temporal_{condition}_d30_seed1_2gap",
        help="Experiment directory template under --model-root. Must include {condition}.",
    )
    parser.add_argument(
        "--conditions",
        nargs="+",
        default=["T00", "T25", "T50", "T75", "T100"],
        choices=sorted(TIME_CONDITIONS),
    )
    parser.add_argument("--epoch", type=int, default=40)
    parser.add_argument("--latest-checkpoint", action="store_true")
    parser.add_argument("--seed", type=int, default=628)
    parser.add_argument("--num-rollouts", type=int, default=10)
    parser.add_argument("--horizon", type=int, default=80)
    parser.add_argument("--sample-hz", type=float, default=8.0)
    parser.add_argument("--action-gap", type=int, default=2)
    parser.add_argument("--action-dt", type=float, default=None)
    parser.add_argument("--num-points", type=int, default=10000)
    parser.add_argument("--success-lift-height", type=float, default=0.20)
    parser.add_argument("--random-start-x", type=float, default=0.40)
    parser.add_argument("--random-start-z", type=float, default=0.40)
    parser.add_argument("--random-start-max-attempts", type=int, default=200)
    parser.add_argument("--playback-speed", type=float, default=100.0)
    parser.add_argument("--cuda", action="store_true")
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
    if args.save_videos:
        args.video_dir.mkdir(parents=True, exist_ok=True)

    summaries = []
    for condition in args.conditions:
        ckpt = latest_checkpoint(
            args.model_root,
            condition,
            args.epoch,
            use_latest=args.latest_checkpoint,
            experiment_template=args.experiment_template,
        )
        summary = evaluate_condition(args, condition, ckpt)
        summaries.append(summary)
        out_path = args.output_dir / f"temporal_{condition}_seed{args.seed}_n{args.num_rollouts}.json"
        out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    aggregate = {
        "seed": args.seed,
        "num_rollouts": args.num_rollouts,
        "horizon": args.horizon,
        "action_dt": args.action_dt,
        "success_lift_height": args.success_lift_height,
        "evaluation_distribution": "common_fixed_start",
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
