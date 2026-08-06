#!/usr/bin/env python3
import argparse
import json
import os
import random
import sys
from collections import deque
from pathlib import Path

import numpy as np
import pybullet as pb

from main_abla_1 import DEFAULT_CORRIDOR_START_CENTER, PandaSim, sample_xz_disk
from rollout_contract import (
    checkpoints_from_manifest,
    condition_rollout_statistics,
    file_sha256,
    load_json,
    paired_discordances,
    stream_seed,
    validate_rollout_files,
    write_json,
)


ARCAP_ROOT = Path("/users/k23114984/code/arcap_policy/STEP2_train_policy")
DEFAULT_MODEL_ROOT = Path(
    "/scratch/prj/eng_demt_robot_learning/trained_models/ar_guidance_spatial_S15_S35"
)
DEFAULT_OUTPUT = Path(
    "/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/ar_guidance_spatial_S15_S35/policy_rollouts_seed628_latest"
)
DEFAULT_VIDEO_DIR = DEFAULT_OUTPUT / "videos"

CONDITIONS = {
    "S15": {"corridor_start_radius": 0.15, "pre_grasp_radius": 0.036},
    "S20": {"corridor_start_radius": 0.20, "pre_grasp_radius": 0.048},
    "S25": {"corridor_start_radius": 0.25, "pre_grasp_radius": 0.060},
    "S30": {"corridor_start_radius": 0.30, "pre_grasp_radius": 0.072},
    "S35": {"corridor_start_radius": 0.35, "pre_grasp_radius": 0.084},
}
CONDITION_ORDER = tuple(CONDITIONS)
TRO_POSITION_MVP0_CONDITIONS = {
    "START15_APP6": {"corridor_start_radius": 0.15, "pre_grasp_radius": 0.060},
    "START35_APP6": {"corridor_start_radius": 0.35, "pre_grasp_radius": 0.060},
    "START25_APP3P6": {"corridor_start_radius": 0.25, "pre_grasp_radius": 0.036},
    "START25_APP8P4": {"corridor_start_radius": 0.25, "pre_grasp_radius": 0.084},
}
TRO_POSITION_MVP0_ORDER = tuple(TRO_POSITION_MVP0_CONDITIONS)
TRO_POSITION_CONFIRMATION_CONDITIONS = {
    "START15_APP6": {"corridor_start_radius": 0.15, "pre_grasp_radius": 0.060},
    "START35_APP6": {"corridor_start_radius": 0.35, "pre_grasp_radius": 0.060},
    "START25_APP3P6": {"corridor_start_radius": 0.25, "pre_grasp_radius": 0.036},
    "START25_APP6": {"corridor_start_radius": 0.25, "pre_grasp_radius": 0.060},
    "START25_APP8P4": {"corridor_start_radius": 0.25, "pre_grasp_radius": 0.084},
}
TRO_POSITION_CONFIRMATION_ORDER = tuple(TRO_POSITION_CONFIRMATION_CONDITIONS)
TRO_POSITION_STAGE2_CONDITIONS = {
    "START15_APP6": {"corridor_start_radius": 0.15, "pre_grasp_radius": 0.060},
    "START35_APP6": {"corridor_start_radius": 0.35, "pre_grasp_radius": 0.060},
    "START25_APP3P6": {"corridor_start_radius": 0.25, "pre_grasp_radius": 0.036},
    "START25_APP6": {"corridor_start_radius": 0.25, "pre_grasp_radius": 0.060},
    "START25_APP8P4": {"corridor_start_radius": 0.25, "pre_grasp_radius": 0.084},
}
TRO_POSITION_STAGE2_ORDER = tuple(TRO_POSITION_STAGE2_CONDITIONS)
TRO_POSITION_COMPOSITION_CONDITIONS = {
    "START15_APP3P6": {"corridor_start_radius": 0.15, "pre_grasp_radius": 0.036},
    "START15_APP6": {"corridor_start_radius": 0.15, "pre_grasp_radius": 0.060},
    "START15_APP8P4": {"corridor_start_radius": 0.15, "pre_grasp_radius": 0.084},
    "START25_APP3P6": {"corridor_start_radius": 0.25, "pre_grasp_radius": 0.036},
    "START25_APP6": {"corridor_start_radius": 0.25, "pre_grasp_radius": 0.060},
    "START25_APP8P4": {"corridor_start_radius": 0.25, "pre_grasp_radius": 0.084},
    "START35_APP3P6": {"corridor_start_radius": 0.35, "pre_grasp_radius": 0.036},
    "START35_APP6": {"corridor_start_radius": 0.35, "pre_grasp_radius": 0.060},
    "START35_APP8P4": {"corridor_start_radius": 0.35, "pre_grasp_radius": 0.084},
}
TRO_POSITION_COMPOSITION_ORDER = tuple(TRO_POSITION_COMPOSITION_CONDITIONS)


