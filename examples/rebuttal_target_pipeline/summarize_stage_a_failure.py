#!/usr/bin/env python3
"""Summarise an incomplete Target collection without treating it as formal data."""

import argparse
import collections
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def finite_values(rows, key):
    values = [row[key] for row in rows if isinstance(row.get(key), (int, float))]
    return [float(value) for value in values if math.isfinite(float(value))]


def extrema(values):
    if not values:
        return {"count": 0, "min": None, "max": None, "mean": None}
    return {
        "count": len(values),
        "min": min(values),
        "max": max(values),
        "mean": sum(values) / len(values),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    participant_reports = {}
    total_successes = 0
    total_attempts = 0
    total_failures = 0
    failure_taxonomy = collections.Counter()
    attempt_hashes = {}

    for participant_index in range(1, 11):
        participant_id = f"T{participant_index:02d}"
        participant_dir = args.root / participant_id
        successful_paths = sorted(participant_dir.glob("demo_[0-9][0-9].json"))
        attempt_paths = sorted((participant_dir / "attempts").glob("demo_*_attempt_*.json"))
        attempts = [json.loads(path.read_text(encoding="utf-8")) for path in attempt_paths]
        attempt_hashes.update({str(path.relative_to(args.root)): sha256(path) for path in attempt_paths})
        failed = [row for row in attempts if row.get("success") is not True]
        setup_failures = 0
        metrics = []
        taxonomy = collections.Counter()
        attempts_per_demo = collections.Counter()
        for row in attempts:
            attempts_per_demo[str(row.get("demo_index"))] += 1
            details = row.get("details", {})
            if details.get("setup_success") is not True:
                setup_failures += 1
                reason = details.get("setup_details", {}).get("reason") or "setup_failure"
                taxonomy[reason] += 1
                continue
            success = details.get("success", {})
            reasons = list(success.get("failure_reasons", []))
            if row.get("success") is not True and not reasons:
                reasons = [details.get("failure_stage") or "unclassified_scientific_failure"]
            for reason in reasons:
                taxonomy[reason] += 1
            metrics.append(success)
        failure_taxonomy.update(taxonomy)
        total_successes += len(successful_paths)
        total_attempts += len(attempts)
        total_failures += len(failed)
        participant_reports[participant_id] = {
            "successful_formal_demos": len(successful_paths),
            "attempt_records": len(attempts),
            "failed_attempt_records": len(failed),
            "setup_failures": setup_failures,
            "attempts_per_demo": dict(sorted(attempts_per_demo.items(), key=lambda item: int(item[0]))),
            "failure_taxonomy": dict(sorted(taxonomy.items())),
            "target_xy_error": extrema(finite_values(metrics, "target_xy_error")),
            "middle_waypoint_error": extrema(finite_values(metrics, "middle_waypoint_error")),
            "maximum_cylinder_tilt_degrees": extrema(
                finite_values(metrics, "maximum_cylinder_tilt_degrees")
            ),
        }

    payload = {
        "group": "simulation_target_group",
        "seed": 20260806,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "formal_experiment_complete": False,
        "stage": "Stage A collection failure",
        "counts": {
            "successful_formal_demos": total_successes,
            "attempt_records": total_attempts,
            "failed_attempt_records": total_failures,
        },
        "failure_taxonomy": dict(sorted(failure_taxonomy.items())),
        "participant_reports": participant_reports,
        "attempt_record_hashes": attempt_hashes,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload["counts"], sort_keys=True))
    print(json.dumps(payload["failure_taxonomy"], sort_keys=True))


if __name__ == "__main__":
    main()
