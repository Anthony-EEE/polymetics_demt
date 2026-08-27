#!/usr/bin/env python3
"""Independently validate all Bimodal symlink views against frozen Target data."""

from __future__ import annotations

import argparse
import os
import random
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from common import (
    BIMODAL_ROOT,
    DESIGN_SEED,
    EXPECTED_PAIRS,
    GROUP,
    MIXED_ROOT,
    PAIRING_MANIFEST,
    PARTICIPANTS,
    TARGET_GROUP,
    TARGET_RAW_ROOT,
    assert_within,
    canonical_hash,
    load_json,
    sha256_file,
    verify_frozen_inputs,
    write_json_atomic_exclusive,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mixed-root", type=Path, default=MIXED_ROOT)
    parser.add_argument("--pairing", type=Path, default=PAIRING_MANIFEST)
    parser.add_argument(
        "--output", type=Path, default=BIMODAL_ROOT / "mixed_raw_validation_report.json"
    )
    args = parser.parse_args()
    if args.mixed_root.resolve() != MIXED_ROOT.resolve():
        raise ValueError(f"Formal mixed root must be {MIXED_ROOT}")
    frozen_inputs = verify_frozen_inputs()
    pairing = load_json(args.pairing)
    errors = []
    reports = {}
    expected_pair_lookup = {
        participant: pair for participant, pair in zip(PARTICIPANTS, EXPECTED_PAIRS)
    }
    if pairing.get("group") != GROUP:
        errors.append("pairing_wrong_group")
    pairing_content = dict(pairing)
    pairing_hash = pairing_content.pop("canonical_content_sha256", None)
    if pairing_hash != canonical_hash(pairing_content):
        errors.append("pairing_canonical_hash_mismatch")
    source_records = pairing.get("source_participants", {})
    expected_participant_dirs = set(PARTICIPANTS)
    actual_participant_dirs = {p.name for p in args.mixed_root.iterdir() if p.is_dir()}
    if actual_participant_dirs != expected_participant_dirs:
        errors.append(
            f"participant_directories_mismatch:{sorted(actual_participant_dirs)}"
        )

    for b_index, participant_id in enumerate(PARTICIPANTS, start=1):
        participant_errors = []
        root = args.mixed_root / participant_id
        manifest_path = root / "mixture_manifest.json"
        if not manifest_path.is_file() or manifest_path.stat().st_size == 0:
            errors.append(f"{participant_id}:missing_or_empty_manifest")
            continue
        manifest = load_json(manifest_path)
        content = dict(manifest)
        recorded_canonical = content.pop("canonical_content_sha256", None)
        if recorded_canonical != canonical_hash(content):
            participant_errors.append("canonical_hash_mismatch")
        left_source, right_source = expected_pair_lookup[participant_id]
        if (
            manifest.get("group") != GROUP
            or manifest.get("participant_id") != participant_id
            or manifest.get("left_source") != left_source
            or manifest.get("right_source") != right_source
            or manifest.get("pairing_manifest_sha256") != sha256_file(args.pairing)
        ):
            participant_errors.append("identity_or_pairing_mismatch")
        expected_items = [
            {"route": route, "source_participant_id": source, "source_demo_index": demo}
            for route, source in (("L", left_source), ("R", right_source))
            for demo in range(30)
        ]
        expected_seed = DESIGN_SEED + 1000 + b_index
        random.Random(expected_seed).shuffle(expected_items)
        mappings = manifest.get("mappings", [])
        if len(mappings) != 60:
            participant_errors.append(f"mapping_count:{len(mappings)}")
        route_counts = Counter()
        source_demo_keys = []
        for mixed_index in range(60):
            raw_link = root / f"demo_{mixed_index}"
            result_link = root / f"demo_{mixed_index:02d}.json"
            if not raw_link.is_symlink() or not result_link.is_symlink():
                participant_errors.append(f"{mixed_index}:missing_symlink")
                continue
            raw_target_text = os.readlink(raw_link)
            result_target_text = os.readlink(result_link)
            if Path(raw_target_text).is_absolute() or Path(result_target_text).is_absolute():
                participant_errors.append(f"{mixed_index}:absolute_symlink")
                continue
            try:
                raw_resolved = assert_within(raw_link, TARGET_RAW_ROOT)
                result_resolved = assert_within(result_link, TARGET_RAW_ROOT)
            except Exception as exc:
                participant_errors.append(f"{mixed_index}:invalid_resolved_target:{exc}")
                continue
            if not raw_resolved.is_dir() or not result_resolved.is_file():
                participant_errors.append(f"{mixed_index}:broken_target")
                continue
            if mixed_index >= len(mappings):
                continue
            row = mappings[mixed_index]
            expected = expected_items[mixed_index]
            actual_key = {
                "route": row.get("route"),
                "source_participant_id": row.get("source_participant_id"),
                "source_demo_index": row.get("source_demo_index"),
            }
            if row.get("mixed_demo_index") != mixed_index or actual_key != expected:
                participant_errors.append(f"{mixed_index}:shuffle_replay_mismatch")
            source = expected["source_participant_id"]
            demo = expected["source_demo_index"]
            expected_raw = TARGET_RAW_ROOT / source / f"demo_{demo}"
            expected_result = TARGET_RAW_ROOT / source / f"demo_{demo:02d}.json"
            if raw_resolved != expected_raw.resolve() or result_resolved != expected_result.resolve():
                participant_errors.append(f"{mixed_index}:resolved_path_mismatch")
            result = load_json(result_resolved)
            metadata = load_json(raw_resolved / "metadata.json")
            if (
                result.get("group") != TARGET_GROUP
                or result.get("participant_id") != source
                or result.get("demo_index") != demo
                or result.get("condition") != expected["route"]
                or result.get("success") is not True
                or result.get("details", {}).get("success", {}).get("success") is not True
                or metadata.get("first_saved_phase") != "policy_inference_start"
                or metadata.get("scripted_setup_saved") is not False
            ):
                participant_errors.append(f"{mixed_index}:invalid_target_success_metadata")
            provenance = source_records[source]["demo_provenance"][demo]
            if (
                sha256_file(result_resolved) != row.get("source_result_sha256")
                or row.get("source_result_sha256") != provenance["source_result_sha256"]
                or sha256_file(raw_resolved / "metadata.json")
                != row.get("source_raw_metadata_sha256")
                or row.get("source_raw_metadata_sha256")
                != provenance["source_metadata_sha256"]
            ):
                participant_errors.append(f"{mixed_index}:source_hash_mismatch")
            route_counts[expected["route"]] += 1
            source_demo_keys.append((source, demo))
        expected_names = {
            "mixture_manifest.json",
            *(f"demo_{index}" for index in range(60)),
            *(f"demo_{index:02d}.json" for index in range(60)),
        }
        actual_names = {entry.name for entry in root.iterdir()}
        if actual_names != expected_names:
            participant_errors.append(f"unexpected_or_missing_entries:{sorted(actual_names ^ expected_names)}")
        if route_counts != Counter({"L": 30, "R": 30}):
            participant_errors.append(f"route_counts:{dict(route_counts)}")
        if len(source_demo_keys) != 60 or len(set(source_demo_keys)) != 60:
            participant_errors.append("duplicated_or_missing_source_demo")
        for source in (left_source, right_source):
            demos = sorted(demo for participant, demo in source_demo_keys if participant == source)
            if demos != list(range(30)):
                participant_errors.append(f"{source}:source_demo_set:{demos}")
        reports[participant_id] = {
            "manifest": str(manifest_path.resolve()),
            "manifest_sha256": sha256_file(manifest_path),
            "shuffle_seed": expected_seed,
            "route_counts": dict(route_counts),
            "unique_source_demos": len(set(source_demo_keys)),
            "errors": participant_errors,
        }
        errors.extend(f"{participant_id}:{value}" for value in participant_errors)

    partial_paths = sorted(
        str(path) for path in args.mixed_root.parent.glob(f"{args.mixed_root.name}.inprogress.*")
    )
    zero_byte_files = sorted(
        str(path) for path in args.mixed_root.rglob("*") if path.is_file() and path.stat().st_size == 0
    )
    if partial_paths:
        errors.append(f"partial_mixed_roots:{partial_paths}")
    if zero_byte_files:
        errors.append(f"zero_byte_files:{zero_byte_files}")
    report = {
        "schema_version": 1,
        "group": GROUP,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "passed": not errors and len(reports) == 10,
        "errors": errors,
        "counts": {
            "participants": len(reports),
            "raw_symlinks": sum(60 for row in reports.values() if not row["errors"]),
            "result_symlinks": sum(60 for row in reports.values() if not row["errors"]),
            "trajectory_memberships": sum(
                row["unique_source_demos"] for row in reports.values()
            ),
            "partial_roots": len(partial_paths),
            "zero_byte_files": len(zero_byte_files),
        },
        "pairing_manifest": {"path": str(args.pairing.resolve()), "sha256": sha256_file(args.pairing)},
        "frozen_inputs": frozen_inputs,
        "participant_reports": reports,
    }
    write_json_atomic_exclusive(args.output, report)
    print(f"passed={report['passed']} errors={len(errors)} output={args.output}")
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