def active_conditions(args):
    if args.experiment_profile == "tro_position_mvp0":
        return TRO_POSITION_MVP0_CONDITIONS
    if args.experiment_profile == "tro_position_confirmation":
        return TRO_POSITION_CONFIRMATION_CONDITIONS
    if args.experiment_profile in (
        "tro_position_stage2",
        "tro_position_stage2_idood",
    ):
        return TRO_POSITION_STAGE2_CONDITIONS
    if args.experiment_profile == "tro_position_composition":
        return TRO_POSITION_COMPOSITION_CONDITIONS
    return CONDITIONS


def active_condition_order(args):
    return tuple(active_conditions(args))


def accepted_start_manifest_condition_orders(args):
    orders = {active_condition_order(args)}
    if args.experiment_profile == "tro_position_composition":
        # Composition deliberately reuses the immutable Stage 2 and RMAX40
        # state manifests. Their state/RNG contract was frozen before the
        # four missing conditions existed, so their metadata retains the
        # five-condition Stage 2 order.
        orders.add(TRO_POSITION_STAGE2_ORDER)
    return orders


def evaluation_protocol(args):
    protocol = {
        "seed": int(args.seed),
        "num_rollouts": int(args.num_rollouts),
        "horizon": int(args.horizon),
        "sample_hz": float(args.sample_hz),
        "action_gap": int(args.action_gap),
        "action_dt": float(args.action_dt),
        "terminate_on_success": bool(args.terminate_on_success),
        "success_lift_height": float(args.success_lift_height),
        "num_points": int(args.num_points),
        "corridor_start_center": [float(v) for v in args.corridor_start_center],
        "shared_start_radius_min": float(args.shared_start_radius_min),
        "shared_start_radius_max": float(args.shared_start_radius),
        "corridor_start_max_error": float(args.corridor_start_max_error),
        "evaluation_distribution": evaluation_distribution(args),
        "rng_protocol": "independent spatial/runtime/point-cloud streams; Python, NumPy, Torch and CUDA reset per rollout",
    }
    if args.bank_id is not None:
        protocol["bank_id"] = str(args.bank_id)
    return protocol


def radius_tag(radius):
    cm = float(radius) * 100.0
    if np.isclose(cm, round(cm)):
        return f"r{int(round(cm))}"
    return "r" + f"{float(radius):.3f}".rstrip("0").rstrip(".").replace(".", "p")


def start_sampling_mode(args):
    if float(args.shared_start_radius_min) > 0.0:
        return "xz_annulus"
    return "xz_disk"


def evaluation_distribution(args):
    if args.bank_id is not None:
        return str(args.bank_id)
    outer = radius_tag(args.shared_start_radius)
    if start_sampling_mode(args) == "xz_annulus":
        inner = radius_tag(args.shared_start_radius_min)
        return f"paired_shared_absolute_corridor_starts_annulus_{inner}_{outer}"
    return f"paired_shared_absolute_corridor_starts_{outer}"


def sample_xz_annulus(inner_radius, outer_radius, rng=None):
    rng = np.random if rng is None else rng
    inner_radius = float(inner_radius)
    outer_radius = float(outer_radius)
    theta = rng.uniform(0.0, 2.0 * np.pi)
    radius = np.sqrt(rng.uniform(inner_radius * inner_radius, outer_radius * outer_radius))
    return np.array([radius * np.cos(theta), 0.0, radius * np.sin(theta)], dtype=float)


