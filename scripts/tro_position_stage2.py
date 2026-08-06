#!/usr/bin/env python3
"""Execution and strict artifact utilities for T-RO Stage 2 Position axial replication."""

import argparse
import hashlib
import json
import math
import os
import random
import re
import shutil
import sys
from pathlib import Path

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES_DIR = PROJECT_ROOT / "examples"
if str(EXAMPLES_DIR) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_DIR))

EXPERIMENT_ROOT = (
    PROJECT_ROOT / "experiments" / "tro_stage2_position_axial_replication"
)
MANIFEST_ROOT = EXPERIMENT_ROOT / "manifests"
LATENT_ROOT = MANIFEST_ROOT / "paired_latents"
ROLLOUT_MANIFEST_ROOT = MANIFEST_ROOT / "rollout_5seed"
CONFIG_ROOT = EXPERIMENT_ROOT / "configs" / "training"
DATA_ROOT = PROJECT_ROOT / "dataset" / "tro_position_stage2_axial"
MODEL_ROOT = Path(
    "/scratch/prj/eng_demt_robot_learning/trained_models/"
    "tro_position_stage2_axial"
)
SHARED_ROOT = PROJECT_ROOT / "experiments" / "shared_artifacts"

STAGE1_ROOT = PROJECT_ROOT / "experiments" / "mvp0_position_event"
STAGE1_DATASETS = STAGE1_ROOT / "manifests" / "datasets.json"
STAGE1_LATENTS = {
    4: STAGE1_ROOT / "manifests" / "paired_latents_b1.json",
    5: STAGE1_ROOT / "manifests" / "paired_latents_b0.json",
}
STAGE1_BLOCK = {4: "1", 5: "0"}
STAGE1B_CHECKPOINTS = (
    STAGE1_ROOT / "confirmation_earlystop" / "manifests" / "checkpoints.json"
)
STAGE1B_COMPARISON = (
    STAGE1_ROOT / "confirmation_earlystop" / "analysis" / "comparison.json"
)
STAGE1B_SUMMARY = (
    STAGE1_ROOT / "confirmation_earlystop" / "analysis" / "summary.md"
)
LEGACY_RAW = (
    PROJECT_ROOT
    / "dataset"
    / "ar_guidance_spatial_S15_S35"
    / "spatial_S25_d30_seed1"
)
LEGACY_HDF5 = (
    PROJECT_ROOT
    / "dataset"
    / "ar_guidance_spatial_S15_S35"
    / "spatial_S25_d30_seed1_2gap.hdf5"
)
LEGACY_CHECKPOINT = Path(
    "/scratch/prj/eng_demt_robot_learning/trained_models/"
    "ar_guidance_spatial_S15_S35/S25/spatial_S25_d30_seed1_2gap/"
    "20260704004132/models/model_epoch_80.pth"
)
TRAINING_TEMPLATE = (
    STAGE1_ROOT
    / "confirmation_earlystop"
    / "configs"
    / "training"
    / "START15_APP6.json"
)

CONDITIONS = {
    "START15_APP6": (0.15, 0.060),
    "START35_APP6": (0.35, 0.060),
    "START25_APP3P6": (0.25, 0.036),
    "START25_APP6": (0.25, 0.060),
    "START25_APP8P4": (0.25, 0.084),
}
CONDITION_ORDER = tuple(CONDITIONS)
CANONICAL_SEEDS = {
    1: {"collection": 1, "training": 1, "source": "new_plus_legacy_reference"},
    2: {"collection": 2, "training": 2, "source": "fully_new"},
    3: {"collection": 3, "training": 3, "source": "fully_new"},
    4: {"collection": 1702, "training": 2702, "source": "old_block1_alias"},
    5: {"collection": 1701, "training": 2701, "source": "stage1b_block0_alias"},
}
ROLLOUT_SEEDS = (1, 2, 3, 4, 5)
BANKS = ("inner", "outer")
NEW_DATASET_CONDITIONS = {
    1: tuple(c for c in CONDITION_ORDER if c != "START25_APP6"),
    2: CONDITION_ORDER,
    3: CONDITION_ORDER,
    4: ("START25_APP6",),
    5: ("START25_APP6",),
}
NEW_POLICY_CONDITIONS = {
    1: tuple(c for c in CONDITION_ORDER if c != "START25_APP6"),
    2: CONDITION_ORDER,
    3: CONDITION_ORDER,
    4: CONDITION_ORDER,
    5: ("START25_APP6",),
}
FROZEN_HASHES = {
    STAGE1B_COMPARISON: (
        "0c17c65330b8ab25867e75b1409553e1ad2dfbb33ad52789acc586d1f7a9d1d1"
    ),
    STAGE1B_SUMMARY: (
        "c285ea524ac8ef795b073f6f2e54925745ae2e0ddef4a7238192407b7b6c1d29"
    ),
    LEGACY_HDF5: (
        "2f2a3ed8c6b99e0dd83cdddd11d43a414bf38ed89b7128a63d30a7d7974877e5"
    ),
    LEGACY_CHECKPOINT: (
        "e666ab6a53f87f8d0f2e0a5ba29bd34b28cc39930d57cc848abfa5745465d60f"
    ),
}
CHECKPOINT_RE = re.compile(r"model_epoch_(\d+)\.pth$")
WANDB_PROJECT = "TRO_MVP"
_TREE_HASH_CACHE = {}
FALLBACK_REGISTRY = MANIFEST_ROOT / "fallback_activations.json"


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_frozen_json(path, payload):
    path = Path(path)
    if path.exists():
        existing = read_json(path)
        if existing != payload:
            raise FileExistsError(f"Refusing to replace different frozen artifact: {path}")
        return
    write_json(path, payload)


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tree_sha256(path):
    path = Path(path)
    cache_key = str(path.resolve())
    if cache_key in _TREE_HASH_CACHE:
        return _TREE_HASH_CACHE[cache_key]
    digest = hashlib.sha256()
    for child in sorted(p for p in path.rglob("*") if p.is_file()):
        digest.update(str(child.relative_to(path)).encode("utf-8"))
        digest.update(b"\0")
        with child.open("rb") as stream:
            for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
                digest.update(chunk)
        digest.update(b"\0")
    value = digest.hexdigest()
    _TREE_HASH_CACHE[cache_key] = value
    return value


