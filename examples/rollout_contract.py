"""Shared validation/statistics helpers for paired rollout supplements."""

import hashlib
import json
import math
from pathlib import Path

import numpy as np


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def file_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stream_seed(seed, rollout_index, stream_tag):
    """Return a stable uint32 seed for an explicitly separated RNG stream."""
    sequence = np.random.SeedSequence([int(seed), int(rollout_index), int(stream_tag)])
    return int(sequence.generate_state(1, dtype=np.uint32)[0])


def wilson_interval(successes, total, z=1.959963984540054):
    if total <= 0:
        return [None, None]
    p = successes / total
    denominator = 1.0 + z * z / total
    center = (p + z * z / (2.0 * total)) / denominator
    margin = z * math.sqrt(p * (1.0 - p) / total + z * z / (4.0 * total * total)) / denominator
    return [center - margin, center + margin]


def condition_rollout_statistics(summary):
    rollouts = summary["rollouts"]
    successful = [row for row in rollouts if row["success"]]
    steps = [int(row["steps"]) for row in successful]
    times = [float(row["time_to_success_s"]) for row in successful]
    return {
        "success_count": len(successful),
        "failure_count": len(rollouts) - len(successful),
        "success_rate": len(successful) / len(rollouts),
        "success_rate_wilson_95": wilson_interval(len(successful), len(rollouts)),
        "successful_steps": {
            "mean": float(np.mean(steps)) if steps else None,
            "median": float(np.median(steps)) if steps else None,
            "min": min(steps) if steps else None,
            "max": max(steps) if steps else None,
        },
        "successful_time_to_success_s": {
            "mean": float(np.mean(times)) if times else None,
            "median": float(np.median(times)) if times else None,
            "min": min(times) if times else None,
            "max": max(times) if times else None,
        },
        "failure_rollout_indices": [int(row["rollout_index"]) for row in rollouts if not row["success"]],
    }


def paired_discordances(condition_order, summary_by_condition):
    tables = {}
    for left_index, left in enumerate(condition_order):
        for right in condition_order[left_index + 1 :]:
            left_success = [bool(row["success"]) for row in summary_by_condition[left]["rollouts"]]
            right_success = [bool(row["success"]) for row in summary_by_condition[right]["rollouts"]]
            tables[f"{left}_vs_{right}"] = {
                "both_success": sum(a and b for a, b in zip(left_success, right_success)),
                f"{left}_only": sum(a and not b for a, b in zip(left_success, right_success)),
                f"{right}_only": sum((not a) and b for a, b in zip(left_success, right_success)),
                "both_failure": sum((not a) and (not b) for a, b in zip(left_success, right_success)),
            }
    return tables


def validate_rollout_files(output_dir, condition, expected_rollouts, expected_rows):
    rollout_dir = Path(output_dir) / "rollouts" / condition
    expected_names = {f"rollout_{index:03d}.json" for index in range(expected_rollouts)}
    actual_names = {path.name for path in rollout_dir.glob("*.json")}
    if actual_names != expected_names:
        missing = sorted(expected_names - actual_names)
        stale = sorted(actual_names - expected_names)
        raise ValueError(f"{condition} per-rollout JSON set mismatch: missing={missing}, stale={stale}")
    loaded = [load_json(rollout_dir / f"rollout_{index:03d}.json") for index in range(expected_rollouts)]
    if loaded != expected_rows:
        raise ValueError(f"{condition} per-rollout JSON content differs from condition summary")


def checkpoints_from_manifest(path, expected_order, conditions):
    manifest = load_json(path)
    if manifest.get("condition_order") != list(expected_order):
        raise ValueError(f"Checkpoint manifest condition_order must be exactly {', '.join(expected_order)}")
    records = manifest.get("checkpoints", {})
    resolved = {}
    for condition in conditions:
        record = records.get(condition)
        if not isinstance(record, dict) or not record.get("path") or not record.get("sha256"):
            raise KeyError(f"Checkpoint manifest missing explicit path/hash for {condition}")
        checkpoint = Path(record["path"])
        if not checkpoint.is_file():
            raise FileNotFoundError(f"Checkpoint for {condition} does not exist: {checkpoint}")
        actual_hash = file_sha256(checkpoint)
        if actual_hash != record["sha256"]:
            raise ValueError(f"Checkpoint hash mismatch for {condition}: {actual_hash} != {record['sha256']}")
        resolved[condition] = checkpoint
    return manifest, resolved
