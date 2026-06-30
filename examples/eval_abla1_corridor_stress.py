#!/usr/bin/env python3
import argparse
import json
import math
from collections import deque
from pathlib import Path

import numpy as np
import pybullet as pb

from eval_abla1_trained_policies import (
    CONDITIONS,
    DEFAULT_MODEL_ROOT,
    RolloutVideoRecorder,
    apply_policy_action,
    current_obs,
    latest_checkpoint,
    load_policy,
    render_rgb,
    reset_cube,
    set_all_seeds,
    stack_obs_history,
)
from main_abla_1 import DEFAULT_CORRIDOR_START_CENTER, PandaSim, sample_xz_disk


DEFAULT_OUTPUT = Path(
    "/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full/"
    "policy_rollouts_seed628_corridor_stress_r050"
)
DEFAULT_VIDEO_DIR = DEFAULT_OUTPUT / "videos"


def radius_tag(radius):
    return f"r{int(round(float(radius) * 100)):03d}"


def radius_range_tag(inner_radius, outer_radius):
    if float(inner_radius) <= 0.0:
        return radius_tag(outer_radius)
    return f"r{int(round(float(inner_radius) * 100)):03d}_{int(round(float(outer_radius) * 100)):03d}"


def sample_xz_annulus(inner_radius, outer_radius):
    inner_radius = float(inner_radius)
    outer_radius = float(outer_radius)
    if inner_radius < 0.0:
        raise ValueError(f"inner_radius must be non-negative, got {inner_radius}")
    if outer_radius < inner_radius:
        raise ValueError(f"outer_radius must be >= inner_radius, got {outer_radius} < {inner_radius}")
    if outer_radius <= 0.0:
        return np.zeros(3, dtype=float)
    if inner_radius <= 0.0:
        return sample_xz_disk(outer_radius)

    theta = np.random.uniform(0.0, 2.0 * math.pi)
    r = math.sqrt(np.random.uniform(inner_radius ** 2, outer_radius ** 2))
    return np.array([r * math.cos(theta), 0.0, r * math.sin(theta)], dtype=float)


def sample_reachable_corridor_stress_start(
    sim,
    stress_radius,
    stress_inner_radius,
    corridor_start_center,
    max_attempts,
    max_error,
    z_min,
    z_max,
):
    base_corridor_start = np.asarray(corridor_start_center, dtype=float)
    if base_corridor_start.shape != (3,):
        raise ValueError(f"corridor_start_center must contain 3 values, got {corridor_start_center!r}")

    current_q = [pb.getJointState(sim.panda, j)[0] for j in sim.arm_joint_indices]
    reasons = {}
    recent_rejections = []
    quat = sim.default_orientation_quat

    for attempt in range(1, int(max_attempts) + 1):
        delta = sample_xz_annulus(float(stress_inner_radius), float(stress_radius))
        pos = base_corridor_start + delta

        reject_reason = None
        if z_min is not None and pos[2] < float(z_min):
            reject_reason = "below_z_min"
        elif z_max is not None and pos[2] > float(z_max):
            reject_reason = "above_z_max"

        error = None
        q = None
        realised = None
        if reject_reason is None:
            q = sim.solve_ik(pos, quat)
            sim.reset_arm_joints(q)
            realised = sim.ee_pos()
            sim.reset_arm_joints(current_q)
            error = float(np.linalg.norm(realised - pos))
            if error > float(max_error):
                reject_reason = "ik_error"

        if reject_reason is None:
            return pos, q, {
                "attempts": attempt,
                "base_corridor_start": base_corridor_start.tolist(),
                "corridor_start_center": base_corridor_start.tolist(),
                "stress_radius": float(stress_radius),
                "stress_inner_radius": float(stress_inner_radius),
                "stress_delta": delta.tolist(),
                "stress_delta_norm": float(np.linalg.norm(delta)),
                "max_error": float(max_error),
                "realised_error": error,
                "realised_start": realised.tolist(),
                "rejected_count": attempt - 1,
                "rejection_reasons": reasons,
                "recent_rejections": recent_rejections[-20:],
                "z_min": None if z_min is None else float(z_min),
                "z_max": None if z_max is None else float(z_max),
            }

        reasons[reject_reason] = reasons.get(reject_reason, 0) + 1
        recent_rejections.append(
            {
                "pos": pos.tolist(),
                "delta": delta.tolist(),
                "reason": reject_reason,
                "ik_error": error,
            }
        )

    raise RuntimeError(
        f"Could not sample a reachable corridor stress start after {max_attempts} attempts "
        f"with radius=[{stress_inner_radius}, {stress_radius}], "
        f"z_min={z_min}, z_max={z_max}, max_error={max_error}. "
        f"Rejection reasons: {reasons}"
    )