def metadata_tree_sha256(path):
    path = Path(path)
    digest = hashlib.sha256()
    metadata_files = sorted(path.glob("demo_*/metadata.json"))
    if len(metadata_files) != 30:
        raise ValueError(f"Expected 30 metadata files under {path}")
    for child in metadata_files:
        digest.update(str(child.relative_to(path)).encode("utf-8"))
        digest.update(b"\0")
        digest.update(child.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def git_commit():
    return os.popen(f"git -C {PROJECT_ROOT} rev-parse HEAD").read().strip()


def checkpoint_epoch(path):
    match = CHECKPOINT_RE.fullmatch(Path(path).name)
    if match is None:
        raise ValueError(f"Cannot parse checkpoint epoch: {path}")
    return int(match.group(1))


def deterministic_runtime_seed(collection_seed, candidate_index):
    sequence = np.random.SeedSequence(
        [int(collection_seed), int(candidate_index), 0x535441474532]
    )
    return int(sequence.generate_state(1, dtype=np.uint32)[0])


def slot_plan():
    rows = []
    for canonical_seed in CANONICAL_SEEDS:
        settings = CANONICAL_SEEDS[canonical_seed]
        for condition in CONDITION_ORDER:
            rows.append(
                {
                    "canonical_seed": canonical_seed,
                    "condition": condition,
                    "source_collection_seed": settings["collection"],
                    "source_training_seed": settings["training"],
                    "reused_dataset": condition not in NEW_DATASET_CONDITIONS[canonical_seed],
                    "reused_policy": condition not in NEW_POLICY_CONDITIONS[canonical_seed],
                }
            )
    return rows


def source_stage1_dataset(canonical_seed, condition):
    manifest = read_json(STAGE1_DATASETS)
    block = STAGE1_BLOCK[canonical_seed]
    matches = [
        row
        for row in manifest["blocks"][block]["datasets"]
        if row["condition"] == condition
    ]
    if len(matches) != 1:
        raise ValueError(
            f"Expected one Stage 1 dataset for seed{canonical_seed}/{condition}"
        )
    return matches[0]


def source_stage1b_policy(condition):
    return read_json(STAGE1B_CHECKPOINTS)["checkpoints"][condition]


def verify_frozen_hashes():
    verified = {}
    for path, expected in FROZEN_HASHES.items():
        actual = sha256(path)
        if actual != expected:
            raise ValueError(f"Frozen hash mismatch for {path}: {actual} != {expected}")
        verified[str(path.resolve())] = actual
    return verified


def build_reuse_records(audit_hashes=True):
    datasets = []
    policies = []
    legacy_raw_hash = metadata_tree_sha256(LEGACY_RAW)
    datasets.append(
        {
            "canonical_seed": 1,
            "condition": "START25_APP6",
            "source_collection_seed": 1,
            "source_training_seed": 1,
            "reused_dataset": True,
            "reused_policy": True,
            "source_artifact_path": str(LEGACY_HDF5.resolve()),
            "source_artifact_sha256": FROZEN_HASHES[LEGACY_HDF5],
            "source_raw_path": str(LEGACY_RAW.resolve()),
            "source_raw_tree_sha256": legacy_raw_hash,
            "source_raw_hash_scope": "30 metadata.json files",
            "canonical_candidate_ids": list(range(30)),
        }
    )
    policies.append(
        {
            "canonical_seed": 1,
            "condition": "START25_APP6",
            "source_collection_seed": 1,
            "source_training_seed": 1,
            "reused_dataset": True,
            "reused_policy": True,
            "source_artifact_path": str(LEGACY_CHECKPOINT.resolve()),
            "source_artifact_sha256": FROZEN_HASHES[LEGACY_CHECKPOINT],
            "epoch": 80,
        }
    )
    for canonical_seed in (4, 5):
        for condition in CONDITION_ORDER:
            if condition == "START25_APP6":
                continue
            row = source_stage1_dataset(canonical_seed, condition)
            actual = sha256(row["hdf5_path"]) if audit_hashes else row["hdf5_sha256"]
            if actual != row["hdf5_sha256"]:
                raise ValueError(
                    f"Source HDF5 hash mismatch seed{canonical_seed}/{condition}"
                )
            actual_raw = (
                tree_sha256(row["raw_path"])
                if audit_hashes
                else row["raw_tree_sha256"]
            )
            if actual_raw != row["raw_tree_sha256"]:
                raise ValueError(
                    f"Source raw tree hash mismatch seed{canonical_seed}/{condition}"
                )
            datasets.append(
                {
                    "canonical_seed": canonical_seed,
                    "condition": condition,
                    "source_collection_seed": CANONICAL_SEEDS[canonical_seed][
                        "collection"
                    ],
                    "source_training_seed": CANONICAL_SEEDS[canonical_seed]["training"],
                    "reused_dataset": True,
                    "reused_policy": canonical_seed == 5,
                    "source_artifact_path": row["hdf5_path"],
                    "source_artifact_sha256": row["hdf5_sha256"],
                    "source_raw_path": row["raw_path"],
                    "source_raw_tree_sha256": row["raw_tree_sha256"],
                    "source_block": int(STAGE1_BLOCK[canonical_seed]),
                    "canonical_candidate_ids": row["canonical_candidate_ids"],
                }
            )
            if canonical_seed == 5:
                checkpoint = source_stage1b_policy(condition)
                actual_checkpoint = (
                    sha256(checkpoint["path"]) if audit_hashes else checkpoint["sha256"]
                )
                if actual_checkpoint != checkpoint["sha256"]:
                    raise ValueError(f"Stage 1b checkpoint hash mismatch: {condition}")
                policies.append(
                    {
                        "canonical_seed": 5,
                        "condition": condition,
                        "source_collection_seed": 1701,
                        "source_training_seed": 2701,
                        "reused_dataset": True,
                        "reused_policy": True,
                        "source_artifact_path": checkpoint["path"],
                        "source_artifact_sha256": checkpoint["sha256"],
                        "epoch": checkpoint["epoch"],
                    }
                )
    if len(datasets) != 9 or len(policies) != 5:
        raise AssertionError(
            f"Reuse audit counts changed: datasets={len(datasets)}, policies={len(policies)}"
        )
    return datasets, policies


def latent_record_from_offsets(index, metadata_path, metadata):
    start = np.asarray(metadata["corridor_start_delta"], dtype=float)
    approach = np.asarray(metadata["pre_grasp_delta"], dtype=float)
    if abs(start[1]) > 1e-10 or abs(approach[2]) > 1e-10:
        raise ValueError(f"Legacy seed1 planes changed in {metadata_path}")
    start_fraction = float(np.linalg.norm(start) / 0.25)
    approach_fraction = float(np.linalg.norm(approach) / 0.060)
    return {
        "candidate_index": index,
        "accepted_candidate_id": f"legacy_seed1_demo_{index:03d}",
        "start_angle": float(math.atan2(start[2], start[0]) % (2.0 * math.pi)),
        "start_radial_quantile": start_fraction * start_fraction,
        "approach_angle": float(
            math.atan2(approach[1], approach[0]) % (2.0 * math.pi)
        ),
        "approach_radial_quantile": approach_fraction * approach_fraction,
        "collection_seed": 1,
        "runtime_seed": deterministic_runtime_seed(1, index),
        "source_demo_index": index,
        "source_metadata_path": str(metadata_path.resolve()),
        "source_metadata_sha256": sha256(metadata_path),
        "source_exact_offsets": {
            "start_xz": start.tolist(),
            "approach_xy": approach.tolist(),
        },
        "runtime_seed_provenance": (
            "deterministic Stage 2 runtime alias; legacy raw metadata did not "
            "record the original simulator runtime RNG"
        ),
    }


def reconstruct_seed1_latents():
    demos = sorted(
        (p for p in LEGACY_RAW.glob("demo_*") if p.is_dir()),
        key=lambda p: int(p.name.split("_", 1)[1]),
    )
    if len(demos) != 30:
        raise ValueError(f"Expected 30 legacy seed1 demos, got {len(demos)}")
    records = []
    for index, demo in enumerate(demos):
        if int(demo.name.split("_", 1)[1]) != index:
            raise ValueError("Legacy seed1 demo indices are not exactly 0..29")
        metadata_path = demo / "metadata.json"
        metadata = read_json(metadata_path)
        if metadata["condition"] != "S25":
            raise ValueError(f"Unexpected legacy seed1 condition in {metadata_path}")
        if not math.isclose(float(metadata["sample_hz"]), 8.0):
            raise ValueError(f"Legacy seed1 sample rate changed in {metadata_path}")
        records.append(latent_record_from_offsets(index, metadata_path, metadata))
    return records


def source_accepted_latents(canonical_seed):
    source_manifest = read_json(STAGE1_LATENTS[canonical_seed])
    dataset_manifest = read_json(STAGE1_DATASETS)
    block = STAGE1_BLOCK[canonical_seed]
    accepted = dataset_manifest["blocks"][block]["accepted_candidate_indices"]
    by_id = {
        int(row["candidate_index"]): row for row in source_manifest["candidates"]
    }
    records = []
    for candidate_index in accepted:
        record = dict(by_id[int(candidate_index)])
        record["accepted_candidate_id"] = (
            f"source_seed{CANONICAL_SEEDS[canonical_seed]['collection']}_"
            f"candidate_{int(candidate_index):03d}"
        )
        records.append(record)
    if len(records) != 30:
        raise ValueError(f"seed{canonical_seed}: expected 30 accepted source latents")
    return records, accepted


def new_candidate_pool(canonical_seed, count=160):
    collection_seed = CANONICAL_SEEDS[canonical_seed]["collection"]
    rng = np.random.default_rng(collection_seed)
    records = []
    for candidate_index in range(count):
        records.append(
            {
                "candidate_index": candidate_index,
                "accepted_candidate_id": (
                    f"seed{canonical_seed}_candidate_{candidate_index:03d}"
                ),
                "start_angle": float(rng.uniform(0.0, 2.0 * math.pi)),
                "start_radial_quantile": float(rng.uniform(0.0, 1.0)),
                "approach_angle": float(rng.uniform(0.0, 2.0 * math.pi)),
                "approach_radial_quantile": float(rng.uniform(0.0, 1.0)),
                "collection_seed": collection_seed,
                "runtime_seed": int(rng.integers(0, 2**32, dtype=np.uint32)),
            }
        )
    return records


def fallback_activations():
    if not FALLBACK_REGISTRY.exists():
        return {}
    payload = read_json(FALLBACK_REGISTRY)
    return {
        int(row["canonical_seed"]): row for row in payload.get("activations", [])
    }


def is_fallback_active(canonical_seed):
    return int(canonical_seed) in fallback_activations()


def active_latent_path(canonical_seed):
    activation = fallback_activations().get(int(canonical_seed))
    if activation is not None:
        return Path(activation["latent_manifest_path"])
    return LATENT_ROOT / f"seed{canonical_seed}.json"


def active_new_dataset_conditions(canonical_seed):
    if is_fallback_active(canonical_seed):
        return CONDITION_ORDER
    return NEW_DATASET_CONDITIONS[int(canonical_seed)]


def active_new_policy_conditions(canonical_seed):
    if is_fallback_active(canonical_seed):
        return CONDITION_ORDER
    return NEW_POLICY_CONDITIONS[int(canonical_seed)]


def latent_payload(canonical_seed):
    settings = CANONICAL_SEEDS[canonical_seed]
    if canonical_seed == 1:
        candidates = reconstruct_seed1_latents()
        source_path = str(LEGACY_RAW.resolve())
        source_hash = metadata_tree_sha256(LEGACY_RAW)
        locked_ids = [row["candidate_index"] for row in candidates]
        locked = True
    elif canonical_seed in (4, 5):
        candidates, locked_ids = source_accepted_latents(canonical_seed)
        source_path = str(STAGE1_LATENTS[canonical_seed].resolve())
        source_hash = sha256(STAGE1_LATENTS[canonical_seed])
        locked = True
    else:
        candidates = new_candidate_pool(canonical_seed)
        source_path = None
        source_hash = None
        locked_ids = None
        locked = False
    return {
        "schema_version": 1,
        "manifest_type": "tro_stage2_five_condition_paired_latents",
        "canonical_seed": canonical_seed,
        "source_collection_seed": settings["collection"],
        "source_training_seed": settings["training"],
        "condition_order": list(CONDITION_ORDER),
        "formal_new_collection_conditions": list(
            NEW_DATASET_CONDITIONS[canonical_seed]
        ),
        "target_successful_demonstrations_per_condition": 30,
        "sampling": {
            "start_plane": "xz",
            "approach_plane": "xy",
            "radial_mapping": "realised_fraction = sqrt(radial_quantile)",
            "whole_slot_rejection_rule": (
                "if any condition fails, reject candidate for the whole five-condition slot"
            ),
        },
        "locked_to_existing_accepted_records": locked,
        "locked_accepted_candidate_ids": locked_ids,
        "source_artifact_path": source_path,
        "source_artifact_sha256": source_hash,
        "candidates": candidates,
    }


def create_latent_manifests():
    LATENT_ROOT.mkdir(parents=True, exist_ok=True)
    records = {}
    for canonical_seed in CANONICAL_SEEDS:
        path = LATENT_ROOT / f"seed{canonical_seed}.json"
        payload = latent_payload(canonical_seed)
        write_frozen_json(path, payload)
        records[str(canonical_seed)] = {
            "path": str(path.resolve()),
            "sha256": sha256(path),
            "candidate_count": len(payload["candidates"]),
            "locked": payload["locked_to_existing_accepted_records"],
        }
    return records


def planned_dataset_record(row, reuse_by_key):
    canonical_seed = row["canonical_seed"]
    condition = row["condition"]
    if row["reused_dataset"]:
        source = reuse_by_key[(canonical_seed, condition)]
        return {
            **row,
            "status": "reused_verified",
            "source_artifact_path": source["source_artifact_path"],
            "source_artifact_sha256": source["source_artifact_sha256"],
            "raw_path": source["source_raw_path"],
            "raw_tree_sha256": source["source_raw_tree_sha256"],
            "hdf5_path": source["source_artifact_path"],
            "hdf5_sha256": source["source_artifact_sha256"],
            "canonical_candidate_ids": source["canonical_candidate_ids"],
        }
    raw = DATA_ROOT / "formal" / f"seed{canonical_seed}" / "raw" / condition
    hdf5 = (
        DATA_ROOT
        / "formal"
        / f"seed{canonical_seed}"
        / "hdf5"
        / f"{condition}_seed{canonical_seed}_d30_2gap.hdf5"
    )
    return {
        **row,
        "status": "planned_new",
        "source_artifact_path": str(hdf5.resolve()),
        "source_artifact_sha256": None,
        "raw_path": str(raw.resolve()),
        "raw_tree_sha256": None,
        "hdf5_path": str(hdf5.resolve()),
        "hdf5_sha256": None,
    }


def planned_policy_record(row, reuse_by_key):
    canonical_seed = row["canonical_seed"]
    condition = row["condition"]
    if row["reused_policy"]:
        source = reuse_by_key[(canonical_seed, condition)]
        return {
            **row,
            "status": "reused_verified",
            "source_artifact_path": source["source_artifact_path"],
            "source_artifact_sha256": source["source_artifact_sha256"],
            "checkpoint_path": source["source_artifact_path"],
            "checkpoint_sha256": source["source_artifact_sha256"],
            "epoch": source["epoch"],
        }
    config = CONFIG_ROOT / f"seed{canonical_seed}" / f"{condition}.json"
    return {
        **row,
        "status": "planned_new",
        "source_artifact_path": str(config.resolve()),
        "source_artifact_sha256": None,
        "config_path": str(config.resolve()),
        "checkpoint_path": None,
        "checkpoint_sha256": None,
        "epoch": None,
    }


def freeze_protocol(args):
    verified = verify_frozen_hashes()
    datasets_reused, policies_reused = build_reuse_records(
        audit_hashes=not args.skip_large_rehash
    )
    latent_manifests = create_latent_manifests()
    rows = slot_plan()
    counts = {
        "total_slots": len(rows),
        "new_datasets": sum(not row["reused_dataset"] for row in rows),
        "reused_datasets": sum(row["reused_dataset"] for row in rows),
        "new_policies": sum(not row["reused_policy"] for row in rows),
        "reused_policies": sum(row["reused_policy"] for row in rows),
        "new_successful_demonstrations": (
            sum(not row["reused_dataset"] for row in rows) * 30
        ),
        "rollout_tasks": 250,
        "rollout_rows": 6250,
    }
    expected = {
        "total_slots": 25,
        "new_datasets": 16,
        "reused_datasets": 9,
        "new_policies": 20,
        "reused_policies": 5,
        "new_successful_demonstrations": 480,
        "rollout_tasks": 250,
        "rollout_rows": 6250,
    }
    if counts != expected:
        raise AssertionError(f"Stage 2 matrix changed: {counts} != {expected}")
    protocol = {
        "schema_version": 1,
        "experiment": "tro_stage2_position_axial_replication",
        "authority": str((EXPERIMENT_ROOT / "PLAN.md").resolve()),
        "git_commit_at_freeze": git_commit(),
        "condition_order": list(CONDITION_ORDER),
        "conditions": {
            condition: {
                "start_radius_m": radii[0],
                "approach_radius_m": radii[1],
                "role": "reference" if condition == "START25_APP6" else "axial",
            }
            for condition, radii in CONDITIONS.items()
        },
        "canonical_seed_mapping": {
            str(seed): {
                "canonical_seed": seed,
                "source_collection_seed": row["collection"],
                "source_training_seed": row["training"],
                "source": row["source"],
            }
            for seed, row in CANONICAL_SEEDS.items()
        },
        "slot_matrix": rows,
        "expected_counts": counts,
        "task": {
            "trajectory": ["Start", "Approach", "Descent", "Grasp", "Lift"],
            "base_corridor_start": [0.30, 0.0, 0.50],
            "start_plane": "xz",
            "approach_plane": "xy",
            "sample_hz": 8,
            "action_gap": 2,
            "successful_demonstrations_per_dataset": 30,
            "success": "final cube z >= 0.20 m",
        },
        "training": {
            "from_scratch": True,
            "max_epochs": 3000,
            "validation_early_stopping_patience": 41,
            "checkpoint_interval_epochs": 20,
            "checkpoint_selection": "highest numeric emitted model_epoch_*.pth",
            "rollout_based_checkpoint_selection": False,
            "wandb_project": WANDB_PROJECT,
        },
        "formal_rollout": {
            "seeds": list(ROLLOUT_SEEDS),
            "banks": {
                "inner": {"count": 25, "range_m": "[0.00, 0.25]"},
                "outer": {"count": 25, "range_m": "(0.25, 0.35]"},
            },
            "horizon": 200,
            "sample_hz": 8,
            "action_gap": 2,
            "action_dt": 0.25,
            "num_points": 10000,
            "terminate_on_success": True,
            "videos": False,
        },
        "analysis": {
            "independent_unit": "dataset-policy slot",
            "delta_min": 0.05,
            "positive_slots_required": 4,
            "classification": ["strong", "partial", "null/unstable"],
        },
        "frozen_hashes": verified,
        "paired_latent_manifests": latent_manifests,
    }
    reuse = {
        "schema_version": 1,
        "status": "verified",
        "expected_reused_dataset_slots": 9,
        "expected_reused_policy_slots": 5,
        "datasets": datasets_reused,
        "policies": policies_reused,
    }
    write_json(MANIFEST_ROOT / "protocol.json", protocol)
    write_json(MANIFEST_ROOT / "artifact_reuse.json", reuse)
    dataset_by_key = {
        (row["canonical_seed"], row["condition"]): row
        for row in datasets_reused
    }
    policy_by_key = {
        (row["canonical_seed"], row["condition"]): row for row in policies_reused
    }
    write_json(
        MANIFEST_ROOT / "datasets.json",
        {
            "schema_version": 1,
            "counts": {
                "total": 25,
                "new": 16,
                "reused": 9,
            },
            "datasets": [
                planned_dataset_record(row, dataset_by_key) for row in rows
            ],
        },
    )
    write_json(
        MANIFEST_ROOT / "policies.json",
        {
            "schema_version": 1,
            "counts": {
                "total": 25,
                "new": 20,
                "reused": 5,
            },
            "policies": [
                planned_policy_record(row, policy_by_key) for row in rows
            ],
        },
    )
    print(json.dumps({"status": "verified", "counts": counts}, indent=2))


def generate_rollout_manifests(_args):
    from eval_abla1_trained_policies import (
        generate_shared_corridor_starts,
        write_start_manifest,
    )

    registry_records = []
    for seed in ROLLOUT_SEEDS:
        for bank in BANKS:
            bank_id = f"tro_stage2_seed{seed}_{bank}_n25_v1"
            radius_min, radius_max = (
                (0.0, 0.25) if bank == "inner" else (0.25, 0.35)
            )
            output = ROLLOUT_MANIFEST_ROOT / f"{bank_id}.json"
            namespace = argparse.Namespace(
                experiment_profile="tro_position_stage2",
                conditions=list(CONDITION_ORDER),
                seed=seed,
                num_rollouts=25,
                horizon=200,
                sample_hz=8.0,
                action_gap=2,
                action_dt=0.25,
                terminate_on_success=True,
                success_lift_height=0.20,
                num_points=10000,
                corridor_start_center=(0.30, 0.0, 0.50),
                shared_start_radius_min=radius_min,
                shared_start_radius=radius_max,
                corridor_start_max_error=0.025,
                bank_id=bank_id,
                max_start_sample_attempts=1000,
                gui=False,
                playback_speed=100.0,
            )
            if output.exists():
                manifest = read_json(output)
                if manifest["condition_order"] != list(CONDITION_ORDER):
                    raise ValueError(f"Existing rollout manifest changed: {output}")
            else:
                starts, records = generate_shared_corridor_starts(namespace)
                write_start_manifest(namespace, output, starts, records)
            registry_records.append(
                {
                    "artifact_id": bank_id,
                    "experiment": "tro_stage2_position_axial_replication",
                    "path": str(output.resolve()),
                    "sha256": sha256(output),
                    "rollout_seed": seed,
                    "bank": bank,
                    "num_states": 25,
                    "protocol_sha256": sha256(MANIFEST_ROOT / "protocol.json"),
                }
            )
    registry_path = SHARED_ROOT / "rollout_manifest_registry.json"
    registry = (
        read_json(registry_path)
        if registry_path.exists()
        else {"schema_version": 1, "artifacts": []}
    )
    existing = {
        row["artifact_id"]: row for row in registry.get("artifacts", [])
    }
    for row in registry_records:
        old = existing.get(row["artifact_id"])
        if old is not None and old != row:
            raise ValueError(
                f"Shared rollout registry conflict for {row['artifact_id']}"
            )
        existing[row["artifact_id"]] = row
    registry["artifacts"] = [
        existing[key] for key in sorted(existing)
    ]
    write_json(registry_path, registry)
    print(f"Frozen and registered {len(registry_records)} rollout manifests")


def activate_fallback(args):
    canonical_seed = int(args.canonical_seed)
    if canonical_seed not in (1, 4, 5):
        raise ValueError("Whole-slot source fallback applies only to locked seeds 1/4/5")
    existing = fallback_activations()
    if canonical_seed in existing:
        print(f"seed{canonical_seed} whole-slot fallback already active")
        return
    evidence_candidates = [
        collection_root(canonical_seed, smoke=True, ignore_fallback=True)
        / "collection_progress.json",
        collection_root(canonical_seed, smoke=False, ignore_fallback=True)
        / "collection_progress.json",
    ]
    evidence_path = next(
        (
            path
            for path in evidence_candidates
            if path.exists() and read_json(path).get("fallback_required") is True
        ),
        None,
    )
    if evidence_path is None:
        raise ValueError(
            f"seed{canonical_seed}: no persistent scientific failure evidence"
        )
    evidence = read_json(evidence_path)
    settings = CANONICAL_SEEDS[canonical_seed]
    payload = {
        "schema_version": 1,
        "manifest_type": "tro_stage2_whole_slot_scientific_fallback_latents",
        "canonical_seed": canonical_seed,
        "source_collection_seed": settings["collection"],
        "source_training_seed": settings["training"],
        "condition_order": list(CONDITION_ORDER),
        "formal_new_collection_conditions": list(CONDITION_ORDER),
        "target_successful_demonstrations_per_condition": 30,
        "sampling": {
            "start_plane": "xz",
            "approach_plane": "xy",
            "radial_mapping": "realised_fraction = sqrt(radial_quantile)",
            "whole_slot_rejection_rule": (
                "if any condition fails, reject candidate for the full "
                "five-condition fallback slot"
            ),
        },
        "locked_to_existing_accepted_records": False,
        "locked_accepted_candidate_ids": None,
        "fallback_from_latent_manifest": str(
            (LATENT_ROOT / f"seed{canonical_seed}.json").resolve()
        ),
        "fallback_from_latent_manifest_sha256": sha256(
            LATENT_ROOT / f"seed{canonical_seed}.json"
        ),
        "persistent_failure_evidence_path": str(evidence_path.resolve()),
        "persistent_failure_evidence_sha256": sha256(evidence_path),
        "persistent_failure": evidence["fallback_reason"],
        "candidates": new_candidate_pool(canonical_seed),
    }
    latent_path = (
        LATENT_ROOT / f"seed{canonical_seed}_fallback_whole_slot.json"
    )
    write_frozen_json(latent_path, payload)
    activation = {
        "canonical_seed": canonical_seed,
        "source_collection_seed": settings["collection"],
        "source_training_seed": settings["training"],
        "reason": "persistent scientific failure in exact reused-slot pairing",
        "evidence_path": str(evidence_path.resolve()),
        "evidence_sha256": sha256(evidence_path),
        "latent_manifest_path": str(latent_path.resolve()),
        "latent_manifest_sha256": sha256(latent_path),
        "all_five_conditions_rebuilt": True,
    }
    existing[canonical_seed] = activation
    write_json(
        FALLBACK_REGISTRY,
        {
            "schema_version": 1,
            "protocol_rule": (
                "persistent reused-slot scientific failure rebuilds the full "
                "five-condition canonical slot"
            ),
            "activations": [existing[key] for key in sorted(existing)],
        },
    )

    datasets = read_json(MANIFEST_ROOT / "datasets.json")
    dataset_rows = []
    for row in datasets["datasets"]:
        if int(row["canonical_seed"]) != canonical_seed:
            dataset_rows.append(row)
            continue
        condition = row["condition"]
        raw = (
            DATA_ROOT
            / "formal_fallback"
            / f"seed{canonical_seed}"
            / "raw"
            / condition
        )
        hdf5 = (
            DATA_ROOT
            / "formal_fallback"
            / f"seed{canonical_seed}"
            / "hdf5"
            / f"{condition}_seed{canonical_seed}_d30_2gap.hdf5"
        )
        dataset_rows.append(
            {
                **row,
                "reused_dataset": False,
                "reused_policy": False,
                "status": "planned_new_whole_slot_fallback",
                "source_artifact_path": str(hdf5.resolve()),
                "source_artifact_sha256": None,
                "raw_path": str(raw.resolve()),
                "raw_tree_sha256": None,
                "hdf5_path": str(hdf5.resolve()),
                "hdf5_sha256": None,
                "canonical_candidate_ids": None,
                "fallback_activation_path": str(FALLBACK_REGISTRY.resolve()),
                "fallback_activation_sha256": sha256(FALLBACK_REGISTRY),
            }
        )
    datasets["datasets"] = dataset_rows
    datasets["counts"] = {
        "total": 25,
        "new": sum(not row["reused_dataset"] for row in dataset_rows),
        "reused": sum(row["reused_dataset"] for row in dataset_rows),
    }
    write_json(MANIFEST_ROOT / "datasets.json", datasets)

    policies = read_json(MANIFEST_ROOT / "policies.json")
    policy_rows = []
    for row in policies["policies"]:
        if int(row["canonical_seed"]) != canonical_seed:
            policy_rows.append(row)
            continue
        condition = row["condition"]
        config = CONFIG_ROOT / f"seed{canonical_seed}" / f"{condition}.json"
        policy_rows.append(
            {
                **row,
                "reused_dataset": False,
                "reused_policy": False,
                "status": "planned_new_whole_slot_fallback",
                "source_artifact_path": str(config.resolve()),
                "source_artifact_sha256": None,
                "config_path": str(config.resolve()),
                "checkpoint_path": None,
                "checkpoint_sha256": None,
                "epoch": None,
                "fallback_activation_path": str(FALLBACK_REGISTRY.resolve()),
                "fallback_activation_sha256": sha256(FALLBACK_REGISTRY),
            }
        )
    policies["policies"] = policy_rows
    policies["counts"] = {
        "total": 25,
        "new": sum(not row["reused_policy"] for row in policy_rows),
        "reused": sum(row["reused_policy"] for row in policy_rows),
    }
    write_json(MANIFEST_ROOT / "policies.json", policies)

    reuse = read_json(MANIFEST_ROOT / "artifact_reuse.json")
    for kind in ("datasets", "policies"):
        for row in reuse[kind]:
            if int(row["canonical_seed"]) == canonical_seed:
                row["active_in_primary"] = False
                row["inactive_reason"] = (
                    "whole-slot fallback after persistent scientific failure"
                )
    reuse.setdefault("fallback_activations", []).append(activation)
    write_json(MANIFEST_ROOT / "artifact_reuse.json", reuse)
    print(
        json.dumps(
            {
                "activated": activation,
                "dataset_counts": datasets["counts"],
                "policy_counts": policies["counts"],
            },
            indent=2,
        )
    )


def run_candidate(condition, latent, output_dir, sample_hz, playback_speed):
    from main_abla_1 import PandaSim

    start_radius, approach_radius = CONDITIONS[condition]
    random.seed(int(latent["runtime_seed"]))
    np.random.seed(int(latent["runtime_seed"]))
    sim = PandaSim(
        gui=False,
        output_dir=output_dir,
        sample_hz=sample_hz,
    )
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
            experiment_track_override="tro_position_stage2_axial",
        )
        return bool(success), details
    finally:
        sim.close()


