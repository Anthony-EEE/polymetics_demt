#!/usr/bin/env python3
"""Shared constants and fail-closed helpers for the isolated Bimodal pipeline."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


GROUP = "simulation_bimodal_group"
TARGET_GROUP = "simulation_target_group"
DESIGN_SEED = 20260807
SOURCE_SEED = 20260806
SPLIT_SEED = 20260807
ACTION_GAP = 2
NUM_POINTS = 10000
PARTICIPANTS = [f"B{index:02d}" for index in range(1, 11)]
LEFT_SOURCES = [f"T{index:02d}" for index in range(1, 6)]
RIGHT_SOURCES = [f"T{index:02d}" for index in range(6, 11)]
EXPECTED_PAIRS: List[Tuple[str, str]] = [
    ("T01", "T07"),
    ("T03", "T06"),
    ("T03", "T07"),
    ("T03", "T10"),
    ("T05", "T10"),
    ("T05", "T09"),
    ("T03", "T09"),
    ("T04", "T06"),
    ("T02", "T10"),
    ("T04", "T08"),
]

REPO = Path(__file__).resolve().parents[2]
TARGET_RAW_ROOT = (
    REPO
    / "rebuttal_dataset/simulation_target_group/full_seed20260806/"
    "protocol_release_z008_target_tol010_start_replenish"
)
TARGET_HDF5_ROOT = REPO / "rebuttal_dataset/simulation_target_group/hdf5"
TARGET_MODELS_ROOT = REPO / "rebuttal_dataset/simulation_target_group/models"
TARGET_ANALYSIS_ROOT = REPO / "rebuttal_dataset/simulation_target_group/analysis"
BIMODAL_ROOT = REPO / "rebuttal_dataset/simulation_bimodal_group"
PAIRING_MANIFEST = BIMODAL_ROOT / "pairing_manifest.json"
MIXED_ROOT = BIMODAL_ROOT / "mixed_raw"
HDF5_ROOT = BIMODAL_ROOT / "hdf5"

FROZEN_INPUTS: Dict[str, Tuple[Path, str]] = {
    "target_hdf5_validation": (
        TARGET_HDF5_ROOT / "validation_report.json",
        "44ad0c763badba8e41d56d1093989629fb88186ada225bbb267d35a87df20099",
    ),
    "target_training_manifest": (
        TARGET_MODELS_ROOT / "training_experiment_manifest.json",
        "610caef20d78f441df533aa2b1951029006cdf7b1d5aabf37c8bb1fdde8a5623",
    ),
    "target_selected_checkpoints": (
        TARGET_MODELS_ROOT / "selected_checkpoints_manifest.json",
        "a06b1784234ef4f6e07f23b16fc82781e95c29a83553474b8bccf15ba870ea93",
    ),
    "target_paired_rollout_specs": (
        TARGET_ANALYSIS_ROOT / "paired_rollout_specs.json",
        "10dbbe16da06b4013899e350fece05687abc8c45471b584ac5a2473a0e486dad",
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


def target_hdf5_path(participant_id: str) -> Path:
    return TARGET_HDF5_ROOT / (
        f"{TARGET_GROUP}_{participant_id}_d30_seed{SOURCE_SEED}_gap{ACTION_GAP}.hdf5"
    )


def target_hdf5_manifest_path(participant_id: str) -> Path:
    return target_hdf5_path(participant_id).with_suffix(".manifest.json")


def expected_pair_rows() -> List[Dict[str, Any]]:
    return [
        {
            "participant_id": participant_id,
            "left_source": pair[0],
            "right_source": pair[1],
        }
        for participant_id, pair in zip(PARTICIPANTS, EXPECTED_PAIRS)
    ]


def assert_within(path: Path, root: Path) -> Path:
    resolved = Path(path).resolve(strict=True)
    root_resolved = Path(root).resolve(strict=True)
    if resolved != root_resolved and root_resolved not in resolved.parents:
        raise ValueError(f"Resolved path escapes frozen root: {path} -> {resolved}")
    return resolved


def decode_rows(values: Iterable[Any]) -> List[str]:
    return [value.decode("utf-8") if isinstance(value, bytes) else str(value) for value in values]

