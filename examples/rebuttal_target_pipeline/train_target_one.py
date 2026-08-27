#!/usr/bin/env python3
"""Run and post-check one frozen Target participant training configuration."""

import argparse
import hashlib
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


GROUP = "simulation_target_group"
TRAIN_ENTRYPOINT = Path(
    "/users/k23114984/code/arcap_policy/STEP2_train_policy/robomimic/scripts/train.py"
)
PYTHON = Path("/scratch/users/k23114984/conda/arcap/bin/python")
NONFINITE = re.compile(r"(?<![A-Za-z0-9_])(?:nan|[-+]?inf(?:inity)?)(?![A-Za-z0-9_])", re.I)
INFRASTRUCTURE_FAILURE_SIGNATURES = (
    "CUDA error: uncorrectable ECC error encountered",
    "CUDA error: all CUDA-capable devices are busy or unavailable",
)


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json_exclusive(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=2, sort_keys=True)
        stream.write("\n")


def frozen_config_is_subset(frozen, saved):
    """Robomimic expands external configs with defaults before saving them."""
    if isinstance(frozen, dict):
        return isinstance(saved, dict) and all(
            key in saved and frozen_config_is_subset(value, saved[key])
            for key, value in frozen.items()
        )
    if isinstance(frozen, list):
        return isinstance(saved, list) and len(frozen) == len(saved) and all(
            frozen_config_is_subset(left, right) for left, right in zip(frozen, saved)
        )
    return frozen == saved


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--participant", required=True, choices=[f"T{i:02d}" for i in range(1, 11)])
    parser.add_argument("--models-root", type=Path, required=True)
    parser.add_argument("--python", type=Path, default=PYTHON)
    parser.add_argument("--train-entrypoint", type=Path, default=TRAIN_ENTRYPOINT)
    parser.add_argument(
        "--infrastructure-retry-index",
        type=int,
        default=0,
        help="Retry a preserved infrastructure-only failure with the exact frozen config",
    )
    args = parser.parse_args()

    models_root = args.models_root.resolve()
    participant = args.participant
    config_path = models_root / "configs" / f"{participant}.json"
    frozen_manifest_path = models_root / "training_experiment_manifest.json"
    retry_index = args.infrastructure_retry_index
    if retry_index < 0:
        raise ValueError("Infrastructure retry index cannot be negative")
    status_name = (
        f"{participant}.json"
        if retry_index == 0
        else f"{participant}.infra_retry_{retry_index}.json"
    )
    status_path = models_root / "status" / status_name
    for required in (args.python, args.train_entrypoint, config_path, frozen_manifest_path):
        if not required.is_file():
            raise FileNotFoundError(required)
    if status_path.exists():
        raise FileExistsError(f"Refusing to overwrite training status: {status_path}")
    config = json.loads(config_path.read_text(encoding="utf-8"))
    manifest = json.loads(frozen_manifest_path.read_text(encoding="utf-8"))
    expected = manifest["configs"][participant]
    if sha256(config_path) != expected["sha256"]:
        raise ValueError(f"Frozen config hash mismatch for {participant}")
    if config["train"]["num_epochs"] != 40 or config["train"]["seed"] != 1:
        raise ValueError("Training budget or seed differs from the frozen protocol")
    experiment_name = config["experiment"]["name"]
    experiment_root = Path(config["train"]["output_dir"]) / experiment_name
    existing_run_dirs = (
        sorted(path for path in experiment_root.iterdir() if path.is_dir())
        if experiment_root.is_dir()
        else []
    )
    retry_evidence = None
    if retry_index == 0 and experiment_root.exists():
        raise FileExistsError(f"Refusing to overwrite/re-enter experiment root: {experiment_root}")
    if retry_index > 0:
        prior_status_paths = [
            models_root / "status" / f"{participant}.json",
            *(
                models_root / "status" / f"{participant}.infra_retry_{index}.json"
                for index in range(1, retry_index)
            ),
        ]
        prior_statuses = []
        for prior_status_path in prior_status_paths:
            if not prior_status_path.is_file():
                raise FileNotFoundError(prior_status_path)
            prior_status = json.loads(prior_status_path.read_text(encoding="utf-8"))
            if (
                prior_status.get("participant_id") != participant
                or prior_status.get("passed_postcheck")
                or prior_status.get("checkpoint") is not None
                or prior_status.get("config", {}).get("sha256") != expected["sha256"]
            ):
                raise ValueError(f"Prior status is not an eligible failed attempt: {prior_status_path}")
            prior_statuses.append(prior_status)
        original_status = prior_statuses[0]
        original_log = original_status.get("log") or {}
        original_log_path = Path(original_log.get("path", ""))
        if not original_log_path.is_file() or sha256(original_log_path) != original_log.get("sha256"):
            raise ValueError(f"Original failure log is missing or changed: {original_log_path}")
        original_log_text = original_log_path.read_text(encoding="utf-8", errors="replace")
        matched_signature = next(
            (value for value in INFRASTRUCTURE_FAILURE_SIGNATURES if value in original_log_text),
            None,
        )
        if matched_signature is None:
            raise ValueError(f"Original failure is not allowlisted infrastructure: {prior_status_paths[0]}")
        for prior_status_path, prior_status in zip(prior_status_paths[1:], prior_statuses[1:]):
            if prior_status.get("attempt_kind") != "infrastructure_retry":
                raise ValueError(f"Intermediate retry status has wrong kind: {prior_status_path}")
            if prior_status.get("infrastructure_retry", {}).get("matched_signature") != matched_signature:
                raise ValueError(f"Intermediate retry lost original failure provenance: {prior_status_path}")
        if not existing_run_dirs:
            raise ValueError(f"Prior infrastructure failure run is missing: {experiment_root}")
        retry_evidence = {
            "retry_index": retry_index,
            "prior_status_path": str(prior_status_paths[-1]),
            "prior_status_sha256": sha256(prior_status_paths[-1]),
            "original_failure_status_path": str(prior_status_paths[0]),
            "original_failure_status_sha256": sha256(prior_status_paths[0]),
            "original_failure_log_path": str(original_log_path),
            "original_failure_log_sha256": original_log["sha256"],
            "preserved_prior_attempts": [
                {"path": str(path), "sha256": sha256(path)} for path in prior_status_paths
            ],
            "matched_signature": matched_signature,
            "frozen_config_reused_byte_for_byte": True,
            "existing_output_prompt_response": "n (preserve parent and add timestamp)",
        }

    started_at = datetime.now(timezone.utc).isoformat()
    command = [str(args.python), str(args.train_entrypoint), "--config", str(config_path)]
    if retry_index > 0:
        completed = subprocess.run(command, check=False, input="n\n", text=True)
    else:
        completed = subprocess.run(command, check=False)
    all_run_dirs = sorted(path for path in experiment_root.iterdir() if path.is_dir()) if experiment_root.is_dir() else []
    previous_run_dir_set = {path.resolve() for path in existing_run_dirs}
    run_dirs = [path for path in all_run_dirs if path.resolve() not in previous_run_dir_set]
    errors = []
    if completed.returncode != 0:
        errors.append(f"subprocess_exit_code:{completed.returncode}")
    if len(run_dirs) != 1:
        errors.append(f"expected_one_run_dir_found:{len(run_dirs)}")
    run_dir = run_dirs[0] if len(run_dirs) == 1 else None
    checkpoint = run_dir / "models" / "model_epoch_40.pth" if run_dir else None
    log_path = run_dir / "logs" / "log.txt" if run_dir else None
    run_config = run_dir / "config.json" if run_dir else None
    if checkpoint is None or not checkpoint.is_file() or checkpoint.stat().st_size == 0:
        errors.append("missing_or_empty_epoch40_checkpoint")
    if log_path is None or not log_path.is_file() or log_path.stat().st_size == 0:
        errors.append("missing_or_empty_training_log")
        log_text = ""
    else:
        log_text = log_path.read_text(encoding="utf-8", errors="replace")
        if "Training completed all 40 epochs." not in log_text:
            errors.append("missing_all_40_epochs_completion_marker")
        if "finished run successfully!" not in log_text:
            errors.append("missing_entrypoint_success_marker")
        match = NONFINITE.search(log_text)
        if match:
            errors.append(f"nonfinite_token_in_training_log:{match.group(0)}")
    if run_config is None or not run_config.is_file():
        errors.append("missing_saved_run_config")
    elif not frozen_config_is_subset(
        config, json.loads(run_config.read_text(encoding="utf-8"))
    ):
        errors.append("saved_run_config_does_not_contain_frozen_config")
    status = {
        "schema_version": 1,
        "group": GROUP,
        "participant_id": participant,
        "started_at_utc": started_at,
        "finished_at_utc": datetime.now(timezone.utc).isoformat(),
        "slurm": {
            "job_id": os.environ.get("SLURM_JOB_ID"),
            "array_job_id": os.environ.get("SLURM_ARRAY_JOB_ID"),
            "array_task_id": os.environ.get("SLURM_ARRAY_TASK_ID"),
            "node_list": os.environ.get("SLURM_NODELIST"),
        },
        "subprocess_exit_code": completed.returncode,
        "attempt_kind": "formal" if retry_index == 0 else "infrastructure_retry",
        "infrastructure_retry": retry_evidence,
        "passed_postcheck": not errors,
        "errors": errors,
        "config": {"path": str(config_path), "sha256": sha256(config_path)},
        "run_dir": str(run_dir) if run_dir else None,
        "log": {"path": str(log_path), "sha256": sha256(log_path)} if log_path and log_path.is_file() else None,
        "checkpoint": (
            {"path": str(checkpoint), "sha256": sha256(checkpoint), "selected_epoch": 40}
            if checkpoint and checkpoint.is_file()
            else None
        ),
    }
    write_json_exclusive(status_path, status)
    print(json.dumps(status, indent=2, sort_keys=True))
    raise SystemExit(0 if not errors else 1)


if __name__ == "__main__":
    main()