def collection_root(canonical_seed, smoke, ignore_fallback=False):
    fallback = is_fallback_active(canonical_seed) and not ignore_fallback
    namespace = (
        "smoke_fallback"
        if smoke and fallback
        else (
            "formal_fallback"
            if fallback
            else ("smoke" if smoke else "formal")
        )
    )
    return DATA_ROOT / namespace / f"seed{canonical_seed}"


def collect(args):
    canonical_seed = int(args.canonical_seed)
    target = int(args.target)
    manifest_path = active_latent_path(canonical_seed)
    manifest = read_json(manifest_path)
    run_root = collection_root(canonical_seed, args.smoke)
    raw_root = run_root / "raw"
    staging_root = run_root / ".paired_staging"
    progress_path = run_root / "collection_progress.json"
    conditions = tuple(active_new_dataset_conditions(canonical_seed))
    progress = (
        read_json(progress_path)
        if progress_path.exists()
        else {
            "schema_version": 1,
            "canonical_seed": canonical_seed,
            "source_collection_seed": CANONICAL_SEEDS[canonical_seed][
                "collection"
            ],
            "source_training_seed": CANONICAL_SEEDS[canonical_seed]["training"],
            "target": target,
            "smoke": bool(args.smoke),
            "condition_order": list(CONDITION_ORDER),
            "execution_conditions": list(conditions),
            "latent_manifest": str(manifest_path.resolve()),
            "latent_manifest_sha256": sha256(manifest_path),
            "accepted_candidate_indices": [],
            "rejected_candidates": [],
            "infrastructure_retries": [],
            "fallback_required": False,
        }
    )
    if (
        int(progress["canonical_seed"]) != canonical_seed
        or int(progress["target"]) != target
        or bool(progress["smoke"]) != bool(args.smoke)
    ):
        raise ValueError(f"Collection resume invariant changed: {progress_path}")
    accepted = list(progress["accepted_candidate_indices"])
    for condition in conditions:
        condition_root = raw_root / condition
        existing = list(condition_root.glob("demo_*")) if condition_root.exists() else []
        if len(existing) != len(accepted):
            raise RuntimeError(
                f"seed{canonical_seed}/{condition}: {len(existing)} demos != "
                f"{len(accepted)} accepted candidates"
            )
    if len(accepted) >= target:
        print(f"seed{canonical_seed} already complete: {len(accepted)}/{target}")
        return
    decided = set(accepted) | {
        int(row["candidate_index"]) for row in progress["rejected_candidates"]
    }
    locked = bool(manifest["locked_to_existing_accepted_records"])
    for latent in manifest["candidates"]:
        candidate_index = int(latent["candidate_index"])
        if candidate_index in decided:
            continue
        staging = staging_root / f"candidate_{candidate_index:04d}"
        if staging.exists():
            shutil.rmtree(staging)
        results = {}
        all_success = True
        for condition in conditions:
            success = False
            details = None
            for scientific_attempt in range(2 if locked else 1):
                attempt_root = staging / condition / f"attempt_{scientific_attempt}"
                success, details = run_candidate(
                    condition,
                    latent,
                    attempt_root,
                    sample_hz=float(args.sample_hz),
                    playback_speed=float(args.playback_speed),
                )
                if success:
                    source = (
                        attempt_root
                        / f"demo_{candidate_index}"
                    )
                    destination = staging / condition / "accepted"
                    if destination.exists():
                        shutil.rmtree(destination)
                    source.rename(destination)
                    for sibling in (staging / condition).glob("attempt_*"):
                        if sibling.exists():
                            shutil.rmtree(sibling)
                    break
                if attempt_root.exists():
                    shutil.rmtree(attempt_root)
            results[condition] = {"success": success, "details": details}
            if not success:
                all_success = False
                break
        if not all_success:
            failure = {
                "candidate_index": candidate_index,
                "accepted_candidate_id": latent["accepted_candidate_id"],
                "condition_results": results,
                "reason": "persistent_scientific_failure",
            }
            progress["rejected_candidates"].append(failure)
            if staging.exists():
                shutil.rmtree(staging)
            if locked:
                progress["fallback_required"] = True
                progress["fallback_reason"] = failure
                write_json(progress_path, progress)
                raise RuntimeError(
                    f"seed{canonical_seed} locked source latent {candidate_index} "
                    "failed persistently; whole-slot fallback is required"
                )
            write_json(progress_path, progress)
            print(
                f"seed{canonical_seed}: rejected whole-slot candidate {candidate_index}",
                flush=True,
            )
            continue
        demo_index = len(accepted)
        for condition in conditions:
            source = staging / condition / "accepted"
            destination_root = raw_root / condition
            destination_root.mkdir(parents=True, exist_ok=True)
            destination = destination_root / f"demo_{demo_index}"
            if destination.exists():
                raise FileExistsError(f"Refusing to overwrite {destination}")
            source.rename(destination)
        if staging.exists():
            shutil.rmtree(staging)
        accepted.append(candidate_index)
        progress["accepted_candidate_indices"] = accepted
        write_json(progress_path, progress)
        print(
            f"seed{canonical_seed}: accepted candidate {candidate_index} "
            f"({len(accepted)}/{target})",
            flush=True,
        )
        if len(accepted) == target:
            break
    if len(accepted) != target:
        raise RuntimeError(
            f"seed{canonical_seed}: exhausted frozen candidate pool at "
            f"{len(accepted)}/{target}"
        )


