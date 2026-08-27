#!/usr/bin/env python3
"""Freeze the uniform Target participant-policy training protocol.

This helper is intentionally preparation-only: it refuses to create configs
until all ten validated participant HDF5 files exist, and it never launches a
training job. Participant-specific config differences are limited to the
dataset path and experiment name.
"""

import argparse
import copy
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


GROUP = "simulation_target_group"
PARTICIPANTS = [f"T{index:02d}" for index in range(1, 11)]
TRAINING_SEED = 1
NUM_EPOCHS = 40
STEPS_PER_EPOCH = 250
VALIDATION_STEPS_PER_EPOCH = 50
SELECTED_EPOCH = 40
TEMPLATE = Path(
    "/users/k23114984/code/arcap_policy/STEP2_train_policy/robomimic/"
    "training_config/sim_test_00.json"
)
TRAIN_ENTRYPOINT = Path(
    "/users/k23114984/code/arcap_policy/STEP2_train_policy/robomimic/scripts/train.py"
)


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(payload):
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def load_json(path):
    with Path(path).open("r", encoding="utf-8") as stream:
        return json.load(stream)


def write_json_exclusive(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=2, sort_keys=True)
        stream.write("\n")


def git_state(repo):
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=str(repo), check=True, text=True, capture_output=True
    ).stdout.strip()
    branch = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=str(repo),
        check=True,
        text=True,
        capture_output=True,
    ).stdout.strip()
    status = subprocess.run(
        ["git", "status", "--porcelain=v1", "--untracked-files=no"],
        cwd=str(repo),
        check=True,
        text=True,
        capture_output=True,
    ).stdout.splitlines()
    return {
        "head": head,
        "branch": branch,
        "tracked_porcelain_v1": status,
        "tracked_dirty": bool(status),
        "untracked_files_excluded_from_status_snapshot": True,
    }


def freeze_config(template, participant_id, hdf5_path, runs_root):
    config = copy.deepcopy(template)
    config["experiment"]["name"] = f"{GROUP}_{participant_id}_seed{TRAINING_SEED}_epoch{NUM_EPOCHS}"
    config["experiment"]["validate"] = True
    config["experiment"]["logging"].update(
        {
            "terminal_output_to_txt": True,
            "log_tb": False,
            "log_wandb": False,
            "wandb_proj_name": "rebuttal",
        }
    )
    config["experiment"]["save"].update(
        {
            "enabled": True,
            "every_n_seconds": None,
            "every_n_epochs": 20,
            "epochs": [],
            "on_best_validation": False,
            "on_best_rollout_return": False,
            "on_best_rollout_success_rate": False,
        }
    )
    config["experiment"]["epoch_every_n_steps"] = STEPS_PER_EPOCH
    config["experiment"]["validation_epoch_every_n_steps"] = VALIDATION_STEPS_PER_EPOCH
    config["experiment"]["render"] = False
    config["experiment"]["render_video"] = False
    config["experiment"]["keep_all_videos"] = False
    config["experiment"]["rollout"]["enabled"] = False
    config["train"]["data"] = [{"path": str(hdf5_path.resolve())}]
    config["train"]["output_dir"] = str(runs_root.resolve())
    config["train"]["num_epochs"] = NUM_EPOCHS
    config["train"]["seed"] = TRAINING_SEED
    config["train"]["cuda"] = True
    config["train"]["batch_size"] = 16
    config["train"]["num_data_workers"] = 2
    return config