def run_one_stress_rollout(
    sim,
    policy,
    rollout_index,
    seed,
    condition,
    horizon,
    action_dt,
    success_lift_height,
    stress_radius,
    stress_inner_radius,
    corridor_start_center,
    stress_max_attempts,
    stress_max_error,
    stress_z_min,
    stress_z_max,
    num_points,
    terminate_on_success,
    video_recorder=None,
    video_every_n_actions=2,
):
    reset_cube(sim)
    sim.reset()
    reset_cube(sim)

    stress_start, stress_start_q, stress_info = sample_reachable_corridor_stress_start(
        sim=sim,
        stress_radius=stress_radius,
        stress_inner_radius=stress_inner_radius,
        corridor_start_center=corridor_start_center,
        max_attempts=stress_max_attempts,
        max_error=stress_max_error,
        z_min=stress_z_min,
        z_max=stress_z_max,
    )
    sim.reset_to_ee_pose(stress_start_q, gripper_width=0.04)

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
                f"{condition} stress {rollout_index:02d}",
                f"r=[{stress_inner_radius:.2f},{stress_radius:.2f}] d={stress_info['stress_delta_norm']:.3f}",
            ],
        )

    steps_taken = 0
    for step in range(int(horizon)):
        obs = stack_obs_history(obs_history)
        action = policy(ob=obs)
        gripper_state = apply_policy_action(sim, action, action_dt=action_dt)
        obs_history.append(current_obs(sim, gripper_state, num_points=num_points, pcd_rng=pcd_rng))
        steps_taken = step + 1

        if video_recorder is not None and step % int(video_every_n_actions) == 0:
            video_recorder.append(
                render_rgb(sim),
                [
                    f"{condition} stress {rollout_index:02d}",
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
                f"{condition} stress {rollout_index:02d}",
                f"success={bool(is_success)} z={details['final_cube_z']:.3f}",
            ],
        )
        video_recorder.separator()

    return {
        "condition": condition,
        "rollout_index": rollout_index,
        "success": bool(is_success),
        "steps": steps_taken,
        "stress_start": stress_start.tolist(),
        "stress_info": stress_info,
        "final_ee": sim.ee_pos().tolist(),
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
    tag = radius_range_tag(args.stress_inner_radius, args.stress_radius)
    if args.save_videos:
        video_path = args.video_dir / f"abla1_corridor_stress_{condition}_{tag}_seed{args.seed}_n{args.num_rollouts}.mp4"
        video_recorder = RolloutVideoRecorder(video_path, fps=args.video_fps)
        print(f"[{condition}] writing video={video_path}")

    try:
        for i in range(args.num_rollouts):
            result = run_one_stress_rollout(
                sim=sim,
                policy=policy,
                rollout_index=i,
                seed=args.seed,
                condition=condition,
                horizon=args.horizon,
                action_dt=args.action_dt,
                success_lift_height=args.success_lift_height,
                stress_radius=args.stress_radius,
                stress_inner_radius=args.stress_inner_radius,
                corridor_start_center=args.corridor_start_center,
                stress_max_attempts=args.stress_max_attempts,
                stress_max_error=args.stress_max_error,
                stress_z_min=args.stress_z_min,
                stress_z_max=args.stress_z_max,
                num_points=args.num_points,
                terminate_on_success=args.terminate_on_success,
                video_recorder=video_recorder,
                video_every_n_actions=args.video_every_n_actions,
            )
            results.append(result)
            print(
                f"[{condition}] stress rollout {i:02d}: success={result['success']} "
                f"final_cube_z={result['final_cube_z']:.4f} "
                f"d={result['stress_info']['stress_delta_norm']:.4f} "
                f"attempts={result['stress_info']['attempts']} "
                f"start={np.round(result['stress_start'], 4).tolist()}",
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
        "stress_radius": float(args.stress_radius),
        "stress_inner_radius": float(args.stress_inner_radius),
        "stress_z_min": None if args.stress_z_min is None else float(args.stress_z_min),
        "stress_z_max": None if args.stress_z_max is None else float(args.stress_z_max),
        "corridor_start_center": [float(v) for v in args.corridor_start_center],
        "video_path": (
            str(args.video_dir / f"abla1_corridor_stress_{condition}_{tag}_seed{args.seed}_n{args.num_rollouts}.mp4")
            if args.save_videos
            else None
        ),
        "rollouts": results,
    }


def parse_args():
    parser = argparse.ArgumentParser(
        description="Evaluate ablation-1 policies from a broad corridor-entry stress distribution."
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
    parser.add_argument("--stress-radius", type=float, default=0.50)
    parser.add_argument("--stress-inner-radius", type=float, default=0.0)
    parser.add_argument("--stress-max-attempts", type=int, default=1000)
    parser.add_argument("--stress-max-error", type=float, default=0.025)
    parser.add_argument("--stress-z-min", type=float, default=0.04)
    parser.add_argument("--stress-z-max", type=float, default=0.70)
    parser.add_argument(
        "--corridor-start-center",
        type=float,
        nargs=3,
        default=DEFAULT_CORRIDOR_START_CENTER,
        metavar=("X", "Y", "Z"),
    )
    parser.add_argument("--entry-dx", type=float, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--entry-dz", type=float, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--corridor-start-y", type=float, default=None, help=argparse.SUPPRESS)
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
    if args.stress_inner_radius < 0.0:
        raise ValueError(f"--stress-inner-radius must be non-negative, got {args.stress_inner_radius}")
    if args.stress_radius < args.stress_inner_radius:
        raise ValueError(
            f"--stress-radius must be >= --stress-inner-radius, got "
            f"{args.stress_radius} < {args.stress_inner_radius}"
        )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    if args.save_videos:
        args.video_dir.mkdir(parents=True, exist_ok=True)

    summaries = []
    tag = radius_range_tag(args.stress_inner_radius, args.stress_radius)
    for condition in args.conditions:
        ckpt = latest_checkpoint(args.model_root, condition, args.epoch, args.experiment_template)
        summary = evaluate_condition(args, condition, ckpt)
        summaries.append(summary)
        out_path = args.output_dir / f"abla1_corridor_stress_{condition}_{tag}_seed{args.seed}_n{args.num_rollouts}.json"
        out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    aggregate = {
        "seed": args.seed,
        "num_rollouts": args.num_rollouts,
        "horizon": args.horizon,
        "action_dt": args.action_dt,
        "success_lift_height": args.success_lift_height,
        "stress_radius": float(args.stress_radius),
        "stress_inner_radius": float(args.stress_inner_radius),
        "stress_z_min": None if args.stress_z_min is None else float(args.stress_z_min),
        "stress_z_max": None if args.stress_z_max is None else float(args.stress_z_max),
        "corridor_start_center": [float(v) for v in args.corridor_start_center],
        "summaries": summaries,
    }
    aggregate_path = args.output_dir / f"summary_corridor_stress_{tag}_seed{args.seed}_n{args.num_rollouts}.json"
    aggregate_path.write_text(json.dumps(aggregate, indent=2), encoding="utf-8")

    print("\nCorridor stress success rates")
    for s in summaries:
        print(f"{s['condition']}: {s['success_count']}/{s['num_rollouts']} = {s['success_rate']:.3f}")
    print(f"\nWrote {aggregate_path}")


if __name__ == "__main__":
    main()
