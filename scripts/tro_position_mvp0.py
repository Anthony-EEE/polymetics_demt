#!/usr/bin/env python3
"""Frozen utilities and execution driver for T-RO Stage 1 Position MVP."""

import argparse
import hashlib
import json
import math
import os
import random
import shutil
import sys
from pathlib import Path

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES_DIR = PROJECT_ROOT / "examples"
if str(EXAMPLES_DIR) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_DIR))

EXPERIMENT_ROOT = PROJECT_ROOT / "experiments" / "mvp0_position_event"
MANIFEST_ROOT = EXPERIMENT_ROOT / "manifests"
DATA_ROOT = PROJECT_ROOT / "dataset" / "tro_position_mvp0"
MODEL_ROOT = PROJECT_ROOT.parent / "trained_models" / "tro_position_mvp0"
LEGACY_ROOT = (
    PROJECT_ROOT
    / "dataset"
    / "ar_guidance_spatial_S15_S35"
    / "policy_rollouts_seed628_shared_r35_paired_n50_h200"
)
LEGACY_SUMMARY = LEGACY_ROOT / "summary_seed628_n50.json"
LEGACY_PARENT = LEGACY_ROOT / "shared_start_manifest_seed628_n50_r35.json"
LEGACY_CHECKPOINT_MANIFEST = LEGACY_ROOT / "checkpoint_manifest.json"

CONDITIONS = {
    "START15_APP6": (0.15, 0.060),
    "START35_APP6": (0.35, 0.060),
    "START25_APP3P6": (0.25, 0.036),
    "START25_APP8P4": (0.25, 0.084),
}
CONDITION_ORDER = tuple(CONDITIONS)
BANKS = {
    "legacy_seed628_reference_r00_r25_n25_v1": {
        "indices": [
            0, 1, 2, 3, 9, 12, 13, 14, 16, 17, 18, 20, 21, 27, 29, 33,
            34, 35, 37, 40, 41, 42, 45, 46, 48,
        ],
        "minimum": 0.0,
        "maximum": 0.25,
        "predicate": "0.00 <= radial_distance_from_center <= 0.25",
    },
    "legacy_seed628_outer_r25_r35_n25_v1": {
        "indices": [
            4, 5, 6, 7, 8, 10, 11, 15, 19, 22, 23, 24, 25, 26, 28, 30,
            31, 32, 36, 38, 39, 43, 44, 47, 49,
        ],
        "minimum": 0.25,
        "maximum": 0.35,
        "predicate": "0.25 < radial_distance_from_center <= 0.35",
    },
}
EXPECTED_HASHES = {
    "summary": "ec9c95ba26e3a4b9f18ae7c34966a8d55dc3acca2af10c18bdbc43d12c827d78",
    "parent_manifest": "84316b36922ea71225615d285bffccdfef4b99289650e302c963deb761f516ce",
    "s25_epoch80": "e666ab6a53f87f8d0f2e0a5ba29bd34b28cc39930d57cc848abfa5745465d60f",
}
BLOCKS = {
    0: {"collection_seed": 1701, "training_seed": 2701},
    1: {"collection_seed": 1702, "training_seed": 2702},
}


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tree_sha256(path):
    path = Path(path)
    digest = hashlib.sha256()
    for child in sorted(p for p in path.rglob("*") if p.is_file()):
        digest.update(str(child.relative_to(path)).encode("utf-8"))
        digest.update(b"\0")
        with child.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        digest.update(b"\0")
    return digest.hexdigest()


def evaluation_protocol(bank_id, minimum, maximum):
    return {
        "seed": 628,
        "num_rollouts": 25,
        "horizon": 200,
        "sample_hz": 8.0,
        "action_gap": 2,
        "action_dt": 0.25,
        "terminate_on_success": True,
        "success_lift_height": 0.2,
        "num_points": 10000,
        "corridor_start_center": [0.3, 0.0, 0.5],
        "shared_start_radius_min": minimum,
        "shared_start_radius_max": maximum,
        "corridor_start_max_error": 0.025,
        "evaluation_distribution": bank_id,
        "rng_protocol": (
            "independent spatial/runtime/point-cloud streams; Python, NumPy, "
            "Torch and CUDA reset per rollout"
        ),
        "bank_id": bank_id,
    }