def validate_raw(args):
    from check_abla1_dataset import check_demo
    from main_abla_1 import disk_offset

    canonical_seed = int(args.canonical_seed)
    target = int(args.target)
    run_root = collection_root(canonical_seed, args.smoke)
    raw_root = run_root / "raw"
    progress = read_json(run_root / "collection_progress.json")
    accepted = list(progress["accepted_candidate_indices"])
    manifest = read_json(active_latent_path(canonical_seed))
    candidates = {
        int(row["candidate_index"]): row for row in manifest["candidates"]
    }
    if len(accepted) != target:
        raise ValueError(f"seed{canonical_seed}: expected {target}, got {len(accepted)}")
    if manifest["locked_to_existing_accepted_records"]:
        expected = list(manifest["locked_accepted_candidate_ids"])[:target]
        if accepted != expected:
            raise ValueError(
                f"seed{canonical_seed}: locked accepted IDs changed: {accepted}"
            )
    errors = []
    dataset_records = []
    latent_by_demo = {}
    for condition in active_new_dataset_conditions(canonical_seed):
        condition_root = raw_root / condition
        demos = sorted(
            condition_root.glob("demo_*"),
            key=lambda p: int(p.name.split("_", 1)[1]),
        )
        if len(demos) != target:
            errors.append(
                f"seed{canonical_seed}/{condition}: expected {target}, got {len(demos)}"
            )
        condition_ids = []
        for demo_index, demo in enumerate(demos):
            _, demo_errors, _ = check_demo(demo, expected_condition=condition)
            errors.extend(str(error) for error in demo_errors)
            metadata = read_json(demo / "metadata.json")
            if metadata.get("experiment_track") != "tro_position_stage2_axial":
                errors.append(f"{demo}: wrong experiment_track")
            if not math.isclose(float(metadata.get("sample_hz", -1)), 8.0):
                errors.append(f"{demo}: sample_hz must be 8")
            latent = metadata["paired_latent"]
            candidate_index = int(latent["candidate_index"])
            condition_ids.append(candidate_index)
            expected_latent = candidates[candidate_index]
            if latent != expected_latent:
                errors.append(f"{demo}: latent differs from frozen manifest")
            latent_by_demo.setdefault(demo_index, []).append(latent)
            start_radius, approach_radius = CONDITIONS[condition]
            expected_start = disk_offset(
                latent["start_angle"],
                latent["start_radial_quantile"],
                start_radius,
                "xz",
            )
            expected_approach = disk_offset(
                latent["approach_angle"],
                latent["approach_radial_quantile"],
                approach_radius,
                "xy",
            )
            if not np.allclose(
                metadata["corridor_start_delta"], expected_start, atol=1e-10
            ):
                errors.append(f"{demo}: Start offset mismatch")
            if not np.allclose(
                metadata["pre_grasp_delta"], expected_approach, atol=1e-10
            ):
                errors.append(f"{demo}: Approach offset mismatch")
        if condition_ids != accepted:
            errors.append(f"seed{canonical_seed}/{condition}: candidate IDs changed")
        dataset_records.append(
            {
                "canonical_seed": canonical_seed,
                "condition": condition,
                "source_collection_seed": CANONICAL_SEEDS[canonical_seed][
                    "collection"
                ],
                "source_training_seed": CANONICAL_SEEDS[canonical_seed]["training"],
                "reused_dataset": False,
                "reused_policy": condition not in active_new_policy_conditions(
                    canonical_seed
                ),
                "source_artifact_path": str(condition_root.resolve()),
                "source_artifact_sha256": tree_sha256(condition_root),
                "raw_path": str(condition_root.resolve()),
                "raw_tree_sha256": tree_sha256(condition_root),
                "num_successful_demonstrations": len(demos),
                "canonical_candidate_ids": condition_ids,
                "radii": {
                    "start": CONDITIONS[condition][0],
                    "approach": CONDITIONS[condition][1],
                },
            }
        )
    for demo_index, latents in latent_by_demo.items():
        if any(latent != latents[0] for latent in latents[1:]):
            errors.append(
                f"seed{canonical_seed}/demo{demo_index}: normalized latent mismatch"
            )
    if errors:
        raise ValueError("Raw validation failed:\n" + "\n".join(errors))
    report = {
        "schema_version": 1,
        "status": "valid",
        "canonical_seed": canonical_seed,
        "source_collection_seed": CANONICAL_SEEDS[canonical_seed]["collection"],
        "source_training_seed": CANONICAL_SEEDS[canonical_seed]["training"],
        "smoke": bool(args.smoke),
        "condition_order": list(CONDITION_ORDER),
        "execution_conditions": list(active_new_dataset_conditions(canonical_seed)),
        "accepted_candidate_indices": accepted,
        "rejected_candidates": progress["rejected_candidates"],
        "datasets": dataset_records,
    }
    write_json(run_root / "raw_validation.json", report)
    if not args.smoke:
        update_formal_dataset_manifest(report)
    print(
        f"Validated seed{canonical_seed}: "
        f"{len(active_new_dataset_conditions(canonical_seed)) * target} demonstrations"
    )


