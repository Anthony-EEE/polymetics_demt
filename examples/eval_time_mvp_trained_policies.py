#!/usr/bin/env python3
import argparse
import hashlib
import json
import math
import os
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
from main_time_mvp import TIME_CONDITIONS, TimeMvpSim, reciprocal_condition_metadata


DEFAULT_MODEL_ROOT = Path(
    "/scratch/prj/eng_demt_robot_learning/trained_models/temporal_vref_reciprocal_spatial_v2"
)
DEFAULT_OUTPUT = Path(
    "/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/temporal_vref_reciprocal_spatial_v2/policy_rollouts_seed628_paired_n50_h200"
)
DEFAULT_VIDEO_DIR = DEFAULT_OUTPUT / "videos"
RECIPROCAL_CONDITIONS = ("VR1P5", "V050_200", "VR3", "VR4")


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def file_sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def evaluation_protocol(args):
    return {
        "seed": int(args.seed),
        "num_rollouts": int(args.num_rollouts),
        "horizon": int(args.horizon),
        "sample_hz": float(args.sample_hz),
        "action_gap": int(args.action_gap),
        "action_dt": float(args.action_dt),
        "terminate_on_success": bool(args.terminate_on_success),
        "success_lift_height": float(args.success_lift_height),
        "num_points": int(args.num_points),
        "random_start_bounds": {"x": [0.2, 0.6], "y": [0.0, 0.0], "z": [0.2, 0.6]},
        "evaluation_distribution": "paired_varied_reachable_random_starts_and_rng",
        "rng_protocol": "reset Python, NumPy, Torch, CUDA, and point-cloud RNG to seed + rollout_index before each rollout",
    }


def create_paired_manifest(args):
    protocol = evaluation_protocol(args)
    rollouts = []
    start_rng = np.random.default_rng(np.random.SeedSequence([args.seed, 0x5354415254]))
    sim = TimeMvpSim(gui=False, output_dir=None, sample_hz=args.sample_hz)
    sim.playback_speed = 1000.0
    sim.setup()
    try:
        source_draw_index = 0
        while len(rollouts) < args.num_rollouts:
            if source_draw_index >= args.num_rollouts * args.random_start_max_attempts:
                raise RuntimeError("Could not generate enough reachable paired rollout starts")
            proposed = np.array(
                [start_rng.uniform(0.2, 0.6), 0.0, start_rng.uniform(0.2, 0.6)], dtype=float
            )
            source_draw_index += 1
            try:
                resolved, _, info = sim.sample_reachable_random_start(
                    x_bounds=(proposed[0], proposed[0]),
                    z_bounds=(proposed[2], proposed[2]),
                    max_attempts=1,
                )
            except RuntimeError:
                continue
            rollout_index = len(rollouts)
            rollout_seed = int(args.seed + rollout_index)
            rollouts.append(
                {
                    "rollout_index": rollout_index,
                    "source_draw_index": source_draw_index - 1,
                    "random_start": resolved.tolist(),
                    "manifest_ik_validation": info,
                    "rng_seed": rollout_seed,
                    "point_cloud_rng_seed": rollout_seed,
                }
            )
    finally:
        sim.close()
    return {
        "schema_version": 2,
        "condition_order": list(RECIPROCAL_CONDITIONS),
        "protocol": protocol,
        "rollouts": rollouts,
    }