def freeze_legacy(_args):
    summary_hash = sha256(LEGACY_SUMMARY)
    parent_hash = sha256(LEGACY_PARENT)
    if summary_hash != EXPECTED_HASHES["summary"]:
        raise ValueError(f"Legacy summary hash mismatch: {summary_hash}")
    if parent_hash != EXPECTED_HASHES["parent_manifest"]:
        raise ValueError(f"Legacy parent manifest hash mismatch: {parent_hash}")

    checkpoint_manifest = read_json(LEGACY_CHECKPOINT_MANIFEST)
    s25 = checkpoint_manifest["checkpoints"]["S25"]
    checkpoint_hash = sha256(s25["path"])
    if checkpoint_hash != EXPECTED_HASHES["s25_epoch80"]:
        raise ValueError(f"Legacy S25 checkpoint hash mismatch: {checkpoint_hash}")

    parent = read_json(LEGACY_PARENT)
    records = parent["shared_start_records"]
    starts = parent["shared_corridor_starts"]
    reference_indices = [
        i for i, row in enumerate(records)
        if 0.0 <= float(row["radial_distance_from_center"]) <= 0.25
    ]
    outer_indices = [
        i for i, row in enumerate(records)
        if 0.25 < float(row["radial_distance_from_center"]) <= 0.35
    ]
    expected_reference = BANKS["legacy_seed628_reference_r00_r25_n25_v1"]["indices"]
    expected_outer = BANKS["legacy_seed628_outer_r25_r35_n25_v1"]["indices"]
    if reference_indices != expected_reference:
        raise ValueError(f"Reference bank indices mismatch: {reference_indices}")
    if outer_indices != expected_outer:
        raise ValueError(f"Outer bank indices mismatch: {outer_indices}")

    child_hashes = {}
    for bank_id, spec in BANKS.items():
        indices = spec["indices"]
        child = {
            "schema_version": 1,
            "manifest_type": "read_only_child_of_legacy_shared_start_manifest",
            "bank_id": bank_id,
            "condition_order": list(CONDITION_ORDER),
            "protocol": evaluation_protocol(bank_id, spec["minimum"], spec["maximum"]),
            "seed": 628,
            "num_rollouts": 25,
            "sample_hz": 8.0,
            "corridor_start_center": [0.3, 0.0, 0.5],
            "start_sampling_mode": "xz_disk" if spec["minimum"] == 0.0 else "xz_annulus",
            "shared_start_radius_min": spec["minimum"],
            "shared_start_radius_max": spec["maximum"],
            "shared_start_radius": spec["maximum"],
            "corridor_start_max_error": 0.025,
            "max_start_sample_attempts": 1000,
            "evaluation_distribution": bank_id,
            "parent_manifest_path": str(LEGACY_PARENT),
            "parent_manifest_sha256": parent_hash,
            "deterministic_radius_predicate": spec["predicate"],
            "legacy_rollout_indices": indices,
            "state_ids": [f"legacy_seed628_state_{i:03d}" for i in indices],
            "shared_corridor_starts": [starts[i] for i in indices],
            "shared_start_records": [records[i] for i in indices],
        }
        child_path = MANIFEST_ROOT / f"{bank_id}.json"
        write_json(child_path, child)
        child_hashes[bank_id] = {
            "path": str(child_path),
            "sha256": sha256(child_path),
            "num_states": len(indices),
            "legacy_rollout_indices": indices,
        }

    evidence = {
        "schema_version": 1,
        "status": "verified",
        "legacy_root_read_only": str(LEGACY_ROOT),
        "verified_hashes": {
            "summary_seed628_n50": {
                "path": str(LEGACY_SUMMARY),
                "sha256": summary_hash,
            },
            "shared_start_manifest_seed628_n50_r35": {
                "path": str(LEGACY_PARENT),
                "sha256": parent_hash,
            },
            "s25_epoch80_checkpoint": {
                "path": s25["path"],
                "sha256": checkpoint_hash,
                "epoch": 80,
            },
        },
        "child_banks": child_hashes,
        "historical_only": {
            "S15": {"reference_bank": 14, "outer_bank": 4, "denominator": 25},
            "S25": {"reference_bank": 8, "outer_bank": 10, "denominator": 25},
            "S35": {"reference_bank": 5, "outer_bank": 2, "denominator": 25},
        },
    }
    write_json(MANIFEST_ROOT / "legacy_evidence.json", evidence)
    print(json.dumps(evidence, indent=2))


