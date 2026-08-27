#!/usr/bin/env python3
"""Convert Target post-grasp raw demos to participant-level robomimic HDF5.

The project converter creates ``action_gap`` phase-offset augmentations per raw
demo.  The rebuttal protocol instead requires exactly 30 HDF5 trajectories per
participant, so this converter keeps only the phase-zero sequence while
preserving the established observation keys, future-joint action definition,
dtypes, and action gap.
"""

import argparse
import hashlib
import json
import math
import os
import re
from datetime import datetime, timezone
from pathlib import Path

import h5py
import numpy as np
import open3d as o3d


GROUP = "simulation_target_group"
SEED = 20260806
PARTICIPANTS = [f"T{index:02d}" for index in range(1, 11)]
EXPECTED_DEMOS = list(range(30))
ACTION_GAP = 2
NUM_POINTS = 10000
SPLIT_SEED = 0
VALID_RATIO = 0.1


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path):
    with Path(path).open("r", encoding="utf-8") as stream:
        return json.load(stream)


def write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def numbered_dirs(root, prefix):
    pattern = re.compile(rf"{re.escape(prefix)}(\d+)")
    rows = []
    for path in Path(root).iterdir():
        match = pattern.fullmatch(path.name)
        if path.is_dir() and match:
            rows.append((int(match.group(1)), path))
    return [path for _, path in sorted(rows)]


def load_vector(path, size):
    value = np.atleast_1d(np.loadtxt(str(path), delimiter=",", dtype=np.float64)).reshape(-1)
    if value.shape != (size,) or not np.isfinite(value).all():
        raise ValueError(f"Invalid finite vector {path}: expected ({size},), got {value.shape}")
    return value


def deterministic_pointcloud(path, participant_index, demo_index, frame_index, conversion_seed):
    cloud = o3d.io.read_point_cloud(str(path))
    points = np.asarray(cloud.points, dtype=np.float64)
    colors = np.asarray(cloud.colors, dtype=np.float64)
    if points.ndim != 2 or points.shape[1] != 3 or points.shape[0] == 0:
        raise ValueError(f"Invalid point cloud points in {path}: {points.shape}")
    if colors.shape != points.shape:
        raise ValueError(f"Invalid point cloud colors in {path}: {colors.shape} vs {points.shape}")
    pointcloud = np.hstack((points, colors))
    if not np.isfinite(pointcloud).all():
        raise ValueError(f"Non-finite point cloud in {path}")
    if len(pointcloud) < NUM_POINTS:
        repeats = int(math.ceil(NUM_POINTS / len(pointcloud)))
        pointcloud = np.tile(pointcloud, (repeats, 1))[:NUM_POINTS]
    elif len(pointcloud) > NUM_POINTS:
        rng = np.random.default_rng(
            np.random.SeedSequence(
                [int(conversion_seed), int(participant_index), int(demo_index), int(frame_index)]
            )
        )
        indices = rng.choice(len(pointcloud), NUM_POINTS, replace=False)
        pointcloud = pointcloud[indices]
    if pointcloud.shape != (NUM_POINTS, 6):
        raise RuntimeError(f"Point-cloud sampling failed for {path}: {pointcloud.shape}")
    return pointcloud


def expected_output_path(output_root, participant_id):
    return output_root / f"{GROUP}_{participant_id}_d30_seed{SEED}_gap{ACTION_GAP}.hdf5"