def validate_paired_manifest(args, manifest):
    if manifest.get("condition_order") != list(RECIPROCAL_CONDITIONS):
        raise ValueError("Paired manifest condition_order must be exactly VR1P5, V050_200, VR3, VR4")
    if manifest.get("protocol") != evaluation_protocol(args):
        raise ValueError("Paired manifest protocol does not exactly match evaluation arguments")
    rollouts = manifest.get("rollouts", [])
    if len(rollouts) != args.num_rollouts:
        raise ValueError(f"Paired manifest has {len(rollouts)} rollouts, expected {args.num_rollouts}")
    for index, spec in enumerate(rollouts):
        if spec.get("rollout_index") != index:
            raise ValueError(f"Paired manifest rollout index mismatch at position {index}")
        if len(spec.get("random_start", [])) != 3:
            raise ValueError(f"Paired manifest rollout {index} has invalid random_start")
        if spec.get("rng_seed") != args.seed + index:
            raise ValueError(f"Paired manifest rollout {index} has invalid rng_seed")
        if spec.get("point_cloud_rng_seed") != args.seed + index:
            raise ValueError(f"Paired manifest rollout {index} has invalid point_cloud_rng_seed")
        start = [float(value) for value in spec["random_start"]]
        if abs(start[1]) > 1e-12 or not (0.2 <= start[0] <= 0.6) or not (0.2 <= start[2] <= 0.6):
            raise ValueError(f"Paired manifest rollout {index} start violates spatial bounds")
        if float((spec.get("manifest_ik_validation") or {}).get("realised_error", math.inf)) > 0.025:
            raise ValueError(f"Paired manifest rollout {index} was not IK validated")
    distinct_starts = {tuple(float(value) for value in spec["random_start"]) for spec in rollouts}
    if len(distinct_starts) != args.num_rollouts:
        raise ValueError(
            f"Paired manifest repeats fixed/random starts: {len(distinct_starts)} distinct for {args.num_rollouts} rollouts"
        )
    return rollouts


def checkpoints_from_manifest(path, conditions):
    manifest = load_json(path)
    if manifest.get("condition_order") != list(RECIPROCAL_CONDITIONS):
        raise ValueError("Checkpoint manifest condition_order must be exactly VR1P5, V050_200, VR3, VR4")
    checkpoints = manifest.get("checkpoints", {})
    resolved = {}
    for condition in conditions:
        record = checkpoints.get(condition)
        if not isinstance(record, dict) or not record.get("path"):
            raise KeyError(f"Checkpoint manifest missing explicit path for {condition}")
        checkpoint = Path(record["path"])
        if not checkpoint.is_file():
            raise FileNotFoundError(f"Checkpoint for {condition} does not exist: {checkpoint}")
        resolved[condition] = checkpoint
    if manifest.get("old_fixed_point_checkpoint_reused") is not False:
        raise ValueError("Checkpoint manifest must explicitly prohibit old fixed-point checkpoint reuse")
    for condition in RECIPROCAL_CONDITIONS:
        if checkpoints.get(condition, {}).get("source") != "corrected_spatial_v2_training_latest_checkpoint":
            raise ValueError(f"{condition} is not marked as a newly corrected trained checkpoint")
    return manifest, resolved


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
    paired_spec,
    condition,
    horizon,
    action_dt,
    success_lift_height,
    random_start_max_attempts,
    num_points,
    terminate_on_success,
    video_recorder=None,
    video_every_n_actions=2,
):
    rollout_seed = int(paired_spec["rng_seed"])
    point_cloud_rng_seed = int(paired_spec["point_cloud_rng_seed"])
    set_all_seeds(rollout_seed)
    random.seed(rollout_seed)
    np.random.seed(rollout_seed)

    reset_cube(sim)
    sim.reset()
    reset_cube(sim)

    random_start = np.asarray(paired_spec["random_start"], dtype=float)
    random_start, random_start_q, random_start_info = sim.sample_reachable_random_start(
        x_bounds=(random_start[0], random_start[0]),
        z_bounds=(random_start[2], random_start[2]),
        max_attempts=random_start_max_attempts,
    )
    sim.reset_to_ee_pose(random_start_q, gripper_width=0.04)

    gripper_state = -1.0
    pcd_rng = np.random.default_rng(point_cloud_rng_seed)
    policy.start_episode()
    obs_horizon = int(policy.policy.global_config.algo.horizon.observation_horizon)
    first_obs = current_obs(sim, gripper_state, num_points=num_points, pcd_rng=pcd_rng)
    obs_history = deque([first_obs] * obs_horizon, maxlen=obs_horizon)

    if video_recorder is not None:
        video_recorder.append(
            render_rgb(sim),
            [f"{condition} rollout {rollout_index:02d}", "shared varied reachable start"],
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
        "paired_spec": paired_spec,
        "rng_seed": rollout_seed,
        "point_cloud_rng_seed": point_cloud_rng_seed,
        "success": bool(is_success),
        "steps": step + 1,
        "time_to_success_s": float((step + 1) * action_dt) if is_success else None,
        "random_start": random_start.tolist(),
        "random_start_info": random_start_info,
        "final_cube_z": details["final_cube_z"],
        "success_details": details,
    }