def sample_shared_start_delta(args, rng=None):
    rng = np.random if rng is None else rng
    outer_radius = float(args.shared_start_radius)
    if start_sampling_mode(args) == "xz_annulus":
        return sample_xz_annulus(args.shared_start_radius_min, outer_radius, rng=rng)
    theta = rng.uniform(0.0, 2.0 * np.pi)
    radius = outer_radius * np.sqrt(rng.uniform(0.0, 1.0))
    return np.array([radius * np.cos(theta), 0.0, radius * np.sin(theta)], dtype=float)


def xz_radius(delta):
    delta = np.asarray(delta, dtype=float)
    return float(np.linalg.norm(delta[[0, 2]]))


def xz_angle(delta):
    delta = np.asarray(delta, dtype=float)
    return float(np.arctan2(delta[2], delta[0]))


def validate_start_sampling_args(args):
    inner_radius = float(args.shared_start_radius_min)
    outer_radius = float(args.shared_start_radius)
    if inner_radius < 0.0:
        raise ValueError("--shared-start-radius-min must be >= 0.")
    if outer_radius <= 0.0:
        raise ValueError("--shared-start-radius must be > 0.")
    if inner_radius >= outer_radius:
        raise ValueError("--shared-start-radius-min must be smaller than --shared-start-radius.")


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


def latest_checkpoint(model_root, condition, epoch, experiment_template="{condition}/spatial_{condition}_d30_seed1_2gap"):
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


def solve_ik_with_error(sim, target_pos, quat=None):
    if quat is None:
        quat = sim.default_orientation_quat
    target_pos = np.asarray(target_pos, dtype=float)
    current_q = [pb.getJointState(sim.panda, j)[0] for j in sim.arm_joint_indices]
    q = sim.solve_ik(target_pos, quat)
    sim.reset_arm_joints(q)
    realised = sim.ee_pos()
    sim.reset_arm_joints(current_q)
    error = float(np.linalg.norm(realised - target_pos))
    return q, realised, error


def generate_shared_corridor_starts(args):
    base_corridor_start = np.asarray(args.corridor_start_center, dtype=float)
    spatial_rng = np.random.default_rng(stream_seed(args.seed, 0, 0x53504154))
    starts = []
    records = []
    distribution = evaluation_distribution(args)
    sampling_mode = start_sampling_mode(args)

    sim = PandaSim(gui=args.gui, output_dir=None, sample_hz=args.sample_hz)
    sim.playback_speed = args.playback_speed
    sim.setup()
    try:
        for rollout_index in range(args.num_rollouts):
            rejected = []
            for attempt in range(1, int(args.max_start_sample_attempts) + 1):
                delta = sample_shared_start_delta(args, rng=spatial_rng)
                normalized_delta = delta / float(args.shared_start_radius)
                target = base_corridor_start + delta
                _, realised, error = solve_ik_with_error(sim, target)

                if error <= float(args.corridor_start_max_error):
                    radial_distance = xz_radius(delta)
                    starts.append(target)
                    records.append(
                        {
                            "rollout_index": rollout_index,
                            "state_id": (
                                f"{args.bank_id}_state_{rollout_index:03d}"
                                if args.bank_id is not None
                                else f"seed{args.seed}_state_{rollout_index:03d}"
                            ),
                            "attempts": attempt,
                            "max_error": float(args.corridor_start_max_error),
                            "start_sampling_mode": sampling_mode,
                            "evaluation_distribution": distribution,
                            "shared_start_radius_min": float(args.shared_start_radius_min),
                            "shared_start_radius_max": float(args.shared_start_radius),
                            "shared_start_radius": float(args.shared_start_radius),
                            "normalized_delta": normalized_delta.tolist(),
                            "corridor_start_delta": delta.tolist(),
                            "radial_distance_from_center": radial_distance,
                            "start_angle_rad": xz_angle(delta),
                            "corridor_start": target.tolist(),
                            "realised_start": realised.tolist(),
                            "ik_error": error,
                            "rejected_count": attempt - 1,
                            "recent_rejections": rejected[-10:],
                            "rng_seed": stream_seed(args.seed, rollout_index, 0x52554E),
                            "point_cloud_rng_seed": stream_seed(args.seed, rollout_index, 0x504344),
                        }
                    )
                    break

                rejected.append(
                    {
                        "start_sampling_mode": sampling_mode,
                        "shared_start_radius_min": float(args.shared_start_radius_min),
                        "shared_start_radius_max": float(args.shared_start_radius),
                        "normalized_delta": normalized_delta.tolist(),
                        "corridor_start_delta": delta.tolist(),
                        "radial_distance_from_center": xz_radius(delta),
                        "start_angle_rad": xz_angle(delta),
                        "corridor_start": target.tolist(),
                        "ik_error": error,
                    }
                )
            else:
                raise RuntimeError(
                    "Could not generate shared reachable corridor starts for "
                    f"rollout {rollout_index} after {args.max_start_sample_attempts} attempts."
                )
    finally:
        if sim.client is not None:
            pb.disconnect(sim.client)

    print(
        f"Generated {len(starts)} shared reachable corridor starts with "
        f"distribution={distribution} for conditions={args.conditions}."
    )
    if len({tuple(start.tolist()) for start in starts}) != int(args.num_rollouts):
        raise RuntimeError("Generated Position manifest contains repeated corridor starts")
    return starts, records