def make_latents(args):
    block = int(args.block)
    settings = BLOCKS[block]
    rng = np.random.default_rng(settings["collection_seed"])
    candidates = []
    for candidate_index in range(int(args.num_candidates)):
        candidates.append(
            {
                "candidate_index": candidate_index,
                "start_angle": float(rng.uniform(0.0, 2.0 * math.pi)),
                "start_radial_quantile": float(rng.uniform(0.0, 1.0)),
                "approach_angle": float(rng.uniform(0.0, 2.0 * math.pi)),
                "approach_radial_quantile": float(rng.uniform(0.0, 1.0)),
                "collection_seed": settings["collection_seed"],
                "runtime_seed": int(rng.integers(0, 2**32, dtype=np.uint32)),
            }
        )
    payload = {
        "schema_version": 1,
        "block": block,
        "condition_order": list(CONDITION_ORDER),
        "collection_seed": settings["collection_seed"],
        "training_seed": settings["training_seed"],
        "sampling": {
            "start_plane": "xz",
            "approach_plane": "xy",
            "radial_mapping": "realised_fraction = sqrt(radial_quantile)",
            "rejection_rule": "reject candidate for the entire block if any condition fails",
        },
        "target_successful_demonstrations_per_condition": 30,
        "num_candidates_including_replacements": len(candidates),
        "candidates": candidates,
    }
    path = MANIFEST_ROOT / f"paired_latents_b{block}.json"
    if path.exists() and read_json(path) != payload:
        raise FileExistsError(f"Refusing to replace a different frozen latent manifest: {path}")
    write_json(path, payload)
    print(f"Wrote {path} sha256={sha256(path)} candidates={len(candidates)}")


def run_candidate(condition, latent, output_dir, sample_hz, playback_speed):
    from main_abla_1 import PandaSim

    start_radius, approach_radius = CONDITIONS[condition]
    random.seed(int(latent["runtime_seed"]))
    np.random.seed(int(latent["runtime_seed"]))
    sim = PandaSim(gui=False, output_dir=output_dir, sample_hz=sample_hz)
    sim.playback_speed = playback_speed
    try:
        sim.setup()
        sim.begin_demo(int(latent["candidate_index"]))
        success, details = sim.run_pick_and_lift_ablation(
            condition_label=condition,
            corridor_start_radius=start_radius,
            pre_grasp_radius=approach_radius,
            corridor_start_center=(0.30, 0.0, 0.50),
            success_lift_height=0.20,
            paired_latent=latent,
        )
        return bool(success), details, sim.demo_dir
    finally:
        sim.close()


