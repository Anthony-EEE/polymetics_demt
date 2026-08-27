#!/usr/bin/env python3
"""Policy-blind IK preflight for Target collection replenishment candidates."""

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pybullet as pb


EXAMPLES_DIR = Path(__file__).resolve().parents[1]
if str(EXAMPLES_DIR) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_DIR))

from main_obstacle_transport import WAYPOINT_REACH_TOLERANCE  # noqa: E402
from main_obstacle_transport_target_participants import (  # noqa: E402
    TARGET_PARTICIPANTS,
    participant_task_spec,
)
from rebuttal_target_pipeline.target_protocol import TargetObstacleTransportSim  # noqa: E402


GROUP = "simulation_target_group"
SEED = 20260806


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def candidate_reachability(sim, spec):
    box = np.asarray(spec["box_initial_position"], dtype=float)
    quat = sim.default_orientation_quat
    required = {
        "scripted_ee_initial": np.asarray(spec["scripted_ee_initial_position"], dtype=float),
        "pre_grasp": np.asarray([box[0], box[1], 0.16], dtype=float),
        "grasp": np.asarray([box[0], box[1], 0.04], dtype=float),
        "transport_start": np.asarray([box[0], box[1], spec["transport_z"]], dtype=float),
    }
    unreachable_setup = [
        name
        for name, point in required.items()
        if not sim.ik_reachable(
            point,
            quat,
            max_error=0.04 if name == "grasp" else 0.025,
        )
    ]
    middle = np.asarray(spec["middle_waypoint"], dtype=float)
    middle_reachable = sim.ik_reachable(
        middle,
        quat,
        max_error=WAYPOINT_REACH_TOLERANCE,
    )
    return {
        "setup_reachable": not unreachable_setup,
        "unreachable_setup_waypoints": unreachable_setup,
        "middle_waypoint_reachable": bool(middle_reachable),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-attempts", type=int, default=30)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    if args.max_attempts != 30:
        raise ValueError("Formal collection preflight requires the frozen 30-attempt cap")

    sim = TargetObstacleTransportSim(gui=False, output_dir=None, sample_hz=8.0)
    sim.playback_speed = 1000.0
    sim.setup()
    accepted = []
    rejected = []
    try:
        for participant_id in TARGET_PARTICIPANTS:
            for demo_index in range(30):
                for attempt_index in range(args.max_attempts):
                    spec = participant_task_spec(
                        participant_id,
                        demo_index,
                        attempt_index,
                        SEED,
                    )
                    checks = candidate_reachability(sim, spec)
                    record = {
                        "participant_id": participant_id,
                        "route": spec["condition"],
                        "demo_index": demo_index,
                        "attempt_index": attempt_index,
                        "box_initial_position": spec["box_initial_position"],
                        "middle_waypoint": spec["middle_waypoint"],
                        "checks": checks,
                    }
                    if checks["setup_reachable"] and checks["middle_waypoint_reachable"]:
                        accepted.append(record)
                        break
                    rejected.append(record)
                else:
                    raise RuntimeError(
                        f"No IK-feasible candidate within 30 attempts: "
                        f"{participant_id} demo {demo_index}"
                    )
    finally:
        if sim.client is not None:
            pb.disconnect(sim.client)

    source_paths = {
        "target_collector": EXAMPLES_DIR / "main_obstacle_transport_target_participants.py",
        "shared_task": EXAMPLES_DIR / "main_obstacle_transport.py",
        "target_protocol": Path(__file__).resolve().parent / "target_protocol.py",
        "preflight": Path(__file__).resolve(),
    }
    payload = {
        "schema_version": 1,
        "group": GROUP,
        "seed": SEED,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "policy_blind": True,
        "check_scope": "IK feasibility only; no collection outcome or learned policy queried",
        "max_attempts": args.max_attempts,
        "accepted_count": len(accepted),
        "rejected_count": len(rejected),
        "all_300_have_feasible_candidate": len(accepted) == 300,
        "accepted": accepted,
        "rejected": rejected,
        "software": {
            name: {"path": str(path.resolve()), "sha256": sha256(path)}
            for name, path in source_paths.items()
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(
        json.dumps(
            {
                "output": str(args.output),
                "accepted": len(accepted),
                "rejected": len(rejected),
                "max_first_feasible_attempt": max(row["attempt_index"] for row in accepted),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