def write_start_manifest(args, path, starts, records):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema_version": 2,
        "condition_order": list(active_condition_order(args)),
        "protocol": evaluation_protocol(args),
        "seed": int(args.seed),
        "num_rollouts": int(args.num_rollouts),
        "sample_hz": float(args.sample_hz),
        "corridor_start_center": [float(v) for v in args.corridor_start_center],
        "start_sampling_mode": start_sampling_mode(args),
        "shared_start_radius_min": float(args.shared_start_radius_min),
        "shared_start_radius_max": float(args.shared_start_radius),
        "shared_start_radius": float(args.shared_start_radius),
        "corridor_start_max_error": float(args.corridor_start_max_error),
        "max_start_sample_attempts": int(args.max_start_sample_attempts),
        "evaluation_distribution": evaluation_distribution(args),
        "shared_corridor_starts": [np.asarray(start, dtype=float).tolist() for start in starts],
        "shared_start_records": records,
    }
    write_json(path, manifest)
    print(f"Wrote shared start manifest={path}")


def load_start_manifest(args, path):
    path = Path(path)
    manifest = load_json(path)
    manifest_order = tuple(manifest.get("condition_order", ()))
    if manifest_order not in accepted_start_manifest_condition_orders(args):
        raise ValueError("Position start manifest has an invalid condition_order")
    if manifest.get("protocol") != evaluation_protocol(args):
        raise ValueError("Position start manifest protocol does not exactly match evaluation arguments")
    starts = [np.asarray(start, dtype=float) for start in manifest["shared_corridor_starts"]]
    records = manifest["shared_start_records"]
    if len(starts) != int(args.num_rollouts):
        raise ValueError(
            f"Manifest {path} has {len(starts)} starts, expected {args.num_rollouts}."
        )
    if len(records) != int(args.num_rollouts):
        raise ValueError(
            f"Manifest {path} has {len(records)} start records, expected {args.num_rollouts}."
        )
    expected_radius = float(args.shared_start_radius)
    actual_radius = float(
        manifest.get("shared_start_radius_max", manifest.get("shared_start_radius", expected_radius))
    )
    if not np.isclose(actual_radius, expected_radius):
        raise ValueError(
            f"Manifest {path} shared_start_radius={actual_radius}, expected {expected_radius}."
        )
    expected_min_radius = float(args.shared_start_radius_min)
    actual_min_radius = float(manifest.get("shared_start_radius_min", 0.0))
    if not np.isclose(actual_min_radius, expected_min_radius):
        raise ValueError(
            f"Manifest {path} shared_start_radius_min={actual_min_radius}, expected {expected_min_radius}."
        )
    expected_distribution = evaluation_distribution(args)
    actual_distribution = manifest.get("evaluation_distribution", expected_distribution)
    if actual_distribution != expected_distribution:
        raise ValueError(
            f"Manifest {path} evaluation_distribution={actual_distribution!r}, "
            f"expected {expected_distribution!r}."
        )
    if len({tuple(start.tolist()) for start in starts}) != int(args.num_rollouts):
        raise ValueError(f"Manifest {path} does not contain {args.num_rollouts} distinct starts")
    legacy_indices = manifest.get("legacy_rollout_indices")
    if legacy_indices is None:
        legacy_indices = list(range(int(args.num_rollouts)))
    if len(legacy_indices) != int(args.num_rollouts):
        raise ValueError(f"Manifest {path} legacy_rollout_indices length mismatch")
    for index, (start, record, legacy_index) in enumerate(zip(starts, records, legacy_indices)):
        if record.get("rollout_index") != legacy_index or not np.allclose(start, record.get("corridor_start")):
            raise ValueError(f"Manifest {path} rollout ordering/content mismatch at {index}")
        if record.get("rng_seed") != stream_seed(args.seed, legacy_index, 0x52554E):
            raise ValueError(f"Manifest {path} runtime RNG seed mismatch at {index}")
        if record.get("point_cloud_rng_seed") != stream_seed(args.seed, legacy_index, 0x504344):
            raise ValueError(f"Manifest {path} point-cloud RNG seed mismatch at {index}")
        if float(record.get("ik_error", float("inf"))) > float(args.corridor_start_max_error):
            raise ValueError(f"Manifest {path} rollout {index} was not IK validated")
    print(f"Loaded {len(starts)} shared corridor starts from manifest={path}")
    return starts, records