def validate_source_demo(raw_root, participant_id, demo_index, route):
    participant_dir = raw_root / participant_id
    result_path = participant_dir / f"demo_{demo_index:02d}.json"
    raw_dir = participant_dir / f"demo_{demo_index}"
    metadata_path = raw_dir / "metadata.json"
    result = load_json(result_path)
    metadata = load_json(metadata_path)
    for label, row in (("result", result), ("metadata", metadata)):
        if row.get("group") != GROUP:
            raise ValueError(f"{result_path}: wrong {label} group {row.get('group')!r}")
        if row.get("participant_id") != participant_id:
            raise ValueError(f"{result_path}: wrong {label} participant")
        if row.get("condition") != route:
            raise ValueError(f"{result_path}: wrong {label} route")
        if int(row.get("demo_index", -1)) != demo_index:
            raise ValueError(f"{result_path}: wrong {label} demo index")
    if result.get("success") is not True or result.get("details", {}).get("success", {}).get("success") is not True:
        raise ValueError(f"{result_path}: source demo is not successful")
    if result.get("spec") != metadata.get("spec"):
        raise ValueError(f"{result_path}: result/metadata spec mismatch")
    if metadata.get("first_saved_phase") != "policy_inference_start":
        raise ValueError(f"{metadata_path}: wrong collection boundary")
    if metadata.get("scripted_setup_saved") is not False:
        raise ValueError(f"{metadata_path}: scripted setup marked as saved")

    frames = numbered_dirs(raw_dir, "frame_")
    indices = [int(path.name.split("_", 1)[1]) for path in frames]
    if not frames or indices != list(range(len(frames))):
        raise ValueError(f"{raw_dir}: empty or non-contiguous frames")
    if int(metadata.get("frame_count", -1)) != len(frames):
        raise ValueError(f"{metadata_path}: frame count mismatch")
    phases = [(frame / "phase.txt").read_text(encoding="utf-8").strip() for frame in frames]
    if phases[0] != "policy_inference_start":
        raise ValueError(f"{raw_dir}: frame zero is {phases[0]!r}")
    if any(phase.startswith("scripted_") for phase in phases):
        raise ValueError(f"{raw_dir}: scripted frame found in successful raw data")
    frame_zero_time = load_vector(frames[0] / "time.txt", 1)[0]
    frame_zero_hand = load_vector(frames[0] / "hand_joints.txt", 1)[0]
    if not math.isclose(float(frame_zero_time), 0.0, abs_tol=1e-12):
        raise ValueError(f"{raw_dir}: frame-zero time is not zero")
    if not math.isclose(float(frame_zero_hand), 1.0, abs_tol=1e-12):
        raise ValueError(f"{raw_dir}: frame-zero gripper is not closed")
    return {
        "raw_dir": raw_dir,
        "frames": frames,
        "result": result,
        "metadata": metadata,
        "result_path": result_path,
        "metadata_path": metadata_path,
    }


def split_demo_names(demo_names):
    # This exactly follows robomimic/scripts/split_train_val.py: lexicographic
    # demo ordering, NumPy legacy seed 0, and a 10% validation mask.
    ordered = sorted(demo_names)
    num_valid = int(VALID_RATIO * len(ordered))
    mask = np.zeros(len(ordered), dtype=np.int64)
    mask[:num_valid] = 1
    rng = np.random.RandomState(SPLIT_SEED)
    rng.shuffle(mask)
    train_names = [name for index, name in enumerate(ordered) if mask[index] == 0]
    valid_names = [name for index, name in enumerate(ordered) if mask[index] == 1]
    return train_names, valid_names