def collect(args):
    block = int(args.block)
    target = int(args.target)
    manifest = read_json(MANIFEST_ROOT / f"paired_latents_b{block}.json")
    run_tag = "smoke" if args.smoke else f"block{block}"
    run_root = DATA_ROOT / run_tag
    raw_root = run_root / "raw"
    staging_root = run_root / ".paired_staging"
    progress_path = run_root / "collection_progress.json"
    progress = (
        read_json(progress_path)
        if progress_path.exists()
        else {
            "schema_version": 1,
            "block": block,
            "target": target,
            "latent_manifest": str(MANIFEST_ROOT / f"paired_latents_b{block}.json"),
            "latent_manifest_sha256": sha256(MANIFEST_ROOT / f"paired_latents_b{block}.json"),
            "accepted_candidate_indices": [],
            "rejected_candidates": [],
            "infrastructure_retries": [],
        }
    )
    if int(progress["block"]) != block or int(progress["target"]) != target:
        raise ValueError(f"Existing collection progress has different block/target: {progress_path}")
    accepted = list(progress["accepted_candidate_indices"])
    for condition in CONDITION_ORDER:
        condition_root = raw_root / condition
        existing = sorted(condition_root.glob("demo_*")) if condition_root.exists() else []
        if len(existing) != len(accepted):
            raise RuntimeError(
                f"Resume invariant failed for {condition}: {len(existing)} demos != "
                f"{len(accepted)} accepted candidates"
            )
    if len(accepted) >= target:
        print(f"Collection already complete: {len(accepted)}/{target}")
        return

    decided = set(accepted) | {
        int(row["candidate_index"]) for row in progress["rejected_candidates"]
    }
    for latent in manifest["candidates"]:
        candidate_index = int(latent["candidate_index"])
        if candidate_index in decided:
            continue
        candidate_staging = staging_root / f"candidate_{candidate_index:04d}"
        if candidate_staging.exists():
            shutil.rmtree(candidate_staging)
        condition_results = {}
        all_success = True
        for condition in CONDITION_ORDER:
            success, details, demo_dir = run_candidate(
                condition,
                latent,
                candidate_staging / condition,
                sample_hz=float(args.sample_hz),
                playback_speed=float(args.playback_speed),
            )
            condition_results[condition] = {
                "success": success,
                "details": details,
            }
            if not success:
                all_success = False
                break

        if not all_success:
            progress["rejected_candidates"].append(
                {
                    "candidate_index": candidate_index,
                    "condition_results": condition_results,
                    "reason": "waypoint_unreachable_or_final_cube_z_below_0.20",
                }
            )
            if candidate_staging.exists():
                shutil.rmtree(candidate_staging)
            write_json(progress_path, progress)
            print(f"Rejected paired candidate {candidate_index}", flush=True)
            continue

        accepted_index = len(accepted)
        for condition in CONDITION_ORDER:
            source = candidate_staging / condition / f"demo_{candidate_index}"
            destination_root = raw_root / condition
            destination_root.mkdir(parents=True, exist_ok=True)
            destination = destination_root / f"demo_{accepted_index}"
            if destination.exists():
                raise FileExistsError(f"Refusing to overwrite {destination}")
            source.rename(destination)
        shutil.rmtree(candidate_staging)
        accepted.append(candidate_index)
        progress["accepted_candidate_indices"] = accepted
        write_json(progress_path, progress)
        print(
            f"Accepted paired candidate {candidate_index}: {len(accepted)}/{target}",
            flush=True,
        )
        if len(accepted) >= target:
            break
    if len(accepted) != target:
        raise RuntimeError(
            f"Candidate pool exhausted at {len(accepted)}/{target}; frozen settings unchanged"
        )


