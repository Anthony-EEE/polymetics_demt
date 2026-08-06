#!/usr/bin/env python3
"""Strict execution utilities for T-RO Stage 2c Position composition."""

import argparse
import hashlib
import json
import math
import os
import random
import re
import subprocess
import sys
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "examples"))
sys.path.insert(0, str(ROOT / "scripts"))

from main_abla_1 import PandaSim, disk_offset  # noqa: E402
from eval_abla1_trained_policies import solve_ik_with_error  # noqa: E402


EXPERIMENT = ROOT / "experiments" / "tro_stage2_position_composition"
MANIFESTS = EXPERIMENT / "manifests"
CONFIGS = EXPERIMENT / "configs" / "training"
ANALYSIS = EXPERIMENT / "analysis"
DATA_ROOT = ROOT / "dataset" / "tro_position_stage2_composition"
MODEL_ROOT = Path(
    "/scratch/prj/eng_demt_robot_learning/trained_models/"
    "tro_position_stage2_composition"
)
AXIAL = ROOT / "experiments" / "tro_stage2_position_axial_replication"
AXIAL_MANIFESTS = AXIAL / "manifests"
AXIAL_DATA = ROOT / "dataset" / "tro_position_stage2_axial"
IDOOD = ROOT / "experiments" / "tro_stage2_position_axial_idood_rerollout"
IDOOD_DATA = ROOT / "dataset" / "tro_position_stage2_axial_idood_rerollout"
SHARED = ROOT / "experiments" / "shared_artifacts"