def update_formal_dataset_manifest(report):
    manifest_path = MANIFEST_ROOT / "datasets.json"
    manifest = read_json(manifest_path)
    by_key = {
        (row["canonical_seed"], row["condition"]): row
        for row in manifest["datasets"]
    }
    for record in report["datasets"]:
        key = (record["canonical_seed"], record["condition"])
        existing = by_key[key]
        existing.update(record)
        existing["status"] = "raw_validated"
    manifest["datasets"] = [
        by_key[(seed, condition)]
        for seed in CANONICAL_SEEDS
        for condition in CONDITION_ORDER
    ]
    write_json(manifest_path, manifest)


def apply_legacy_split(path):
    import h5py

    with h5py.File(LEGACY_HDF5, "r") as source:
        train = [
            value.decode() if isinstance(value, bytes) else str(value)
            for value in source["mask/train"][:]
        ]
        valid = [
            value.decode() if isinstance(value, bytes) else str(value)
            for value in source["mask/valid"][:]
        ]
    if len(train) != 54 or len(valid) != 6:
        raise ValueError("Legacy train/valid mask is not exactly 54/6")
    with h5py.File(path, "r+") as hdf5:
        if set(hdf5["data"]) != set(train) | set(valid):
            raise ValueError(f"{path}: episode names differ from legacy 54/6 mask")
        mask = hdf5.require_group("mask")
        for key in ("train", "valid"):
            if key in mask:
                del mask[key]
        dtype = h5py.string_dtype(encoding="utf-8")
        mask.create_dataset("train", data=np.asarray(train, dtype=object), dtype=dtype)
        mask.create_dataset("valid", data=np.asarray(valid, dtype=object), dtype=dtype)
        hdf5.attrs["tro_stage2_sample_hz"] = 8.0
        hdf5.attrs["tro_stage2_action_gap"] = 2
        hdf5.attrs["tro_stage2_augmentation"] = "two_episodes_per_demo"
        hdf5.attrs["tro_stage2_split"] = "exact_legacy_S25_54_train_6_valid"


