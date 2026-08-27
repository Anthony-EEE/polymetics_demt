#!/usr/bin/env python3
"""Freeze the authorised no-replacement Bimodal Left-Right pairing draw."""

from __future__ import annotations

import argparse
import random
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from common import (
    BIMODAL_ROOT,
    DESIGN_SEED,
    EXPECTED_PAIRS,
    LEFT_SOURCES,
    PAIRING_MANIFEST,
    PARTICIPANTS,
    RIGHT_SOURCES,
    SOURCE_SEED,
    TARGET_GROUP,
    TARGET_RAW_ROOT,
    canonical_hash,
    load_json,
    sha256_file,
    target_hdf5_manifest_path,
    target_hdf5_path,
    verify_frozen_inputs,
    write_json_atomic_exclusive,
)


def source_record(participant_id: str) -> dict:
    route = "L" if participant_id in LEFT_SOURCES else "R"
    raw_participant = TARGET_RAW_ROOT / participant_id
    summary_path = raw_participant / "summary.json"
    hdf5_path = target_hdf5_path(participant_id)
    hdf5_manifest_path = target_hdf5_manifest_path(participant_id)
    for path in (raw_participant, summary_path, hdf5_path, hdf5_manifest_path):
        if not path.exists():
            raise FileNotFoundError(path)
    conversion = load_json(hdf5_manifest_path)
    if (
        conversion.get("group") != TARGET_GROUP
        or conversion.get("participant_id") != participant_id
        or conversion.get("route") != route
        or conversion.get("trajectory_count") != 30
        or conversion.get("source_seed") != SOURCE_SEED
    ):
        raise ValueError(f"Invalid frozen Target HDF5 manifest for {participant_id}")
    actual_hdf5_hash = sha256_file(hdf5_path)
    if conversion.get("hdf5_sha256") != actual_hdf5_hash:
        raise ValueError(f"Target HDF5 hash mismatch for {participant_id}")
    raw_rows = conversion.get("raw_to_hdf5", [])
    if sorted(row.get("source_demo_index") for row in raw_rows) != list(range(30)):
        raise ValueError(f"Target provenance is incomplete for {participant_id}")
    demo_provenance = []
    for row in sorted(raw_rows, key=lambda item: item["source_demo_index"]):
        demo_index = int(row["source_demo_index"])
        raw_path = TARGET_RAW_ROOT / participant_id / f"demo_{demo_index}"
        result_path = TARGET_RAW_ROOT / participant_id / f"demo_{demo_index:02d}.json"
        metadata_path = raw_path / "metadata.json"
        if row.get("source_result_sha256") != sha256_file(result_path):
            raise ValueError(f"Result hash mismatch for {participant_id} demo {demo_index}")
        if row.get("source_metadata_sha256") != sha256_file(metadata_path):
            raise ValueError(f"Metadata hash mismatch for {participant_id} demo {demo_index}")
        demo_provenance.append(
            {
                "source_demo_index": demo_index,
                "source_raw_path": str(raw_path.resolve()),
                "source_result_path": str(result_path.resolve()),
                "source_metadata_sha256": row["source_metadata_sha256"],
                "source_result_sha256": row["source_result_sha256"],
                "source_attempt_index": int(row["source_attempt_index"]),
                "source_raw_frame_count": int(row["raw_frame_count"]),
                "source_trajectory_length": int(row["trajectory_length"]),
            }
        )
    first_result = load_json(TARGET_RAW_ROOT / participant_id / "demo_00.json")
    return {
        "participant_id": participant_id,
        "route": route,
        "personal_waypoint_center": first_result["spec"]["participant_waypoint_center"],
        "raw_participant_path": str(raw_participant.resolve()),
        "raw_summary": {
            "path": str(summary_path.resolve()),
            "sha256": sha256_file(summary_path),
        },
        "hdf5": {
            "path": str(hdf5_path.resolve()),
            "sha256": actual_hdf5_hash,
            "size_bytes": hdf5_path.stat().st_size,
        },
        "hdf5_conversion_manifest": {
            "path": str(hdf5_manifest_path.resolve()),
            "sha256": sha256_file(hdf5_manifest_path),
        },
        "demo_provenance": demo_provenance,
    }


def build_manifest() -> dict:
    frozen_inputs = verify_frozen_inputs()
    candidates = [(left, right) for left in LEFT_SOURCES for right in RIGHT_SOURCES]
    selected = random.Random(DESIGN_SEED).sample(candidates, 10)
    if selected != EXPECTED_PAIRS:
        raise RuntimeError(f"Frozen stdlib draw drifted: {selected!r}")
    if len(set(selected)) != 10:
        raise RuntimeError("Pair draw is not unique")
    sources_used = sorted({value for pair in selected for value in pair})
    source_records = {source: source_record(source) for source in sources_used}
    left_counts = Counter(left for left, _ in selected)
    right_counts = Counter(right for _, right in selected)
    pair_rows = []
    for participant_id, (left, right) in zip(PARTICIPANTS, selected):
        pair_rows.append(
            {
                "participant_id": participant_id,
                "left_source": left,
                "right_source": right,
                "left_route": source_records[left]["route"],
                "right_route": source_records[right]["route"],
                "left_center": source_records[left]["personal_waypoint_center"],
                "right_center": source_records[right]["personal_waypoint_center"],
            }
        )
    payload = {
        "schema_version": 1,
        "group": "simulation_bimodal_group",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "FROZEN_BEFORE_MIXED_VIEW_CREATION",
        "design": {
            "algorithm": "python_stdlib_random.Random(seed).sample(left_major_candidates, 10)",
            "python_random_seed": DESIGN_SEED,
            "candidate_order": [list(pair) for pair in candidates],
            "selected_order": [list(pair) for pair in selected],
            "unique_pairs_without_replacement": True,
            "source_participant_reuse_allowed": True,
            "outcome_dependent_redraw": False,
        },
        "participant_order": PARTICIPANTS,
        "pairs": pair_rows,
        "multiplicity": {
            "left_source_pair_counts": dict(sorted(left_counts.items())),
            "right_source_pair_counts": dict(sorted(right_counts.items())),
            "source_trajectory_memberships": {
                source: 30 * (left_counts[source] + right_counts[source]) for source in sources_used
            },
            "underlying_unique_target_trajectories": 30 * len(sources_used),
            "bimodal_trajectory_memberships": 600,
        },
        "source_participants": source_records,
        "frozen_inputs": frozen_inputs,
    }
    payload["canonical_content_sha256"] = canonical_hash(payload)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=PAIRING_MANIFEST)
    args = parser.parse_args()
    if args.output.resolve() != PAIRING_MANIFEST.resolve():
        raise ValueError(f"Formal output must be {PAIRING_MANIFEST}")
    BIMODAL_ROOT.mkdir(parents=True, exist_ok=True)
    manifest = build_manifest()
    write_json_atomic_exclusive(args.output, manifest)
    print(f"wrote={args.output} sha256={sha256_file(args.output)} pairs={len(manifest['pairs'])}")


if __name__ == "__main__":
    main()