def build_aggregate(args, summaries, shared_corridor_starts, shared_start_records):
    summary_by_condition = {summary["condition"]: summary for summary in summaries}
    condition_order = active_condition_order(args)
    return {
        **evaluation_protocol(args),
        "condition_order": list(condition_order),
        "checkpoint_manifest": str(args.checkpoint_manifest),
        "checkpoint_manifest_sha256": file_sha256(args.checkpoint_manifest),
        "start_manifest": str(args.start_manifest),
        "start_manifest_sha256": file_sha256(args.start_manifest),
        "evaluation_distribution": evaluation_distribution(args),
        "corridor_start_center": [float(v) for v in args.corridor_start_center],
        "start_sampling_mode": start_sampling_mode(args),
        "shared_start_radius_min": float(args.shared_start_radius_min),
        "shared_start_radius_max": float(args.shared_start_radius),
        "shared_start_radius": float(args.shared_start_radius),
        "corridor_start_max_error": float(args.corridor_start_max_error),
        "max_start_sample_attempts": int(args.max_start_sample_attempts),
        "shared_corridor_starts": [start.tolist() for start in shared_corridor_starts],
        "shared_start_records": shared_start_records,
        "condition_statistics": {
            condition: condition_rollout_statistics(summary_by_condition[condition])
            for condition in condition_order
        },
        "paired_success_discordances": paired_discordances(condition_order, summary_by_condition),
        "summaries": [summary_by_condition[condition] for condition in condition_order],
    }