def convert_participant(raw_root, output_root, participant_id, conversion_seed, raw_validation_path):
    manifest = load_json(raw_root / "participant_manifest.json")
    if manifest.get("group") != GROUP or int(manifest.get("seed", -1)) != SEED:
        raise ValueError("Raw participant manifest group/seed mismatch")
    if list(manifest.get("participants", {})) != PARTICIPANTS:
        raise ValueError("Raw participant manifest does not contain frozen T01-T10 order")
    participant = manifest["participants"][participant_id]
    route = participant["route"]
    participant_index = int(participant_id[1:])

    sources = [
        validate_source_demo(raw_root, participant_id, demo_index, route)
        for demo_index in EXPECTED_DEMOS
    ]
    output_root.mkdir(parents=True, exist_ok=True)
    output_path = expected_output_path(output_root, participant_id)
    if output_path.exists():
        raise FileExistsError(f"Refusing to overwrite existing HDF5: {output_path}")
    partial_path = output_path.with_name(f"{output_path.name}.inprogress.{os.getpid()}")
    if partial_path.exists():
        raise FileExistsError(f"Refusing to overwrite conversion partial: {partial_path}")

    lengths = []
    source_rows = []
    mean_init_arm = []
    mean_init_hand = []
    total = 0
    with h5py.File(partial_path, "w") as output:
        output.attrs["group"] = GROUP
        output.attrs["participant_id"] = participant_id
        output.attrs["route"] = route
        output.attrs["source_seed"] = SEED
        output.attrs["conversion_seed"] = int(conversion_seed)
        output.attrs["action_gap"] = ACTION_GAP
        output.attrs["phase_offset"] = 0
        output.attrs["num_points"] = NUM_POINTS
        data = output.create_group("data")

        for demo_index, source in enumerate(sources):
            frames = source["frames"]
            arm = np.stack([load_vector(frame / "arm_joints.txt", 7) for frame in frames])
            hand = np.stack([load_vector(frame / "hand_joints.txt", 1) for frame in frames])
            future_indices = np.minimum(np.arange(len(frames)) + ACTION_GAP, len(frames) - 1)
            actions = np.concatenate((arm[future_indices], hand[future_indices]), axis=1)
            sample_indices = np.arange(0, len(frames), ACTION_GAP, dtype=np.int64)
            trajectory_length = len(sample_indices)
            if trajectory_length < 2:
                raise ValueError(f"{source['raw_dir']}: trajectory too short after gap sampling")

            name = f"demo_{demo_index}"
            demo = data.create_group(name)
            demo.attrs["num_samples"] = trajectory_length
            demo.attrs["group"] = GROUP
            demo.attrs["participant_id"] = participant_id
            demo.attrs["route"] = route
            demo.attrs["source_seed"] = SEED
            demo.attrs["source_demo_index"] = demo_index
            demo.attrs["source_attempt_index"] = int(source["result"]["attempt_index"])
            demo.attrs["source_raw_path"] = str(source["raw_dir"].resolve())
            demo.attrs["source_result_sha256"] = sha256(source["result_path"])
            demo.attrs["source_metadata_sha256"] = sha256(source["metadata_path"])
            demo.attrs["raw_frame_count"] = len(frames)
            demo.attrs["phase_offset"] = 0
            demo.attrs["action_gap"] = ACTION_GAP

            obs = demo.create_group("obs")
            obs.create_dataset("robot0_arm_joints", data=arm[sample_indices], dtype=np.float64)
            obs.create_dataset("robot0_hand_joints", data=hand[sample_indices], dtype=np.float64)
            pointcloud_dataset = obs.create_dataset(
                "pointcloud",
                shape=(trajectory_length, NUM_POINTS, 6),
                dtype=np.float64,
            )
            for output_index, raw_index in enumerate(sample_indices):
                pointcloud_dataset[output_index] = deterministic_pointcloud(
                    frames[int(raw_index)] / "point_cloud.ply",
                    participant_index,
                    demo_index,
                    int(raw_index),
                    conversion_seed,
                )

            demo.create_dataset("actions", data=actions[sample_indices], dtype=np.float64)
            dones = np.zeros(trajectory_length, dtype=np.int64)
            dones[-1] = 1
            demo.create_dataset("dones", data=dones, dtype=np.int64)
            demo.create_dataset("rewards", data=np.zeros(trajectory_length), dtype=np.float64)
            demo.create_dataset("states", data=np.zeros(trajectory_length), dtype=np.float64)

            mean_init_arm.append(arm[0])
            mean_init_hand.append(hand[0])
            total += trajectory_length
            lengths.append(trajectory_length)
            source_rows.append(
                {
                    "hdf5_demo": name,
                    "participant_id": participant_id,
                    "route": route,
                    "source_seed": SEED,
                    "source_demo_index": demo_index,
                    "source_attempt_index": int(source["result"]["attempt_index"]),
                    "source_raw_path": str(source["raw_dir"].resolve()),
                    "source_result_sha256": sha256(source["result_path"]),
                    "source_metadata_sha256": sha256(source["metadata_path"]),
                    "raw_frame_count": len(frames),
                    "trajectory_length": trajectory_length,
                }
            )
            print(f"{participant_id} {name}: raw={len(frames)} hdf5={trajectory_length}", flush=True)

        data.attrs["total"] = total
        data.attrs["mean_init_arm"] = np.mean(np.stack(mean_init_arm), axis=0)
        data.attrs["mean_init_hand"] = np.mean(np.stack(mean_init_hand), axis=0)
        train_names, valid_names = split_demo_names(list(data.keys()))
        if len(train_names) != 27 or len(valid_names) != 3:
            raise RuntimeError(f"Unexpected train/valid counts: {len(train_names)}/{len(valid_names)}")
        mask_group = output.create_group("mask")
        mask_group.create_dataset("train", data=np.asarray(train_names, dtype="S"))
        mask_group.create_dataset("valid", data=np.asarray(valid_names, dtype="S"))
        mask_group.attrs["split_seed"] = SPLIT_SEED
        mask_group.attrs["split_algorithm"] = "robomimic_split_train_val_lexicographic_randomstate0"
        output.flush()

    os.replace(partial_path, output_path)
    output_hash = sha256(output_path)
    sidecar = {
        "schema_version": 1,
        "group": GROUP,
        "participant_id": participant_id,
        "route": route,
        "source_seed": SEED,
        "conversion_seed": int(conversion_seed),
        "action_gap": ACTION_GAP,
        "phase_offset": 0,
        "num_points": NUM_POINTS,
        "trajectory_count": len(source_rows),
        "total_samples": total,
        "trajectory_lengths": lengths,
        "train_demo_names": train_names,
        "valid_demo_names": valid_names,
        "hdf5_path": str(output_path.resolve()),
        "hdf5_size_bytes": output_path.stat().st_size,
        "hdf5_sha256": output_hash,
        "raw_validation_report": str(raw_validation_path.resolve()),
        "raw_validation_report_sha256": sha256(raw_validation_path),
        "raw_to_hdf5": source_rows,
    }
    sidecar_path = output_path.with_suffix(".manifest.json")
    write_json(sidecar_path, sidecar)
    print(f"Wrote {output_path} sha256={output_hash}", flush=True)
    return sidecar


