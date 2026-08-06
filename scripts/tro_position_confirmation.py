#!/usr/bin/env python3
"""Prepare and freeze the single-block T-RO Position confirmation experiment."""

import argparse
import hashlib
import json
import os
import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT_ROOT = (
    PROJECT_ROOT / "experiments" / "mvp0_position_event" / "confirmation_earlystop"
)
CONFIG_ROOT = EXPERIMENT_ROOT / "configs" / "training"
MANIFEST_ROOT = EXPERIMENT_ROOT / "manifests"
ROLLOUT_MANIFEST_ROOT = MANIFEST_ROOT / "rollout_5seed"
SOURCE_ROLLOUT_MANIFEST_ROOT = (
    PROJECT_ROOT
    / "experiments"
    / "mvp0_position_event"
    / "manifests"
    / "rollout_5seed"
)
SOURCE_CONFIG_ROOT = (
    PROJECT_ROOT
    / "experiments"
    / "mvp0_position_event"
    / "configs"
    / "training_generated"
    / "block0"
)
MODEL_ROOT = PROJECT_ROOT.parent / "trained_models" / "tro_position_confirmation"
DATA_ROOT = PROJECT_ROOT / "dataset" / "tro_position_mvp0" / "block0" / "hdf5"
LEGACY_BASELINE_DATA = (
    PROJECT_ROOT
    / "dataset"
    / "ar_guidance_spatial_S15_S35"
    / "spatial_S25_d30_seed1_2gap.hdf5"
)
LEGACY_BASELINE_CHECKPOINT = (
    PROJECT_ROOT.parent
    / "trained_models"
    / "ar_guidance_spatial_S15_S35"
    / "S25"
    / "spatial_S25_d30_seed1_2gap"
    / "20260704004132"
    / "models"
    / "model_epoch_80.pth"
)
LEGACY_BASELINE_HASH = (
    "e666ab6a53f87f8d0f2e0a5ba29bd34b28cc39930d57cc848abfa5745465d60f"
)
TRAINED_CONDITIONS = (
    "START15_APP6",
    "START35_APP6",
    "START25_APP3P6",
    "START25_APP8P4",
)
CONDITION_ORDER = (
    "START15_APP6",
    "START35_APP6",
    "START25_APP3P6",
    "START25_APP6",
    "START25_APP8P4",
)
TRAINING_SEED = 2701
WANDB_PROJECT = "TRO_MVP"
CHECKPOINT_RE = re.compile(r"model_epoch_(\d+)\.pth$")


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


def checkpoint_epoch(path):
    match = CHECKPOINT_RE.fullmatch(Path(path).name)
    if match is None:
        raise ValueError(f"Cannot parse checkpoint epoch: {path}")
    return int(match.group(1))


def source_dataset(condition):
    return DATA_ROOT / f"{condition}_b0_d30_2gap.hdf5"


def create_configs(_args):
    CONFIG_ROOT.mkdir(parents=True, exist_ok=True)
    configs = {}
    for condition in TRAINED_CONDITIONS:
        source_config = SOURCE_CONFIG_ROOT / f"{condition}.json"
        dataset = source_dataset(condition)
        if not source_config.is_file():
            raise FileNotFoundError(source_config)
        if not dataset.is_file():
            raise FileNotFoundError(dataset)
        config = read_json(source_config)
        run_name = f"tro_pos_confirm_{condition}_d30_seed{TRAINING_SEED}_2gap"
        config["experiment"]["name"] = run_name
        config["experiment"]["logging"]["log_wandb"] = True
        config["experiment"]["logging"]["wandb_proj_name"] = WANDB_PROJECT
        config["experiment"]["save"]["enabled"] = True
        config["experiment"]["save"]["every_n_epochs"] = 20
        config["experiment"]["save"]["epochs"] = []
        config["experiment"]["save"]["on_best_validation"] = False
        config["experiment"]["save"]["on_best_rollout_return"] = False
        config["experiment"]["save"]["on_best_rollout_success_rate"] = False
        config["train"]["data"][0]["path"] = str(dataset.resolve())
        config["train"]["output_dir"] = str((MODEL_ROOT / condition).resolve())
        config["train"]["num_epochs"] = 3000
        config["train"]["seed"] = TRAINING_SEED
        output = CONFIG_ROOT / f"{condition}.json"
        write_json(output, config)
        configs[condition] = {
            "path": str(output.resolve()),
            "sha256": sha256(output),
            "source_config": str(source_config.resolve()),
            "source_dataset": str(dataset.resolve()),
        }

    baseline_hash = sha256(LEGACY_BASELINE_CHECKPOINT)
    if baseline_hash != LEGACY_BASELINE_HASH:
        raise ValueError(
            f"Legacy START25_APP6 checkpoint hash mismatch: {baseline_hash}"
        )
    protocol = {
        "schema_version": 1,
        "experiment": "tro_position_confirmation_earlystop",
        "condition_order": list(CONDITION_ORDER),
        "new_training_conditions": list(TRAINED_CONDITIONS),
        "baseline_condition": "START25_APP6",
        "source_dataset_block": 0,
        "source_dataset_block_role": "pre_registered_mandatory_primary_block",
        "data_collection_performed": False,
        "hdf5_rebuild_performed": False,
        "training_seed": TRAINING_SEED,
        "training": {
            "from_scratch": True,
            "strict_epoch40_resume_supported": False,
            "strict_epoch40_resume_reason": (
                "existing checkpoints contain model/config/shape/normalization "
                "only; optimizer, scheduler, epoch, best validation loss and "
                "early-stop patience state are absent"
            ),
            "max_epochs": 3000,
            "early_stopping": "repository train.py fixed patience=41",
            "checkpoint_interval_epochs": 20,
            "checkpoint_selection": (
                "highest numeric model_epoch_*.pth emitted by each run, frozen "
                "before rollout inspection"
            ),
            "wandb_project": WANDB_PROJECT,
        },
        "baseline": {
            "source_alias": "legacy S25",
            "radii_m": {"start": 0.25, "approach": 0.060},
            "dataset_path": str(LEGACY_BASELINE_DATA.resolve()),
            "checkpoint_path": str(LEGACY_BASELINE_CHECKPOINT.resolve()),
            "checkpoint_epoch": 80,
            "checkpoint_sha256": baseline_hash,
            "retraining_required": False,
        },
        "configs": configs,
    }
    rollout_manifests = {}
    for seed in (628, 629, 630, 631, 632):
        for bank in ("inner", "outer"):
            bank_id = f"tro_pos_seed{seed}_{bank}_n25_v1"
            source = SOURCE_ROLLOUT_MANIFEST_ROOT / f"{bank_id}.json"
            manifest = read_json(source)
            source_hash = sha256(source)
            manifest["condition_order"] = list(CONDITION_ORDER)
            manifest["confirmation_reuse"] = {
                "source_manifest_path": str(source.resolve()),
                "source_manifest_sha256": source_hash,
                "state_and_rng_records_unchanged": True,
                "only_condition_order_extended": True,
            }
            output = ROLLOUT_MANIFEST_ROOT / f"{bank_id}.json"
            write_json(output, manifest)
            rollout_manifests[bank_id] = {
                "path": str(output.resolve()),
                "sha256": sha256(output),
                "source_path": str(source.resolve()),
                "source_sha256": source_hash,
            }
    protocol["rollout_manifests"] = rollout_manifests
    write_json(MANIFEST_ROOT / "protocol.json", protocol)
    print(f"Wrote {len(configs)} configs with W&B project {WANDB_PROJECT}")
    print(f"Protocol: {MANIFEST_ROOT / 'protocol.json'}")