def validate_raw(args):
    from check_abla1_dataset import check_demo
    from main_abla_1 import disk_offset

    block = int(args.block)
    target = int(args.target)
    run_tag = "smoke" if args.smoke else f"block{block}"
    run_root = DATA_ROOT / run_tag
    raw_root = run_root / "raw"
    progress = read_json(run_root / "collection_progress.json")
    accepted = progress["accepted_candidate_indices"]
    if len(accepted) != target:
        raise ValueError(f"Expected {target} accepted candidates, got {len(accepted)}")

    errors = []
    dataset_records = []
    paired_by_demo = {}
    for condition in CONDITION_ORDER:
        condition_root = raw_root / condition
        demos = sorted(
            condition_root.glob("demo_*"),
            key=lambda p: int(p.name.split("_", 1)[1]),
        )
        if len(demos) != target:
            errors.append(f"{condition}: expected {target} demos, got {len(demos)}")
        candidate_ids = []
        for demo_index, demo_dir in enumerate(demos):
            _, demo_errors, _ = check_demo(
                demo_dir,
                expected_condition=condition,
            )
            errors.extend(str(error) for error in demo_errors)
            metadata = read_json(demo_dir / "metadata.json")
            if not math.isclose(float(metadata.get("sample_hz", -1.0)), 8.0):
                errors.append(
                    f"{condition}/{demo_dir.name}: sample_hz="
                    f"{metadata.get('sample_hz')} must match frozen legacy S25 value 8.0"
                )
            latent = metadata["paired_latent"]
            candidate_ids.append(int(latent["candidate_index"]))
            paired_by_demo.setdefault(demo_index, []).append(latent)
            start_radius, approach_radius = CONDITIONS[condition]
            expected_start = disk_offset(
                latent["start_angle"], latent["start_radial_quantile"], start_radius, "xz"
            )
            expected_approach = disk_offset(
                latent["approach_angle"],
                latent["approach_radial_quantile"],
                approach_radius,
                "xy",
            )
            if not np.allclose(metadata["corridor_start_delta"], expected_start, atol=1e-10):
                errors.append(f"{condition}/{demo_dir.name}: Start offset mismatch")
            if not np.allclose(metadata["pre_grasp_delta"], expected_approach, atol=1e-10):
                errors.append(f"{condition}/{demo_dir.name}: Approach offset mismatch")
            cube = metadata["cube_position"]
            if not np.allclose(metadata["grasp"], [cube[0], cube[1], 0.04], atol=1e-10):
                errors.append(f"{condition}/{demo_dir.name}: fixed grasp target changed")
            if not np.allclose(metadata["lift"], [cube[0], cube[1], 0.30], atol=1e-10):
                errors.append(f"{condition}/{demo_dir.name}: fixed lift target changed")
        if candidate_ids != accepted:
            errors.append(f"{condition}: candidate IDs differ from block accepted list")
        dataset_records.append(
            {
                "condition": condition,
                "block": block,
                "collection_seed": BLOCKS[block]["collection_seed"],
                "canonical_candidate_ids": candidate_ids,
                "radii": {
                    "start": CONDITIONS[condition][0],
                    "approach": CONDITIONS[condition][1],
                },
                "raw_path": str(condition_root),
                "raw_tree_sha256": tree_sha256(condition_root),
                "num_successful_demonstrations": len(demos),
                "failures_and_replacements": progress["rejected_candidates"],
            }
        )
    for demo_index, latents in paired_by_demo.items():
        if any(latent != latents[0] for latent in latents[1:]):
            errors.append(f"demo_{demo_index}: normalized latent differs across conditions")
    if errors:
        raise ValueError("Raw validation failed:\n" + "\n".join(errors))

    report = {
        "schema_version": 1,
        "block": block,
        "run_tag": run_tag,
        "target_per_condition": target,
        "condition_order": list(CONDITION_ORDER),
        "accepted_candidate_indices": accepted,
        "rejected_candidates": progress["rejected_candidates"],
        "datasets": dataset_records,
        "status": "valid",
    }
    write_json(run_root / "raw_validation.json", report)
    if not args.smoke:
        datasets_path = MANIFEST_ROOT / "datasets.json"
        existing = read_json(datasets_path) if datasets_path.exists() else {
            "schema_version": 1,
            "blocks": {},
        }
        existing["blocks"][str(block)] = report
        write_json(datasets_path, existing)
    print(f"Validated {len(CONDITION_ORDER) * target} successful paired demonstrations")