def merge_manifests(output_root):
    rows = []
    for participant_id in PARTICIPANTS:
        path = expected_output_path(output_root, participant_id).with_suffix(".manifest.json")
        row = load_json(path)
        if row.get("participant_id") != participant_id or row.get("trajectory_count") != 30:
            raise ValueError(f"Invalid participant conversion manifest: {path}")
        rows.append(row)
    if len({tuple(row["valid_demo_names"]) for row in rows}) != 1:
        raise ValueError("Participant train/valid splits differ")
    aggregate = {
        "schema_version": 1,
        "group": GROUP,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "participant_order": PARTICIPANTS,
        "participant_manifests": rows,
        "counts": {"participants": 10, "trajectories_per_participant": 30, "total_trajectories": 300},
        "schema": {
            "actions": {"shape": ["T", 8], "dtype": "float64", "alignment": "raw joint state t+2"},
            "obs/pointcloud": {"shape": ["T", 10000, 6], "dtype": "float64"},
            "obs/robot0_arm_joints": {"shape": ["T", 7], "dtype": "float64"},
            "obs/robot0_hand_joints": {"shape": ["T", 1], "dtype": "float64"},
            "dones": {"shape": ["T"], "dtype": "int64", "terminal_last": True},
            "rewards": {"shape": ["T"], "dtype": "float64"},
            "states": {"shape": ["T"], "dtype": "float64"},
        },
        "split": {
            "seed": SPLIT_SEED,
            "algorithm": "robomimic_split_train_val_lexicographic_randomstate0",
            "train": rows[0]["train_demo_names"],
            "valid": rows[0]["valid_demo_names"],
        },
    }
    write_json(output_root / "raw_to_hdf5_manifest.json", aggregate)
    write_json(output_root / "schema_summary.json", aggregate["schema"])
    write_json(
        output_root / "trajectory_length_summary.json",
        {
            row["participant_id"]: {
                "count": len(row["trajectory_lengths"]),
                "min": min(row["trajectory_lengths"]),
                "max": max(row["trajectory_lengths"]),
                "mean": float(np.mean(row["trajectory_lengths"])),
                "total": sum(row["trajectory_lengths"]),
            }
            for row in rows
        },
    )
    print(f"Merged 10 conversion manifests under {output_root}", flush=True)


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--participants", nargs="+", choices=PARTICIPANTS, default=PARTICIPANTS)
    parser.add_argument("--conversion-seed", type=int, default=SEED)
    parser.add_argument("--raw-validation", type=Path)
    parser.add_argument("--merge-only", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    if args.conversion_seed != SEED:
        raise ValueError(f"Conversion seed is frozen to {SEED}")
    raw_validation_path = args.raw_validation or args.raw_root / "validation_report.json"
    if not raw_validation_path.is_file():
        raise FileNotFoundError(raw_validation_path)
    raw_validation = load_json(raw_validation_path)
    if (
        raw_validation.get("group") != GROUP
        or raw_validation.get("seed") != SEED
        or not raw_validation.get("passed")
        or raw_validation.get("counts", {}).get("participants") != 10
        or raw_validation.get("counts", {}).get("successful_demos") != 300
        or Path(raw_validation.get("root", "")).resolve() != args.raw_root.resolve()
    ):
        raise ValueError(f"Raw validation gate did not pass the exact 300-demo input: {raw_validation_path}")
    if args.merge_only:
        merge_manifests(args.output_root)
        return
    for participant_id in args.participants:
        convert_participant(
            args.raw_root,
            args.output_root,
            participant_id,
            args.conversion_seed,
            raw_validation_path,
        )
    if args.participants == PARTICIPANTS:
        merge_manifests(args.output_root)


if __name__ == "__main__":
    main()