def find_single_run(condition):
    condition_root = MODEL_ROOT / condition
    run_name = f"tro_pos_confirm_{condition}_d30_seed{TRAINING_SEED}_2gap"
    experiment_root = condition_root / run_name
    run_dirs = sorted(path for path in experiment_root.glob("*") if path.is_dir())
    with_checkpoints = [
        path
        for path in run_dirs
        if list((path / "models").glob("model_epoch_*.pth"))
    ]
    if len(with_checkpoints) != 1:
        raise ValueError(
            f"Expected exactly one checkpoint-bearing run for {condition}, got "
            f"{[str(path) for path in with_checkpoints]}"
        )
    return with_checkpoints[0]


def freeze_checkpoints(_args):
    protocol_path = MANIFEST_ROOT / "protocol.json"
    protocol = read_json(protocol_path)
    checkpoints = {}
    for condition in TRAINED_CONDITIONS:
        run_dir = find_single_run(condition)
        candidates = sorted(
            (run_dir / "models").glob("model_epoch_*.pth"),
            key=checkpoint_epoch,
        )
        available = [
            {
                "epoch": checkpoint_epoch(path),
                "path": str(path.resolve()),
                "sha256": sha256(path),
                "size_bytes": path.stat().st_size,
            }
            for path in candidates
        ]
        selected = available[-1]
        saved_config = read_json(run_dir / "config.json")
        if (
            saved_config["experiment"]["logging"]["wandb_proj_name"]
            != WANDB_PROJECT
        ):
            raise ValueError(f"{condition}: saved W&B project is not {WANDB_PROJECT}")
        checkpoints[condition] = {
            "condition": condition,
            "source": "new_from_scratch_early_stopping_training",
            "training_seed": TRAINING_SEED,
            "run_dir": str(run_dir.resolve()),
            "selection_rule": "highest numeric emitted model_epoch_*.pth",
            "available_checkpoints": available,
            **selected,
        }

    baseline_hash = sha256(LEGACY_BASELINE_CHECKPOINT)
    if baseline_hash != LEGACY_BASELINE_HASH:
        raise ValueError(
            f"Legacy START25_APP6 checkpoint hash mismatch: {baseline_hash}"
        )
    checkpoints["START25_APP6"] = {
        "condition": "START25_APP6",
        "source": "reused_legacy_S25_early_stopped_baseline",
        "training_seed": 1,
        "epoch": 80,
        "path": str(LEGACY_BASELINE_CHECKPOINT.resolve()),
        "sha256": baseline_hash,
        "size_bytes": LEGACY_BASELINE_CHECKPOINT.stat().st_size,
        "selection_rule": (
            "highest numeric checkpoint already emitted by the accepted legacy "
            "S25 early-stopping run"
        ),
        "retraining_performed": False,
    }
    payload = {
        "schema_version": 1,
        "manifest_type": "tro_position_confirmation_frozen_checkpoints",
        "condition_order": list(CONDITION_ORDER),
        "training_conditions": list(TRAINED_CONDITIONS),
        "baseline_condition": "START25_APP6",
        "wandb_project": WANDB_PROJECT,
        "protocol_path": str(protocol_path.resolve()),
        "protocol_sha256": sha256(protocol_path),
        "git_commit": os.popen(
            f"git -C {PROJECT_ROOT} rev-parse HEAD"
        ).read().strip(),
        "checkpoints": {
            condition: checkpoints[condition] for condition in CONDITION_ORDER
        },
    }
    output = MANIFEST_ROOT / "checkpoints.json"
    write_json(output, payload)
    print(f"Frozen five-condition checkpoint manifest: {output}")


def parse_args():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("create-configs").set_defaults(func=create_configs)
    subparsers.add_parser("freeze-checkpoints").set_defaults(
        func=freeze_checkpoints
    )
    return parser.parse_args()


def main():
    args = parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
