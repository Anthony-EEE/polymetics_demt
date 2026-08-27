#!/usr/bin/env python3
"""Validate all ten Target participant HDF5 files and run loader smokes."""

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import h5py
import numpy as np


GROUP = "simulation_target_group"
SEED = 20260806
PARTICIPANTS = [f"T{index:02d}" for index in range(1, 11)]
EXPECTED_KEYS = {
    "actions": ((None, 8), np.dtype("float64")),
    "dones": ((None,), np.dtype("int64")),
    "rewards": ((None,), np.dtype("float64")),
    "states": ((None,), np.dtype("float64")),
    "obs/pointcloud": ((None, 10000, 6), np.dtype("float64")),
    "obs/robot0_arm_joints": ((None, 7), np.dtype("float64")),
    "obs/robot0_hand_joints": ((None, 1), np.dtype("float64")),
}


def sha256(path):
    import hashlib

    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def decode_rows(dataset):
    return [value.decode("utf-8") if isinstance(value, bytes) else str(value) for value in dataset[:]]


def finite_dataset(dataset, chunk=8):
    for start in range(0, len(dataset), chunk):
        if not np.isfinite(dataset[start : start + chunk]).all():
            return False
    return True


def get_path(group, key):
    node = group
    for component in key.split("/"):
        node = node[component]
    return node


def validate_one(path, participant_id, errors):
    participant_report = {
        "path": str(path.resolve()),
        "sha256": sha256(path),
        "size_bytes": path.stat().st_size,
        "trajectory_lengths": [],
    }
    with h5py.File(path, "r") as hdf5:
        for key, expected in (
            ("group", GROUP),
            ("participant_id", participant_id),
            ("source_seed", SEED),
            ("action_gap", 2),
            ("phase_offset", 0),
            ("num_points", 10000),
        ):
            actual = hdf5.attrs.get(key)
            if actual != expected:
                errors.append(f"{participant_id}:wrong_root_attr:{key}:{actual!r}")
        if "data" not in hdf5 or "mask" not in hdf5:
            errors.append(f"{participant_id}:missing_data_or_mask")
            return participant_report
        data = hdf5["data"]
        names = sorted(data, key=lambda name: int(name.split("_", 1)[1]))
        if names != [f"demo_{index}" for index in range(30)]:
            errors.append(f"{participant_id}:wrong_demo_names:{names}")
        total = 0
        source_demo_indices = []
        for name in names:
            demo = data[name]
            length = int(demo.attrs.get("num_samples", -1))
            participant_report["trajectory_lengths"].append(length)
            total += length
            if demo.attrs.get("group") != GROUP or demo.attrs.get("participant_id") != participant_id:
                errors.append(f"{participant_id}:{name}:wrong_identity_attrs")
            source_index = int(demo.attrs.get("source_demo_index", -1))
            source_demo_indices.append(source_index)
            if source_index != int(name.split("_", 1)[1]):
                errors.append(f"{participant_id}:{name}:wrong_source_demo_index:{source_index}")
            if int(demo.attrs.get("source_seed", -1)) != SEED:
                errors.append(f"{participant_id}:{name}:wrong_source_seed")
            if int(demo.attrs.get("action_gap", -1)) != 2 or int(demo.attrs.get("phase_offset", -1)) != 0:
                errors.append(f"{participant_id}:{name}:wrong_alignment_attrs")
            for key, (shape, dtype) in EXPECTED_KEYS.items():
                try:
                    dataset = get_path(demo, key)
                except KeyError:
                    errors.append(f"{participant_id}:{name}:missing_key:{key}")
                    continue
                expected_shape = tuple(length if value is None else value for value in shape)
                if dataset.shape != expected_shape:
                    errors.append(
                        f"{participant_id}:{name}:wrong_shape:{key}:{dataset.shape}:{expected_shape}"
                    )
                if dataset.dtype != dtype:
                    errors.append(f"{participant_id}:{name}:wrong_dtype:{key}:{dataset.dtype}:{dtype}")
                if not finite_dataset(dataset, chunk=1 if key == "obs/pointcloud" else 32):
                    errors.append(f"{participant_id}:{name}:nonfinite:{key}")
            if length > 0:
                dones = demo["dones"][:]
                if not (dones[-1] == 1 and np.count_nonzero(dones) == 1):
                    errors.append(f"{participant_id}:{name}:invalid_terminal_dones")
                raw_count = int(demo.attrs.get("raw_frame_count", -1))
                if length != int(math.ceil(raw_count / 2.0)):
                    errors.append(
                        f"{participant_id}:{name}:wrong_gap_length:raw={raw_count}:hdf5={length}"
                    )
                raw_path = Path(str(demo.attrs.get("source_raw_path", "")))
                result_path = raw_path.parent / f"demo_{source_index:02d}.json"
                metadata_path = raw_path / "metadata.json"
                if not raw_path.is_dir() or not result_path.is_file() or not metadata_path.is_file():
                    errors.append(f"{participant_id}:{name}:missing_raw_provenance")
                else:
                    if sha256(result_path) != demo.attrs.get("source_result_sha256"):
                        errors.append(f"{participant_id}:{name}:result_hash_mismatch")
                    if sha256(metadata_path) != demo.attrs.get("source_metadata_sha256"):
                        errors.append(f"{participant_id}:{name}:metadata_hash_mismatch")
                    frame_dirs = sorted(
                        (entry for entry in raw_path.iterdir() if entry.is_dir() and entry.name.startswith("frame_")),
                        key=lambda entry: int(entry.name.split("_", 1)[1]),
                    )
                    arm = np.stack([np.loadtxt(frame / "arm_joints.txt").reshape(-1) for frame in frame_dirs])
                    hand = np.stack([np.loadtxt(frame / "hand_joints.txt").reshape(-1) for frame in frame_dirs])
                    raw_indices = np.arange(0, len(frame_dirs), 2)
                    future = np.minimum(raw_indices + 2, len(frame_dirs) - 1)
                    expected_actions = np.concatenate((arm[future], hand[future]), axis=1)
                    if not np.array_equal(demo["obs/robot0_arm_joints"][:], arm[raw_indices]):
                        errors.append(f"{participant_id}:{name}:arm_observation_alignment_mismatch")
                    if not np.array_equal(demo["obs/robot0_hand_joints"][:], hand[raw_indices]):
                        errors.append(f"{participant_id}:{name}:hand_observation_alignment_mismatch")
                    if not np.array_equal(demo["actions"][:], expected_actions):
                        errors.append(f"{participant_id}:{name}:action_alignment_mismatch")
        if source_demo_indices != list(range(30)):
            errors.append(f"{participant_id}:wrong_source_demo_indices:{source_demo_indices}")
        if int(data.attrs.get("total", -1)) != total:
            errors.append(f"{participant_id}:data_total_mismatch:{data.attrs.get('total')}:{total}")
        for key, size in (("mean_init_arm", 7), ("mean_init_hand", 1)):
            value = np.asarray(data.attrs.get(key, [])).reshape(-1)
            if value.shape != (size,) or not np.isfinite(value).all():
                errors.append(f"{participant_id}:invalid_data_attr:{key}:{value.shape}")
        train = decode_rows(hdf5["mask/train"]) if "train" in hdf5["mask"] else []
        valid = decode_rows(hdf5["mask/valid"]) if "valid" in hdf5["mask"] else []
        if len(train) != 27 or len(valid) != 3 or set(train) & set(valid) or set(train) | set(valid) != set(names):
            errors.append(f"{participant_id}:invalid_train_valid_masks")
        participant_report.update(
            {
                "trajectory_count": len(names),
                "total_samples": total,
                "train_demo_names": train,
                "valid_demo_names": valid,
                "length_min": min(participant_report["trajectory_lengths"], default=None),
                "length_max": max(participant_report["trajectory_lengths"], default=None),
            }
        )
    return participant_report


