#!/usr/bin/env python3
"""Validate Bimodal HDF5 payloads, source equality, provenance, and loaders."""

from __future__ import annotations

import argparse
import math
import random
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import h5py
import numpy as np

from common import (
    ACTION_GAP,
    DESIGN_SEED,
    GROUP,
    HDF5_ROOT,
    NUM_POINTS,
    PAIRING_MANIFEST,
    PARTICIPANTS,
    SOURCE_SEED,
    SPLIT_SEED,
    TARGET_GROUP,
    canonical_hash,
    decode_rows,
    load_json,
    sha256_file,
    verify_frozen_inputs,
    write_json_atomic_exclusive,
)


EXPECTED_KEYS = {
    "actions": ((None, 8), np.dtype("float64")),
    "dones": ((None,), np.dtype("int64")),
    "rewards": ((None,), np.dtype("float64")),
    "states": ((None,), np.dtype("float64")),
    "obs/pointcloud": ((None, NUM_POINTS, 6), np.dtype("float64")),
    "obs/robot0_arm_joints": ((None, 7), np.dtype("float64")),
    "obs/robot0_hand_joints": ((None, 1), np.dtype("float64")),
}


def hdf5_path(root: Path, participant_id: str) -> Path:
    return root / f"{GROUP}_{participant_id}_d60_seed{DESIGN_SEED}_gap{ACTION_GAP}.hdf5"


def get_path(group: h5py.Group, key: str):
    node = group
    for component in key.split("/"):
        node = node[component]
    return node


def finite_dataset(dataset: h5py.Dataset, chunk: int) -> bool:
    for start in range(0, len(dataset), chunk):
        if not np.isfinite(dataset[start : start + chunk]).all():
            return False
    return True


def dataset_paths(group: h5py.Group):
    paths = []

    def visitor(name, node):
        if isinstance(node, h5py.Dataset):
            paths.append(name)

    group.visititems(visitor)
    return sorted(paths)


def datasets_equal(left: h5py.Dataset, right: h5py.Dataset) -> bool:
    if left.shape != right.shape or left.dtype != right.dtype:
        return False
    if left.ndim == 0:
        return bool(np.array_equal(left[()], right[()]))
    chunk = 1 if left.ndim >= 3 else 128
    for start in range(0, left.shape[0], chunk):
        if not np.array_equal(left[start : start + chunk], right[start : start + chunk]):
            return False
    return True


