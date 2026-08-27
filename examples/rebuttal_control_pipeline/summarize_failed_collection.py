#!/usr/bin/env python3
"""Summarize an incomplete Control collection without treating it as formal data."""

import argparse
import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path


GROUP = "simulation_control_group"
PARTICIPANTS = [f"C{index:02d}" for index in range(1, 11)]


def load_json(path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def failure_reasons(attempt):
    details = attempt.get("details", {})
    reasons = details.get("success", {}).get("failure_reasons") or []
    if reasons:
        return [str(reason) for reason in reasons]
    reason = (
        details.get("failure_stage")
        or details.get("setup_details", {}).get("reason")
        or "task_failure"
    )
    return [str(reason)]


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--held-tasks", nargs="*", type=int, default=[])
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main():
    args = parse_args()
    root = args.root.resolve()
    report = {
        "group": GROUP,
        "stage": "Stage A raw collection",
        "status": "FAILED_PROTOCOL",
        "formal_data_usable": False,
        "cause": "frozen demo-2 high-release target misses; SCR-C001 awaiting approval",
        "root": str(root),
        "slurm_array_job_id": str(args.job_id),
        "held_array_tasks": list(args.held_tasks),
        "participants": {},
    }
    total_attempts = 0
    total_failures = 0
    total_successes = 0
    total_frames = 0
    total_scripted_frames = 0
    reason_labels = Counter()
    failed_raw_demo_dirs = []

    for participant_id in PARTICIPANTS:
        participant_dir = root / participant_id
        attempt_paths = sorted((participant_dir / "attempts").glob("demo_*_attempt_*.json"))
        result_paths = sorted(participant_dir.glob("demo_[0-9][0-9].json"))
        participant_failures = 0
        participant_reasons = Counter()
        best_failed_demo2_target_error = None
        for path in attempt_paths:
            attempt = load_json(path)
            if attempt.get("success"):
                continue
            participant_failures += 1
            reasons = failure_reasons(attempt)
            participant_reasons.update(reasons)
            reason_labels.update(reasons)
            if attempt.get("demo_index") == 2:
                value = attempt.get("details", {}).get("success", {}).get("target_xy_error")
                if isinstance(value, (int, float)) and math.isfinite(value):
                    best_failed_demo2_target_error = (
                        float(value)
                        if best_failed_demo2_target_error is None
                        else min(best_failed_demo2_target_error, float(value))
                    )

        frame_count = 0
        scripted_frames = 0
        for result_path in result_paths:
            demo_index = int(result_path.stem.split("_")[1])
            demo_dir = participant_dir / f"demo_{demo_index}"
            frame_dirs = sorted(
                path for path in demo_dir.glob("frame_*") if path.is_dir()
            )
            frame_count += len(frame_dirs)
            for frame_dir in frame_dirs:
                phase_path = frame_dir / "phase.txt"
                if phase_path.is_file() and phase_path.read_text(encoding="utf-8").strip().startswith("scripted_"):
                    scripted_frames += 1

        for demo_dir in participant_dir.glob("demo_[0-9]*"):
            if not demo_dir.is_dir() or not re.fullmatch(r"demo_\d+", demo_dir.name):
                continue
            demo_index = int(demo_dir.name.split("_")[1])
            if not (participant_dir / f"demo_{demo_index:02d}.json").is_file():
                failed_raw_demo_dirs.append(str(demo_dir.relative_to(root)))

        participant_report = {
            "directory_exists": participant_dir.is_dir(),
            "summary_exists": (participant_dir / "summary.json").is_file(),
            "successful_demos": len(result_paths),
            "attempt_jsons": len(attempt_paths),
            "failed_attempts": participant_failures,
            "failed_reason_labels": dict(sorted(participant_reasons.items())),
            "raw_frames": frame_count,
            "scripted_frames": scripted_frames,
            "best_failed_demo2_target_xy_error": best_failed_demo2_target_error,
        }
        report["participants"][participant_id] = participant_report
        total_attempts += len(attempt_paths)
        total_failures += participant_failures
        total_successes += len(result_paths)
        total_frames += frame_count
        total_scripted_frames += scripted_frames

    zero_byte_files = sorted(
        str(path.relative_to(root))
        for path in root.rglob("*")
        if path.is_file() and path.stat().st_size == 0
    )
    report["totals"] = {
        "successful_demos": total_successes,
        "expected_successful_demos": 300,
        "attempt_jsons": total_attempts,
        "failed_attempts": total_failures,
        "failed_reason_labels": dict(sorted(reason_labels.items())),
        "raw_frames": total_frames,
        "scripted_frames": total_scripted_frames,
        "failed_raw_demo_dirs": sorted(failed_raw_demo_dirs),
        "zero_byte_files": zero_byte_files,
    }

    repo_root = Path(__file__).resolve().parents[2]
    hash_paths = {
        "participant_manifest": root / "participant_manifest.json",
        "failed_validation": root / "diagnostics" / "stage_a_failed_validation.json",
        "control_collector": repo_root / "examples" / "main_obstacle_transport_control_participants.py",
        "control_wrapper": repo_root / "examples" / "rebuttal_control_pipeline" / "collect_control_array.sbatch",
        "control_validator": repo_root / "examples" / "rebuttal_control_pipeline" / "validate_raw_collection.py",
        "shared_task_read_only": repo_root / "examples" / "main_obstacle_transport.py",
    }
    report["sha256"] = {
        name: sha256(path) for name, path in hash_paths.items() if path.is_file()
    }

    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(output)
    print(json.dumps(report["totals"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