V1_PROTOCOL_ID = "tro_stage2_position_composition_missing_cells_v1"
PROTOCOL_ID = (
    "tro_stage2_position_composition_missing_cells_v2_retry_until_success"
)
CONDITIONS = {
    "START15_APP3P6": (0.15, 0.036),
    "START15_APP6": (0.15, 0.060),
    "START15_APP8P4": (0.15, 0.084),
    "START25_APP3P6": (0.25, 0.036),
    "START25_APP6": (0.25, 0.060),
    "START25_APP8P4": (0.25, 0.084),
    "START35_APP3P6": (0.35, 0.036),
    "START35_APP6": (0.35, 0.060),
    "START35_APP8P4": (0.35, 0.084),
}
CONDITION_ORDER = tuple(CONDITIONS)
NEW_CONDITIONS = (
    "START15_APP3P6",
    "START15_APP8P4",
    "START35_APP3P6",
    "START35_APP8P4",
)
AXIAL_CONDITIONS = (
    "START15_APP6",
    "START35_APP6",
    "START25_APP3P6",
    "START25_APP6",
    "START25_APP8P4",
)
SEEDS = {
    1: {"collection": 1, "training": 1},
    2: {"collection": 2, "training": 2},
    3: {"collection": 3, "training": 3},
    4: {"collection": 1702, "training": 2702},
    5: {"collection": 1701, "training": 2701},
}
ROLLOUT_SEEDS = (1, 2, 3, 4, 5)
FROZEN_LATENT_KEYS = (
    "candidate_index",
    "accepted_candidate_id",
    "start_angle",
    "start_radial_quantile",
    "approach_angle",
    "approach_radial_quantile",
    "collection_seed",
)
FROZEN_TOP = {
    AXIAL_MANIFESTS / "checkpoints.json":
        "240a936999281f429dd1b043b19df5bd9291ed478933305a7c051c5183227580",
    AXIAL / "analysis" / "comparison.json":
        "c70020fe70ab5aae9959ea990e66a2e2f3c4af4c05f24557a79d64c973ef9113",
    AXIAL / "analysis" / "summary.md":
        "825a13e358b01e8707c99e1f19673b01d46df62edbacecce12bff6bbc6684370",
    IDOOD / "analysis" / "comparison.json":
        "ae30a6133436654d6adee85dae14b8db490718df65a5e526638a68f75e3a2353",
    IDOOD / "analysis" / "summary.md":
        "5d495bc11fc7a0ee1f4f912b816d3d143578f2bd38ce3caa50718d144ee73528",
}
CHECKPOINT_RE = re.compile(r"model_epoch_(\d+)\.pth$")
TRAINING_TEMPLATE = (
    ROOT / "experiments" / "mvp0_position_event" / "confirmation_earlystop"
    / "configs" / "training" / "START15_APP6.json"
)
LEGACY_SPLIT = (
    ROOT / "dataset" / "ar_guidance_spatial_S15_S35"
    / "spatial_S25_d30_seed1_2gap.hdf5"
)


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_frozen_json(path, payload):
    path = Path(path)
    rendered = json.dumps(payload, indent=2) + "\n"
    if path.exists() and path.read_text(encoding="utf-8") != rendered:
        raise FileExistsError(f"Refusing to replace frozen artifact: {path}")
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rendered, encoding="utf-8")


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tree_sha256(path):
    path = Path(path)
    digest = hashlib.sha256()
    for child in sorted(p for p in path.rglob("*") if p.is_file()):
        digest.update(str(child.relative_to(path)).encode())
        digest.update(b"\0")
        digest.update(child.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def checkpoint_epoch(path):
    match = CHECKPOINT_RE.fullmatch(Path(path).name)
    if not match:
        raise ValueError(f"Invalid checkpoint name: {path}")
    return int(match.group(1))


def git_commit():
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()


def composition_attempt_seed(base_runtime_seed, attempt_index):
    """Return the frozen v2 bundle seed for one scientific attempt."""
    base_runtime_seed = int(base_runtime_seed)
    attempt_index = int(attempt_index)
    if not 0 <= base_runtime_seed <= 0xFFFFFFFF:
        raise ValueError("base_runtime_seed must be an unsigned 32-bit integer")
    if attempt_index < 0:
        raise ValueError("attempt_index must be non-negative")
    if attempt_index == 0:
        return base_runtime_seed
    message = (
        f"composition-v2:{base_runtime_seed}:{attempt_index}".encode("ascii")
    )
    return int.from_bytes(hashlib.sha256(message).digest()[:4], "big")


def attempt_latent(frozen_latent, attempt_index):
    """Add explicit v2 provenance without changing the frozen latent identity."""
    base_runtime_seed = int(frozen_latent["runtime_seed"])
    runtime_seed = composition_attempt_seed(base_runtime_seed, attempt_index)
    value = dict(frozen_latent)
    value["runtime_seed"] = runtime_seed
    value["composition_v2"] = {
        "protocol_id": PROTOCOL_ID,
        "base_runtime_seed": base_runtime_seed,
        "attempt_index": int(attempt_index),
        "attempt_runtime_seed": runtime_seed,
        "same_seed_across_four_corners": True,
    }
    return value


def assert_frozen_latent_identity(actual, frozen):
    for key in FROZEN_LATENT_KEYS:
        if actual.get(key) != frozen.get(key):
            raise ValueError(f"Frozen latent identity changed at key {key}")


def progress_v2_path(run_root):
    return Path(run_root) / "collection_progress_v2.json"


def attempt_staging_path(run_root, demo_index, candidate_index, attempt_index):
    return (
        Path(run_root) / ".paired_staging_v2"
        / f"demo_{demo_index:03d}_candidate_{candidate_index:04d}"
        / f"attempt_{attempt_index:03d}"
    )


def accepted_bundle_path(run_root, demo_index, candidate_index, attempt_index):
    return (
        Path(run_root) / "accepted_bundles_v2"
        / f"demo_{demo_index:03d}_candidate_{candidate_index:04d}"
        / f"attempt_{attempt_index:03d}"
    )


def failed_bundle_path(run_root, demo_index, candidate_index, attempt_index):
    return (
        Path(run_root) / "scientific_attempts_v2"
        / f"demo_{demo_index:03d}_candidate_{candidate_index:04d}"
        / f"attempt_{attempt_index:03d}"
    )


def attempt_record(result_path):
    payload = read_json(result_path)
    required = {
        "demo_index", "candidate_index", "attempt_index", "base_runtime_seed",
        "attempt_runtime_seed", "condition_results",
    }
    if not required.issubset(payload):
        raise ValueError(f"Incomplete attempt record: {result_path}")
    if list(payload["condition_results"]) != list(NEW_CONDITIONS):
        raise ValueError(f"Attempt condition order changed: {result_path}")
    return payload


def materialize_accepted_bundle(
    run_root, bundle, demo_index, candidate_index
):
    """Expose one atomically accepted bundle through the four raw datasets."""
    bundle = Path(bundle)
    for condition in NEW_CONDITIONS:
        source = bundle / condition / f"demo_{candidate_index}"
        if not source.is_dir():
            raise FileNotFoundError(source)
        destination = Path(run_root) / "raw" / condition / f"demo_{demo_index}"
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists() or destination.is_symlink():
            if (
                destination.is_symlink()
                and destination.resolve() == source.resolve()
            ):
                continue
            raise FileExistsError(f"Refusing to replace accepted row {destination}")
        relative = os.path.relpath(source, destination.parent)
        destination.symlink_to(relative, target_is_directory=True)


def finalize_attempt(run_root, staging, result):
    """Archive a complete result or atomically accept its whole four-corner bundle."""
    run_root = Path(run_root)
    staging = Path(staging)
    demo_index = int(result["demo_index"])
    candidate_index = int(result["candidate_index"])
    attempt_index = int(result["attempt_index"])
    successes = [
        bool(result["condition_results"][condition]["success"])
        for condition in NEW_CONDITIONS
    ]
    if all(successes):
        destination = accepted_bundle_path(
            run_root, demo_index, candidate_index, attempt_index
        )
        if staging.exists():
            destination.parent.mkdir(parents=True, exist_ok=True)
            if destination.exists():
                raise FileExistsError(destination)
            staging.rename(destination)
        if not destination.is_dir():
            raise FileNotFoundError(destination)
        materialize_accepted_bundle(
            run_root, destination, demo_index, candidate_index
        )
        return "accepted", destination
    destination = failed_bundle_path(
        run_root, demo_index, candidate_index, attempt_index
    )
    if staging.exists():
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            raise FileExistsError(destination)
        staging.rename(destination)
    if not destination.is_dir():
        raise FileNotFoundError(destination)
    return "scientific_failure", destination


def active_source(seed):
    fallbacks = {
        int(row["canonical_seed"]): row
        for row in read_json(
            AXIAL_MANIFESTS / "fallback_activations.json"
        )["activations"]
    }
    if seed in fallbacks:
        latent = Path(fallbacks[seed]["latent_manifest_path"])
        namespace = "formal_fallback"
    else:
        latent = AXIAL_MANIFESTS / "paired_latents" / f"seed{seed}.json"
        namespace = "formal"
    progress = AXIAL_DATA / namespace / f"seed{seed}" / "collection_progress.json"
    return latent, progress, namespace


def accepted_latents(seed):
    latent_path, progress_path, namespace = active_source(seed)
    progress = read_json(progress_path)
    payload = read_json(latent_path)
    if sha256(latent_path) != progress["latent_manifest_sha256"]:
        raise ValueError(f"seed{seed}: active latent/progress hash mismatch")
    accepted = [int(v) for v in progress["accepted_candidate_indices"]]
    if len(accepted) != 30 or len(set(accepted)) != 30:
        raise ValueError(f"seed{seed}: expected 30 unique accepted candidates")
    by_id = {int(row["candidate_index"]): row for row in payload["candidates"]}
    records = [by_id[index] for index in accepted]
    return records, {
        "canonical_seed": seed,
        "source_collection_seed": SEEDS[seed]["collection"],
        "source_training_seed": SEEDS[seed]["training"],
        "paired_latent_manifest_path": str(latent_path.resolve()),
        "paired_latent_manifest_sha256": sha256(latent_path),
        "accepted_candidate_indices": accepted,
        "source_progress_path": str(progress_path.resolve()),
        "source_progress_sha256": sha256(progress_path),
        "source_namespace": namespace,
    }


def audit_anchors():
    top = {}
    for path, expected in FROZEN_TOP.items():
        actual = sha256(path)
        if actual != expected:
            raise ValueError(f"Frozen anchor changed: {path}")
        top[str(path.resolve())] = actual
    source = read_json(AXIAL_MANIFESTS / "checkpoints.json")
    if len(source["checkpoints"]) != 25:
        raise ValueError("Axial checkpoint anchor count is not 25")
    checkpoints = []
    datasets = []
    for row in source["checkpoints"]:
        checkpoint = Path(row["checkpoint_path"])
        if sha256(checkpoint) != row["checkpoint_sha256"]:
            raise ValueError(f"Checkpoint changed: {checkpoint}")
        dataset = Path(row["dataset_path"])
        if sha256(dataset) != row["dataset_sha256"]:
            raise ValueError(f"Dataset changed: {dataset}")
        checkpoints.append({
            "canonical_seed": int(row["canonical_seed"]),
            "condition": row["condition"],
            "path": str(checkpoint.resolve()),
            "sha256": row["checkpoint_sha256"],
            "epoch": int(row["epoch"]),
        })
        datasets.append({
            "canonical_seed": int(row["canonical_seed"]),
            "condition": row["condition"],
            "path": str(dataset.resolve()),
            "sha256": row["dataset_sha256"],
        })
    common = []
    for path in sorted((AXIAL_MANIFESTS / "rollout_5seed").glob("*.json")):
        common.append({"path": str(path.resolve()), "sha256": sha256(path)})
    rmax40 = []
    for path in sorted(
        (IDOOD / "manifests" / "rollout_5seed_rmax40").glob("*.json")
    ):
        rmax40.append({"path": str(path.resolve()), "sha256": sha256(path)})
    if len(common) != 10 or len(rmax40) != 30:
        raise ValueError("Reused rollout manifest counts changed")
    return top, checkpoints, datasets, common, rmax40


def slot_rows(anchor_checkpoints, anchor_datasets):
    cp = {
        (row["canonical_seed"], row["condition"]): row
        for row in anchor_checkpoints
    }
    ds = {
        (row["canonical_seed"], row["condition"]): row
        for row in anchor_datasets
    }
    latent_info = {seed: accepted_latents(seed)[1] for seed in SEEDS}
    rows = []
    for condition in CONDITION_ORDER:
        start_radius, approach_radius = CONDITIONS[condition]
        for seed in SEEDS:
            base = {
                "canonical_seed": seed,
                "source_collection_seed": SEEDS[seed]["collection"],
                "source_training_seed": SEEDS[seed]["training"],
                "condition": condition,
                "start_support_radius_m": start_radius,
                "approach_radius_m": approach_radius,
                "paired_latent_manifest_path":
                    latent_info[seed]["paired_latent_manifest_path"],
                "paired_latent_manifest_sha256":
                    latent_info[seed]["paired_latent_manifest_sha256"],
            }
            if condition in NEW_CONDITIONS:
                raw = DATA_ROOT / "formal" / f"seed{seed}" / "raw" / condition
                hdf5 = (
                    DATA_ROOT / "formal" / f"seed{seed}" / "hdf5"
                    / f"{condition}_seed{seed}_d30_2gap.hdf5"
                )
                config = CONFIGS / f"seed{seed}" / f"{condition}.json"
                rows.append({
                    **base,
                    "reused_dataset": False,
                    "reused_policy": False,
                    "status": "planned_new",
                    "raw_path": str(raw.resolve()),
                    "hdf5_path": str(hdf5.resolve()),
                    "config_path": str(config.resolve()),
                    "source_artifact_path": str(hdf5.resolve()),
                    "source_artifact_sha256": None,
                })
            else:
                key = (seed, condition)
                rows.append({
                    **base,
                    "reused_dataset": True,
                    "reused_policy": True,
                    "status": "reused_verified",
                    "hdf5_path": ds[key]["path"],
                    "hdf5_sha256": ds[key]["sha256"],
                    "checkpoint_path": cp[key]["path"],
                    "checkpoint_sha256": cp[key]["sha256"],
                    "epoch": cp[key]["epoch"],
                    "source_artifact_path": cp[key]["path"],
                    "source_artifact_sha256": cp[key]["sha256"],
                })
    return rows


def freeze_protocol(_args):
    top, checkpoints, datasets, common, rmax40 = audit_anchors()
    rows = slot_rows(checkpoints, datasets)
    counts = {
        "policy_slots": len(rows),
        "immutable_anchor_slots": sum(r["reused_policy"] for r in rows),
        "new_dataset_policy_slots": sum(not r["reused_policy"] for r in rows),
        "new_datasets": 20,
        "new_demonstrations": 600,
        "new_hdf5": 20,
        "new_policies": 20,
        "common_absolute_tasks": 200,
        "common_absolute_rows": 5000,
        "rmax40_tasks": 200,
        "rmax40_rows": 5000,
    }
    expected = {
        "policy_slots": 45, "immutable_anchor_slots": 25,
        "new_dataset_policy_slots": 20, "new_datasets": 20,
        "new_demonstrations": 600, "new_hdf5": 20, "new_policies": 20,
        "common_absolute_tasks": 200, "common_absolute_rows": 5000,
        "rmax40_tasks": 200, "rmax40_rows": 5000,
    }
    if counts != expected:
        raise AssertionError("Composition scope/counts changed")
    protocol = {
        "schema_version": 1,
        "protocol_id": V1_PROTOCOL_ID,
        "authority": str((EXPERIMENT / "PLAN.md").resolve()),
        "git_commit_at_freeze": git_commit(),
        "condition_order": list(CONDITION_ORDER),
        "new_conditions": list(NEW_CONDITIONS),
        "canonical_seed_mapping": {
            str(seed): {
                "canonical_seed": seed,
                "source_collection_seed": value["collection"],
                "source_training_seed": value["training"],
            } for seed, value in SEEDS.items()
        },
        "expected_counts": counts,
        "task": {
            "trajectory": ["Start", "Approach", "Descent", "Grasp", "Lift"],
            "base_corridor_start": [0.30, 0.0, 0.50],
            "start_plane": "xz", "approach_plane": "xy",
            "sample_hz": 8, "action_gap": 2,
            "successful_demonstrations_per_dataset": 30,
            "success": "final cube z >= 0.20 m",
        },
        "training": {
            "from_scratch": True, "max_epochs": 3000,
            "validation_early_stopping_patience": 41,
            "checkpoint_interval_epochs": 20,
            "checkpoint_selection": "highest numeric emitted model_epoch_*.pth",
            "rollout_based_checkpoint_selection": False,
            "wandb_project": "TRO_MVP",
        },
        "formal_rollout": {
            "seeds": list(ROLLOUT_SEEDS), "horizon": 200,
            "sample_hz": 8, "action_gap": 2, "action_dt": 0.25,
            "num_points": 10000, "terminate_on_success": True,
            "videos": False,
        },
        "analysis": {
            "independent_unit": "canonical dataset-policy seed",
            "delta_interaction": 0.05,
            "same_nonzero_sign_required": 4,
            "frozen_contrasts": [
                "I_tight_15", "I_tight_35", "I_wide_15", "I_wide_35"
            ],
        },
        "frozen_source_hashes": top,
    }
    reuse = {
        "schema_version": 1, "status": "verified",
        "models_copied": False, "datasets_copied": False,
        "anchor_checkpoints": checkpoints, "anchor_datasets": datasets,
    }
    write_frozen_json(MANIFESTS / "protocol.json", protocol)
    write_frozen_json(MANIFESTS / "anchor_reuse.json", reuse)
    write_frozen_json(
        MANIFESTS / "common_absolute_rollout_reuse.json",
        {"schema_version": 1, "count": 10, "manifests": common},
    )
    write_frozen_json(
        MANIFESTS / "rmax40_rollout_reuse.json",
        {"schema_version": 1, "count": 30, "manifests": rmax40},
    )
    write_json(
        MANIFESTS / "datasets.json",
        {"schema_version": 1, "counts": {"total": 45, "new": 20, "reused": 25},
         "datasets": rows},
    )
    write_json(
        MANIFESTS / "policies.json",
        {"schema_version": 1, "counts": {"total": 45, "new": 20, "reused": 25},
         "policies": rows},
    )
    if not (MANIFESTS / "jobs.json").exists():
        write_json(
            MANIFESTS / "jobs.json",
            {"schema_version": 1, "protocol_id": PROTOCOL_ID, "jobs": [],
             "infrastructure_retries": []},
        )
    print(json.dumps({"status": "verified", "counts": counts}, indent=2))


def axial_raw_metadata(seed, condition, demo_index):
    manifest = read_json(AXIAL_MANIFESTS / "datasets.json")
    rows = [
        row for row in manifest["datasets"]
        if int(row["canonical_seed"]) == seed and row["condition"] == condition
    ]
    if len(rows) != 1:
        raise ValueError(f"Missing axial dataset anchor seed{seed}/{condition}")
    return read_json(Path(rows[0]["raw_path"]) / f"demo_{demo_index}" / "metadata.json")


def feasibility_audit(_args):
    if not (MANIFESTS / "protocol.json").exists():
        raise FileNotFoundError("Run freeze-protocol first")
    for path, expected in FROZEN_TOP.items():
        if sha256(path) != expected:
            raise ValueError(f"Frozen anchor changed before feasibility: {path}")
    sim = PandaSim(gui=False, output_dir=None, sample_hz=8.0)
    sim.playback_speed = 100.0
    sim.setup()
    detailed = []
    max_start_error = 0.0
    max_approach_error = 0.0
    try:
        cube = sim.cube_pos()
        base_start = np.asarray([0.30, 0.0, 0.50])
        base_approach = np.asarray([cube[0], cube[1], 0.22])
        fixed = {
            "grasp": np.asarray([cube[0], cube[1], 0.04]),
            "lift": np.asarray([cube[0], cube[1], 0.30]),
        }
        fixed_errors = {
            name: solve_ik_with_error(sim, target)[2]
            for name, target in fixed.items()
        }
        if any(error > 0.025 for error in fixed_errors.values()):
            raise RuntimeError(f"Fixed waypoint IK failure: {fixed_errors}")
        for seed in SEEDS:
            records, info = accepted_latents(seed)
            for demo_index, latent in enumerate(records):
                candidate_index = int(latent["candidate_index"])
                for anchor_condition in AXIAL_CONDITIONS:
                    metadata = axial_raw_metadata(seed, anchor_condition, demo_index)
                    scientific_keys = (
                        "candidate_index", "start_angle",
                        "start_radial_quantile", "approach_angle",
                        "approach_radial_quantile", "collection_seed",
                        "runtime_seed",
                    )
                    if any(
                        metadata["paired_latent"].get(key) != latent.get(key)
                        for key in scientific_keys
                    ):
                        raise ValueError(
                            f"seed{seed}/demo{demo_index}/{anchor_condition}: "
                            "anchor normalized latent mismatch"
                        )
                for condition in NEW_CONDITIONS:
                    start_radius, approach_radius = CONDITIONS[condition]
                    start_delta = disk_offset(
                        latent["start_angle"], latent["start_radial_quantile"],
                        start_radius, "xz"
                    )
                    approach_delta = disk_offset(
                        latent["approach_angle"],
                        latent["approach_radial_quantile"],
                        approach_radius, "xy"
                    )
                    if np.linalg.norm(start_delta) > start_radius + 1e-12:
                        raise ValueError("Start bound violation")
                    if np.linalg.norm(approach_delta) > approach_radius + 1e-12:
                        raise ValueError("Approach bound violation")
                    _, realised_start, start_error = solve_ik_with_error(
                        sim, base_start + start_delta
                    )
                    _, realised_approach, approach_error = solve_ik_with_error(
                        sim, base_approach + approach_delta
                    )
                    max_start_error = max(max_start_error, start_error)
                    max_approach_error = max(max_approach_error, approach_error)
                    detailed.append({
                        "canonical_seed": seed,
                        "source_collection_seed": SEEDS[seed]["collection"],
                        "source_training_seed": SEEDS[seed]["training"],
                        "condition": condition, "demo_index": demo_index,
                        "candidate_index": candidate_index,
                        "accepted_candidate_id": latent["accepted_candidate_id"],
                        "paired_latent_manifest_path":
                            info["paired_latent_manifest_path"],
                        "paired_latent_manifest_sha256":
                            info["paired_latent_manifest_sha256"],
                        "start_delta": start_delta.tolist(),
                        "approach_delta": approach_delta.tolist(),
                        "start_ik_realised": realised_start.tolist(),
                        "approach_ik_realised": realised_approach.tolist(),
                        "start_ik_error": start_error,
                        "approach_ik_error": approach_error,
                        "waypoint_ik_reachable":
                            start_error <= 0.025 and approach_error <= 0.025,
                        "exact_links_to_five_axial_anchors": True,
                    })
    finally:
        sim.close()
    failures = [r for r in detailed if not r["waypoint_ik_reachable"]]
    payload = {
        "schema_version": 1,
        "status": "valid" if not failures else "protocol_blocker",
        "protocol_id": PROTOCOL_ID,
        "expected_records": 600,
        "audited_records": len(detailed),
        "four_corners": list(NEW_CONDITIONS),
        "canonical_seeds": list(SEEDS),
        "latents_per_seed": 30,
        "exact_links_to_25_immutable_anchor_slots": True,
        "all_start_xz_and_approach_xy_bounds_valid": True,
        "all_waypoints_ik_reachable": not failures,
        "max_start_ik_error": max_start_error,
        "max_approach_ik_error": max_approach_error,
        "fixed_waypoint_ik_errors": fixed_errors,
        "failures": failures,
        "records": detailed,
    }
    write_frozen_json(MANIFESTS / "feasibility_audit.json", payload)
    if len(detailed) != 600 or failures:
        raise RuntimeError("Exact feasibility gate failed; protocol review required")
    print(json.dumps({k: payload[k] for k in (
        "status", "audited_records", "max_start_ik_error",
        "max_approach_ik_error")}, indent=2))


def collection_root(seed, smoke):
    return DATA_ROOT / ("smoke" if smoke else "formal") / f"seed{seed}"


def retained_v1_bundle_record(run_root, seed, demo_index, candidate_index, latent):
    condition_paths = {}
    for condition in NEW_CONDITIONS:
        demo = Path(run_root) / "raw" / condition / f"demo_{demo_index}"
        metadata_path = demo / "metadata.json"
        if not metadata_path.is_file():
            raise FileNotFoundError(metadata_path)
        metadata = read_json(metadata_path)
        assert_frozen_latent_identity(metadata["paired_latent"], latent)
        if not bool(metadata.get("success", {}).get("success")):
            raise ValueError(f"v1 accepted bundle contains a failed corner: {demo}")
        if int(metadata["paired_latent"]["runtime_seed"]) != int(
            latent["runtime_seed"]
        ):
            raise ValueError(f"v1 attempt-0 runtime seed changed: {demo}")
        condition_paths[condition] = {
            "path": str(demo.resolve()),
            "tree_sha256": tree_sha256(demo),
        }
    return {
        "demo_index": int(demo_index),
        "candidate_index": int(candidate_index),
        "accepted_candidate_id": latent["accepted_candidate_id"],
        "attempt_index": 0,
        "base_runtime_seed": int(latent["runtime_seed"]),
        "attempt_runtime_seed": int(latent["runtime_seed"]),
        "condition_results": {
            condition: {"success": True} for condition in NEW_CONDITIONS
        },
        "accepted_path": None,
        "condition_paths": condition_paths,
        "source": "retained_complete_v1_attempt_zero_bundle",
    }


def migrate_v1_progress(seed):
    """Create an idempotent v2 progress ledger without rewriting v1 evidence."""
    run_root = collection_root(seed, False)
    old_path = run_root / "collection_progress.json"
    new_path = progress_v2_path(run_root)
    records, latent_info = accepted_latents(seed)
    frozen_ids = [int(row["candidate_index"]) for row in records]
    if new_path.exists():
        progress = read_json(new_path)
        if (
            progress["protocol_id"] != PROTOCOL_ID
            or progress["frozen_candidate_indices"] != frozen_ids
            or progress["v1_progress_sha256"] != sha256(old_path)
        ):
            raise ValueError(f"v2 progress invariant changed: {new_path}")
        return progress

    old = read_json(old_path)
    if old["protocol_id"] != V1_PROTOCOL_ID:
        raise ValueError(f"Unexpected v1 progress protocol: {old_path}")
    completed = [int(value) for value in old["accepted_candidate_indices"]]
    if completed != frozen_ids[:len(completed)]:
        raise ValueError(f"v1 accepted order changed: {old_path}")
    accepted_bundles = [
        retained_v1_bundle_record(
            run_root, seed, demo_index, candidate_index, records[demo_index]
        )
        for demo_index, candidate_index in enumerate(completed)
    ]

    scientific_attempts = []
    for failure in old.get("scientific_failures", []):
        demo_index = int(failure["demo_index"])
        latent = records[demo_index]
        candidate_index = int(failure["candidate_index"])
        if candidate_index != int(latent["candidate_index"]):
            raise ValueError(f"v1 failure latent changed: {old_path}")
        archive = Path(failure["archived_path"])
        if not archive.is_dir():
            raise FileNotFoundError(archive)
        condition_results = failure["condition_results"]
        if list(condition_results) != list(NEW_CONDITIONS):
            raise ValueError(f"v1 failure condition order changed: {old_path}")
        scientific_attempts.append({
            "demo_index": demo_index,
            "candidate_index": candidate_index,
            "accepted_candidate_id": latent["accepted_candidate_id"],
            "attempt_index": 0,
            "base_runtime_seed": int(latent["runtime_seed"]),
            "attempt_runtime_seed": int(latent["runtime_seed"]),
            "condition_results": condition_results,
            "failed_conditions": [
                condition for condition in NEW_CONDITIONS
                if not bool(condition_results[condition]["success"])
            ],
            "archived_path": str(archive.resolve()),
            "archive_tree_sha256": tree_sha256(archive),
            "source": "preserved_v1_scientific_failure_attempt_zero",
        })

    infrastructure_retries = list(old.get("infrastructure_retries", []))
    legacy_staging_root = run_root / ".paired_staging"
    interrupted = sorted(
        path for path in legacy_staging_root.glob("demo_*") if path.is_dir()
    ) if legacy_staging_root.exists() else []
    for index, staging in enumerate(interrupted):
        match = re.fullmatch(
            r"demo_(\d+)_candidate_(\d+)", staging.name
        )
        if not match:
            raise ValueError(f"Unexpected v1 staging directory: {staging}")
        demo_index = int(match.group(1))
        candidate_index = int(match.group(2))
        if candidate_index != int(records[demo_index]["candidate_index"]):
            raise ValueError(f"Interrupted v1 latent changed: {staging}")
        archive = (
            run_root / "infrastructure_attempts_v2"
            / f"migration_v1_job36053381_{staging.name}_{index:03d}"
        )
        archive.parent.mkdir(parents=True, exist_ok=True)
        if archive.exists():
            raise FileExistsError(archive)
        staging.rename(archive)
        infrastructure_retries.append({
            "demo_index": demo_index,
            "candidate_index": candidate_index,
            "attempt_index": 0,
            "attempt_runtime_seed": int(records[demo_index]["runtime_seed"]),
            "reason": (
                "v1 collection task cancelled after scientific failure in "
                "another array task; incomplete bundle archived"
            ),
            "archived_path": str(archive.resolve()),
            "archive_tree_sha256": tree_sha256(archive),
            "identical_frozen_attempt_clean_retry": True,
            "source_job_id": "36053381",
        })

    progress = {
        "schema_version": 2,
        "protocol_id": PROTOCOL_ID,
        "canonical_seed": seed,
        "source_collection_seed": SEEDS[seed]["collection"],
        "source_training_seed": SEEDS[seed]["training"],
        "target": 30,
        "smoke": False,
        "condition_order": list(CONDITION_ORDER),
        "execution_conditions": list(NEW_CONDITIONS),
        **latent_info,
        "frozen_candidate_indices": frozen_ids,
        "accepted_candidate_indices": completed,
        "accepted_bundles": accepted_bundles,
        "scientific_attempts": scientific_attempts,
        "infrastructure_retries": infrastructure_retries,
        "v1_progress_path": str(old_path.resolve()),
        "v1_progress_sha256": sha256(old_path),
        "v1_progress_preserved": True,
        "protocol_blocker": False,
    }
    write_frozen_json(new_path, progress)
    return progress


def freeze_protocol_v2(_args):
    amendment_path = MANIFESTS / "protocol_amendment_v2.json"
    blocker_path = MANIFESTS / "protocol_blocker.json"
    snapshot_path = MANIFESTS / "final_hashes.json"
    amendment = read_json(amendment_path)
    blocker = read_json(blocker_path)
    snapshot = read_json(snapshot_path)
    if amendment["status"] != "authorized_ready_to_implement":
        raise ValueError("Protocol v2 amendment is not authorised")
    if blocker["protocol_id"] != V1_PROTOCOL_ID:
        raise ValueError("Historical blocker protocol changed")
    if (
        snapshot["composition_manifests"]["protocol_blocker.json"]
        != sha256(blocker_path)
    ):
        raise ValueError("Historical protocol_blocker.json hash changed")
    for failure in blocker["failures"]:
        progress_path = Path(failure["collection_progress_path"])
        evidence_path = Path(failure["evidence_path"])
        if sha256(progress_path) != failure["collection_progress_sha256"]:
            raise ValueError(f"Historical v1 progress changed: {progress_path}")
        if tree_sha256(evidence_path) != failure["evidence_tree_sha256"]:
            raise ValueError(
                f"Historical v1 failure evidence changed: {evidence_path}"
            )
    audit_anchors()
    migrations = []
    for seed in SEEDS:
        progress = migrate_v1_progress(seed)
        migrations.append({
            "canonical_seed": seed,
            "v1_progress_path": progress["v1_progress_path"],
            "v1_progress_sha256": progress["v1_progress_sha256"],
            "v2_progress_path": str(
                progress_v2_path(collection_root(seed, False)).resolve()
            ),
            "v2_progress_sha256": sha256(
                progress_v2_path(collection_root(seed, False))
            ),
            "retained_complete_bundles": len(progress["accepted_bundles"]),
            "migrated_scientific_attempts":
                len(progress["scientific_attempts"]),
            "archived_infrastructure_attempts":
                len(progress["infrastructure_retries"]),
        })
    payload = {
        "schema_version": 2,
        "protocol_id": PROTOCOL_ID,
        "amends": V1_PROTOCOL_ID,
        "status": "implemented_tested_frozen",
        "authority": str((EXPERIMENT / "PLAN.md").resolve()),
        "amendment_path": str(amendment_path.resolve()),
        "amendment_sha256": sha256(amendment_path),
        "preserved_v1_evidence": {
            "protocol_blocker_path": str(blocker_path.resolve()),
            "protocol_blocker_sha256": sha256(blocker_path),
            "final_hashes_v1_snapshot_path": str(snapshot_path.resolve()),
            "final_hashes_v1_snapshot_sha256": sha256(snapshot_path),
            "formal_collection_job_id": "36053381",
        },
        "collection": {
            "accepted_unit": "atomic_four_corner_attempt_bundle",
            "new_conditions": list(NEW_CONDITIONS),
            "canonical_seeds": list(SEEDS),
            "frozen_latent_ids_per_seed": 30,
            "attempt_zero": "frozen Stage 2 runtime_seed",
            "attempt_seed_derivation": (
                "uint32_be(SHA256(\"composition-v2:"
                "{base_runtime_seed}:{attempt_index}\")[0:4])"
            ),
            "integer_encoding": "decimal integers with no whitespace",
            "same_attempt_seed_across_four_corners": True,
            "scientific_attempt_limit": None,
            "failed_bundles_enter_dataset": False,
            "condition_specific_retry": False,
        },
        "progress_migration": migrations,
        "tests_required": [
            "attempt-seed determinism",
            "atomic rejection and acceptance",
            "failure archival",
            "crash/resume idempotence",
            "exact 30-latent preservation",
        ],
        "test_evidence": {
            "command": (
                "/scratch/users/k23114984/conda/arcap/bin/python -m pytest -q "
                "tests/test_tro_position_mvp0.py "
                "tests/test_tro_position_confirmation.py "
                "tests/test_tro_position_stage2.py "
                "tests/test_tro_position_stage2_idood.py "
                "tests/test_tro_position_composition.py"
            ),
            "result": "43 passed in 68.88s",
            "all_required_v2_semantics_covered": True,
        },
        "implementation": {
            "collector_path": str(Path(__file__).resolve()),
            "collector_sha256": sha256(Path(__file__).resolve()),
            "tests_path": str(
                (ROOT / "tests" / "test_tro_position_composition.py").resolve()
            ),
            "tests_sha256": sha256(
                ROOT / "tests" / "test_tro_position_composition.py"
            ),
        },
        "immutable_anchors_revalidated": True,
    }
    write_frozen_json(MANIFESTS / "protocol_v2.json", payload)
    print(json.dumps({
        "status": payload["status"],
        "protocol_id": PROTOCOL_ID,
        "migrations": migrations,
    }, indent=2))


def run_candidate(
    condition, latent, attempt_index, output_dir, sample_hz, playback_speed
):
    start_radius, approach_radius = CONDITIONS[condition]
    attempt_value = attempt_latent(latent, attempt_index)
    random.seed(int(attempt_value["runtime_seed"]))
    np.random.seed(int(attempt_value["runtime_seed"]))
    sim = PandaSim(gui=False, output_dir=output_dir, sample_hz=sample_hz)
    sim.playback_speed = playback_speed
    try:
        sim.setup()
        sim.begin_demo(int(latent["candidate_index"]))
        return sim.run_pick_and_lift_ablation(
            condition_label=condition,
            corridor_start_radius=start_radius,
            pre_grasp_radius=approach_radius,
            corridor_start_center=(0.30, 0.0, 0.50),
            success_lift_height=0.20,
            paired_latent=attempt_value,
            experiment_track_override="tro_position_stage2_composition",
        )
    finally:
        sim.close()


def collect(args):
    feasibility = read_json(MANIFESTS / "feasibility_audit.json")
    if feasibility["status"] != "valid" or feasibility["audited_records"] != 600:
        raise RuntimeError("Formal collection is gated by exact feasibility")
    protocol_v2 = read_json(MANIFESTS / "protocol_v2.json")
    if (
        protocol_v2["protocol_id"] != PROTOCOL_ID
        or protocol_v2["status"] != "implemented_tested_frozen"
    ):
        raise RuntimeError("Formal collection is gated by frozen protocol v2")
    seed = int(args.canonical_seed)
    target = int(args.target)
    if bool(args.smoke) or target != 30:
        raise ValueError(
            "Protocol v2 resumes formal target-30 collection only; "
            "the completed v1 smoke remains immutable"
        )
    records, latent_info = accepted_latents(seed)
    if len(records) != 30:
        raise ValueError("Protocol v2 requires exactly 30 frozen latents")
    run_root = collection_root(seed, False)
    raw_root = run_root / "raw"
    progress_path = progress_v2_path(run_root)
    progress = read_json(progress_path)
    invariants = (
        progress["protocol_id"] == PROTOCOL_ID
        and int(progress["canonical_seed"]) == seed
        and int(progress["target"]) == target
        and not bool(progress["smoke"])
        and progress["paired_latent_manifest_sha256"]
        == latent_info["paired_latent_manifest_sha256"]
        and progress["frozen_candidate_indices"]
        == [int(row["candidate_index"]) for row in records]
    )
    if not invariants:
        raise ValueError(f"Collection resume invariant changed: {progress_path}")
    completed = list(progress["accepted_candidate_indices"])
    expected_ids = [int(row["candidate_index"]) for row in records]
    if completed != expected_ids[:len(completed)]:
        raise ValueError("Accepted frozen candidate order changed")
    for condition in NEW_CONDITIONS:
        root = raw_root / condition
        demos = list(root.glob("demo_*")) if root.exists() else []
        if len(demos) != len(completed):
            raise RuntimeError(
                f"seed{seed}/{condition}: {len(demos)} demos != {len(completed)}"
            )
    for demo_index in range(len(completed), target):
        latent = records[demo_index]
        candidate_index = int(latent["candidate_index"])
        prior_scientific = [
            row for row in progress["scientific_attempts"]
            if int(row["demo_index"]) == demo_index
        ]
        attempt_index = (
            max(int(row["attempt_index"]) for row in prior_scientific) + 1
            if prior_scientific else 0
        )
        while True:
            staging = attempt_staging_path(
                run_root, demo_index, candidate_index, attempt_index
            )
            accepted_path = accepted_bundle_path(
                run_root, demo_index, candidate_index, attempt_index
            )
            failure_path = failed_bundle_path(
                run_root, demo_index, candidate_index, attempt_index
            )
            result = None
            if accepted_path.is_dir():
                result = attempt_record(accepted_path / "attempt_result.json")
                disposition, archive = finalize_attempt(
                    run_root, staging, result
                )
            elif failure_path.is_dir():
                result = attempt_record(failure_path / "attempt_result.json")
                disposition, archive = finalize_attempt(
                    run_root, staging, result
                )
            elif staging.exists() and (staging / "attempt_result.json").is_file():
                result = attempt_record(staging / "attempt_result.json")
                disposition, archive = finalize_attempt(
                    run_root, staging, result
                )
            else:
                if staging.exists():
                    retry_index = len(progress["infrastructure_retries"])
                    archive = (
                        run_root / "infrastructure_attempts_v2"
                        / f"resume_demo_{demo_index:03d}_attempt_"
                          f"{attempt_index:03d}_{retry_index:03d}"
                    )
                    archive.parent.mkdir(parents=True, exist_ok=True)
                    staging.rename(archive)
                    progress["infrastructure_retries"].append({
                        "demo_index": demo_index,
                        "candidate_index": candidate_index,
                        "attempt_index": attempt_index,
                        "attempt_runtime_seed": composition_attempt_seed(
                            latent["runtime_seed"], attempt_index
                        ),
                        "reason": (
                            "incomplete staging directory from prior "
                            "infrastructure interruption"
                        ),
                        "archived_path": str(archive.resolve()),
                        "archive_tree_sha256": tree_sha256(archive),
                        "identical_frozen_attempt_clean_retry": True,
                    })
                    write_json(progress_path, progress)
                results = {}
                try:
                    for condition in NEW_CONDITIONS:
                        attempt_root = staging / condition
                        success, details = run_candidate(
                            condition, latent, attempt_index, attempt_root,
                            float(args.sample_hz), float(args.playback_speed)
                        )
                        results[condition] = {
                            "success": bool(success), "details": details
                        }
                except Exception as error:
                    retry_index = len(progress["infrastructure_retries"])
                    archive = (
                        run_root / "infrastructure_attempts_v2"
                        / f"exception_demo_{demo_index:03d}_attempt_"
                          f"{attempt_index:03d}_{retry_index:03d}"
                    )
                    if staging.exists():
                        archive.parent.mkdir(parents=True, exist_ok=True)
                        staging.rename(archive)
                    progress["infrastructure_retries"].append({
                        "demo_index": demo_index,
                        "candidate_index": candidate_index,
                        "attempt_index": attempt_index,
                        "attempt_runtime_seed": composition_attempt_seed(
                            latent["runtime_seed"], attempt_index
                        ),
                        "reason": f"{type(error).__name__}: {error}",
                        "archived_path": (
                            str(archive.resolve()) if archive.exists() else None
                        ),
                        "archive_tree_sha256": (
                            tree_sha256(archive) if archive.exists() else None
                        ),
                        "identical_frozen_attempt_clean_retry": True,
                    })
                    write_json(progress_path, progress)
                    raise
                result = {
                    "schema_version": 2,
                    "protocol_id": PROTOCOL_ID,
                    "canonical_seed": seed,
                    "demo_index": demo_index,
                    "candidate_index": candidate_index,
                    "accepted_candidate_id": latent["accepted_candidate_id"],
                    "base_runtime_seed": int(latent["runtime_seed"]),
                    "attempt_index": attempt_index,
                    "attempt_runtime_seed": composition_attempt_seed(
                        latent["runtime_seed"], attempt_index
                    ),
                    "condition_results": results,
                    "failed_conditions": [
                        condition for condition in NEW_CONDITIONS
                        if not bool(results[condition]["success"])
                    ],
                    "same_attempt_seed_across_four_corners": True,
                }
                write_json(staging / "attempt_result.json", result)
                disposition, archive = finalize_attempt(
                    run_root, staging, result
                )
            if disposition == "scientific_failure":
                if not any(
                    int(row["demo_index"]) == demo_index
                    and int(row["attempt_index"]) == attempt_index
                    for row in progress["scientific_attempts"]
                ):
                    progress["scientific_attempts"].append({
                        **result,
                        "archived_path": str(archive.resolve()),
                        "archive_tree_sha256": tree_sha256(archive),
                        "source": "protocol_v2_atomic_four_corner_attempt",
                    })
                    write_json(progress_path, progress)
                print(
                    f"seed{seed}: rejected complete bundle demo{demo_index} "
                    f"attempt{attempt_index} failed="
                    f"{result['failed_conditions']}; retrying all four corners",
                    flush=True,
                )
                attempt_index += 1
                continue
            accepted_record = {
                **result,
                "accepted_path": str(archive.resolve()),
                "accepted_tree_sha256": tree_sha256(archive),
                "condition_paths": {
                    condition: {
                        "path": str(
                            (raw_root / condition / f"demo_{demo_index}").resolve()
                        ),
                        "tree_sha256": tree_sha256(
                            raw_root / condition / f"demo_{demo_index}"
                        ),
                    }
                    for condition in NEW_CONDITIONS
                },
                "source": "protocol_v2_atomic_four_corner_attempt",
            }
            if not any(
                int(row["demo_index"]) == demo_index
                for row in progress["accepted_bundles"]
            ):
                progress["accepted_bundles"].append(accepted_record)
                completed.append(candidate_index)
                progress["accepted_candidate_indices"] = completed
                write_json(progress_path, progress)
            print(
                f"seed{seed}: accepted frozen candidate {candidate_index} "
                f"on bundle attempt {attempt_index} "
                f"({len(completed)}/{target})", flush=True
            )
            break
    validate_raw(argparse.Namespace(
        canonical_seed=seed, target=target, smoke=False
    ))


def validate_raw(args):
    from check_abla1_dataset import check_demo

    seed = int(args.canonical_seed)
    target = int(args.target)
    run_root = collection_root(seed, bool(args.smoke))
    progress = read_json(
        run_root / "collection_progress.json"
        if args.smoke else progress_v2_path(run_root)
    )
    records, latent_info = accepted_latents(seed)
    records = records[:target]
    accepted = [int(v) for v in progress["accepted_candidate_indices"]]
    expected = [int(row["candidate_index"]) for row in records]
    if accepted != expected:
        raise ValueError(f"seed{seed}: exact accepted IDs changed")
    accepted_by_demo = {}
    if not args.smoke:
        if len(progress["accepted_bundles"]) != target:
            raise ValueError(f"seed{seed}: accepted bundle count is not {target}")
        accepted_by_demo = {
            int(row["demo_index"]): row for row in progress["accepted_bundles"]
        }
        if sorted(accepted_by_demo) != list(range(target)):
            raise ValueError(f"seed{seed}: accepted bundle indices changed")
    errors = []
    dataset_rows = []
    for condition in NEW_CONDITIONS:
        raw = run_root / "raw" / condition
        demos = sorted(
            raw.glob("demo_*"), key=lambda p: int(p.name.split("_", 1)[1])
        )
        if len(demos) != target:
            errors.append(f"{condition}: expected {target}, got {len(demos)}")
        for demo_index, demo in enumerate(demos):
            _, demo_errors, _ = check_demo(demo, expected_condition=condition)
            errors.extend(str(value) for value in demo_errors)
            metadata = read_json(demo / "metadata.json")
            if metadata.get("experiment_track") != "tro_position_stage2_composition":
                errors.append(f"{demo}: wrong experiment track")
            try:
                assert_frozen_latent_identity(
                    metadata["paired_latent"], records[demo_index]
                )
            except ValueError as error:
                errors.append(f"{demo}: {error}")
            if not args.smoke:
                bundle = accepted_by_demo[demo_index]
                if not bool(bundle["condition_results"][condition]["success"]):
                    errors.append(f"{demo}: accepted bundle has failed corner")
                actual_seed = int(metadata["paired_latent"]["runtime_seed"])
                expected_seed = int(bundle["attempt_runtime_seed"])
                if actual_seed != expected_seed:
                    errors.append(
                        f"{demo}: attempt seed {actual_seed} != {expected_seed}"
                    )
                if bundle["source"].startswith("protocol_v2"):
                    provenance = metadata["paired_latent"].get("composition_v2")
                    expected_provenance = {
                        "protocol_id": PROTOCOL_ID,
                        "base_runtime_seed":
                            int(records[demo_index]["runtime_seed"]),
                        "attempt_index": int(bundle["attempt_index"]),
                        "attempt_runtime_seed": expected_seed,
                        "same_seed_across_four_corners": True,
                    }
                    if provenance != expected_provenance:
                        errors.append(f"{demo}: v2 attempt provenance mismatch")
            start_radius, approach_radius = CONDITIONS[condition]
            expected_start = disk_offset(
                records[demo_index]["start_angle"],
                records[demo_index]["start_radial_quantile"],
                start_radius, "xz"
            )
            expected_approach = disk_offset(
                records[demo_index]["approach_angle"],
                records[demo_index]["approach_radial_quantile"],
                approach_radius, "xy"
            )
            if not np.allclose(
                metadata["corridor_start_delta"], expected_start, atol=1e-10
            ):
                errors.append(f"{demo}: Start reconstruction mismatch")
            if not np.allclose(
                metadata["pre_grasp_delta"], expected_approach, atol=1e-10
            ):
                errors.append(f"{demo}: Approach reconstruction mismatch")
        demo_hashes = [
            {"demo_index": index, "tree_sha256": tree_sha256(demo)}
            for index, demo in enumerate(demos)
        ]
        digest = hashlib.sha256()
        for row in demo_hashes:
            digest.update(
                f"{row['demo_index']}:{row['tree_sha256']}\n".encode("ascii")
            )
        dataset_rows.append({
            "canonical_seed": seed,
            "condition": condition,
            "source_collection_seed": SEEDS[seed]["collection"],
            "source_training_seed": SEEDS[seed]["training"],
            "paired_latent_manifest_path":
                latent_info["paired_latent_manifest_path"],
            "paired_latent_manifest_sha256":
                latent_info["paired_latent_manifest_sha256"],
            "canonical_candidate_ids": accepted,
            "raw_path": str(raw.resolve()),
            "raw_tree_sha256": digest.hexdigest(),
            "demo_tree_hashes": demo_hashes,
            "num_successful_demonstrations": len(demos),
        })
    if errors:
        raise ValueError("Raw validation failed:\n" + "\n".join(errors))
    report = {
        "schema_version": 1, "status": "valid",
        "canonical_seed": seed, "smoke": bool(args.smoke),
        "target": target, "execution_conditions": list(NEW_CONDITIONS),
        "accepted_candidate_indices": accepted,
        "accepted_bundle_count": (
            None if args.smoke else len(progress["accepted_bundles"])
        ),
        "scientific_attempt_count": (
            None if args.smoke else len(progress["scientific_attempts"])
        ),
        "infrastructure_retry_count": (
            None if args.smoke else len(progress["infrastructure_retries"])
        ),
        "datasets": dataset_rows,
    }
    write_json(run_root / "raw_validation.json", report)
    if not args.smoke:
        manifest = read_json(MANIFESTS / "datasets.json")
        by_key = {
            (int(row["canonical_seed"]), row["condition"]): row
            for row in manifest["datasets"]
        }
        for row in dataset_rows:
            target_row = by_key[(seed, row["condition"])]
            target_row.update(row)
            target_row["status"] = "raw_validated"
        manifest["datasets"] = [
            by_key[(seed_id, condition)]
            for condition in CONDITION_ORDER for seed_id in SEEDS
        ]
        write_json(MANIFESTS / "datasets.json", manifest)
    print(f"Validated seed{seed}: {4 * target} exact-paired demonstrations")


def apply_frozen_split(path):
    import h5py

    with h5py.File(LEGACY_SPLIT, "r") as source:
        train = list(source["mask/train"][:])
        valid = list(source["mask/valid"][:])
    if len(train) != 54 or len(valid) != 6:
        raise ValueError("Frozen split is not 54/6")
    with h5py.File(path, "r+") as hdf5:
        if len(hdf5["data"]) != 60:
            raise ValueError("Composition HDF5 does not contain 60 episodes")
        mask = hdf5.require_group("mask")
        for name in ("train", "valid"):
            if name in mask:
                del mask[name]
        mask.create_dataset("train", data=train)
        mask.create_dataset("valid", data=valid)
        hdf5.attrs["tro_stage2_composition_sample_hz"] = 8.0
        hdf5.attrs["tro_stage2_composition_action_gap"] = 2
        hdf5.attrs["tro_stage2_composition_augmentation"] = \
            "two_episodes_per_demo"
        hdf5.attrs["tro_stage2_composition_split"] = \
            "exact_legacy_S25_54_train_6_valid"


def create_hdf5(args):
    seed = int(args.canonical_seed)
    validation = read_json(
        collection_root(seed, False) / "raw_validation.json"
    )
    if validation["status"] != "valid" or validation["target"] != 30:
        raise RuntimeError("HDF5 creation requires formal raw validation")
    step1 = Path("/users/k23114984/code/arcap_policy/STEP1_build_dataset")
    sys.path.insert(0, str(step1))
    from dataset_utils import process_hdf5_arcap_multi

    output_root = collection_root(seed, False) / "hdf5"
    output_root.mkdir(parents=True, exist_ok=True)
    for condition in NEW_CONDITIONS:
        raw = collection_root(seed, False) / "raw" / condition
        output = output_root / f"{condition}_seed{seed}_d30_2gap.hdf5"
        if output.exists():
            raise FileExistsError(f"Refusing to overwrite {output}")
        process_hdf5_arcap_multi(
            output_hdf5_file=str(output), dataset_folders=[str(raw)],
            action_gap=2, num_points_to_sample=10000,
            hand_ahead=0, last_mean=1, visualize=False,
        )
        apply_frozen_split(output)
        print(f"Wrote {output}", flush=True)
    validate_hdf5_seed(seed)


def validate_hdf5_seed(seed):
    import h5py

    manifest = read_json(MANIFESTS / "datasets.json")
    by_key = {
        (int(row["canonical_seed"]), row["condition"]): row
        for row in manifest["datasets"]
    }
    for condition in NEW_CONDITIONS:
        path = (
            collection_root(seed, False) / "hdf5"
            / f"{condition}_seed{seed}_d30_2gap.hdf5"
        )
        with h5py.File(path, "r") as hdf5:
            if (
                len(hdf5["data"]) != 60
                or len(hdf5["mask/train"]) != 54
                or len(hdf5["mask/valid"]) != 6
            ):
                raise ValueError(f"Invalid HDF5 structure: {path}")
        row = by_key[(seed, condition)]
        row.update({
            "status": "hdf5_validated",
            "hdf5_path": str(path.resolve()), "hdf5_sha256": sha256(path),
            "hdf5_size_bytes": path.stat().st_size,
            "source_artifact_path": str(path.resolve()),
            "source_artifact_sha256": sha256(path),
            "episodes": 60, "train_mask_count": 54,
            "valid_mask_count": 6, "sample_hz": 8, "action_gap": 2,
        })
    manifest["datasets"] = [
        by_key[(seed_id, condition)]
        for condition in CONDITION_ORDER for seed_id in SEEDS
    ]
    write_json(MANIFESTS / "datasets.json", manifest)
    print(f"Validated four composition HDF5 files for seed{seed}")


def validate_all_datasets(_args):
    manifest = read_json(MANIFESTS / "datasets.json")
    new_rows = [row for row in manifest["datasets"] if not row["reused_dataset"]]
    reused_rows = [row for row in manifest["datasets"] if row["reused_dataset"]]
    if len(new_rows) != 20 or len(reused_rows) != 25:
        raise ValueError("Dataset matrix is not 20 new + 25 anchors")
    for row in manifest["datasets"]:
        path = Path(row["hdf5_path"])
        if not path.is_file() or sha256(path) != row["hdf5_sha256"]:
            raise ValueError(f"Dataset hash validation failed: {path}")
        if not row["reused_dataset"] and row["status"] != "hdf5_validated":
            raise ValueError(f"New HDF5 not validated: {path}")
    print("Validated 45/45 dataset slots: 20 new + 25 immutable anchors")


def create_train_configs(_args):
    validate_all_datasets(_args)
    template = read_json(TRAINING_TEMPLATE)
    datasets = read_json(MANIFESTS / "datasets.json")
    dataset_by_key = {
        (int(row["canonical_seed"]), row["condition"]): row
        for row in datasets["datasets"]
    }
    policies = read_json(MANIFESTS / "policies.json")
    by_key = {
        (int(row["canonical_seed"]), row["condition"]): row
        for row in policies["policies"]
    }
    created = 0
    for seed in SEEDS:
        training_seed = SEEDS[seed]["training"]
        for condition in NEW_CONDITIONS:
            dataset = dataset_by_key[(seed, condition)]
            config = json.loads(json.dumps(template))
            run_name = (
                f"composition_seed{seed}_source{training_seed}_{condition}"
            )
            output = CONFIGS / f"seed{seed}" / f"{condition}.json"
            config["experiment"]["name"] = run_name
            config["experiment"]["logging"]["log_wandb"] = True
            config["experiment"]["logging"]["wandb_proj_name"] = "TRO_MVP"
            config["experiment"]["save"]["enabled"] = True
            config["experiment"]["save"]["every_n_epochs"] = 20
            config["experiment"]["save"]["epochs"] = []
            config["experiment"]["save"]["on_best_validation"] = False
            config["experiment"]["save"]["on_best_rollout_return"] = False
            config["experiment"]["save"]["on_best_rollout_success_rate"] = False
            config["experiment"]["rollout"]["enabled"] = False
            config["train"]["data"][0]["path"] = dataset["hdf5_path"]
            config["train"]["output_dir"] = str(
                (MODEL_ROOT / f"seed{seed}" / condition).resolve()
            )
            config["train"]["num_epochs"] = 3000
            config["train"]["seed"] = training_seed
            write_frozen_json(output, config)
            row = by_key[(seed, condition)]
            row.update({
                "status": "config_frozen",
                "config_path": str(output.resolve()),
                "config_sha256": sha256(output),
                "source_artifact_path": str(output.resolve()),
                "source_artifact_sha256": sha256(output),
                "dataset_path": dataset["hdf5_path"],
                "dataset_sha256": dataset["hdf5_sha256"],
                "run_name": run_name, "wandb_project": "TRO_MVP",
            })
            created += 1
    if created != 20:
        raise AssertionError("Training config scope changed")
    policies["policies"] = [
        by_key[(seed, condition)]
        for condition in CONDITION_ORDER for seed in SEEDS
    ]
    write_json(MANIFESTS / "policies.json", policies)
    print("Created and froze exactly 20 composition training configs")


def find_single_run(seed, condition, run_name):
    root = MODEL_ROOT / f"seed{seed}" / condition / run_name
    bearing = [
        path for path in sorted(root.glob("*")) if path.is_dir()
        and list((path / "models").glob("model_epoch_*.pth"))
    ]
    if len(bearing) != 1:
        raise ValueError(
            f"seed{seed}/{condition}: expected one checkpoint-bearing run, "
            f"got {[str(path) for path in bearing]}"
        )
    return bearing[0]


def freeze_checkpoints(_args):
    audit_anchors()
    policies = read_json(MANIFESTS / "policies.json")
    by_key = {
        (int(row["canonical_seed"]), row["condition"]): row
        for row in policies["policies"]
    }
    output_rows = []
    for condition in CONDITION_ORDER:
        for seed in SEEDS:
            row = by_key[(seed, condition)]
            if row["reused_policy"]:
                path = Path(row["checkpoint_path"])
                if sha256(path) != row["checkpoint_sha256"]:
                    raise ValueError(f"Reused checkpoint changed: {path}")
                output_rows.append({
                    **row,
                    "selection_rule":
                        "reused pre-frozen accepted checkpoint; no retraining",
                })
                continue
            run_dir = find_single_run(seed, condition, row["run_name"])
            checkpoints = sorted(
                (run_dir / "models").glob("model_epoch_*.pth"),
                key=checkpoint_epoch,
            )
            inventory = [{
                "epoch": checkpoint_epoch(path), "path": str(path.resolve()),
                "sha256": sha256(path), "size_bytes": path.stat().st_size,
            } for path in checkpoints]
            if not inventory:
                raise FileNotFoundError(f"No checkpoints: {run_dir}")
            saved_config = run_dir / "config.json"
            saved = read_json(saved_config)
            if saved["train"]["data"][0]["path"] != row["dataset_path"]:
                raise ValueError("Saved training dataset differs from frozen config")
            if int(saved["train"]["seed"]) != SEEDS[seed]["training"]:
                raise ValueError("Saved training seed differs from protocol")
            selected = inventory[-1]
            row.update({
                "status": "checkpoint_frozen",
                "run_dir": str(run_dir.resolve()),
                "available_checkpoints": inventory,
                "selection_rule": "highest numeric emitted model_epoch_*.pth",
                "epoch": selected["epoch"],
                "checkpoint_path": selected["path"],
                "checkpoint_sha256": selected["sha256"],
                "checkpoint_size_bytes": selected["size_bytes"],
                "saved_config_path": str(saved_config.resolve()),
                "saved_config_sha256": sha256(saved_config),
            })
            output_rows.append(dict(row))
    if len(output_rows) != 45:
        raise AssertionError("Checkpoint matrix is not 45 slots")
    policies["policies"] = [
        by_key[(seed, condition)]
        for condition in CONDITION_ORDER for seed in SEEDS
    ]
    write_json(MANIFESTS / "policies.json", policies)
    unified = {
        "schema_version": 1,
        "manifest_type": "tro_stage2_composition_pre_rollout_checkpoints",
        "frozen_before_rollout": True,
        "condition_order": list(CONDITION_ORDER),
        "canonical_seeds": list(SEEDS),
        "selection_rule": "highest numeric emitted model_epoch_*.pth",
        "checkpoints": output_rows,
    }
    write_frozen_json(MANIFESTS / "checkpoints.json", unified)
    for seed in SEEDS:
        seed_rows = {
            row["condition"]: {
                **row,
                "path": row["checkpoint_path"],
                "sha256": row["checkpoint_sha256"],
            }
            for row in output_rows if int(row["canonical_seed"]) == seed
        }
        write_frozen_json(
            MANIFESTS / f"checkpoints_seed{seed}.json",
            {
                "schema_version": 1,
                "manifest_type": "tro_stage2_composition_checkpoint_view",
                "canonical_seed": seed,
                "condition_order": list(CONDITION_ORDER),
                "unified_checkpoint_manifest":
                    str((MANIFESTS / "checkpoints.json").resolve()),
                "unified_checkpoint_manifest_sha256":
                    sha256(MANIFESTS / "checkpoints.json"),
                "checkpoints": seed_rows,
            },
        )
    print("Frozen 45/45 checkpoints before any composition rollout")


def summary_path(surface, seed, rollout_seed, bank, condition):
    if surface == "common_absolute":
        if condition in NEW_CONDITIONS:
            root = (
                DATA_ROOT / "rollouts" / "common_absolute" / "formal"
                / f"seed{seed}" / f"rollout_seed{rollout_seed}" / bank
            )
        else:
            root = (
                AXIAL_DATA / "rollouts" / "formal" / f"seed{seed}"
                / f"rollout_seed{rollout_seed}" / bank
            )
    elif surface == "rmax40":
        if condition in NEW_CONDITIONS:
            root = (
                DATA_ROOT / "rollouts" / "rmax40" / "formal"
                / f"seed{seed}" / f"rollout_seed{rollout_seed}" / bank
            )
        else:
            root = (
                IDOOD_DATA / "rmax40" / "rollouts" / "formal"
                / f"seed{seed}" / f"rollout_seed{rollout_seed}" / bank
            )
    else:
        raise KeyError(surface)
    return root / f"spatial_{condition}_seed{rollout_seed}_n25.json"


def strict_merge(_args):
    checkpoints = read_json(MANIFESTS / "checkpoints.json")
    cp = {
        (int(row["canonical_seed"]), row["condition"]): row
        for row in checkpoints["checkpoints"]
    }
    reports = {}
    combined_index = {"schema_version": 1, "protocol_id": PROTOCOL_ID}
    for surface, banks in (
        ("common_absolute", ("inner", "outer")),
        ("rmax40", ("id", "ood")),
    ):
        source_summaries = []
        task_rows = []
        pairing = {}
        for seed in SEEDS:
            for rollout_seed in ROLLOUT_SEEDS:
                for bank in banks:
                    reference_specs = None
                    for condition in CONDITION_ORDER:
                        path = summary_path(
                            surface, seed, rollout_seed, bank, condition
                        )
                        if not path.is_file():
                            raise FileNotFoundError(path)
                        payload = read_json(path)
                        expected_cp = cp[(seed, condition)]
                        if payload["condition"] != condition:
                            raise ValueError(f"{path}: condition mismatch")
                        if payload["checkpoint"] != expected_cp["checkpoint_path"]:
                            raise ValueError(f"{path}: checkpoint path mismatch")
                        if (
                            payload["checkpoint_sha256"]
                            != expected_cp["checkpoint_sha256"]
                            or sha256(payload["checkpoint"])
                            != expected_cp["checkpoint_sha256"]
                        ):
                            raise ValueError(f"{path}: checkpoint hash mismatch")
                        rows = payload["rollouts"]
                        if (
                            payload["num_rollouts"] != 25
                            or len(rows) != 25
                            or [int(row["rollout_index"]) for row in rows]
                            != list(range(25))
                        ):
                            raise ValueError(f"{path}: incomplete rollout rows")
                        specs = [
                            (
                                row["state_id"], row["rng_seed"],
                                row["point_cloud_rng_seed"],
                                row["paired_spec"]["corridor_start"],
                            ) for row in rows
                        ]
                        if reference_specs is None:
                            reference_specs = specs
                        elif specs != reference_specs:
                            raise ValueError(
                                f"{surface}/seed{seed}/rollout{rollout_seed}/"
                                f"{bank}: nine-condition pairing mismatch"
                            )
                        source_summaries.append({
                            "canonical_seed": seed,
                            "rollout_seed": rollout_seed,
                            "bank": bank, "condition": condition,
                            "reused_anchor": condition not in NEW_CONDITIONS,
                            "path": str(path.resolve()),
                            "sha256": sha256(path),
                            "rows": 25,
                            "successes": int(payload["success_count"]),
                        })
                        task_rows.append({
                            "canonical_seed": seed,
                            "rollout_seed": rollout_seed,
                            "bank": bank, "condition": condition,
                            "summary_path": str(path.resolve()),
                            "summary_sha256": sha256(path),
                        })
                    pairing[
                        f"seed{seed}/rollout_seed{rollout_seed}/{bank}"
                    ] = True
        new = [row for row in source_summaries if not row["reused_anchor"]]
        old = [row for row in source_summaries if row["reused_anchor"]]
        report = {
            "schema_version": 1, "status": "valid",
            "surface": surface,
            "validated_tasks": len(source_summaries),
            "validated_rows": len(source_summaries) * 25,
            "policies": 45,
            "new_tasks": len(new), "new_rows": len(new) * 25,
            "reused_anchor_tasks": len(old),
            "reused_anchor_rows": len(old) * 25,
            "nine_condition_absolute_pairing": all(pairing.values()),
            "checkpoint_hashes": "revalidated",
            "large_rows_copied": False,
            "source_summaries": source_summaries,
        }
        if (
            report["validated_tasks"] != 450
            or report["validated_rows"] != 11250
            or report["new_tasks"] != 200
            or report["new_rows"] != 5000
            or report["reused_anchor_tasks"] != 250
        ):
            raise AssertionError(f"{surface}: strict coverage mismatch")
        reports[surface] = report
        combined_index[surface] = task_rows
        write_frozen_json(
            MANIFESTS / f"merge_validation_{surface}.json", report
        )
    write_frozen_json(MANIFESTS / "full_surface_index.json", combined_index)
    write_frozen_json(
        MANIFESTS / "merge_validation.json",
        {
            "schema_version": 1, "status": "valid",
            "new_tasks": 400, "new_rows": 10000,
            "full_common_absolute_tasks": 450,
            "full_common_absolute_rows": 11250,
            "full_rmax40_tasks": 450,
            "full_rmax40_rows": 11250,
            "common_absolute_report_sha256":
                sha256(MANIFESTS / "merge_validation_common_absolute.json"),
            "rmax40_report_sha256":
                sha256(MANIFESTS / "merge_validation_rmax40.json"),
            "large_rows_copied": False,
        },
    )
    print("Strict merge valid: 400/400 new tasks, 10,000/10,000 rows")


def record_job(args):
    path = MANIFESTS / "jobs.json"
    payload = read_json(path)
    row = {
        "phase": args.phase,
        "job_id": str(args.job_id),
        "dependency": args.dependency,
        "submission_command": args.submission_command,
        "identical_frozen_input_retry_of": args.retry_of,
        "status": args.status,
    }
    if any(
        old["job_id"] == row["job_id"] and old["phase"] == row["phase"]
        for old in payload["jobs"]
    ):
        raise ValueError(f"Job already recorded: {row['job_id']}")
    payload["jobs"].append(row)
    write_json(path, payload)
    print(json.dumps(row, indent=2))


def parse_args():
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("freeze-protocol").set_defaults(func=freeze_protocol)
    commands.add_parser("freeze-protocol-v2").set_defaults(
        func=freeze_protocol_v2
    )
    commands.add_parser("audit-feasibility").set_defaults(func=feasibility_audit)
    for name, func in (("collect", collect), ("validate-raw", validate_raw)):
        command = commands.add_parser(name)
        command.add_argument(
            "--canonical-seed", type=int, choices=tuple(SEEDS), required=True
        )
        command.add_argument("--target", type=int, choices=(1, 30), required=True)
        command.add_argument("--smoke", action="store_true")
        command.add_argument("--sample-hz", type=float, default=8.0)
        command.add_argument("--playback-speed", type=float, default=100.0)
        command.set_defaults(func=func)
    hdf5 = commands.add_parser("create-hdf5")
    hdf5.add_argument(
        "--canonical-seed", type=int, choices=tuple(SEEDS), required=True
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
    commands.add_parser("strict-merge").set_defaults(func=strict_merge)
    job = commands.add_parser("record-job")
    job.add_argument("--phase", required=True)
    job.add_argument("--job-id", required=True)
    job.add_argument("--dependency", default=None)
    job.add_argument("--submission-command", required=True)
    job.add_argument("--retry-of", default=None)
    job.add_argument("--status", default="submitted")
    job.set_defaults(func=record_job)
    return parser.parse_args()


def main():
    args = parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