def create_hdf5(args):
    canonical_seed = int(args.canonical_seed)
    arcap_step1 = Path("/users/k23114984/code/arcap_policy/STEP1_build_dataset")
    if str(arcap_step1) not in sys.path:
        sys.path.insert(0, str(arcap_step1))
    from dataset_utils import process_hdf5_arcap_multi

    seed_root = collection_root(canonical_seed, smoke=False)
    output_root = seed_root / "hdf5"
    output_root.mkdir(parents=True, exist_ok=True)
    for condition in active_new_dataset_conditions(canonical_seed):
        raw = seed_root / "raw" / condition
        output = output_root / f"{condition}_seed{canonical_seed}_d30_2gap.hdf5"
        if output.exists():
            raise FileExistsError(f"Refusing to overwrite HDF5: {output}")
        process_hdf5_arcap_multi(
            output_hdf5_file=str(output),
            dataset_folders=[str(raw)],
            action_gap=2,
            num_points_to_sample=10000,
            hand_ahead=0,
            last_mean=1,
            visualize=False,
        )
        apply_legacy_split(output)
        print(f"Wrote {output}", flush=True)
    validate_hdf5_seed(canonical_seed)


def validate_hdf5_seed(canonical_seed):
    import h5py

    manifest_path = MANIFEST_ROOT / "datasets.json"
    manifest = read_json(manifest_path)
    by_key = {
        (row["canonical_seed"], row["condition"]): row
        for row in manifest["datasets"]
    }
    for condition in active_new_dataset_conditions(canonical_seed):
        path = (
            collection_root(canonical_seed, smoke=False)
            / "hdf5"
            / f"{condition}_seed{canonical_seed}_d30_2gap.hdf5"
        )
        with h5py.File(path, "r") as hdf5:
            if len(hdf5["data"]) != 60:
                raise ValueError(f"{path}: expected 60 augmented episodes")
            if len(hdf5["mask/train"]) != 54 or len(hdf5["mask/valid"]) != 6:
                raise ValueError(f"{path}: expected exact 54/6 split")
            if float(hdf5.attrs["tro_stage2_sample_hz"]) != 8.0:
                raise ValueError(f"{path}: sample rate metadata changed")
            if int(hdf5.attrs["tro_stage2_action_gap"]) != 2:
                raise ValueError(f"{path}: action gap metadata changed")
        row = by_key[(canonical_seed, condition)]
        row.update(
            {
                "status": "hdf5_validated",
                "hdf5_path": str(path.resolve()),
                "hdf5_sha256": sha256(path),
                "hdf5_size_bytes": path.stat().st_size,
                "source_artifact_path": str(path.resolve()),
                "source_artifact_sha256": sha256(path),
                "episodes": 60,
                "train_mask_count": 54,
                "valid_mask_count": 6,
                "sample_hz": 8,
                "action_gap": 2,
            }
        )
    manifest["datasets"] = [
        by_key[(seed, condition)]
        for seed in CANONICAL_SEEDS
        for condition in CONDITION_ORDER
    ]
    write_json(manifest_path, manifest)
    print(f"Validated Stage 2 HDF5 for canonical seed {canonical_seed}")


