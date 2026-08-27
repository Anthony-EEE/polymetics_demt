#!/usr/bin/env python3
"""Shared constants and fail-closed helpers for Control-derived Bimodal."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


GROUP = "simulation_control_bimodal_group"
CONTROL_GROUP = "simulation_control_group"
BIMODAL_GROUP = "simulation_bimodal_group"
TARGET_GROUP = "simulation_target_group"
DESIGN_SEED = 20260807
SOURCE_SEED = 20260806
SPLIT_SEED = 20260807
ACTION_GAP = 2
NUM_POINTS = 10000
PARTICIPANTS = [f"CB{index:02d}" for index in range(1, 11)]
MATCHED_BIMODAL_PARTICIPANTS = [f"B{index:02d}" for index in range(1, 11)]
LEFT_SOURCES = [f"C{index:02d}" for index in range(1, 6)]
RIGHT_SOURCES = [f"C{index:02d}" for index in range(6, 11)]
EXPECTED_PAIRS: List[Tuple[str, str]] = [
    ("C01", "C07"),
    ("C03", "C06"),
    ("C03", "C07"),
    ("C03", "C10"),
    ("C05", "C10"),
    ("C05", "C09"),
    ("C03", "C09"),
    ("C04", "C06"),
    ("C02", "C10"),
    ("C04", "C08"),
]
EXPECTED_NORMALIZED_TRAINING_PROTOCOL_SHA256 = (
    "6c309f4330939e5dede194de669bae3ea167e2978262de906ff970f5a18fd77d"
)

REPO = Path(__file__).resolve().parents[2]
CONTROL_RAW_ROOT = (
    REPO
    / "rebuttal_dataset/simulation_control_group/full_seed20260806/"
    "protocol_release_z008_target_tol010_start_replenish"
)
CONTROL_HDF5_ROOT = REPO / "rebuttal_dataset/simulation_control_group/hdf5"
CONTROL_MODELS_ROOT = REPO / "rebuttal_dataset/simulation_control_group/models"
CONTROL_ANALYSIS_ROOT = REPO / "rebuttal_dataset/simulation_control_group/analysis"
BIMODAL_ROOT = REPO / "rebuttal_dataset/simulation_bimodal_group"
BIMODAL_HDF5_ROOT = BIMODAL_ROOT / "hdf5"
BIMODAL_MODELS_ROOT = BIMODAL_ROOT / "models"
BIMODAL_ANALYSIS_ROOT = BIMODAL_ROOT / "analysis"
TARGET_ANALYSIS_ROOT = REPO / "rebuttal_dataset/simulation_target_group/analysis"
CONTROL_BIMODAL_ROOT = REPO / "rebuttal_dataset/simulation_control_bimodal_group"
PAIRING_MANIFEST = CONTROL_BIMODAL_ROOT / "pairing_manifest.json"
MIXED_ROOT = CONTROL_BIMODAL_ROOT / "mixed_raw"
HDF5_ROOT = CONTROL_BIMODAL_ROOT / "hdf5"

FROZEN_INPUTS: Dict[str, Tuple[Path, str]] = {
    "control_raw_validation": (
        CONTROL_RAW_ROOT / "validation_report.json",
        "bd36e47329a55957e688c40ac4c8d65385e0af62a62fcb025d0c228a24be33fc",
    ),
    "control_hdf5_validation": (
        CONTROL_HDF5_ROOT / "validation_report.json",
        "c617bed5ded688a1ecf7a949a401f3bfff16ed450e247aece23e4962c3eb5de5",
    ),
    "control_training_manifest": (
        CONTROL_MODELS_ROOT / "training_experiment_manifest.json",
        "422f1e9a31067a28ab8f4b1633fd7b487c47d3c51ed411e1d248d5e1f0a8f4a8",
    ),
    "control_model_validation": (
        CONTROL_MODELS_ROOT / "model_validation_report.json",
        "c00c49cf164f9ba21a06efa284fa2f34070ae94a747f32bbf98644bd010641bf",
    ),
    "control_selected_checkpoints": (
        CONTROL_MODELS_ROOT / "selected_checkpoints_manifest.json",
        "666e3cb0ff6a0ed7430183d4344e99b629ca545d8140d0359752750c3d51a9e6",
    ),
    "control_final_results": (
        CONTROL_ANALYSIS_ROOT / "final_results.json",
        "cd90fd780fe373d3db6747d084f961ce4c220fcda2ff83e7a2df00c4ce810915",
    ),
    "control_final_validation": (
        CONTROL_ANALYSIS_ROOT / "validation_report.json",
        "6287daf48d3c42f03649321104fefb527191c99baef296b508c370089df9e97f",
    ),
    "target_paired_rollout_specs": (
        TARGET_ANALYSIS_ROOT / "paired_rollout_specs.json",
        "10dbbe16da06b4013899e350fece05687abc8c45471b584ac5a2473a0e486dad",
    ),
    "bimodal_pairing_manifest": (
        BIMODAL_ROOT / "pairing_manifest.json",
        "a6a5198ca147744e5e82d030ed145e50a8e70296e6e40f341f6a97024766fadb",
    ),
    "bimodal_hdf5_validation": (
        BIMODAL_HDF5_ROOT / "validation_report.json",
        "9674e71e7904a370e71a73ec3231af6a4bcf09437179b446b31f6d7e0a4b0047",
    ),
    "bimodal_training_manifest": (
        BIMODAL_MODELS_ROOT / "training_experiment_manifest.json",
        "76da91cbfb5089acc75e218d751ee55773adde3b4569ab8b609e252f6158f3fd",
    ),
    "bimodal_model_validation": (
        BIMODAL_MODELS_ROOT / "model_validation_report.json",
        "5490809c6e11d0918ecf0c00e7979260065c0a691417636ce79fe34c70e06ca1",
    ),
    "bimodal_selected_checkpoints": (
        BIMODAL_MODELS_ROOT / "selected_checkpoints_manifest.json",
        "e05318ebb92b0863287d41b1d899f5ec3731053c29a7698ac8c62431d2ad544b",
    ),
    "bimodal_final_results": (
        BIMODAL_ANALYSIS_ROOT / "final_results.json",
        "d64c223e1a2dde25f9469b9d159316063e6df31a32c5de5bd34f18ba591f3795",
    ),
    "bimodal_final_validation": (
        BIMODAL_ANALYSIS_ROOT / "validation_report.json",
        "4c30d414c65c9eb263328ed3e99b65af67be243ec2bc0ae33b2cb936bf68bdf2",
    ),
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def load_json(path: Path) -> Any:
    with Path(path).open("r", encoding="utf-8") as stream:
        return json.load(stream)


def write_json_atomic_exclusive(path: Path, payload: Any) -> None:
    """Write JSON through a process-specific temp file, refusing replacement."""

    path = Path(path)
    if path.exists() or path.is_symlink():
        raise FileExistsError(f"Refusing to overwrite formal output: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.inprogress.{os.getpid()}")
    if temporary.exists() or temporary.is_symlink():
        raise FileExistsError(f"Stale temporary output exists: {temporary}")
    try:
        with temporary.open("x", encoding="utf-8") as stream:
            json.dump(payload, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        if path.exists() or path.is_symlink():
            raise FileExistsError(f"Output appeared during creation: {path}")
        os.replace(temporary, path)
    except Exception:
        if temporary.exists():
            temporary.unlink()
        raise


def verify_frozen_inputs() -> Dict[str, Dict[str, Any]]:
    rows: Dict[str, Dict[str, Any]] = {}
    for name, (path, expected) in FROZEN_INPUTS.items():
        if not path.is_file():
            raise FileNotFoundError(path)
        actual = sha256_file(path)
        if actual != expected:
            raise ValueError(f"Frozen input hash mismatch for {name}: {actual} != {expected}")
        rows[name] = {
            "path": str(path.resolve()),
            "sha256": actual,
            "size_bytes": path.stat().st_size,
        }
    return rows


def control_hdf5_path(participant_id: str) -> Path:
    return CONTROL_HDF5_ROOT / (
        f"{CONTROL_GROUP}_{participant_id}_d30_seed{SOURCE_SEED}_gap{ACTION_GAP}.hdf5"
    )


def control_hdf5_manifest_path(participant_id: str) -> Path:
    return control_hdf5_path(participant_id).with_suffix(".manifest.json")


def expected_pair_rows() -> List[Dict[str, Any]]:
    return [
        {
            "participant_id": participant_id,
            "left_source": pair[0],
            "right_source": pair[1],
            "matched_bimodal_participant": matched,
        }
        for participant_id, pair, matched in zip(
            PARTICIPANTS, EXPECTED_PAIRS, MATCHED_BIMODAL_PARTICIPANTS
        )
    ]


def assert_within(path: Path, root: Path) -> Path:
    resolved = Path(path).resolve(strict=True)
    root_resolved = Path(root).resolve(strict=True)
    if resolved != root_resolved and root_resolved not in resolved.parents:
        raise ValueError(f"Resolved path escapes frozen root: {path} -> {resolved}")
    return resolved


def decode_rows(values: Iterable[Any]) -> List[str]:
    return [value.decode("utf-8") if isinstance(value, bytes) else str(value) for value in values]