def evaluate_condition(args, condition, ckpt, paired_rollouts, paired_manifest_sha256):
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
                condition=condition,
                horizon=args.horizon,
                action_dt=args.action_dt,
                success_lift_height=args.success_lift_height,
                paired_spec=paired_rollouts[i],
                random_start_max_attempts=args.random_start_max_attempts,
                num_points=args.num_points,
                terminate_on_success=args.terminate_on_success,
                video_recorder=video_recorder,
                video_every_n_actions=args.video_every_n_actions,
            )
            results.append(result)
            rollout_json = (
                args.output_dir / "rollouts" / condition / f"rollout_{i:03d}.json"
            )
            rollout_json.parent.mkdir(parents=True, exist_ok=True)
            rollout_json.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
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
    condition_config = {
        "duration_multiplier_range": [float(v) for v in TIME_CONDITIONS[condition]],
        **reciprocal_condition_metadata(condition),
    }
    return {
        "condition": condition,
        "checkpoint": str(ckpt),
        "device": device,
        "num_rollouts": len(results),
        "success_count": success_count,
        "success_rate": success_count / max(1, len(results)),
        "condition_config": condition_config,
        "protocol": evaluation_protocol(args),
        "paired_manifest": str(args.paired_manifest),
        "paired_manifest_sha256": paired_manifest_sha256,
        "checkpoint_manifest": str(args.checkpoint_manifest),
        "execution": {
            "slurm_job_id": os.environ.get("SLURM_JOB_ID"),
            "slurm_array_job_id": os.environ.get("SLURM_ARRAY_JOB_ID"),
            "slurm_array_task_id": os.environ.get("SLURM_ARRAY_TASK_ID"),
            "slurm_node_list": os.environ.get("SLURM_NODELIST"),
        },
        "evaluation_distribution": "paired_varied_reachable_random_starts_and_rng",
        "video_path": str(video_path) if args.save_videos else None,
        "rollouts": results,
    }


def wilson_interval(successes, total, z=1.959963984540054):
    if total <= 0:
        return [None, None]
    p = successes / total
    denominator = 1.0 + z * z / total
    center = (p + z * z / (2.0 * total)) / denominator
    margin = z * math.sqrt(p * (1.0 - p) / total + z * z / (4.0 * total * total)) / denominator
    return [center - margin, center + margin]


def condition_rollout_statistics(summary):
    rollouts = summary["rollouts"]
    successful = [row for row in rollouts if row["success"]]
    steps = [int(row["steps"]) for row in successful]
    times = [float(row["time_to_success_s"]) for row in successful]
    return {
        "success_count": len(successful),
        "failure_count": len(rollouts) - len(successful),
        "success_rate": len(successful) / len(rollouts),
        "success_rate_wilson_95": wilson_interval(len(successful), len(rollouts)),
        "successful_steps": {
            "mean": float(np.mean(steps)) if steps else None,
            "median": float(np.median(steps)) if steps else None,
            "min": min(steps) if steps else None,
            "max": max(steps) if steps else None,
        },
        "successful_time_to_success_s": {
            "mean": float(np.mean(times)) if times else None,
            "median": float(np.median(times)) if times else None,
            "min": min(times) if times else None,
            "max": max(times) if times else None,
        },
        "failure_rollout_indices": [int(row["rollout_index"]) for row in rollouts if not row["success"]],
    }