def loader_smoke(path: Path, filter_key: str) -> dict:
    step2 = Path("/users/k23114984/code/arcap_policy/STEP2_train_policy")
    if str(step2) not in sys.path:
        sys.path.insert(0, str(step2))
    from robomimic.utils.dataset import SequenceDataset

    dataset = SequenceDataset(
        hdf5_path=str(path),
        obs_keys=["robot0_arm_joints", "robot0_hand_joints", "pointcloud"],
        action_keys=["actions"],
        dataset_keys=["actions", "rewards", "dones"],
        action_config={"actions": {"normalization": "min_max"}},
        frame_stack=1,
        seq_length=20,
        pad_frame_stack=True,
        pad_seq_length=True,
        get_pad_mask=False,
        goal_mode=None,
        hdf5_cache_mode=None,
        hdf5_use_swmr=True,
        hdf5_normalize_obs=False,
        filter_by_attribute=filter_key,
        load_next_obs=False,
    )
    item = dataset[0]
    shapes = {
        "actions": list(item["actions"].shape),
        "obs/robot0_arm_joints": list(item["obs"]["robot0_arm_joints"].shape),
        "obs/robot0_hand_joints": list(item["obs"]["robot0_hand_joints"].shape),
        "obs/pointcloud": list(item["obs"]["pointcloud"].shape),
    }
    expected = {
        "actions": [20, 8],
        "obs/robot0_arm_joints": [20, 7],
        "obs/robot0_hand_joints": [20, 1],
        "obs/pointcloud": [20, NUM_POINTS, 6],
    }
    if shapes != expected:
        raise ValueError(f"Unexpected loader shapes: {shapes}")
    if not all(np.isfinite(value).all() for value in (item["actions"], *item["obs"].values())):
        raise ValueError("Loader returned non-finite values")
    report = {"filter_key": filter_key, "dataset_length": len(dataset), "item_shapes": shapes}
    dataset.close_and_delete_hdf5_handle()
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hdf5-root", type=Path, default=HDF5_ROOT)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--skip-loader-smoke", action="store_true")
    parser.add_argument("--expected-build-attempt", type=int, default=1)
    args = parser.parse_args()
    if args.hdf5_root.resolve() != HDF5_ROOT.resolve():
        raise ValueError(f"Formal HDF5 root must be {HDF5_ROOT}")
    output = args.output or args.hdf5_root / "validation_report.json"
    frozen_inputs = verify_frozen_inputs()
    pairing = load_json(PAIRING_MANIFEST)
    source_records = pairing["source_participants"]
    source_hdf5_hashes = {}
    for source_id, record in source_records.items():
        path = Path(record["hdf5"]["path"])
        actual = sha256_file(path)
        if actual != record["hdf5"]["sha256"]:
            raise ValueError(f"Frozen Target HDF5 changed for {source_id}")
        source_hdf5_hashes[source_id] = actual

    errors = []
    reports = {}
    sidecars = {}
    loader_reports = {}
    global_memberships = []
    split_rng = random.Random(SPLIT_SEED)
    for participant_id in PARTICIPANTS:
        path = hdf5_path(args.hdf5_root, participant_id)
        sidecar_path = path.with_suffix(".manifest.json")
        participant_errors = []
        if not path.is_file() or not sidecar_path.is_file():
            errors.append(f"{participant_id}:missing_hdf5_or_sidecar")
            continue
        sidecar = load_json(sidecar_path)
        sidecar_content = dict(sidecar)
        sidecar_canonical = sidecar_content.pop("canonical_content_sha256", None)
        if sidecar_canonical != canonical_hash(sidecar_content):
            participant_errors.append("sidecar_canonical_hash_mismatch")
        actual_hdf5_hash = sha256_file(path)
        if (
            sidecar.get("group") != GROUP
            or sidecar.get("participant_id") != participant_id
            or sidecar.get("trajectory_count") != 60
            or sidecar.get("route_counts") != {"L": 30, "R": 30}
            or sidecar.get("build_attempt_index") != args.expected_build_attempt
            or sidecar.get("hdf5_sha256") != actual_hdf5_hash
        ):
            participant_errors.append("invalid_sidecar_identity_or_hash")
        mappings = sidecar.get("raw_to_hdf5", [])
        left_indices = [i for i, row in enumerate(mappings) if row.get("route") == "L"]
        right_indices = [i for i, row in enumerate(mappings) if row.get("route") == "R"]
        expected_valid_indices = sorted(
            split_rng.sample(sorted(left_indices), 3)
            + split_rng.sample(sorted(right_indices), 3)
        )
        expected_valid = [f"demo_{index}" for index in expected_valid_indices]
        expected_train = [f"demo_{index}" for index in range(60) if index not in expected_valid_indices]
        route_counts = Counter()
        total_samples = 0
        trajectory_lengths = []
        init_arm = []
        init_hand = []
        source_keys = []
        with h5py.File(path, "r") as hdf5:
            for key, expected in (
                ("group", GROUP),
                ("participant_id", participant_id),
                ("build_attempt_index", args.expected_build_attempt),
                ("design_seed", DESIGN_SEED),
                ("source_seed", SOURCE_SEED),
                ("split_seed", SPLIT_SEED),
                ("action_gap", ACTION_GAP),
                ("phase_offset", 0),
                ("num_points", NUM_POINTS),
            ):
                if hdf5.attrs.get(key) != expected:
                    participant_errors.append(f"wrong_root_attr:{key}:{hdf5.attrs.get(key)!r}")
            if "data" not in hdf5 or "mask" not in hdf5:
                participant_errors.append("missing_data_or_mask")
            else:
                names = sorted(hdf5["data"], key=lambda name: int(name.split("_", 1)[1]))
                if names != [f"demo_{index}" for index in range(60)]:
                    participant_errors.append("wrong_demo_names")
                for mixed_index, name in enumerate(names):
                    demo = hdf5["data"][name]
                    row = mappings[mixed_index] if mixed_index < len(mappings) else {}
                    route = str(demo.attrs.get("route", ""))
                    source_participant = str(demo.attrs.get("source_participant_id", ""))
                    source_demo_index = int(demo.attrs.get("source_demo_index", -1))
                    source_keys.append((source_participant, source_demo_index))
                    global_memberships.append((participant_id, source_participant, source_demo_index))
                    route_counts[route] += 1
                    for key, expected in (
                        ("group", GROUP),
                        ("participant_id", participant_id),
                        ("source_group", TARGET_GROUP),
                        ("source_participant_id", row.get("source_participant_id")),
                        ("source_demo_index", row.get("source_demo_index")),
                        ("route", row.get("route")),
                        ("source_hdf5_sha256", row.get("source_hdf5_sha256")),
                        ("source_metadata_sha256", row.get("source_metadata_sha256")),
                        ("source_result_sha256", row.get("source_result_sha256")),
                    ):
                        if demo.attrs.get(key) != expected:
                            participant_errors.append(f"{name}:wrong_attr:{key}")
                    length = int(demo.attrs.get("num_samples", -1))
                    total_samples += length
                    trajectory_lengths.append(length)
                    raw_count = int(demo.attrs.get("raw_frame_count", -1))
                    if length != int(math.ceil(raw_count / ACTION_GAP)):
                        participant_errors.append(f"{name}:action_gap_length_mismatch")
                    for key, (shape, dtype) in EXPECTED_KEYS.items():
                        try:
                            dataset = get_path(demo, key)
                        except KeyError:
                            participant_errors.append(f"{name}:missing_dataset:{key}")
                            continue
                        expected_shape = tuple(length if value is None else value for value in shape)
                        if dataset.shape != expected_shape or dataset.dtype != dtype:
                            participant_errors.append(
                                f"{name}:shape_or_dtype:{key}:{dataset.shape}:{dataset.dtype}"
                            )
                        if key in (
                            "actions",
                            "obs/pointcloud",
                            "obs/robot0_arm_joints",
                            "obs/robot0_hand_joints",
                        ) and not finite_dataset(dataset, 1 if key == "obs/pointcloud" else 64):
                            participant_errors.append(f"{name}:nonfinite:{key}")
                    if length > 0:
                        dones = demo["dones"][:]
                        if dones[-1] != 1 or np.count_nonzero(dones) != 1:
                            participant_errors.append(f"{name}:invalid_dones")
                        init_arm.append(demo["obs/robot0_arm_joints"][0])
                        init_hand.append(demo["obs/robot0_hand_joints"][0])
                    source_path = Path(str(demo.attrs.get("source_hdf5_path", "")))
                    if (
                        source_participant not in source_hdf5_hashes
                        or demo.attrs.get("source_hdf5_sha256")
                        != source_hdf5_hashes.get(source_participant)
                    ):
                        participant_errors.append(f"{name}:source_hdf5_hash_mismatch")
                    else:
                        with h5py.File(source_path, "r") as source:
                            source_demo = source[f"data/demo_{source_demo_index}"]
                            if dataset_paths(demo) != dataset_paths(source_demo):
                                participant_errors.append(f"{name}:dataset_path_mismatch")
                            else:
                                for dataset_key in dataset_paths(source_demo):
                                    if not datasets_equal(
                                        get_path(demo, dataset_key), get_path(source_demo, dataset_key)
                                    ):
                                        participant_errors.append(
                                            f"{name}:source_payload_mismatch:{dataset_key}"
                                        )
                    result_path = Path(str(demo.attrs.get("source_result_path", "")))
                    metadata_path = Path(str(demo.attrs.get("source_raw_path", ""))) / "metadata.json"
                    if (
                        not result_path.is_file()
                        or not metadata_path.is_file()
                        or sha256_file(result_path) != demo.attrs.get("source_result_sha256")
                        or sha256_file(metadata_path) != demo.attrs.get("source_metadata_sha256")
                    ):
                        participant_errors.append(f"{name}:raw_provenance_hash_mismatch")
                if int(hdf5["data"].attrs.get("total", -1)) != total_samples:
                    participant_errors.append("data_total_mismatch")
                if init_arm and not np.array_equal(
                    np.asarray(hdf5["data"].attrs.get("mean_init_arm")),
                    np.mean(np.stack(init_arm), axis=0),
                ):
                    participant_errors.append("mean_init_arm_mismatch")
                if init_hand and not np.array_equal(
                    np.asarray(hdf5["data"].attrs.get("mean_init_hand")),
                    np.mean(np.stack(init_hand), axis=0),
                ):
                    participant_errors.append("mean_init_hand_mismatch")
                train = decode_rows(hdf5["mask/train"][:])
                valid = decode_rows(hdf5["mask/valid"][:])
                if train != expected_train or valid != expected_valid:
                    participant_errors.append("split_replay_mismatch")
                train_routes = Counter(str(hdf5["data"][name].attrs["route"]) for name in train)
                valid_routes = Counter(str(hdf5["data"][name].attrs["route"]) for name in valid)
                if train_routes != Counter({"L": 27, "R": 27}):
                    participant_errors.append(f"wrong_train_route_counts:{dict(train_routes)}")
                if valid_routes != Counter({"L": 3, "R": 3}):
                    participant_errors.append(f"wrong_valid_route_counts:{dict(valid_routes)}")
        if route_counts != Counter({"L": 30, "R": 30}):
            participant_errors.append(f"route_counts:{dict(route_counts)}")
        if len(source_keys) != 60 or len(set(source_keys)) != 60:
            participant_errors.append("duplicated_source_trajectory_within_participant")
        reports[participant_id] = {
            "path": str(path.resolve()),
            "sha256": actual_hdf5_hash,
            "size_bytes": path.stat().st_size,
            "trajectory_count": len(trajectory_lengths),
            "total_samples": total_samples,
            "trajectory_lengths": trajectory_lengths,
            "route_counts": dict(route_counts),
            "train_demo_names": expected_train,
            "valid_demo_names": expected_valid,
            "unique_source_trajectories": len(set(source_keys)),
            "errors": participant_errors,
        }
        sidecars[participant_id] = sidecar
        errors.extend(f"{participant_id}:{value}" for value in participant_errors)

    build_manifest_path = args.hdf5_root / "build_manifest.json"
    if not build_manifest_path.is_file():
        errors.append("missing_build_manifest")
    else:
        build_manifest = load_json(build_manifest_path)
        content = dict(build_manifest)
        recorded = content.pop("canonical_content_sha256", None)
        if (
            recorded != canonical_hash(content)
            or build_manifest.get("group") != GROUP
            or build_manifest.get("counts", {}).get("total_trajectory_memberships") != 600
            or build_manifest.get("counts", {}).get("underlying_unique_target_trajectories") != 300
            or build_manifest.get("build_attempt_index") != args.expected_build_attempt
        ):
            errors.append("invalid_build_manifest")
    expected_files = {
        "build_manifest.json",
        *(hdf5_path(args.hdf5_root, participant).name for participant in PARTICIPANTS),
        *(hdf5_path(args.hdf5_root, participant).with_suffix(".manifest.json").name for participant in PARTICIPANTS),
        output.name,
    }
    actual_files = {path.name for path in args.hdf5_root.iterdir() if path.is_file()}
    unexpected = sorted(actual_files - expected_files)
    missing = sorted((expected_files - {output.name}) - actual_files)
    partial_paths = sorted(str(path) for path in args.hdf5_root.parent.glob("hdf5.inprogress.*"))
    zero_bytes = sorted(
        str(path) for path in args.hdf5_root.rglob("*") if path.is_file() and path.stat().st_size == 0
    )
    if unexpected:
        errors.append(f"unexpected_hdf5_files:{unexpected}")
    if missing:
        errors.append(f"missing_hdf5_files:{missing}")
    if partial_paths:
        errors.append(f"partial_hdf5_roots:{partial_paths}")
    if zero_bytes:
        errors.append(f"zero_byte_hdf5_files:{zero_bytes}")
    underlying_unique = len({(source, demo) for _, source, demo in global_memberships})
    if len(global_memberships) != 600 or underlying_unique != 300:
        errors.append(
            f"global_membership_or_unique_count:{len(global_memberships)}:{underlying_unique}"
        )

    if not args.skip_loader_smoke and not errors:
        for participant_id in PARTICIPANTS:
            path = hdf5_path(args.hdf5_root, participant_id)
            try:
                loader_reports[participant_id] = {
                    split: loader_smoke(path, split) for split in ("train", "valid")
                }
            except Exception as exc:
                errors.append(f"{participant_id}:loader_smoke:{type(exc).__name__}:{exc}")

    report = {
        "schema_version": 1,
        "group": GROUP,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "passed": not errors and len(reports) == 10 and len(loader_reports) in (0, 10),
        "errors": errors,
        "counts": {
            "participant_hdf5": len(reports),
            "trajectory_memberships": len(global_memberships),
            "underlying_unique_target_trajectories": underlying_unique,
            "loader_smokes": sum(len(row) for row in loader_reports.values()),
            "partial_roots": len(partial_paths),
            "zero_byte_files": len(zero_bytes),
            "unexpected_files": len(unexpected),
        },
        "participant_reports": reports,
        "participant_conversion_manifests": sidecars,
        "loader_smoke": loader_reports,
        "build_manifest": {
            "path": str(build_manifest_path.resolve()),
            "sha256": sha256_file(build_manifest_path) if build_manifest_path.is_file() else None,
        },
        "frozen_inputs": frozen_inputs,
    }
    write_json_atomic_exclusive(output, report)
    print(f"passed={report['passed']} errors={len(errors)} counts={report['counts']}")
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