def dataset_for_slot(canonical_seed, condition):
    manifest = read_json(MANIFEST_ROOT / "datasets.json")
    matches = [
        row
        for row in manifest["datasets"]
        if int(row["canonical_seed"]) == canonical_seed
        and row["condition"] == condition
    ]
    if len(matches) != 1:
        raise ValueError(f"Missing dataset slot seed{canonical_seed}/{condition}")
    path = Path(matches[0]["hdf5_path"])
    if not path.is_file() or not matches[0]["hdf5_sha256"]:
        raise ValueError(f"Dataset slot not HDF5-frozen: seed{canonical_seed}/{condition}")
    if sha256(path) != matches[0]["hdf5_sha256"]:
        raise ValueError(f"Dataset hash mismatch: seed{canonical_seed}/{condition}")
    return matches[0]


def create_train_configs(_args):
    template = read_json(TRAINING_TEMPLATE)
    policies = read_json(MANIFEST_ROOT / "policies.json")
    policy_by_key = {
        (row["canonical_seed"], row["condition"]): row
        for row in policies["policies"]
    }
    created = 0
    for canonical_seed in CANONICAL_SEEDS:
        conditions = active_new_policy_conditions(canonical_seed)
        source_training_seed = CANONICAL_SEEDS[canonical_seed]["training"]
        for condition in conditions:
            dataset = dataset_for_slot(canonical_seed, condition)
            config = json.loads(json.dumps(template))
            run_name = (
                f"stage2_seed{canonical_seed}_source{source_training_seed}_"
                f"{condition}"
            )
            output = CONFIG_ROOT / f"seed{canonical_seed}" / f"{condition}.json"
            config["experiment"]["name"] = run_name
            config["experiment"]["logging"]["log_wandb"] = True
            config["experiment"]["logging"]["wandb_proj_name"] = WANDB_PROJECT
            config["experiment"]["save"]["enabled"] = True
            config["experiment"]["save"]["every_n_epochs"] = 20
            config["experiment"]["save"]["epochs"] = []
            config["experiment"]["save"]["on_best_validation"] = False
            config["experiment"]["save"]["on_best_rollout_return"] = False
            config["experiment"]["save"]["on_best_rollout_success_rate"] = False
            config["experiment"]["rollout"]["enabled"] = False
            config["train"]["data"][0]["path"] = dataset["hdf5_path"]
            config["train"]["output_dir"] = str(
                (MODEL_ROOT / f"seed{canonical_seed}" / condition).resolve()
            )
            config["train"]["num_epochs"] = 3000
            config["train"]["seed"] = source_training_seed
            write_json(output, config)
            record = policy_by_key[(canonical_seed, condition)]
            record.update(
                {
                    "status": "config_frozen",
                    "config_path": str(output.resolve()),
                    "config_sha256": sha256(output),
                    "source_artifact_path": str(output.resolve()),
                    "source_artifact_sha256": sha256(output),
                    "dataset_path": dataset["hdf5_path"],
                    "dataset_sha256": dataset["hdf5_sha256"],
                    "run_name": run_name,
                    "wandb_project": WANDB_PROJECT,
                }
            )
            created += 1
    expected_created = sum(
        len(active_new_policy_conditions(seed)) for seed in CANONICAL_SEEDS
    )
    if created != expected_created:
        raise AssertionError(
            f"Expected {expected_created} configs, created {created}"
        )
    policies["policies"] = [
        policy_by_key[(seed, condition)]
        for seed in CANONICAL_SEEDS
        for condition in CONDITION_ORDER
    ]
    write_json(MANIFEST_ROOT / "policies.json", policies)
    print(f"Created and froze exactly {created} Stage 2 training configs")