def merge_condition_summaries(args, checkpoint_manifest, paired_manifest, paired_manifest_sha256):
    expected_protocol = paired_manifest["protocol"]
    summaries = []
    paired_specs = None
    actual_starts = None
    for condition in RECIPROCAL_CONDITIONS:
        result_path = args.output_dir / f"temporal_{condition}_seed{args.seed}_n{args.num_rollouts}.json"
        if not result_path.is_file():
            raise FileNotFoundError(f"Missing condition rollout result: {result_path}")
        summary = load_json(result_path)
        if summary.get("condition") != condition:
            raise ValueError(f"{result_path} has condition={summary.get('condition')!r}")
        if summary.get("protocol") != expected_protocol:
            raise ValueError(f"{condition} protocol differs from paired manifest")
        if summary.get("paired_manifest_sha256") != paired_manifest_sha256:
            raise ValueError(f"{condition} paired manifest hash mismatch")
        expected_checkpoint = checkpoint_manifest["checkpoints"][condition]["path"]
        if summary.get("checkpoint") != expected_checkpoint:
            raise ValueError(f"{condition} checkpoint differs from explicit checkpoint manifest")
        condition_specs = [rollout.get("paired_spec") for rollout in summary.get("rollouts", [])]
        if condition_specs != paired_manifest["rollouts"]:
            raise ValueError(f"{condition} rollout paired specs differ from paired manifest")
        if paired_specs is None:
            paired_specs = condition_specs
        elif condition_specs != paired_specs:
            raise ValueError(f"{condition} paired starts/RNG differ from another condition")
        condition_actual_starts = [
            {
                "random_start": rollout.get("random_start"),
                "random_start_info": rollout.get("random_start_info"),
            }
            for rollout in summary.get("rollouts", [])
        ]
        if actual_starts is None:
            actual_starts = condition_actual_starts
        elif condition_actual_starts != actual_starts:
            raise ValueError(f"{condition} realised starts differ from another condition")
        for rollout in summary.get("rollouts", []):
            success_details = rollout.get("success_details", {})
            if success_details.get("criterion") != "final_cube_z >= min_cube_z":
                raise ValueError(f"{condition} has inconsistent success criterion")
            if float(success_details.get("min_cube_z", -1.0)) != float(
                expected_protocol["success_lift_height"]
            ):
                raise ValueError(f"{condition} has inconsistent success threshold")
        summaries.append(summary)

    summary_by_condition = {summary["condition"]: summary for summary in summaries}
    paired_discordances = {}
    for left_index, left in enumerate(RECIPROCAL_CONDITIONS):
        for right in RECIPROCAL_CONDITIONS[left_index + 1 :]:
            left_success = [bool(row["success"]) for row in summary_by_condition[left]["rollouts"]]
            right_success = [bool(row["success"]) for row in summary_by_condition[right]["rollouts"]]
            paired_discordances[f"{left}_vs_{right}"] = {
                "both_success": sum(a and b for a, b in zip(left_success, right_success)),
                f"{left}_only": sum(a and not b for a, b in zip(left_success, right_success)),
                f"{right}_only": sum((not a) and b for a, b in zip(left_success, right_success)),
                "both_failure": sum((not a) and (not b) for a, b in zip(left_success, right_success)),
            }

    aggregate = {
        **expected_protocol,
        "condition_order": list(RECIPROCAL_CONDITIONS),
        "checkpoint_manifest": str(args.checkpoint_manifest),
        "checkpoint_manifest_sha256": file_sha256(args.checkpoint_manifest),
        "training_job_ids": {
            condition: checkpoint_manifest["checkpoints"][condition].get("training_job_id")
            for condition in RECIPROCAL_CONDITIONS
        },
        "evaluation_job_ids": {
            condition: summary_by_condition[condition].get("execution", {}).get("slurm_job_id")
            for condition in RECIPROCAL_CONDITIONS
        },
        "paired_manifest": str(args.paired_manifest),
        "paired_manifest_sha256": paired_manifest_sha256,
        "paired_validation": {
            "condition_set_exact": True,
            "protocol_identical": True,
            "starts_and_rng_identical": True,
            "realised_starts_identical": True,
            "success_protocol_identical": True,
            "checkpoints_match_explicit_manifest": True,
        },
        "condition_statistics": {
            condition: condition_rollout_statistics(summary_by_condition[condition])
            for condition in RECIPROCAL_CONDITIONS
        },
        "paired_success_discordances": paired_discordances,
        "summaries": summaries,
    }
    aggregate_path = args.output_dir / f"summary_seed{args.seed}_n{args.num_rollouts}.json"
    aggregate_path.write_text(json.dumps(aggregate, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote validated aggregate {aggregate_path}")
    return aggregate_path


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
        default=list(RECIPROCAL_CONDITIONS),
        choices=sorted(TIME_CONDITIONS),
    )
    parser.add_argument("--checkpoint-manifest", type=Path, default=None)
    parser.add_argument("--paired-manifest", type=Path, default=None)
    parser.add_argument("--write-paired-manifest", type=Path, default=None)
    parser.add_argument("--generate-paired-manifest-only", action="store_true")
    parser.add_argument("--skip-aggregate", action="store_true")
    parser.add_argument("--merge-only", action="store_true")
    parser.add_argument("--epoch", type=int, default=40)
    parser.add_argument("--latest-checkpoint", action="store_true")
    parser.add_argument("--seed", type=int, default=628)
    parser.add_argument("--num-rollouts", type=int, default=50)
    parser.add_argument("--horizon", type=int, default=200)
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

    if tuple(args.conditions) not in (RECIPROCAL_CONDITIONS,) and not set(args.conditions).issubset(
        RECIPROCAL_CONDITIONS
    ):
        raise ValueError("Reciprocal evaluation only accepts VR1P5, V050_200, VR3, and VR4")
    if not args.terminate_on_success:
        raise ValueError("Reciprocal evaluation requires --terminate-on-success")
    if args.horizon != 200 or abs(args.action_dt - 0.25) > 1e-12:
        raise ValueError("Reciprocal evaluation requires horizon=200 and action_dt=0.25")
    if args.seed != 628 or args.num_rollouts != 50:
        raise ValueError("Reciprocal evaluation requires seed=628 and num_rollouts=50")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    if args.save_videos:
        args.video_dir.mkdir(parents=True, exist_ok=True)

    if args.write_paired_manifest is not None:
        manifest = create_paired_manifest(args)
        args.write_paired_manifest.parent.mkdir(parents=True, exist_ok=True)
        args.write_paired_manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote paired rollout manifest {args.write_paired_manifest}")
        if args.generate_paired_manifest_only:
            return

    if args.checkpoint_manifest is None or args.paired_manifest is None:
        raise ValueError("--checkpoint-manifest and --paired-manifest are required")
    checkpoint_manifest, checkpoint_paths = checkpoints_from_manifest(
        args.checkpoint_manifest, args.conditions
    )
    paired_manifest = load_json(args.paired_manifest)
    paired_rollouts = validate_paired_manifest(args, paired_manifest)
    paired_manifest_sha256 = file_sha256(args.paired_manifest)

    if args.merge_only:
        merge_condition_summaries(
            args, checkpoint_manifest, paired_manifest, paired_manifest_sha256
        )
        return

    summaries = []
    for condition in args.conditions:
        summary = evaluate_condition(
            args,
            condition,
            checkpoint_paths[condition],
            paired_rollouts,
            paired_manifest_sha256,
        )
        summaries.append(summary)
        out_path = args.output_dir / f"temporal_{condition}_seed{args.seed}_n{args.num_rollouts}.json"
        out_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    aggregate_path = None
    if not args.skip_aggregate:
        if tuple(args.conditions) != RECIPROCAL_CONDITIONS:
            raise ValueError("Aggregate writing requires exactly all four reciprocal conditions")
        aggregate_path = merge_condition_summaries(
            args, checkpoint_manifest, paired_manifest, paired_manifest_sha256
        )

    print("\nSuccess rates")
    for s in summaries:
        print(f"{s['condition']}: {s['success_count']}/{s['num_rollouts']} = {s['success_rate']:.3f}")
    if aggregate_path is not None:
        print(f"\nWrote {aggregate_path}")


if __name__ == "__main__":
    main()
