#!/usr/bin/env python3
"""Non-formal Control diagnostic for a proposed shared release height."""

import argparse
import json
import sys
from pathlib import Path

import pybullet as pb


EXAMPLES_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EXAMPLES_ROOT))

from main_obstacle_transport import ObstacleTransportSim  # noqa: E402
from main_obstacle_transport_control_participants import (  # noqa: E402
    CONTROL_PARTICIPANTS,
    EXPERIMENT_GROUP,
    participant_task_spec,
)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--participants",
        nargs="+",
        default=list(CONTROL_PARTICIPANTS),
    )
    demos = parser.add_mutually_exclusive_group()
    demos.add_argument("--demo-index", type=int)
    demos.add_argument("--demo-indices", nargs="+", type=int)
    demos.add_argument("--all-30", action="store_true")
    parser.add_argument("--seed", type=int, default=20260806)
    parser.add_argument("--release-z", type=float, default=0.08)
    parser.add_argument("--max-attempts", type=int, default=30)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main():
    args = parse_args()
    unknown = sorted(set(args.participants) - set(CONTROL_PARTICIPANTS))
    if unknown:
        raise ValueError(f"unknown Control participants: {unknown}")
    if args.all_30:
        demo_indices = list(range(30))
    elif args.demo_indices is not None:
        demo_indices = list(args.demo_indices)
    else:
        demo_indices = [2 if args.demo_index is None else args.demo_index]
    if any(index < 0 or index >= 30 for index in demo_indices):
        raise ValueError(f"demo indices must be in [0, 29]: {demo_indices}")
    sim = ObstacleTransportSim(gui=False, output_dir=None, sample_hz=8.0)
    sim.playback_speed = 1000.0
    sim.setup()
    case_results = []
    all_attempts = []
    try:
        for participant_id in args.participants:
            for demo_index in demo_indices:
                accepted = None
                for attempt_index in range(args.max_attempts):
                    spec = participant_task_spec(
                        participant_id,
                        demo_index,
                        attempt_index,
                        args.seed,
                    )
                    original_release_z = float(spec["release_pose"][2])
                    spec["release_pose"][2] = float(args.release_z)
                    spec["diagnostic_override"] = {
                        "formal_data": False,
                        "field": "release_pose_z",
                        "original": original_release_z,
                        "proposed_shared_value": float(args.release_z),
                        "shared_change_request": "SCR-001/SCR-C001",
                    }
                    sim.reset_task_state(spec["box_initial_position"])
                    success, details = sim.run_scripted_transport_and_release(
                        spec,
                        save=False,
                        demo_index=demo_index,
                    )
                    attempt = {
                        "group": EXPERIMENT_GROUP,
                        "formal_data": False,
                        "participant_id": participant_id,
                        "demo_index": demo_index,
                        "attempt_index": attempt_index,
                        "success": bool(success),
                        "spec": spec,
                        "details": details,
                    }
                    all_attempts.append(attempt)
                    if success:
                        accepted = attempt
                        break
                case_results.append(
                    {
                        "participant_id": participant_id,
                        "route": CONTROL_PARTICIPANTS[participant_id]["route"],
                        "demo_index": demo_index,
                        "success": accepted is not None,
                        "accepted_attempt_index": (
                            accepted["attempt_index"] if accepted is not None else None
                        ),
                        "accepted": accepted,
                    }
                )
    finally:
        if sim.client is not None:
            pb.disconnect(sim.client)

    report = {
        "group": EXPERIMENT_GROUP,
        "formal_data": False,
        "diagnostic": "proposed_shared_release_height",
        "shared_change_request": "SCR-001/SCR-C001",
        "seed": args.seed,
        "participant_order": list(args.participants),
        "demo_indices": demo_indices,
        "release_z": args.release_z,
        "successful_cases": sum(row["success"] for row in case_results),
        "case_count": len(case_results),
        "cases": case_results,
        "attempts": all_attempts,
    }
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(output)
    print(
        f"release_z={args.release_z:.3f} participants={len(args.participants)} "
        f"demos={len(demo_indices)} "
        f"successes={report['successful_cases']}/{report['case_count']}"
    )
    if report["successful_cases"] != report["case_count"]:
        raise SystemExit("release-height diagnostic did not pass all cases")


if __name__ == "__main__":
    main()
