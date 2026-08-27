#!/usr/bin/env python3
"""Validate ten frozen Bimodal checkpoints and run load/inference smokes."""

import argparse
import hashlib
import json
import random
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import h5py
import numpy as np


GROUP = "simulation_bimodal_group"
PARTICIPANTS = [f"B{index:02d}" for index in range(1, 11)]
ARCAP_ROOT = Path("/users/k23114984/code/arcap_policy/STEP2_train_policy")
NONFINITE = re.compile(r"(?<![A-Za-z0-9_])(?:nan|[-+]?inf(?:inity)?)(?![A-Za-z0-9_])", re.I)
INFRASTRUCTURE_FAILURE_SIGNATURES = (
    "CUDA error: uncorrectable ECC error encountered",
    "CUDA error: all CUDA-capable devices are busy or unavailable",
)
EXPECTED_PROMPT_RETRY_ERRORS = {
    "expected_one_run_dir_found:0",
    "missing_or_empty_epoch40_checkpoint",
    "missing_or_empty_training_log",
    "missing_saved_run_config",
}


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


def set_seeds(seed):
    np.random.seed(seed)
    random.seed(seed)
    import torch

    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def inference_smoke(checkpoint, hdf5_path, cuda):
    if str(ARCAP_ROOT) not in sys.path:
        sys.path.insert(0, str(ARCAP_ROOT))
    import robomimic.utils.file_utils as FileUtils
    import robomimic.utils.torch_utils as TorchUtils

    device = TorchUtils.get_torch_device(try_to_use_cuda=bool(cuda))
    policy, _ = FileUtils.policy_from_checkpoint(
        ckpt_path=str(checkpoint), device=device, verbose=False
    )
    horizon = int(policy.policy.global_config.algo.horizon.observation_horizon)
    with h5py.File(hdf5_path, "r") as source:
        demo = source["data/demo_0/obs"]
        observation = {
            key: np.repeat(np.asarray(demo[key][0], dtype=np.float32)[None], horizon, axis=0)
            for key in ("robot0_arm_joints", "robot0_hand_joints", "pointcloud")
        }
    set_seeds(1)
    policy.start_episode()
    action = np.asarray(policy(ob=observation), dtype=float).reshape(-1)
    if action.shape != (8,) or not np.isfinite(action).all():
        raise ValueError(f"Invalid inference action shape/value: {action.shape}")
    return {"device": str(device), "observation_horizon": horizon, "action_shape": [8]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models-root", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--cuda", action="store_true")
    args = parser.parse_args()
    models_root = args.models_root.resolve()
    output = args.output or models_root / "model_validation_report.json"
    selected_manifest_path = models_root / "selected_checkpoints_manifest.json"
    if output.exists() or selected_manifest_path.exists():
        raise FileExistsError("Refusing to overwrite model validation or checkpoint manifest")
    frozen_path = models_root / "training_experiment_manifest.json"
    frozen = json.loads(frozen_path.read_text(encoding="utf-8"))
    errors = []
    records = {}
    for participant in PARTICIPANTS:
        try:
            base_status_path = models_root / "status" / f"{participant}.json"
            retry_status_paths = sorted(
                (models_root / "status").glob(f"{participant}.infra_retry_*.json"),
                key=lambda path: int(path.stem.rsplit("_", 1)[-1]),
            )
            status_paths = [base_status_path, *retry_status_paths]
            statuses = [json.loads(path.read_text(encoding="utf-8")) for path in status_paths]
            if any(row.get("participant_id") != participant for row in statuses):
                raise ValueError("participant training status identity mismatch")
            passed_indices = [index for index, row in enumerate(statuses) if row.get("passed_postcheck")]
            if len(passed_indices) != 1 or passed_indices[0] != len(statuses) - 1:
                raise ValueError("expected exactly one final passed training status")
            failure_attempts = []
            for status_path, failed_status in zip(status_paths[:-1], statuses[:-1]):
                if failed_status.get("checkpoint") is not None:
                    raise ValueError("failed infrastructure attempt unexpectedly has a checkpoint")
                failed_log = failed_status.get("log") or {}
                failed_log_path = Path(failed_log.get("path", ""))
                if failed_log_path.is_file():
                    if sha256(failed_log_path) != failed_log.get("sha256"):
                        raise ValueError("failed infrastructure log changed")
                    failed_log_text = failed_log_path.read_text(encoding="utf-8", errors="replace")
                    signature = next(
                        (value for value in INFRASTRUCTURE_FAILURE_SIGNATURES if value in failed_log_text),
                        None,
                    )
                    failure_kind = "gpu_infrastructure"
                    log_record = {
                        "log_path": str(failed_log_path.resolve()),
                        "log_sha256": failed_log["sha256"],
                    }
                elif (
                    failed_status.get("attempt_kind") == "infrastructure_retry"
                    and set(failed_status.get("errors", [])) == EXPECTED_PROMPT_RETRY_ERRORS
                    and failed_status.get("infrastructure_retry", {}).get("matched_signature")
                    in INFRASTRUCTURE_FAILURE_SIGNATURES
                ):
                    signature = "upstream_existing_output_prompt_eof_before_training"
                    failure_kind = "retry_orchestration"
                    log_record = {"log_path": None, "log_sha256": None}
                else:
                    raise ValueError("failed infrastructure attempt lacks auditable evidence")
                if signature is None:
                    raise ValueError("failed training attempt is not an allowlisted infrastructure failure")
                failure_attempts.append(
                    {
                        "status_path": str(status_path.resolve()),
                        "status_sha256": sha256(status_path),
                        **log_record,
                        "failure_kind": failure_kind,
                        "matched_signature": signature,
                        "slurm": failed_status.get("slurm"),
                    }
                )
            status_path = status_paths[-1]
            status = statuses[-1]
            config_record = frozen["configs"][participant]
            config_path = Path(config_record["path"])
            config_hash = sha256(config_path)
            if config_hash != config_record["sha256"]:
                raise ValueError("frozen participant config hash changed")
            if (
                Path(status["config"]["path"]).resolve() != config_path.resolve()
                or status["config"]["sha256"] != config_record["sha256"]
            ):
                raise ValueError("training status config identity/hash mismatch")
            checkpoint = Path(status["checkpoint"]["path"])
            log_path = Path(status["log"]["path"])
            if checkpoint.name != "model_epoch_40.pth":
                raise ValueError("selected checkpoint is not exact epoch 40")
            checkpoint_hash = sha256(checkpoint)
            if checkpoint_hash != status["checkpoint"]["sha256"]:
                raise ValueError("checkpoint hash changed after training postcheck")
            log_hash = sha256(log_path)
            if log_hash != status["log"]["sha256"]:
                raise ValueError("training log hash changed after postcheck")
            log_text = log_path.read_text(encoding="utf-8", errors="replace")
            if NONFINITE.search(log_text):
                raise ValueError("training log contains a non-finite token")
            hdf5_record = frozen["source_hdf5"][participant]
            hdf5_path = Path(hdf5_record["path"])
            hdf5_hash = sha256(hdf5_path)
            if hdf5_hash != hdf5_record["sha256"]:
                raise ValueError("source HDF5 hash changed")
            smoke = inference_smoke(checkpoint, hdf5_path, args.cuda)
            records[participant] = {
                "participant_id": participant,
                "checkpoint": str(checkpoint.resolve()),
                "sha256": checkpoint_hash,
                "selected_epoch": 40,
                "source_hdf5": str(hdf5_path.resolve()),
                "source_hdf5_sha256": hdf5_hash,
                "config": str(config_path.resolve()),
                "config_sha256": config_hash,
                "uniform_training_protocol_sha256": frozen["uniform_training_protocol_sha256"],
                "selected_training_status": str(status_path.resolve()),
                "selected_training_status_sha256": sha256(status_path),
                "preserved_infrastructure_failures": failure_attempts,
                "inference_smoke": smoke,
            }
        except Exception as exc:
            errors.append(f"{participant}:{type(exc).__name__}:{exc}")
    report = {
        "schema_version": 1,
        "group": GROUP,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "passed": not errors and len(records) == 10,
        "errors": errors,
        "checkpoint_count": len(records),
        "training_experiment_manifest": str(frozen_path.resolve()),
        "training_experiment_manifest_sha256": sha256(frozen_path),
        "participants": records,
    }
    write_json_exclusive(output, report)
    if report["passed"]:
        selected = {
            "schema_version": 1,
            "group": GROUP,
            "participant_order": PARTICIPANTS,
            "selection_rule": frozen["checkpoint_selection_rule"],
            "uniform_training_protocol_sha256": frozen["uniform_training_protocol_sha256"],
            "checkpoints": records,
            "model_validation_report": str(Path(output).resolve()),
            "model_validation_report_sha256": sha256(output),
        }
        write_json_exclusive(selected_manifest_path, selected)
    print(json.dumps({"passed": report["passed"], "checkpoint_count": len(records), "errors": errors}, indent=2))
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