def load_condition_summaries(args, checkpoint_manifest):
    condition_order = active_condition_order(args)
    if tuple(args.conditions) != condition_order:
        raise ValueError(f"Position merge requires exact condition order {condition_order}")
    summaries = []
    start_manifest_sha256 = file_sha256(args.start_manifest)
    for condition in condition_order:
        path = args.output_dir / f"spatial_{condition}_seed{args.seed}_n{args.num_rollouts}.json"
        if not path.exists():
            raise FileNotFoundError(f"Missing condition rollout summary: {path}")
        summary = load_json(path)
        if summary.get("condition") != condition:
            raise ValueError(f"{path} has condition={summary.get('condition')!r}")
        if summary.get("protocol") != evaluation_protocol(args):
            raise ValueError(f"{condition} protocol differs from the start manifest")
        if summary.get("start_manifest_sha256") != start_manifest_sha256:
            raise ValueError(f"{condition} start manifest hash mismatch")
        expected_checkpoint = checkpoint_manifest["checkpoints"][condition]
        if summary.get("checkpoint") != expected_checkpoint["path"]:
            raise ValueError(f"{condition} checkpoint path differs from explicit manifest")
        if summary.get("checkpoint_sha256") != expected_checkpoint["sha256"]:
            raise ValueError(f"{condition} checkpoint hash differs from explicit manifest")
        rows = summary.get("rollouts", [])
        if len(rows) != args.num_rollouts:
            raise ValueError(f"{condition} has {len(rows)} rollouts, expected {args.num_rollouts}")
        validate_rollout_files(args.output_dir, condition, args.num_rollouts, rows)
        summaries.append(summary)
    paired_specs = [[row.get("paired_spec") for row in summary["rollouts"]] for summary in summaries]
    if any(specs != paired_specs[0] for specs in paired_specs[1:]):
        raise ValueError("Position paired start/RNG specs differ across conditions")
    realised = [[row.get("corridor_start") for row in summary["rollouts"]] for summary in summaries]
    if any(starts != realised[0] for starts in realised[1:]):
        raise ValueError("Position realised corridor starts differ across conditions")
    return summaries


def write_aggregate_summary(args, summaries, shared_corridor_starts, shared_start_records):
    aggregate = build_aggregate(args, summaries, shared_corridor_starts, shared_start_records)
    aggregate_path = args.output_dir / f"summary_seed{args.seed}_n{args.num_rollouts}.json"
    write_json(aggregate_path, aggregate)

    print("\nSuccess rates")
    for s in summaries:
        print(f"{s['condition']}: {s['success_count']}/{s['num_rollouts']} = {s['success_rate']:.3f}")
    print(f"\nWrote {aggregate_path}")


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
    condition_config,
    horizon,
    action_dt,
    success_lift_height,
    corridor_start_center,
    shared_corridor_start,
    start_sample_record,
    corridor_start_max_error,
    num_points,
    terminate_on_success,
    video_recorder=None,
    video_every_n_actions=2,
):
    rollout_seed = int(start_sample_record["rng_seed"])
    point_cloud_rng_seed = int(start_sample_record["point_cloud_rng_seed"])
    set_all_seeds(rollout_seed)
    reset_cube(sim)
    sim.reset()
    reset_cube(sim)

    base_corridor_start = np.asarray(corridor_start_center, dtype=float)
    corridor_start = np.asarray(shared_corridor_start, dtype=float)
    delta_start = corridor_start - base_corridor_start
    corridor_start_q, realised, corridor_error = solve_ik_with_error(sim, corridor_start)
    if corridor_error > float(corridor_start_max_error):
        raise RuntimeError(
            f"Sampled corridor_start is not reachable: target={corridor_start.tolist()}, "
            f"realised={realised.tolist()}, error={corridor_error:.6f}"
        )
    sim.reset_to_ee_pose(corridor_start_q, gripper_width=0.04)
    corridor_start_info = {
        "base_corridor_start": base_corridor_start.tolist(),
        "corridor_start_delta": delta_start.tolist(),
        "normalized_start_offset": start_sample_record["normalized_delta"],
        "start_sampling_mode": start_sample_record.get("start_sampling_mode", "xz_disk"),
        "shared_start_radius_min": float(start_sample_record.get("shared_start_radius_min", 0.0)),
        "shared_start_radius_max": float(
            start_sample_record.get("shared_start_radius_max", start_sample_record["shared_start_radius"])
        ),
        "shared_start_radius": float(start_sample_record["shared_start_radius"]),
        "radial_distance_from_center": xz_radius(delta_start),
        "start_angle_rad": xz_angle(delta_start),
        "condition_corridor_start_radius": float(
            condition_config["corridor_start_radius"]
        ),
        "ik_realised_error": corridor_error,
        "max_error": float(corridor_start_max_error),
        "shared_start_attempts": int(start_sample_record["attempts"]),
        "shared_start_rejected_count": int(start_sample_record["rejected_count"]),
        "realised_start": realised.tolist(),
    }

    gripper_state = -1.0
    pcd_rng = np.random.default_rng(point_cloud_rng_seed)
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
        "legacy_rollout_index": int(start_sample_record["rollout_index"]),
        "state_id": start_sample_record.get(
            "state_id",
            f"legacy_seed{seed}_state_{int(start_sample_record['rollout_index']):03d}",
        ),
        "paired_spec": start_sample_record,
        "rng_seed": rollout_seed,
        "point_cloud_rng_seed": point_cloud_rng_seed,
        "success": bool(is_success),
        "steps": step + 1,
        "time_to_success_s": float((step + 1) * action_dt) if is_success else None,
        "corridor_start": corridor_start.tolist(),
        "corridor_start_info": corridor_start_info,
        "final_cube_z": details["final_cube_z"],
        "success_details": details,
    }


