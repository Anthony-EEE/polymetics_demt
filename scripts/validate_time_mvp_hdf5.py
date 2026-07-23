#!/usr/bin/env python3
import argparse
from pathlib import Path

import h5py
import numpy as np


def decode_mask(dataset):
    return [value.decode("utf-8") if isinstance(value, bytes) else str(value) for value in dataset[:]]


def validate(path, expected_demos, expected_train, expected_valid, expected_points, expected_channels):
    errors = []
    total_samples = 0
    source_split = {"train": set(), "valid": set()}
    source_samples = {}
    with h5py.File(path, "r") as hdf5:
        if "data" not in hdf5:
            raise ValueError(f"{path}: missing data group")
        demo_names = set(hdf5["data"].keys())
        if len(demo_names) != expected_demos:
            errors.append(f"demo count={len(demo_names)}, expected {expected_demos}")

        for demo_name in sorted(demo_names):
            demo = hdf5["data"][demo_name]
            required = {"actions", "dones", "obs", "rewards", "states"}
            missing = required - set(demo.keys())
            if missing:
                errors.append(f"{demo_name}: missing {sorted(missing)}")
                continue
            num_samples = int(demo.attrs.get("num_samples", -1))
            if num_samples <= 0:
                errors.append(f"{demo_name}: invalid num_samples={num_samples}")
                continue
            total_samples += num_samples
            candidate_id = demo.attrs.get("candidate_id")
            if isinstance(candidate_id, bytes):
                candidate_id = candidate_id.decode("utf-8")
            if not candidate_id:
                errors.append(f"{demo_name}: missing candidate_id attribute")
            if "source_raw_demo_index" not in demo.attrs or "augmentation_index" not in demo.attrs:
                errors.append(f"{demo_name}: missing source/augmentation attributes")
            else:
                source_index = int(demo.attrs["source_raw_demo_index"])
                source_samples.setdefault(source_index, []).append(num_samples)
            for key in ("actions", "dones", "rewards", "states"):
                if demo[key].shape[0] != num_samples:
                    errors.append(
                        f"{demo_name}/{key}: first dimension={demo[key].shape[0]}, expected {num_samples}"
                    )
                elif not np.isfinite(demo[key][:]).all():
                    errors.append(f"{demo_name}/{key}: contains non-finite values")
            if demo["actions"].ndim != 2 or demo["actions"].shape[1] != 8:
                errors.append(f"{demo_name}/actions: expected shape (N, 8), got {demo['actions'].shape}")
            obs = demo["obs"]
            for key in ("pointcloud", "robot0_arm_joints", "robot0_hand_joints"):
                if key not in obs:
                    errors.append(f"{demo_name}/obs: missing {key}")
                elif obs[key].shape[0] != num_samples:
                    errors.append(
                        f"{demo_name}/obs/{key}: first dimension={obs[key].shape[0]}, expected {num_samples}"
                    )
                elif not np.isfinite(obs[key][:]).all():
                    errors.append(f"{demo_name}/obs/{key}: contains non-finite values")
            if "pointcloud" in obs:
                pointcloud = obs["pointcloud"]
                if pointcloud.ndim != 3 or pointcloud.shape[1:] != (
                    expected_points,
                    expected_channels,
                ):
                    errors.append(
                        f"{demo_name}/obs/pointcloud: expected "
                        f"(N, {expected_points}, {expected_channels}), got {pointcloud.shape}"
                    )
                elif not np.isfinite(pointcloud[:]).all():
                    errors.append(f"{demo_name}/obs/pointcloud: contains non-finite values")

        if "mask" not in hdf5 or not {"train", "valid"}.issubset(hdf5["mask"].keys()):
            errors.append("missing train/valid mask datasets")
            train_names = []
            valid_names = []
        else:
            train_names = decode_mask(hdf5["mask"]["train"])
            valid_names = decode_mask(hdf5["mask"]["valid"])
            if len(train_names) != expected_train:
                errors.append(f"train mask count={len(train_names)}, expected {expected_train}")
            if len(valid_names) != expected_valid:
                errors.append(f"valid mask count={len(valid_names)}, expected {expected_valid}")
            if len(set(train_names)) != len(train_names) or len(set(valid_names)) != len(valid_names):
                errors.append("duplicate demo names in masks")
            overlap = set(train_names) & set(valid_names)
            if overlap:
                errors.append(f"train/valid masks overlap: {sorted(overlap)}")
            covered = set(train_names) | set(valid_names)
            if covered != demo_names:
                errors.append(
                    f"mask coverage mismatch: missing={sorted(demo_names - covered)}, "
                    f"extra={sorted(covered - demo_names)}"
                )
            for split_name, names in (("train", train_names), ("valid", valid_names)):
                for name in names:
                    candidate_id = hdf5["data"][name].attrs.get("candidate_id")
                    if isinstance(candidate_id, bytes):
                        candidate_id = candidate_id.decode("utf-8")
                    source_split[split_name].add(str(candidate_id))
            if source_split["train"] & source_split["valid"]:
                errors.append("source candidate IDs overlap between train and valid masks")
            if len(source_split["train"]) != 27 or len(source_split["valid"]) != 3:
                errors.append(
                    f"source candidate split is {len(source_split['train'])}/{len(source_split['valid'])}, expected 27/3"
                )
        for source_index, counts in source_samples.items():
            if len(counts) != 2:
                errors.append(f"source raw demo {source_index}: expected two augmentations, got {len(counts)}")
                continue
            demo_names = [
                name
                for name in hdf5["data"]
                if int(hdf5["data"][name].attrs.get("source_raw_demo_index", -1)) == source_index
            ]
            raw_counts = {
                int(hdf5["data"][name].attrs.get("source_raw_frame_count", -1))
                for name in demo_names
            }
            if len(raw_counts) != 1 or next(iter(raw_counts)) != sum(counts):
                errors.append(
                    f"source raw demo {source_index}: augmented sample counts {counts} do not sum to raw frames {raw_counts}"
                )

    if errors:
        raise ValueError(f"{path} failed validation:\n- " + "\n- ".join(errors))
    print(
        f"OK {path}: demos={expected_demos}, train={expected_train}, valid={expected_valid}, "
        f"total_samples={total_samples}, pointcloud_points={expected_points}"
    )
    return {key: sorted(values) for key, values in source_split.items()}


def parse_args():
    parser = argparse.ArgumentParser(description="Validate reciprocal temporal robomimic HDF5 files.")
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--expected-demos", type=int, default=60)
    parser.add_argument("--expected-train", type=int, default=54)
    parser.add_argument("--expected-valid", type=int, default=6)
    parser.add_argument("--expected-points", type=int, default=10000)
    parser.add_argument("--expected-channels", type=int, default=6)
    return parser.parse_args()


def main():
    args = parse_args()
    split_records = []
    for path in args.paths:
        if not path.is_file():
            raise FileNotFoundError(path)
        split_records.append(validate(
            path,
            args.expected_demos,
            args.expected_train,
            args.expected_valid,
            args.expected_points,
            args.expected_channels,
        ))
    if len({repr(record) for record in split_records}) != 1:
        raise ValueError("candidate-level train/valid source split differs across HDF5 files")
    print("OK candidate-level train/valid source split is identical across all files")


if __name__ == "__main__":
    main()
