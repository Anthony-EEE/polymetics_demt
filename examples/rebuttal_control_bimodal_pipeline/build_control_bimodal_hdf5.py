#!/usr/bin/env python3
"""Build ten standalone shuffled 60-trajectory Control-Bimodal HDF5 datasets."""

from __future__ import annotations

import argparse
import os
import random
import shutil
from contextlib import ExitStack
from datetime import datetime, timezone
from pathlib import Path

import h5py
import numpy as np

from common import (
    ACTION_GAP,
    CONTROL_BIMODAL_ROOT,
    DESIGN_SEED,
    GROUP,
    HDF5_ROOT,
    MIXED_ROOT,
    NUM_POINTS,
    PAIRING_MANIFEST,
    PARTICIPANTS,
    SOURCE_SEED,
    SPLIT_SEED,
    CONTROL_GROUP,
    canonical_hash,
    load_json,
    sha256_file,
    verify_frozen_inputs,
    write_json_atomic_exclusive,
)


def output_path(root: Path, participant_id: str) -> Path:
    return root / f"{GROUP}_{participant_id}_d60_seed{DESIGN_SEED}_gap{ACTION_GAP}.hdf5"


def dataset_paths(group: h5py.Group):
    paths = []

    def visitor(name, node):
        if isinstance(node, h5py.Dataset):
            paths.append(name)

    group.visititems(visitor)
    return sorted(paths)


def get_path(group: h5py.Group, key: str):
    node = group
    for component in key.split("/"):
        node = node[component]
    return node


def assert_dataset_equal(left: h5py.Dataset, right: h5py.Dataset, label: str) -> None:
    if left.shape != right.shape or left.dtype != right.dtype:
        raise RuntimeError(
            f"Post-copy shape/dtype mismatch for {label}: "
            f"{left.shape}/{left.dtype} != {right.shape}/{right.dtype}"
        )
    chunk = 1 if left.ndim >= 3 else 128
    for start in range(0, left.shape[0], chunk):
        if not np.array_equal(left[start : start + chunk], right[start : start + chunk]):
            raise RuntimeError(f"Post-copy payload mismatch for {label} at first-axis {start}")


