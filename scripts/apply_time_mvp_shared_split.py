#!/usr/bin/env python3
"""Apply one candidate-level 27/3 train/valid split to all reciprocal HDF5 files."""

import argparse
import json
from pathlib import Path

import h5py
import numpy as np


CONDITIONS = ("VR1P5", "V050_200", "VR3", "VR4")


def decode(value):
    return value.decode("utf-8") if isinstance(value, bytes) else str(value)


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--valid-candidates", type=int, default=3)
    parser.add_argument("--action-gap", type=int, default=2)
    return parser.parse_args()


def main():
    args = parse_args()
    selection = json.loads(args.selection.read_text(encoding="utf-8"))
    candidate_ids = list(selection["candidate_ids"])
    if len(candidate_ids) != 30 or len(set(candidate_ids)) != 30:
        raise ValueError("Selection must contain exactly 30 distinct candidate IDs")
    rng = np.random.default_rng(args.seed)
    valid_ids = sorted(
        rng.choice(candidate_ids, size=args.valid_candidates, replace=False).tolist()
    )
    valid_set = set(valid_ids)
    train_ids = [candidate_id for candidate_id in candidate_ids if candidate_id not in valid_set]
    split_manifest = {
        "schema_version": 1,
        "seed": int(args.seed),
        "selection": str(args.selection.resolve()),
        "condition_order": list(CONDITIONS),
        "candidate_order": candidate_ids,
        "train_candidate_ids": train_ids,
        "valid_candidate_ids": valid_ids,
        "raw_counts": {"train": len(train_ids), "valid": len(valid_ids)},
        "augmentation_factor": 2,
        "hdf5_counts": {"train": 2 * len(train_ids), "valid": 2 * len(valid_ids)},
    }

    condition_source_sets = {}
    for condition in CONDITIONS:
        path = args.dataset_root / f"temporal_{condition}_d30_seed1_{args.action_gap}gap.hdf5"
        with h5py.File(path, "r+") as hdf5:
            data = hdf5["data"]
            names = sorted(data, key=lambda name: int(name.split("_", 1)[1]))
            by_candidate = {}
            for name in names:
                candidate_id = decode(data[name].attrs.get("candidate_id", ""))
                if not candidate_id:
                    raise ValueError(f"{path}/{name}: missing candidate_id attribute")
                by_candidate.setdefault(candidate_id, []).append(name)
            if set(by_candidate) != set(candidate_ids):
                raise ValueError(f"{path}: source candidate set differs from selection")
            if any(len(values) != 2 for values in by_candidate.values()):
                raise ValueError(f"{path}: expected exactly two augmentations for every candidate")
            train_names = [name for name in names if decode(data[name].attrs["candidate_id"]) not in valid_set]
            valid_names = [name for name in names if decode(data[name].attrs["candidate_id"]) in valid_set]
            if len(train_names) != 54 or len(valid_names) != 6:
                raise ValueError(f"{path}: split produced {len(train_names)}/{len(valid_names)}, expected 54/6")
            mask = hdf5.require_group("mask")
            for key in ("train", "valid"):
                if key in mask:
                    del mask[key]
            string_dtype = h5py.string_dtype(encoding="utf-8")
            mask.create_dataset("train", data=np.asarray(train_names, dtype=object), dtype=string_dtype)
            mask.create_dataset("valid", data=np.asarray(valid_names, dtype=object), dtype=string_dtype)
            mask.attrs["candidate_split_manifest_json"] = json.dumps(split_manifest, sort_keys=True)
            condition_source_sets[condition] = {
                "train": sorted({decode(data[name].attrs["candidate_id"]) for name in train_names}),
                "valid": sorted({decode(data[name].attrs["candidate_id"]) for name in valid_names}),
            }
    if len({json.dumps(value, sort_keys=True) for value in condition_source_sets.values()}) != 1:
        raise RuntimeError("Applied source candidate splits differ across conditions")

    output = args.output or (args.dataset_root / "shared_train_valid_split.json")
    output.write_text(json.dumps(split_manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {output}; raw train/valid=27/3, HDF5 train/valid=54/6")


if __name__ == "__main__":
    main()