def create_hdf5(args):
    arcap_step1 = Path("/users/k23114984/code/arcap_policy/STEP1_build_dataset")
    if str(arcap_step1) not in sys.path:
        sys.path.insert(0, str(arcap_step1))
    from dataset_utils import process_hdf5_arcap_multi

    block = int(args.block)
    block_root = DATA_ROOT / f"block{block}"
    output_root = block_root / "hdf5"
    output_root.mkdir(parents=True, exist_ok=True)
    for condition in CONDITION_ORDER:
        raw = block_root / "raw" / condition
        output = output_root / f"{condition}_b{block}_d30_2gap.hdf5"
        if output.exists():
            raise FileExistsError(f"Refusing to overwrite existing HDF5: {output}")
        process_hdf5_arcap_multi(
            output_hdf5_file=str(output),
            dataset_folders=[str(raw)],
            action_gap=2,
            num_points_to_sample=10000,
            hand_ahead=0,
            last_mean=1,
            visualize=False,
        )
        print(f"Wrote {output} sha256={sha256(output)}", flush=True)
    apply_legacy_train_valid_split(block)
    update_hdf5_manifest(block)


def apply_legacy_train_valid_split(block):
    import h5py

    legacy_hdf5 = (
        PROJECT_ROOT
        / "dataset"
        / "ar_guidance_spatial_S15_S35"
        / "spatial_S25_d30_seed1_2gap.hdf5"
    )
    with h5py.File(legacy_hdf5, "r") as source:
        train_names = [
            value.decode("utf-8") if isinstance(value, bytes) else str(value)
            for value in source["mask/train"][:]
        ]
        valid_names = [
            value.decode("utf-8") if isinstance(value, bytes) else str(value)
            for value in source["mask/valid"][:]
        ]
    if len(train_names) != 54 or len(valid_names) != 6:
        raise ValueError("Legacy S25 mask is not the expected fixed 54/6 split")
    split = {
        "schema_version": 1,
        "source": "exact_read_only_legacy_S25_train_valid_mask",
        "source_hdf5_path": str(legacy_hdf5),
        "source_hdf5_sha256": sha256(legacy_hdf5),
        "train_names": train_names,
        "valid_names": valid_names,
        "condition_order": list(CONDITION_ORDER),
        "block": int(block),
    }
    for condition in CONDITION_ORDER:
        path = DATA_ROOT / f"block{block}" / "hdf5" / f"{condition}_b{block}_d30_2gap.hdf5"
        with h5py.File(path, "r+") as hdf5:
            data_names = set(hdf5["data"])
            if data_names != set(train_names) | set(valid_names):
                raise ValueError(f"{path}: data keys differ from frozen legacy split keys")
            mask = hdf5.require_group("mask")
            for key in ("train", "valid"):
                if key in mask:
                    del mask[key]
            dtype = h5py.string_dtype(encoding="utf-8")
            mask.create_dataset("train", data=np.asarray(train_names, dtype=object), dtype=dtype)
            mask.create_dataset("valid", data=np.asarray(valid_names, dtype=object), dtype=dtype)
            mask.attrs["tro_position_split_manifest_json"] = json.dumps(split, sort_keys=True)
    write_json(MANIFEST_ROOT / f"train_valid_split_b{block}.json", split)
    print(f"Applied exact read-only legacy S25 54/6 train/valid masks to block {block}")


def update_hdf5_manifest(block):
    output_root = DATA_ROOT / f"block{block}" / "hdf5"
    datasets = read_json(MANIFEST_ROOT / "datasets.json")
    for record in datasets["blocks"][str(block)]["datasets"]:
        output = output_root / f"{record['condition']}_b{block}_d30_2gap.hdf5"
        record["hdf5_path"] = str(output)
        record["hdf5_sha256"] = sha256(output)
        record["hdf5_size_bytes"] = output.stat().st_size
    write_json(MANIFEST_ROOT / "datasets.json", datasets)


def apply_split(args):
    block = int(args.block)
    apply_legacy_train_valid_split(block)
    update_hdf5_manifest(block)