def verify_published_candidate(path: Path, participant_id: str, mappings: list) -> None:
    """Re-open the closed candidate and compare every dataset before publication."""

    source_ids = sorted({row["source_participant_id"] for row in mappings})
    source_paths = {
        source_id: Path(next(
            row["source_hdf5_path"]
            for row in mappings
            if row["source_participant_id"] == source_id
        ))
        for source_id in source_ids
    }
    with ExitStack() as stack:
        candidate = stack.enter_context(h5py.File(path, "r"))
        sources = {
            source_id: stack.enter_context(h5py.File(source_path, "r"))
            for source_id, source_path in source_paths.items()
        }
        for mixed_index, row in enumerate(mappings):
            destination = candidate[f"data/demo_{mixed_index}"]
            source = sources[row["source_participant_id"]][
                f"data/demo_{row['source_demo_index']}"
            ]
            if dataset_paths(destination) != dataset_paths(source):
                raise RuntimeError(f"{participant_id}/demo_{mixed_index}: dataset paths differ")
            for key in dataset_paths(source):
                assert_dataset_equal(
                    get_path(destination, key),
                    get_path(source, key),
                    f"{participant_id}/demo_{mixed_index}/{key}",
                )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=HDF5_ROOT)
    parser.add_argument("--attempt-index", type=int, default=1)
    args = parser.parse_args()
    if args.output_root.resolve() != HDF5_ROOT.resolve():
        raise ValueError(f"Formal HDF5 root must be {HDF5_ROOT}")
    if args.output_root.exists() or args.output_root.is_symlink():
        raise FileExistsError(f"Refusing to overwrite HDF5 root: {args.output_root}")
    if args.attempt_index < 1:
        raise ValueError("attempt-index must be positive")
    frozen_inputs = verify_frozen_inputs()
    pairing = load_json(PAIRING_MANIFEST)
    mixed_validation_path = CONTROL_BIMODAL_ROOT / "mixed_raw_validation_report.json"
    if not mixed_validation_path.is_file():
        raise FileNotFoundError(mixed_validation_path)
    mixed_validation = load_json(mixed_validation_path)
    if (
        mixed_validation.get("group") != GROUP
        or mixed_validation.get("passed") is not True
        or mixed_validation.get("counts", {}).get("participants") != 10
        or mixed_validation.get("counts", {}).get("trajectory_memberships") != 600
    ):
        raise ValueError("Mixed-view validation is not a passed 10x60 gate")

    source_records = pairing["source_participants"]
    verified_source_hashes = {}
    for source_id, record in source_records.items():
        source_path = Path(record["hdf5"]["path"])
        actual_hash = sha256_file(source_path)
        if actual_hash != record["hdf5"]["sha256"]:
            raise ValueError(f"Frozen Control HDF5 changed for {source_id}: {source_path}")
        verified_source_hashes[source_id] = actual_hash
    expected_copy_bytes = sum(
        source_records[row[source_key]]["hdf5"]["size_bytes"]
        for row in pairing["pairs"]
        for source_key in ("left_source", "right_source")
    )
    free_bytes = shutil.disk_usage(CONTROL_BIMODAL_ROOT).free
    if free_bytes < int(expected_copy_bytes * 1.10):
        raise OSError(
            f"Insufficient free space: free={free_bytes}, required>={int(expected_copy_bytes * 1.10)}"
        )

    temporary = args.output_root.with_name(f"{args.output_root.name}.inprogress.{os.getpid()}")
    if temporary.exists() or temporary.is_symlink():
        raise FileExistsError(f"Stale temporary HDF5 root exists: {temporary}")
    temporary.mkdir(parents=True, exist_ok=False)
    split_rng = random.Random(SPLIT_SEED)
    participant_manifests = []
    try:
        for participant_id in PARTICIPANTS:
            mixture_path = MIXED_ROOT / participant_id / "mixture_manifest.json"
            mixture = load_json(mixture_path)
            mappings = mixture.get("mappings", [])
            if len(mappings) != 60:
                raise ValueError(f"{participant_id}: mixture manifest is not 60 trajectories")
            left_indices = [row["mixed_demo_index"] for row in mappings if row["route"] == "L"]
            right_indices = [row["mixed_demo_index"] for row in mappings if row["route"] == "R"]
            if len(left_indices) != 30 or len(right_indices) != 30:
                raise ValueError(f"{participant_id}: mixture is not 30L+30R")
            valid_indices = sorted(
                split_rng.sample(sorted(left_indices), 3)
                + split_rng.sample(sorted(right_indices), 3)
            )
            valid_names = [f"demo_{index}" for index in valid_indices]
            train_names = [f"demo_{index}" for index in range(60) if index not in valid_indices]

            destination = output_path(temporary, participant_id)
            init_arm = []
            init_hand = []
            total_samples = 0
            trajectory_lengths = []
            with h5py.File(destination, "x") as target:
                target.attrs.update(
                    {
                        "group": GROUP,
                        "participant_id": participant_id,
                        "build_attempt_index": args.attempt_index,
                        "design_seed": DESIGN_SEED,
                        "source_seed": SOURCE_SEED,
                        "split_seed": SPLIT_SEED,
                        "action_gap": ACTION_GAP,
                        "phase_offset": 0,
                        "num_points": NUM_POINTS,
                        "pairing_manifest_sha256": sha256_file(PAIRING_MANIFEST),
                        "mixture_manifest_sha256": sha256_file(mixture_path),
                    }
                )
                data = target.create_group("data")
                with ExitStack() as stack:
                    source_handles = {
                        source_id: stack.enter_context(
                            h5py.File(Path(source_records[source_id]["hdf5"]["path"]), "r")
                        )
                        for source_id in sorted(
                            {row["source_participant_id"] for row in mappings}
                        )
                    }
                    for mixed_index, row in enumerate(mappings):
                        if row.get("mixed_demo_index") != mixed_index:
                            raise ValueError(f"{participant_id}: non-canonical mixed index {mixed_index}")
                        source_path = Path(row["source_hdf5_path"])
                        source_participant = row["source_participant_id"]
                        source_demo_index = int(row["source_demo_index"])
                        if row["source_hdf5_sha256"] != verified_source_hashes[source_participant]:
                            raise ValueError(
                                f"{participant_id}: mixture source hash mismatch for {source_participant}"
                            )
                        source = source_handles[source_participant]
                        source_group = source[f"data/demo_{source_demo_index}"]
                        source.copy(source_group, data, name=f"demo_{mixed_index}")
                        demo = data[f"demo_{mixed_index}"]
                        demo.attrs.update(
                            {
                                "group": GROUP,
                                "participant_id": participant_id,
                                "route": row["route"],
                                "source_group": CONTROL_GROUP,
                                "source_participant_id": source_participant,
                                "source_demo_index": source_demo_index,
                                "source_hdf5_path": str(source_path.resolve()),
                                "source_hdf5_sha256": row["source_hdf5_sha256"],
                                "source_raw_path": row["source_raw_path"],
                                "source_result_path": row["source_result_path"],
                                "source_metadata_sha256": row["source_raw_metadata_sha256"],
                                "source_result_sha256": row["source_result_sha256"],
                                "pairing_manifest_sha256": sha256_file(PAIRING_MANIFEST),
                                "mixture_manifest_sha256": sha256_file(mixture_path),
                            }
                        )
                        length = int(demo.attrs["num_samples"])
                        trajectory_lengths.append(length)
                        total_samples += length
                        init_arm.append(demo["obs/robot0_arm_joints"][0])
                        init_hand.append(demo["obs/robot0_hand_joints"][0])
                data.attrs["total"] = total_samples
                data.attrs["mean_init_arm"] = np.mean(np.stack(init_arm), axis=0)
                data.attrs["mean_init_hand"] = np.mean(np.stack(init_hand), axis=0)
                mask = target.create_group("mask")
                mask.create_dataset("train", data=np.asarray(train_names, dtype="S"))
                mask.create_dataset("valid", data=np.asarray(valid_names, dtype="S"))
                target.flush()

            verify_published_candidate(destination, participant_id, mappings)
            hdf5_hash = sha256_file(destination)
            provenance_rows = []
            for row in mappings:
                provenance_rows.append(
                    {
                        "hdf5_demo": f"demo_{row['mixed_demo_index']}",
                        "route": row["route"],
                        "source_group": CONTROL_GROUP,
                        "source_participant_id": row["source_participant_id"],
                        "source_demo_index": row["source_demo_index"],
                        "source_hdf5_path": row["source_hdf5_path"],
                        "source_hdf5_sha256": row["source_hdf5_sha256"],
                        "source_raw_path": row["source_raw_path"],
                        "source_result_path": row["source_result_path"],
                        "source_metadata_sha256": row["source_raw_metadata_sha256"],
                        "source_result_sha256": row["source_result_sha256"],
                    }
                )
            manifest = {
                "schema_version": 1,
                "group": GROUP,
                "participant_id": participant_id,
                "build_attempt_index": args.attempt_index,
                "hdf5_path": str((args.output_root / destination.name).resolve()),
                "hdf5_sha256": hdf5_hash,
                "hdf5_size_bytes": destination.stat().st_size,
                "design_seed": DESIGN_SEED,
                "source_seed": SOURCE_SEED,
                "action_gap": ACTION_GAP,
                "phase_offset": 0,
                "num_points": NUM_POINTS,
                "trajectory_count": 60,
                "route_counts": {"L": 30, "R": 30},
                "total_samples": total_samples,
                "trajectory_lengths": trajectory_lengths,
                "split": {
                    "seed": SPLIT_SEED,
                    "algorithm": (
                        "one python_stdlib_random.Random(seed) stream over CB01..CB10; "
                        "sample 3 sorted L indices then 3 sorted R indices per participant"
                    ),
                    "train_demo_names": train_names,
                    "valid_demo_names": valid_names,
                    "train_route_counts": {"L": 27, "R": 27},
                    "valid_route_counts": {"L": 3, "R": 3},
                },
                "pairing_manifest": {
                    "path": str(PAIRING_MANIFEST.resolve()),
                    "sha256": sha256_file(PAIRING_MANIFEST),
                },
                "mixture_manifest": {
                    "path": str(mixture_path.resolve()),
                    "sha256": sha256_file(mixture_path),
                },
                "raw_to_hdf5": provenance_rows,
            }
            manifest["canonical_content_sha256"] = canonical_hash(manifest)
            sidecar = destination.with_suffix(".manifest.json")
            write_json_atomic_exclusive(sidecar, manifest)
            participant_manifests.append(manifest)

        aggregate = {
            "schema_version": 1,
            "group": GROUP,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "participant_order": PARTICIPANTS,
            "build_attempt_index": args.attempt_index,
            "counts": {
                "participants": 10,
                "trajectories_per_participant": 60,
                "total_trajectory_memberships": 600,
                "underlying_unique_control_trajectories": 300,
                "train_memberships": 540,
                "valid_memberships": 60,
            },
            "split_seed": SPLIT_SEED,
            "expected_copy_bytes": expected_copy_bytes,
            "free_bytes_at_preflight": free_bytes,
            "mixed_validation_report": {
                "path": str(mixed_validation_path.resolve()),
                "sha256": sha256_file(mixed_validation_path),
            },
            "frozen_inputs": frozen_inputs,
            "participant_manifests": participant_manifests,
        }
        aggregate["canonical_content_sha256"] = canonical_hash(aggregate)
        write_json_atomic_exclusive(temporary / "build_manifest.json", aggregate)
        if args.output_root.exists() or args.output_root.is_symlink():
            raise FileExistsError(f"HDF5 root appeared during creation: {args.output_root}")
        os.replace(temporary, args.output_root)
    except Exception:
        # Preserve any temp root as diagnostic evidence; never publish it as formal.
        raise
    print(
        f"wrote={args.output_root} participants=10 memberships=600 "
        f"expected_copy_bytes={expected_copy_bytes}"
    )


if __name__ == "__main__":
    main()