def loader_smoke(path, filter_key):
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
    if shapes != {
        "actions": [20, 8],
        "obs/robot0_arm_joints": [20, 7],
        "obs/robot0_hand_joints": [20, 1],
        "obs/pointcloud": [20, 10000, 6],
    }:
        raise ValueError(f"Unexpected SequenceDataset item shapes: {shapes}")
    if not all(np.isfinite(value).all() for value in (item["actions"], *item["obs"].values())):
        raise ValueError("SequenceDataset returned non-finite values")
    result = {"filter_key": filter_key, "dataset_length": len(dataset), "item_shapes": shapes}
    dataset.close_and_delete_hdf5_handle()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hdf5-root", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--skip-loader-smoke", action="store_true")
    args = parser.parse_args()
    output = args.output or args.hdf5_root / "validation_report.json"
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite HDF5 validation report: {output}")
    errors = []
    reports = {}
    sidecars = {}
    for participant_id in PARTICIPANTS:
        path = args.hdf5_root / f"{GROUP}_{participant_id}_d30_seed{SEED}_gap2.hdf5"
        if not path.is_file():
            errors.append(f"{participant_id}:missing_hdf5:{path}")
            continue
        try:
            reports[participant_id] = validate_one(path, participant_id, errors)
            sidecar_path = path.with_suffix(".manifest.json")
            if not sidecar_path.is_file():
                errors.append(f"{participant_id}:missing_conversion_manifest:{sidecar_path}")
            else:
                sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
                sidecars[participant_id] = sidecar
                if (
                    sidecar.get("group") != GROUP
                    or sidecar.get("participant_id") != participant_id
                    or sidecar.get("source_seed") != SEED
                    or sidecar.get("trajectory_count") != 30
                    or sidecar.get("hdf5_sha256") != reports[participant_id]["sha256"]
                    or len(sidecar.get("raw_to_hdf5", [])) != 30
                ):
                    errors.append(f"{participant_id}:invalid_conversion_manifest:{sidecar_path}")
        except Exception as exc:
            errors.append(f"{participant_id}:validation_exception:{type(exc).__name__}:{exc}")
    split_values = {
        json.dumps(
            {
                "train": row.get("train_demo_names"),
                "valid": row.get("valid_demo_names"),
            },
            sort_keys=True,
        )
        for row in reports.values()
    }
    if len(split_values) > 1:
        errors.append("participant_train_valid_splits_differ")

    aggregate_paths = {
        "raw_to_hdf5_manifest": args.hdf5_root / "raw_to_hdf5_manifest.json",
        "schema_summary": args.hdf5_root / "schema_summary.json",
        "trajectory_length_summary": args.hdf5_root / "trajectory_length_summary.json",
    }
    aggregates = {}
    for name, path in aggregate_paths.items():
        if not path.is_file():
            errors.append(f"missing_aggregate_artifact:{name}:{path}")
            continue
        try:
            aggregates[name] = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(f"invalid_aggregate_json:{name}:{type(exc).__name__}:{exc}")
    aggregate = aggregates.get("raw_to_hdf5_manifest")
    if aggregate is not None:
        if (
            aggregate.get("group") != GROUP
            or aggregate.get("participant_order") != PARTICIPANTS
            or aggregate.get("counts")
            != {"participants": 10, "trajectories_per_participant": 30, "total_trajectories": 300}
            or aggregate.get("participant_manifests")
            != [sidecars.get(participant_id) for participant_id in PARTICIPANTS]
        ):
            errors.append("invalid_raw_to_hdf5_aggregate_manifest")
        if aggregates.get("schema_summary") != aggregate.get("schema"):
            errors.append("schema_summary_differs_from_aggregate")
    length_summary = aggregates.get("trajectory_length_summary")
    if length_summary is not None and set(length_summary) != set(PARTICIPANTS):
        errors.append("trajectory_length_summary_participants_mismatch")
    for participant_id, row in reports.items():
        length_row = (length_summary or {}).get(participant_id)
        lengths = row.get("trajectory_lengths", [])
        expected_length_row = {
            "count": len(lengths),
            "min": min(lengths) if lengths else None,
            "max": max(lengths) if lengths else None,
            "mean": float(np.mean(lengths)) if lengths else None,
            "total": sum(lengths),
        }
        if length_row != expected_length_row:
            errors.append(f"{participant_id}:trajectory_length_summary_mismatch")

    expected_files = {
        *(f"{GROUP}_{participant_id}_d30_seed{SEED}_gap2.hdf5" for participant_id in PARTICIPANTS),
        *(f"{GROUP}_{participant_id}_d30_seed{SEED}_gap2.manifest.json" for participant_id in PARTICIPANTS),
        "raw_to_hdf5_manifest.json",
        "schema_summary.json",
        "trajectory_length_summary.json",
    }
    if output.parent.resolve() == args.hdf5_root.resolve():
        expected_files.add(output.name)
    actual_files = {path.name for path in args.hdf5_root.iterdir() if path.is_file()}
    unexpected_files = sorted(actual_files - expected_files)
    missing_expected_files = sorted((expected_files - {output.name}) - actual_files)
    if unexpected_files:
        errors.append(f"unexpected_or_partial_hdf5_artifacts:{unexpected_files}")
    if missing_expected_files:
        errors.append(f"missing_hdf5_artifacts:{missing_expected_files}")
    empty_dirs = [str(path) for path in args.hdf5_root.rglob("*") if path.is_dir() and not any(path.iterdir())]
    zero_byte_files = [str(path) for path in args.hdf5_root.rglob("*") if path.is_file() and path.stat().st_size == 0]
    if empty_dirs:
        errors.append(f"empty_hdf5_directories:{empty_dirs}")
    if zero_byte_files:
        errors.append(f"zero_byte_hdf5_artifacts:{zero_byte_files}")

    loader_reports = {}
    if not args.skip_loader_smoke and not errors:
        for participant_id in PARTICIPANTS:
            path = Path(reports[participant_id]["path"])
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
            "trajectories": sum(row.get("trajectory_count", 0) for row in reports.values()),
            "loader_smokes": sum(len(row) for row in loader_reports.values()),
            "participant_conversion_manifests": len(sidecars),
            "unexpected_or_partial_artifacts": len(unexpected_files),
            "empty_directories": len(empty_dirs),
            "zero_byte_files": len(zero_byte_files),
        },
        "participant_reports": reports,
        "participant_conversion_manifests": sidecars,
        "aggregate_artifacts": {
            name: {"path": str(path.resolve()), "sha256": sha256(path)}
            for name, path in aggregate_paths.items()
            if path.is_file()
        },
        "loader_smoke": loader_reports,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report["counts"], sort_keys=True))
    print(f"passed={report['passed']} errors={len(errors)} output={output}")
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