def create_train_configs(args):
    block = int(args.block)
    template_path = Path(
        "/users/k23114984/code/arcap_policy/STEP2_train_policy/"
        "robomimic/training_config/sim_test_00.json"
    )
    template = read_json(template_path)
    config_root = EXPERIMENT_ROOT / "configs" / "training_generated" / f"block{block}"
    config_root.mkdir(parents=True, exist_ok=True)
    for condition in CONDITION_ORDER:
        config = json.loads(json.dumps(template))
        dataset = DATA_ROOT / f"block{block}" / "hdf5" / f"{condition}_b{block}_d30_2gap.hdf5"
        experiment_name = f"tro_pos_b{block}_{condition}_d30_seed{BLOCKS[block]['training_seed']}_2gap"
        config["train"]["data"][0]["path"] = str(dataset)
        config["train"]["output_dir"] = str(MODEL_ROOT / f"block{block}" / condition)
        config["train"]["seed"] = BLOCKS[block]["training_seed"]
        config["train"]["num_epochs"] = 40
        config["experiment"]["name"] = experiment_name
        config["experiment"]["save"]["enabled"] = True
        config["experiment"]["save"]["every_n_epochs"] = 20
        config["experiment"]["save"]["epochs"] = [40]
        config["experiment"]["save"]["on_best_validation"] = False
        config["experiment"]["save"]["on_best_rollout_return"] = False
        config["experiment"]["save"]["on_best_rollout_success_rate"] = False
        write_json(config_root / f"{condition}.json", config)
    print(f"Wrote four frozen 40-epoch configs under {config_root}")


def freeze_checkpoints(args):
    block = int(args.block)
    checkpoints = {}
    policies = {}
    for condition in CONDITION_ORDER:
        condition_root = MODEL_ROOT / f"block{block}" / condition
        candidates = sorted(condition_root.glob("*/*/models/model_epoch_40.pth"))
        if len(candidates) != 1:
            raise ValueError(
                f"Expected exactly one epoch-40 checkpoint for {condition}, got {candidates}"
            )
        checkpoint = candidates[0]
        later = list(checkpoint.parent.glob("model_epoch_*.pth"))
        epochs = sorted(int(path.stem.rsplit("_", 1)[1]) for path in later)
        if max(epochs) != 40:
            raise ValueError(f"{condition} contains checkpoint after epoch 40: {epochs}")
        config_path = (
            EXPERIMENT_ROOT
            / "configs"
            / "training_generated"
            / f"block{block}"
            / f"{condition}.json"
        )
        record = {
            "condition": condition,
            "block": block,
            "training_seed": BLOCKS[block]["training_seed"],
            "epoch": 40,
            "path": str(checkpoint),
            "sha256": sha256(checkpoint),
            "config_path": str(config_path),
            "config_sha256": sha256(config_path),
            "git_commit": os.popen(f"git -C {PROJECT_ROOT} rev-parse HEAD").read().strip(),
        }
        checkpoints[condition] = record
        policies[condition] = {
            **record,
            "experiment_dir": str(checkpoint.parents[1]),
        }
    checkpoint_manifest = {
        "schema_version": 1,
        "condition_order": list(CONDITION_ORDER),
        "checkpoints": checkpoints,
    }
    block_path = MANIFEST_ROOT / f"checkpoints_b{block}.json"
    write_json(block_path, checkpoint_manifest)
    aggregate_path = MANIFEST_ROOT / "checkpoints.json"
    aggregate = read_json(aggregate_path) if aggregate_path.exists() else {
        "schema_version": 1,
        "blocks": {},
    }
    aggregate["blocks"][str(block)] = checkpoint_manifest
    write_json(aggregate_path, aggregate)
    policies_path = MANIFEST_ROOT / "policies.json"
    aggregate_policies = read_json(policies_path) if policies_path.exists() else {
        "schema_version": 1,
        "blocks": {},
    }
    aggregate_policies["blocks"][str(block)] = policies
    write_json(policies_path, aggregate_policies)
    print(f"Frozen four epoch-40 checkpoints in {block_path}")


def checkpoint_epoch(path):
    try:
        return int(Path(path).stem.rsplit("_", 1)[1])
    except (IndexError, ValueError) as exc:
        raise ValueError(f"Cannot parse checkpoint epoch from {path}") from exc


