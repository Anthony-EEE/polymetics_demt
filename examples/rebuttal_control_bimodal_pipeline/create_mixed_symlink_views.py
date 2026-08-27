#!/usr/bin/env python3
"""Create ten deterministic, fully shuffled 30L+30R relative-symlink views."""

from __future__ import annotations

import argparse
import os
import random
from datetime import datetime, timezone
from pathlib import Path

from common import (
    DESIGN_SEED,
    EXPECTED_PAIRS,
    GROUP,
    MIXED_ROOT,
    PAIRING_MANIFEST,
    PARTICIPANTS,
    REPO,
    CONTROL_RAW_ROOT,
    canonical_hash,
    load_json,
    sha256_file,
    verify_frozen_inputs,
    write_json_atomic_exclusive,
)


def validate_pairing(pairing: dict) -> None:
    expected_rows = [
        {"participant_id": participant, "left_source": left, "right_source": right}
        for participant, (left, right) in zip(PARTICIPANTS, EXPECTED_PAIRS)
    ]
    actual_rows = [
        {
            "participant_id": row.get("participant_id"),
            "left_source": row.get("left_source"),
            "right_source": row.get("right_source"),
        }
        for row in pairing.get("pairs", [])
    ]
    if pairing.get("group") != GROUP or actual_rows != expected_rows:
        raise ValueError("Pairing manifest differs from the frozen authorised design")
    content = dict(pairing)
    recorded = content.pop("canonical_content_sha256", None)
    if recorded != canonical_hash(content):
        raise ValueError("Pairing manifest canonical hash is invalid")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pairing", type=Path, default=PAIRING_MANIFEST)
    parser.add_argument("--output-root", type=Path, default=MIXED_ROOT)
    args = parser.parse_args()
    if args.output_root.resolve() != MIXED_ROOT.resolve():
        raise ValueError(f"Formal mixed root must be {MIXED_ROOT}")
    if args.output_root.exists() or args.output_root.is_symlink():
        raise FileExistsError(f"Refusing to overwrite mixed view root: {args.output_root}")
    verify_frozen_inputs()
    pairing = load_json(args.pairing)
    validate_pairing(pairing)
    source_records = pairing["source_participants"]
    pair_lookup = {row["participant_id"]: row for row in pairing["pairs"]}
    temporary = args.output_root.with_name(f"{args.output_root.name}.inprogress.{os.getpid()}")
    if temporary.exists() or temporary.is_symlink():
        raise FileExistsError(f"Stale temporary mixed root exists: {temporary}")
    temporary.mkdir(parents=True, exist_ok=False)
    try:
        for b_index, participant_id in enumerate(PARTICIPANTS, start=1):
            pair = pair_lookup[participant_id]
            items = [
                {"route": route, "source_participant_id": source, "source_demo_index": demo}
                for route, source in (("L", pair["left_source"]), ("R", pair["right_source"]))
                for demo in range(30)
            ]
            shuffle_seed = DESIGN_SEED + 1000 + b_index
            random.Random(shuffle_seed).shuffle(items)
            participant_root = temporary / participant_id
            participant_root.mkdir()
            mappings = []
            for mixed_index, item in enumerate(items):
                source = item["source_participant_id"]
                demo_index = item["source_demo_index"]
                provenance = source_records[source]["demo_provenance"][demo_index]
                source_raw = Path(provenance["source_raw_path"])
                source_result = Path(provenance["source_result_path"])
                raw_link = participant_root / f"demo_{mixed_index}"
                result_link = participant_root / f"demo_{mixed_index:02d}.json"
                raw_relative = os.path.relpath(source_raw, participant_root)
                result_relative = os.path.relpath(source_result, participant_root)
                if Path(raw_relative).is_absolute() or Path(result_relative).is_absolute():
                    raise RuntimeError("Relative-link construction unexpectedly produced an absolute path")
                raw_link.symlink_to(raw_relative, target_is_directory=True)
                result_link.symlink_to(result_relative)
                mappings.append(
                    {
                        "mixed_demo_index": mixed_index,
                        "route": item["route"],
                        "source_group": "simulation_control_group",
                        "source_participant_id": source,
                        "source_demo_index": demo_index,
                        "source_attempt_index": provenance["source_attempt_index"],
                        "source_raw_path": str(source_raw.resolve()),
                        "source_result_path": str(source_result.resolve()),
                        "raw_link_target": raw_relative,
                        "result_link_target": result_relative,
                        "source_raw_metadata_sha256": provenance["source_metadata_sha256"],
                        "source_result_sha256": provenance["source_result_sha256"],
                        "source_hdf5_path": source_records[source]["hdf5"]["path"],
                        "source_hdf5_sha256": source_records[source]["hdf5"]["sha256"],
                        "source_hdf5_demo": f"data/demo_{demo_index}",
                    }
                )
            manifest = {
                "schema_version": 1,
                "group": GROUP,
                "participant_id": participant_id,
                "created_at_utc": datetime.now(timezone.utc).isoformat(),
                "pairing_manifest": str(args.pairing.resolve()),
                "pairing_manifest_sha256": sha256_file(args.pairing),
                "left_source": pair["left_source"],
                "right_source": pair["right_source"],
                "shuffle": {
                    "algorithm": "python_stdlib_random.Random(seed).shuffle(left_0_29_then_right_0_29)",
                    "seed": shuffle_seed,
                    "alternation_or_run_constraint": False,
                },
                "counts": {"total": 60, "L": 30, "R": 30},
                "mappings": mappings,
            }
            manifest["canonical_content_sha256"] = canonical_hash(manifest)
            write_json_atomic_exclusive(participant_root / "mixture_manifest.json", manifest)
        if args.output_root.exists() or args.output_root.is_symlink():
            raise FileExistsError(f"Mixed root appeared during creation: {args.output_root}")
        os.replace(temporary, args.output_root)
    except Exception:
        # Preserve a non-empty temporary tree for diagnosis; formal root is never partial.
        raise
    print(f"wrote={args.output_root} participants=10 symlinks=1200")


if __name__ == "__main__":
    main()