def find_single_run(canonical_seed, condition, run_name):
    root = MODEL_ROOT / f"seed{canonical_seed}" / condition / run_name
    run_dirs = sorted(p for p in root.glob("*") if p.is_dir())
    bearing = [
        p for p in run_dirs if list((p / "models").glob("model_epoch_*.pth"))
    ]
    if len(bearing) != 1:
        raise ValueError(
            f"seed{canonical_seed}/{condition}: expected one checkpoint-bearing "
            f"run, got {[str(p) for p in bearing]}"
        )
    return bearing[0]


def freeze_checkpoints(_args):
    policies = read_json(MANIFEST_ROOT / "policies.json")
    rows = {
        (row["canonical_seed"], row["condition"]): row
        for row in policies["policies"]
    }
    checkpoint_rows = []
    for canonical_seed in CANONICAL_SEEDS:
        for condition in CONDITION_ORDER:
            policy = rows[(canonical_seed, condition)]
            if policy["reused_policy"]:
                checkpoint_rows.append(
                    {
                        **policy,
                        "selection_rule": (
                            "reused pre-frozen accepted checkpoint; no retraining"
                        ),
                    }
                )
                continue
            run_dir = find_single_run(
                canonical_seed, condition, policy["run_name"]
            )
            candidates = sorted(
                (run_dir / "models").glob("model_epoch_*.pth"),
                key=checkpoint_epoch,
            )
            if not candidates:
                raise FileNotFoundError(f"No checkpoint in {run_dir}")
            inventories = [
                {
                    "epoch": checkpoint_epoch(path),
                    "path": str(path.resolve()),
                    "sha256": sha256(path),
                    "size_bytes": path.stat().st_size,
                }
                for path in candidates
            ]
            selected = inventories[-1]
            saved_config_path = run_dir / "config.json"
            saved = read_json(saved_config_path)
            if saved["train"]["data"][0]["path"] != policy["dataset_path"]:
                raise ValueError(
                    f"seed{canonical_seed}/{condition}: saved dataset mismatch"
                )
            if int(saved["train"]["seed"]) != int(policy["source_training_seed"]):
                raise ValueError(
                    f"seed{canonical_seed}/{condition}: saved training seed mismatch"
                )
            if (
                saved["experiment"]["logging"]["wandb_proj_name"]
                != WANDB_PROJECT
            ):
                raise ValueError(
                    f"seed{canonical_seed}/{condition}: saved W&B project mismatch"
                )
            policy.update(
                {
                    "status": "checkpoint_frozen",
                    "run_dir": str(run_dir.resolve()),
                    "available_checkpoints": inventories,
                    "selection_rule": "highest numeric emitted model_epoch_*.pth",
                    "epoch": selected["epoch"],
                    "checkpoint_path": selected["path"],
                    "checkpoint_sha256": selected["sha256"],
                    "checkpoint_size_bytes": selected["size_bytes"],
                    "saved_config_path": str(saved_config_path.resolve()),
                    "saved_config_sha256": sha256(saved_config_path),
                }
            )
            checkpoint_rows.append(dict(policy))
    if len(checkpoint_rows) != 25:
        raise AssertionError("Checkpoint freeze must cover 25 policy slots")
    policies["policies"] = [
        rows[(seed, condition)]
        for seed in CANONICAL_SEEDS
        for condition in CONDITION_ORDER
    ]
    write_json(MANIFEST_ROOT / "policies.json", policies)
    payload = {
        "schema_version": 1,
        "manifest_type": "tro_stage2_pre_rollout_frozen_checkpoints",
        "frozen_before_rollout": True,
        "condition_order": list(CONDITION_ORDER),
        "canonical_seeds": list(CANONICAL_SEEDS),
        "selection_rule": "highest numeric emitted model_epoch_*.pth",
        "checkpoints": checkpoint_rows,
    }
    write_json(MANIFEST_ROOT / "checkpoints.json", payload)
    by_seed = {}
    for row in checkpoint_rows:
        by_seed.setdefault(int(row["canonical_seed"]), {})[row["condition"]] = {
            **row,
            "path": row["checkpoint_path"],
            "sha256": row["checkpoint_sha256"],
        }
    for canonical_seed in CANONICAL_SEEDS:
        write_json(
            MANIFEST_ROOT / f"checkpoints_seed{canonical_seed}.json",
            {
                "schema_version": 1,
                "manifest_type": "tro_stage2_checkpoint_evaluation_view",
                "canonical_seed": canonical_seed,
                "condition_order": list(CONDITION_ORDER),
                "unified_checkpoint_manifest": str(
                    (MANIFEST_ROOT / "checkpoints.json").resolve()
                ),
                "unified_checkpoint_manifest_sha256": sha256(
                    MANIFEST_ROOT / "checkpoints.json"
                ),
                "checkpoints": by_seed[canonical_seed],
            },
        )
    print("Frozen 25/25 policy checkpoints before Stage 2 rollout")


def validate_all_datasets(_args):
    manifest = read_json(MANIFEST_ROOT / "datasets.json")
    if len(manifest["datasets"]) != 25:
        raise ValueError("Expected exactly 25 dataset slots")
    new = reused = 0
    for row in manifest["datasets"]:
        path = Path(row["hdf5_path"])
        if not path.is_file():
            raise FileNotFoundError(path)
        if sha256(path) != row["hdf5_sha256"]:
            raise ValueError(f"Dataset hash mismatch: {path}")
        if row["reused_dataset"]:
            reused += 1
        else:
            new += 1
            if row["status"] != "hdf5_validated":
                raise ValueError(f"New dataset not validated: {path}")
    expected = read_json(MANIFEST_ROOT / "datasets.json")["counts"]
    if (new, reused) != (expected["new"], expected["reused"]):
        raise ValueError(f"Dataset count mismatch: new={new}, reused={reused}")
    print(
        f"Validated 25/25 dataset slots: {new} new + {reused} reused"
    )


def parse_args():
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    freeze = commands.add_parser("freeze-protocol")
    freeze.add_argument(
        "--skip-large-rehash",
        action="store_true",
        help="Use already frozen Stage 1 hashes after an earlier full audit.",
    )
    freeze.set_defaults(func=freeze_protocol)
    commands.add_parser("generate-rollout-manifests").set_defaults(
        func=generate_rollout_manifests
    )
    fallback = commands.add_parser("activate-fallback")
    fallback.add_argument(
        "--canonical-seed", type=int, choices=(1, 4, 5), required=True
    )
    fallback.set_defaults(func=activate_fallback)
    for name, func in (("collect", collect), ("validate-raw", validate_raw)):
        command = commands.add_parser(name)
        command.add_argument(
            "--canonical-seed", type=int, choices=tuple(CANONICAL_SEEDS), required=True
        )
        command.add_argument("--target", type=int, required=True)
        command.add_argument("--smoke", action="store_true")
        command.add_argument("--sample-hz", type=float, default=8.0)
        command.add_argument("--playback-speed", type=float, default=100.0)
        command.set_defaults(func=func)
    hdf5 = commands.add_parser("create-hdf5")
    hdf5.add_argument(
        "--canonical-seed", type=int, choices=tuple(CANONICAL_SEEDS), required=True
    )
    hdf5.set_defaults(func=create_hdf5)
    commands.add_parser("validate-all-datasets").set_defaults(
        func=validate_all_datasets
    )
    commands.add_parser("create-train-configs").set_defaults(
        func=create_train_configs
    )
    commands.add_parser("freeze-checkpoints").set_defaults(
        func=freeze_checkpoints
    )
    return parser.parse_args()


def main():
    args = parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
