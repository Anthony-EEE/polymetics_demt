#!/usr/bin/env python3
"""Archive a proven failed Bimodal HDF5 attempt without deleting evidence."""

from __future__ import annotations

import argparse
import os
from datetime import datetime, timezone
from pathlib import Path

import h5py
import numpy as np

from common import (
    BIMODAL_ROOT,
    DESIGN_SEED,
    GROUP,
    HDF5_ROOT,
    canonical_hash,
    load_json,
    sha256_file,
    write_json_atomic_exclusive,
)


EXPECTED_ERRORS = {
    "B10:invalid_sidecar_identity_or_hash",
    "B10:demo_10:source_payload_mismatch:obs/pointcloud",
    "B10:demo_10:source_payload_mismatch:obs/robot0_arm_joints",
    "B10:demo_10:source_payload_mismatch:obs/robot0_hand_joints",
    "B10:mean_init_arm_mismatch",
    "B10:mean_init_hand_mismatch",
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attempt-index", type=int, default=1)
    args = parser.parse_args()
    validation_path = HDF5_ROOT / "validation_report.json"
    if not validation_path.is_file():
        raise FileNotFoundError(validation_path)
    report = load_json(validation_path)
    if (
        report.get("group") != GROUP
        or report.get("passed") is not False
        or set(report.get("errors", [])) != EXPECTED_ERRORS
        or report.get("counts", {}).get("participant_hdf5") != 10
        or report.get("counts", {}).get("trajectory_memberships") != 600
        or report.get("counts", {}).get("loader_smokes") != 0
        or report.get("counts", {}).get("partial_roots") != 0
        or report.get("counts", {}).get("zero_byte_files") != 0
        or report.get("counts", {}).get("unexpected_files") != 0
    ):
        raise ValueError("Failed validation does not match the reviewed recoverable attempt")

    b10 = HDF5_ROOT / f"{GROUP}_B10_d60_seed{DESIGN_SEED}_gap2.hdf5"
    b10_sidecar = b10.with_suffix(".manifest.json")
    sidecar = load_json(b10_sidecar)
    if sidecar.get("hdf5_sha256") == sha256_file(b10):
        raise ValueError("B10 no longer demonstrates the recorded post-build hash mismatch")
    source_row = sidecar["raw_to_hdf5"][10]
    with h5py.File(b10, "r") as destination, h5py.File(source_row["source_hdf5_path"], "r") as source:
        destination_demo = destination["data/demo_10"]
        source_demo = source[f"data/demo_{source_row['source_demo_index']}"]
        if np.count_nonzero(destination_demo["obs/robot0_arm_joints"][:]) != 0:
            raise ValueError("Reviewed B10 arm-observation all-zero signature changed")
        if np.count_nonzero(destination_demo["obs/robot0_hand_joints"][:]) != 0:
            raise ValueError("Reviewed B10 hand-observation all-zero signature changed")
        if np.array_equal(
            destination_demo["obs/pointcloud"][:], source_demo["obs/pointcloud"][:]
        ):
            raise ValueError("Reviewed B10 point-cloud mismatch disappeared")

    diagnostics_root = BIMODAL_ROOT / "diagnostics"
    archive = diagnostics_root / f"hdf5_attempt_{args.attempt_index}_failed"
    decision_path = diagnostics_root / f"hdf5_attempt_{args.attempt_index}_recovery.json"
    if archive.exists() or decision_path.exists():
        raise FileExistsError(f"Recovery evidence already exists: {archive} / {decision_path}")
    diagnostics_root.mkdir(parents=True, exist_ok=True)
    failed_validation_hash = sha256_file(validation_path)
    os.replace(HDF5_ROOT, archive)
    decision = {
        "schema_version": 1,
        "group": GROUP,
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "attempt_index": args.attempt_index,
        "classification": "pre-training HDF5 payload-integrity failure",
        "cause": "not established; source remained frozen and only B10/demo_10 observations drifted",
        "scientific_data_consumed": False,
        "training_started": False,
        "failed_root_archive": str(archive.resolve()),
        "failed_validation_report": str((archive / "validation_report.json").resolve()),
        "failed_validation_report_sha256": failed_validation_hash,
        "reviewed_errors": sorted(EXPECTED_ERRORS),
        "recovery": (
            "preserve the entire failed root; strengthen builder with closed-file source equality; "
            "deterministically rebuild all ten from unchanged pairing and mixture manifests"
        ),
    }
    decision["canonical_content_sha256"] = canonical_hash(decision)
    write_json_atomic_exclusive(decision_path, decision)
    print(f"archived={archive} decision={decision_path}")


if __name__ == "__main__":
    main()