def evaluate_condition(args, condition, ckpt, shared_corridor_starts, shared_start_records):
    policy, device = load_policy(ckpt, cuda=args.cuda)
    checkpoint_sha256 = file_sha256(ckpt)
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
        video_path = args.video_dir / f"spatial_{condition}_seed{args.seed}_n{args.num_rollouts}.mp4"
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
                condition_config=active_conditions(args)[condition],
                horizon=args.horizon,
                action_dt=args.action_dt,
                success_lift_height=args.success_lift_height,
                corridor_start_center=args.corridor_start_center,
                shared_corridor_start=shared_corridor_starts[i],
                start_sample_record=shared_start_records[i],
                corridor_start_max_error=args.corridor_start_max_error,
                num_points=args.num_points,
                terminate_on_success=args.terminate_on_success,
                video_recorder=video_recorder,
                video_every_n_actions=args.video_every_n_actions,
            )
            result["block"] = int(args.block)
            result["bank_id"] = args.bank_id
            result["checkpoint_sha256"] = checkpoint_sha256
            results.append(result)
            write_json(args.output_dir / "rollouts" / condition / f"rollout_{i:03d}.json", result)
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
        "checkpoint_sha256": checkpoint_sha256,
        "block": int(args.block),
        "bank_id": args.bank_id,
        "device": device,
        "num_rollouts": len(results),
        "success_count": success_count,
        "success_rate": success_count / max(1, len(results)),
        "condition_config": active_conditions(args)[condition],
        "protocol": evaluation_protocol(args),
        "checkpoint_manifest": str(args.checkpoint_manifest),
        "start_manifest": str(args.start_manifest),
        "start_manifest_sha256": file_sha256(args.start_manifest),
        "execution": {
            "slurm_job_id": os.environ.get("SLURM_JOB_ID"),
            "slurm_array_job_id": os.environ.get("SLURM_ARRAY_JOB_ID"),
            "slurm_array_task_id": os.environ.get("SLURM_ARRAY_TASK_ID"),
            "slurm_node_list": os.environ.get("SLURM_NODELIST"),
        },
        "evaluation_distribution": evaluation_distribution(args),
        "start_sampling_mode": start_sampling_mode(args),
        "shared_start_radius_min": float(args.shared_start_radius_min),
        "shared_start_radius_max": float(args.shared_start_radius),
        "shared_start_radius": float(args.shared_start_radius),
        "video_path": (
            str(args.video_dir / f"spatial_{condition}_seed{args.seed}_n{args.num_rollouts}.mp4")
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
        default="{condition}/spatial_{condition}_d30_seed1_2gap",
        help="Experiment directory template under --model-root. Must include {condition}.",
    )
    parser.add_argument(
        "--experiment-profile",
        choices=(
            "legacy_spatial",
            "tro_position_mvp0",
            "tro_position_confirmation",
            "tro_position_stage2",
            "tro_position_stage2_idood",
            "tro_position_composition",
        ),
        default="legacy_spatial",
    )
    parser.add_argument("--bank-id", default=None)
    parser.add_argument("--block", type=int, default=0)
    parser.add_argument(
        "--conditions",
        nargs="+",
        default=list(CONDITION_ORDER),
        choices=sorted(
            set(CONDITIONS)
            | set(TRO_POSITION_MVP0_CONDITIONS)
            | set(TRO_POSITION_CONFIRMATION_CONDITIONS)
            | set(TRO_POSITION_STAGE2_CONDITIONS)
            | set(TRO_POSITION_COMPOSITION_CONDITIONS)
        ),
    )
    parser.add_argument("--epoch", type=int, default=40)
    parser.add_argument("--checkpoint-manifest", type=Path, default=None)
    parser.add_argument("--seed", type=int, default=628)
    parser.add_argument("--num-rollouts", type=int, default=10)
    parser.add_argument("--horizon", type=int, default=80)
    parser.add_argument("--sample-hz", type=float, default=8.0)
    parser.add_argument("--action-gap", type=int, default=2)
    parser.add_argument("--action-dt", type=float, default=None)
    parser.add_argument("--num-points", type=int, default=10000)
    parser.add_argument("--success-lift-height", type=float, default=0.20)
    parser.add_argument("--shared-start-radius-min", type=float, default=0.0)
    parser.add_argument("--shared-start-radius", type=float, default=0.35)
    parser.add_argument("--corridor-start-max-error", type=float, default=0.025)
    parser.add_argument("--max-start-sample-attempts", type=int, default=1000)
    parser.add_argument("--start-manifest", type=Path, default=None)
    parser.add_argument("--write-start-manifest", type=Path, default=None)
    parser.add_argument("--generate-start-manifest-only", action="store_true")
    parser.add_argument("--merge-only", action="store_true")
    parser.add_argument("--skip-aggregate", action="store_true")
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
    if args.experiment_profile == "tro_position_mvp0" and args.conditions == list(CONDITION_ORDER):
        args.conditions = list(TRO_POSITION_MVP0_ORDER)
    if (
        args.experiment_profile == "tro_position_confirmation"
        and args.conditions == list(CONDITION_ORDER)
    ):
        args.conditions = list(TRO_POSITION_CONFIRMATION_ORDER)
    if (
        args.experiment_profile
        in ("tro_position_stage2", "tro_position_stage2_idood")
        and args.conditions == list(CONDITION_ORDER)
    ):
        args.conditions = list(TRO_POSITION_STAGE2_ORDER)
    if (
        args.experiment_profile == "tro_position_composition"
        and args.conditions == list(CONDITION_ORDER)
    ):
        args.conditions = list(TRO_POSITION_COMPOSITION_ORDER)
    validate_start_sampling_args(args)
    if args.action_dt is None:
        args.action_dt = float(args.action_gap) / float(args.sample_hz)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    if args.save_videos:
        args.video_dir.mkdir(parents=True, exist_ok=True)

    if args.start_manifest is not None:
        shared_corridor_starts, shared_start_records = load_start_manifest(args, args.start_manifest)
    else:
        shared_corridor_starts, shared_start_records = generate_shared_corridor_starts(args)

    if args.write_start_manifest is not None:
        write_start_manifest(args, args.write_start_manifest, shared_corridor_starts, shared_start_records)

    if args.generate_start_manifest_only:
        return

    if args.start_manifest is None or args.checkpoint_manifest is None:
        raise ValueError("--start-manifest and --checkpoint-manifest are required for evaluation/merge")
    checkpoint_manifest, checkpoint_paths = checkpoints_from_manifest(
        args.checkpoint_manifest, active_condition_order(args), args.conditions
    )

    if args.merge_only:
        summaries = load_condition_summaries(args, checkpoint_manifest)
        write_aggregate_summary(args, summaries, shared_corridor_starts, shared_start_records)
        return

    summaries = []
    for condition in args.conditions:
        ckpt = checkpoint_paths[condition]
        summary = evaluate_condition(args, condition, ckpt, shared_corridor_starts, shared_start_records)
        summaries.append(summary)
        out_path = args.output_dir / f"spatial_{condition}_seed{args.seed}_n{args.num_rollouts}.json"
        write_json(out_path, summary)

    if not args.skip_aggregate:
        if tuple(args.conditions) != active_condition_order(args):
            raise ValueError("Position aggregate requires all conditions; use --skip-aggregate for array tasks")
        write_aggregate_summary(args, summaries, shared_corridor_starts, shared_start_records)


if __name__ == "__main__":
    main()