def freeze_latest_existing_checkpoints(args):
    """Inventory existing checkpoints and select the highest saved epoch."""
    block = int(args.block)
    checkpoints = {}
    for condition in CONDITION_ORDER:
        condition_root = MODEL_ROOT / f"block{block}" / condition
        candidates = sorted(
            condition_root.glob("*/*/models/model_epoch_*.pth"),
            key=checkpoint_epoch,
        )
        if not candidates:
            raise FileNotFoundError(f"No existing checkpoints under {condition_root}")
        run_dirs = {path.parents[1] for path in candidates}
        if len(run_dirs) != 1:
            raise ValueError(
                f"Expected exactly one existing training run for {condition}, got "
                f"{sorted(str(path) for path in run_dirs)}"
            )
        available = [
            {
                "epoch": checkpoint_epoch(path),
                "path": str(path),
                "sha256": sha256(path),
                "size_bytes": path.stat().st_size,
            }
            for path in candidates
        ]
        selected = available[-1]
        checkpoints[condition] = {
            "condition": condition,
            "block": block,
            "training_seed": BLOCKS[block]["training_seed"],
            "selection_rule": (
                "highest numeric model_epoch_*.pth already present in the sole "
                "existing training run; no retraining"
            ),
            "available_checkpoints": available,
            **selected,
            "experiment_dir": str(next(iter(run_dirs))),
            "git_commit": os.popen(
                f"git -C {PROJECT_ROOT} rev-parse HEAD"
            ).read().strip(),
        }
    payload = {
        "schema_version": 1,
        "manifest_type": "existing_checkpoint_inventory_and_latest_selection",
        "condition_order": list(CONDITION_ORDER),
        "block": block,
        "retraining_performed": False,
        "checkpoints": checkpoints,
    }
    output = MANIFEST_ROOT / f"checkpoints_latest_existing_b{block}.json"
    write_json(output, payload)
    print(f"Froze existing latest-checkpoint inventory in {output}")


def parse_args():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("freeze-legacy").set_defaults(func=freeze_legacy)

    latents = subparsers.add_parser("make-latents")
    latents.add_argument("--block", type=int, choices=(0, 1), required=True)
    latents.add_argument("--num-candidates", type=int, default=160)
    latents.set_defaults(func=make_latents)

    collection = subparsers.add_parser("collect")
    collection.add_argument("--block", type=int, choices=(0, 1), required=True)
    collection.add_argument("--target", type=int, required=True)
    collection.add_argument("--smoke", action="store_true")
    collection.add_argument("--sample-hz", type=float, default=8.0)
    collection.add_argument("--playback-speed", type=float, default=100.0)
    collection.set_defaults(func=collect)

    validation = subparsers.add_parser("validate-raw")
    validation.add_argument("--block", type=int, choices=(0, 1), required=True)
    validation.add_argument("--target", type=int, required=True)
    validation.add_argument("--smoke", action="store_true")
    validation.set_defaults(func=validate_raw)

    hdf5 = subparsers.add_parser("create-hdf5")
    hdf5.add_argument("--block", type=int, choices=(0, 1), required=True)
    hdf5.set_defaults(func=create_hdf5)

    configs = subparsers.add_parser("create-train-configs")
    configs.add_argument("--block", type=int, choices=(0, 1), required=True)
    configs.set_defaults(func=create_train_configs)

    checkpoints = subparsers.add_parser("freeze-checkpoints")
    checkpoints.add_argument("--block", type=int, choices=(0, 1), required=True)
    checkpoints.set_defaults(func=freeze_checkpoints)

    latest = subparsers.add_parser("freeze-latest-existing-checkpoints")
    latest.add_argument("--block", type=int, choices=(0, 1), required=True)
    latest.set_defaults(func=freeze_latest_existing_checkpoints)

    split = subparsers.add_parser("apply-split")
    split.add_argument("--block", type=int, choices=(0, 1), required=True)
    split.set_defaults(func=apply_split)
    return parser.parse_args()


def main():
    args = parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
