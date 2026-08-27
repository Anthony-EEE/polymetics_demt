#!/usr/bin/env python3
"""Reproduce the lowest-target-error successful Control-Bimodal R rollout."""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from copy import copy
from datetime import datetime, timezone
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
EXAMPLES_DIR = REPO / "examples"
if str(EXAMPLES_DIR) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_DIR))

from rebuttal_bimodal_pipeline import export_success_replays as replay  # noqa: E402
from rebuttal_control_bimodal_pipeline import (  # noqa: E402
    evaluate_control_bimodal_policy as control_eval,
)


GROUP = "simulation_control_bimodal_group"
PARTICIPANTS = [f"CB{index:02d}" for index in range(1, 11)]
ANALYSIS_CSV = (
    REPO
    / "rebuttal_dataset/simulation_control_bimodal_group/analysis/rollout_results.csv"
)
CHECKPOINT_MANIFEST = (
    REPO
    / "rebuttal_dataset/simulation_control_bimodal_group/models/"
    "selected_checkpoints_manifest.json"
)
SPEC_MANIFEST = (
    REPO
    / "rebuttal_dataset/simulation_target_group/analysis/paired_rollout_specs.json"
)
FORMAL_ROLLOUT_ROOT = (
    REPO / "rebuttal_dataset/simulation_control_bimodal_group/policy_rollouts"
)


def warm_up_formal_prefix(
    *,
    policy,
    sim,
    participant,
    selected_eval_case_id,
    selected_repeat_index,
    checkpoint_record,
    spec_manifest,
    spec_hash,
    args,
    case_dir,
):
    """Recreate the persistent-simulator history preceding the selected row."""

    warmup_args = copy(args)
    warmup_args.save_videos = False
    warmup_root = case_dir / ".formal_prefix_warmup"
    warmup_root.mkdir()
    prefix_count = 0
    for case in spec_manifest["eval_cases"]:
        eval_case_id = int(case["eval_case_id"])
        for repeat_index in (0, 1):
            if (eval_case_id, repeat_index) == (
                selected_eval_case_id,
                selected_repeat_index,
            ):
                print(
                    f"Formal-prefix warm-up complete: {prefix_count} prior episodes",
                    flush=True,
                )
                warmup_root.rmdir()
                return
            result = control_eval.run_case(
                sim,
                policy,
                participant,
                case,
                repeat_index,
                warmup_args,
                checkpoint_record,
                spec_hash,
                warmup_root,
            )
            formal_path = FORMAL_ROLLOUT_ROOT / participant / "rollouts" / (
                f"rollout_case_{eval_case_id:02d}_repeat_{repeat_index}.json"
            )
            formal = replay.load_json(formal_path)
            reproduced_route = result["route_behavior"]["realised_route"]
            formal_route = formal["route_behavior"]["realised_route"]
            if (
                bool(result["success"]) != bool(formal["success"])
                or reproduced_route != formal_route
            ):
                raise RuntimeError(
                    "Formal-prefix history diverged at "
                    f"case{eval_case_id}/repeat{repeat_index}: "
                    f"expected success={formal['success']}, route={formal_route}; "
                    f"got success={result['success']}, route={reproduced_route}"
                )
            prefix_count += 1
            print(
                "  formal-prefix "
                f"case={eval_case_id} repeat={repeat_index} "
                f"route={reproduced_route} success={result['success']}",
                flush=True,
            )
    raise ValueError("Selected case/repeat is absent from the frozen manifest")


def configure_control_adapter():
    """Point the validated generic recorder at Control-Bimodal artifacts."""

    replay.GROUP = GROUP
    replay.PARTICIPANTS = PARTICIPANTS
    replay.ANALYSIS_CSV = ANALYSIS_CSV
    replay.CHECKPOINT_MANIFEST = CHECKPOINT_MANIFEST
    replay.SPEC_MANIFEST = SPEC_MANIFEST
    replay.FORMAL_ROLLOUT_ROOT = FORMAL_ROLLOUT_ROOT
    replay.policy_sampling_seed = control_eval.policy_sampling_seed
    replay.PRE_REPRODUCTION_HOOK = warm_up_formal_prefix