def canonical_protocol(config):
    value = copy.deepcopy(config)
    value["experiment"]["name"] = "<PARTICIPANT_EXPERIMENT_NAME>"
    value["train"]["data"] = [{"path": "<PARTICIPANT_HDF5>"}]
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--hdf5-root", type=Path, required=True)
    parser.add_argument("--models-root", type=Path, required=True)
    parser.add_argument("--template", type=Path, default=TEMPLATE)
    parser.add_argument("--train-entrypoint", type=Path, default=TRAIN_ENTRYPOINT)
    args = parser.parse_args()

    repo = args.repo.resolve()
    hdf5_root = args.hdf5_root.resolve()
    models_root = args.models_root.resolve()
    configs_root = models_root / "configs"
    runs_root = models_root / "runs"
    slurm_logs_root = models_root / "slurm_logs"
    manifest_path = models_root / "training_experiment_manifest.json"
    validation_path = hdf5_root / "validation_report.json"

    for required in (args.template, args.train_entrypoint, validation_path):
        if not required.is_file():
            raise FileNotFoundError(required)
    validation = load_json(validation_path)
    if validation.get("group") != GROUP or not validation.get("passed"):
        raise ValueError(f"HDF5 validation report is not a passed {GROUP} report: {validation_path}")
    if validation.get("counts", {}).get("participant_hdf5") != 10:
        raise ValueError("HDF5 validation did not cover exactly ten participants")
    if validation.get("counts", {}).get("trajectories") != 300:
        raise ValueError("HDF5 validation did not cover exactly 300 trajectories")
    if manifest_path.exists() or configs_root.exists() or runs_root.exists() or slurm_logs_root.exists():
        raise FileExistsError(
            "Refusing to overwrite an existing training preparation or run root: "
            f"manifest={manifest_path.exists()} configs={configs_root.exists()} "
            f"runs={runs_root.exists()} slurm_logs={slurm_logs_root.exists()}"
        )

    template = load_json(args.template)
    if template.get("algo_name") != "diffusion_policy":
        raise ValueError("Expected the established diffusion_policy template")
    if template.get("train", {}).get("seq_length") != 20:
        raise ValueError("Established template seq_length drifted from 20")
    if template.get("algo", {}).get("horizon") != {
        "observation_horizon": 7,
        "action_horizon": 10,
        "prediction_horizon": 20,
    }:
        raise ValueError("Established diffusion-policy horizon configuration drifted")

    validated_hdf5 = {}
    for participant_id in PARTICIPANTS:
        hdf5_path = hdf5_root / f"{GROUP}_{participant_id}_d30_seed20260806_gap2.hdf5"
        if not hdf5_path.is_file():
            raise FileNotFoundError(hdf5_path)
        expected_hdf5_hash = validation["participant_reports"][participant_id]["sha256"]
        actual_hdf5_hash = sha256(hdf5_path)
        if actual_hdf5_hash != expected_hdf5_hash:
            raise ValueError(f"HDF5 hash changed after validation for {participant_id}")
        validated_hdf5[participant_id] = (hdf5_path, actual_hdf5_hash)

    configs_root.mkdir(parents=True, exist_ok=False)
    hdf5_rows = {}
    config_rows = {}
    protocol_hashes = set()
    for participant_id in PARTICIPANTS:
        hdf5_path, actual_hdf5_hash = validated_hdf5[participant_id]
        config = freeze_config(template, participant_id, hdf5_path, runs_root)
        protocol_hash = canonical_hash(canonical_protocol(config))
        protocol_hashes.add(protocol_hash)
        config_path = configs_root / f"{participant_id}.json"
        write_json_exclusive(config_path, config)
        hdf5_rows[participant_id] = {
            "path": str(hdf5_path),
            "sha256": actual_hdf5_hash,
            "trajectory_count": 30,
        }
        config_rows[participant_id] = {
            "path": str(config_path.resolve()),
            "sha256": sha256(config_path),
            "experiment_name": config["experiment"]["name"],
            "canonical_training_protocol_sha256": protocol_hash,
        }
    if len(protocol_hashes) != 1:
        raise RuntimeError(f"Participant training protocols differ: {sorted(protocol_hashes)}")

    manifest = {
        "schema_version": 1,
        "group": GROUP,
        "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "FROZEN_BEFORE_FORMAL_TRAINING",
        "participant_order": PARTICIPANTS,
        "checkpoint_selection_rule": {
            "rule": "select exact model_epoch_40.pth",
            "selected_epoch": SELECTED_EPOCH,
            "uses_validation_loss": False,
            "uses_training_loss": False,
            "uses_policy_rollout_performance": False,
            "participant_specific_tuning": False,
        },
        "training_budget": {
            "epochs": NUM_EPOCHS,
            "steps_per_epoch": STEPS_PER_EPOCH,
            "optimizer_steps": NUM_EPOCHS * STEPS_PER_EPOCH,
            "validation_steps_per_epoch": VALIDATION_STEPS_PER_EPOCH,
            "batch_size": 16,
            "training_seed": TRAINING_SEED,
        },
        "learner": {
            "algo_name": "diffusion_policy",
            "architecture": template["algo"],
            "observation_schema": template["observation"],
            "action_schema": {
                "keys": template["train"]["action_keys"],
                "config": template["train"]["action_config"],
            },
        },
        "uniform_training_protocol_sha256": next(iter(protocol_hashes)),
        "configs": config_rows,
        "source_hdf5": hdf5_rows,
        "hdf5_validation_report": {
            "path": str(validation_path),
            "sha256": sha256(validation_path),
        },
        "software": {
            "repository": str(repo),
            "git": git_state(repo),
            "template": {"path": str(args.template.resolve()), "sha256": sha256(args.template)},
            "train_entrypoint": {
                "path": str(args.train_entrypoint.resolve()),
                "sha256": sha256(args.train_entrypoint),
                "exception_exit_caveat": (
                    "entrypoint catches training exceptions; Target runner additionally validates completion artifacts"
                ),
                "hardcoded_early_stop_patience": 41,
                "early_stop_cannot_trigger_before_frozen_epoch_40_budget": True,
            },
        },
    }
    write_json_exclusive(manifest_path, manifest)
    runs_root.mkdir(parents=True, exist_ok=False)
    slurm_logs_root.mkdir(parents=True, exist_ok=False)
    print(json.dumps({"manifest": str(manifest_path), "protocol_sha256": next(iter(protocol_hashes))}, indent=2))


if __name__ == "__main__":
    main()