def successful_r_candidates(path=ANALYSIS_CSV):
    with Path(path).open("r", encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    candidates = [
        dict(row)
        for row in rows
        if row["success"] == "1" and row["realised_route"] == "R"
    ]
    candidates.sort(
        key=lambda row: (
            float(row["target_xy_error"]),
            row["participant_id"],
            int(row["eval_case_id"]),
            int(row["repeat_index"]),
        )
    )
    if not candidates:
        raise RuntimeError("No successful Control-Bimodal R rollout exists")
    return candidates


def inventory_rows(candidates):
    fields = (
        "participant_id",
        "eval_case_id",
        "repeat_index",
        "policy_sampling_seed",
        "target_xy_error",
        "termination_reason",
        "video_path",
    )
    return [{field: row[field] for field in fields} for row in candidates]


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-root",
        type=Path,
        default=REPO / "control_bimodal_replay/min_error_R",
    )
    parser.add_argument("--max-reproduction-attempts", type=int, default=3)
    parser.add_argument("--record-hz", type=float, default=30.0)
    parser.add_argument("--sample-hz", type=float, default=8.0)
    parser.add_argument("--horizon", type=int, default=200)
    parser.add_argument("--action-dt", type=float, default=0.25)
    parser.add_argument("--num-points", type=int, default=10000)
    parser.add_argument("--settle-seconds", type=float, default=1.5)
    parser.add_argument("--playback-speed", type=float, default=1000.0)
    parser.add_argument("--video-fps", type=int, default=10)
    parser.add_argument("--save-videos", action="store_true")
    parser.add_argument("--cuda", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    if args.max_reproduction_attempts < 1:
        raise ValueError("max-reproduction-attempts must be positive")
    configure_control_adapter()
    candidates = successful_r_candidates()
    selected = candidates[0]
    output_root = args.output_root.resolve()
    if output_root.exists() or output_root.is_symlink():
        raise FileExistsError(f"Refusing to overwrite replay export: {output_root}")
    output_root.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_root.with_name(f".{output_root.name}.inprogress.{os.getpid()}")
    if temporary.exists() or temporary.is_symlink():
        raise FileExistsError(f"Stale temporary output: {temporary}")
    temporary.mkdir()

    try:
        inventory = inventory_rows(candidates)
        replay.write_csv(
            temporary / "successful_r_cases_by_error.csv",
            inventory,
            list(inventory[0]),
        )
        checkpoint_manifest, spec_manifest, spec_hash = replay.validate_manifests()
        divergences = []
        reproduction = None
        for attempt_index in range(args.max_reproduction_attempts):
            case_dir = temporary / "R"
            case_dir.mkdir()
            try:
                reproduction = replay.reproduce_one(
                    "R",
                    selected,
                    checkpoint_manifest,
                    spec_manifest,
                    spec_hash,
                    case_dir,
                    args,
                )
                break
            except replay.ReproductionOutcomeDiverged as exc:
                failed_dir = (
                    temporary
                    / "diverged_reproductions"
                    / f"attempt_{attempt_index:02d}"
                )
                failed_dir.parent.mkdir(parents=True, exist_ok=True)
                os.replace(case_dir, failed_dir)
                row = dict(exc.result)
                row["diagnostic_directory_relative_to_export_root"] = str(
                    failed_dir.relative_to(temporary)
                )
                divergences.append(row)
                print(str(exc), flush=True)
        if reproduction is None:
            raise RuntimeError(
                "The fixed minimum-error Control-Bimodal R case did not reproduce "
                f"success in {args.max_reproduction_attempts} attempts"
            )
        manifest = {
            "schema_version": 1,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "group": GROUP,
            "selection": {
                "rule": (
                    "minimum numeric target_xy_error among all formal rows with "
                    "success=1 and realised_route=R; deterministic ID tie-break"
                ),
                "successful_r_candidate_count": len(candidates),
                "selected_rank": 1,
                "selected": {
                    key: selected[key]
                    for key in (
                        "participant_id",
                        "eval_case_id",
                        "repeat_index",
                        "policy_sampling_seed",
                        "target_xy_error",
                        "video_path",
                    )
                },
            },
            "reproduction": reproduction,
            "diverged_reproductions_before_success": divergences,
            "next_transform": (
                "Mirror R/intervention.csv with mirror_intervention_y.py --in-place"
            ),
        }
        replay.write_json(temporary / "manifest.json", manifest)
        os.replace(temporary, output_root)
        print(json.dumps(manifest, indent=2, sort_keys=True), flush=True)
    except Exception:
        print(f"Export failed; diagnostics retained at {temporary}", file=sys.stderr)
        raise


if __name__ == "__main__":
    main()
