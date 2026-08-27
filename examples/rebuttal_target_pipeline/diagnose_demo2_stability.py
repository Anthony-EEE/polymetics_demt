#!/usr/bin/env python3
"""Target-owned diagnostic for the frozen demo-2 grasp/transport failure.

This helper never writes formal demonstrations.  It replays selected frozen
specifications while varying only explicitly named candidate stabilisation
settings, then records enough state to support a shared-change request.  A
candidate is not part of the experiment protocol unless separately approved.
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pybullet as pb


EXAMPLES_DIR = Path(__file__).resolve().parents[1]
if str(EXAMPLES_DIR) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_DIR))

from main_obstacle_transport import ObstacleTransportSim, TARGET_XY  # noqa: E402
from main_obstacle_transport_target_participants import (  # noqa: E402
    participant_task_spec,
)


VARIANTS = {
    "baseline": {"finger_friction": None, "motion_speed": 0.10},
    "finger_friction_0p75": {"finger_friction": 0.75, "motion_speed": 0.10},
    "finger_friction_1": {"finger_friction": 1.0, "motion_speed": 0.10},
    "finger_friction_1p25": {"finger_friction": 1.25, "motion_speed": 0.10},
    "finger_friction_1p5": {"finger_friction": 1.5, "motion_speed": 0.10},
    "finger_friction_2": {"finger_friction": 2.0, "motion_speed": 0.10},
    "dynamic_friction_1p5": {
        "finger_friction": None,
        "dynamic_closed_friction": 1.5,
        "motion_speed": 0.10,
    },
    "dynamic_friction_2": {
        "finger_friction": None,
        "dynamic_closed_friction": 2.0,
        "motion_speed": 0.10,
    },
    "release_z_0p08": {"finger_friction": None, "motion_speed": 0.10, "release_z": 0.08},
    "release_z_0p10": {"finger_friction": None, "motion_speed": 0.10, "release_z": 0.10},
    "release_z_0p12": {"finger_friction": None, "motion_speed": 0.10, "release_z": 0.12},
    "cube_xy_center_before_release": {
        "finger_friction": None,
        "motion_speed": 0.10,
        "cube_xy_center_before_release": True,
    },
    "motion_speed_0p05": {"finger_friction": None, "motion_speed": 0.05},
    "friction_2_speed_0p05": {"finger_friction": 2.0, "motion_speed": 0.05},
}


class DiagnosticSim(ObstacleTransportSim):
    def __init__(self, *args, **kwargs):
        self.dynamic_closed_friction = None
        self.cube_xy_center_before_release = False
        self.centering_events = []
        super().__init__(*args, **kwargs)
        self.phase_snapshots = []

    def _apply_gripper(self, width, force=60, max_vel=0.08):
        if self.dynamic_closed_friction is not None and self.panda is not None:
            friction = self.dynamic_closed_friction if float(width) < 0.03 else 0.5
            for link in (self.left_finger_joint, self.right_finger_joint):
                pb.changeDynamics(self.panda, link, lateralFriction=friction)
        return super()._apply_gripper(width, force=force, max_vel=max_vel)

    def _snapshot(self, phase):
        cube = np.asarray(self.cube_pos(), dtype=float)
        ee = np.asarray(self.ee_pos(), dtype=float)
        self.phase_snapshots.append(
            {
                "phase": phase,
                "cube_position": cube.tolist(),
                "ee_position": ee.tolist(),
                "cube_minus_ee": (cube - ee).tolist(),
            }
        )

    def move_ee_cartesian(self, *args, **kwargs):
        result = super().move_ee_cartesian(*args, **kwargs)
        self._snapshot(kwargs.get("phase_name", "unknown_cartesian_phase"))
        return result

    def command_gripper(self, width, duration, gripper_state, phase_name, save=False):
        if (
            self.cube_xy_center_before_release
            and phase_name == "policy_release"
            and float(width) >= 0.03
        ):
            cube_before = np.asarray(self.cube_pos(), dtype=float)
            ee_before = np.asarray(self.ee_pos(), dtype=float)
            correction = np.asarray(TARGET_XY, dtype=float) - cube_before[:2]
            corrected_ee = ee_before.copy()
            corrected_ee[:2] += correction
            self.move_ee_cartesian(
                corrected_ee,
                target_quat=self.default_orientation_quat,
                speed=self.motion_speed,
                gripper_state=1.0,
                phase_name="policy_target_cube_xy_centering",
                save=save,
            )
            self.centering_events.append(
                {
                    "cube_before": cube_before.tolist(),
                    "ee_before": ee_before.tolist(),
                    "xy_correction": correction.tolist(),
                    "corrected_ee_target": corrected_ee.tolist(),
                    "cube_after": self.cube_pos().tolist(),
                    "ee_after": self.ee_pos().tolist(),
                }
            )
        return super().command_gripper(
            width,
            duration,
            gripper_state,
            phase_name,
            save=save,
        )


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_case(participant_id, demo_index, attempt_index, seed, variant_name):
    settings = VARIANTS[variant_name]
    spec = participant_task_spec(participant_id, demo_index, attempt_index, seed)
    if settings.get("release_z") is not None:
        spec["release_pose"][2] = float(settings["release_z"])
    sim = DiagnosticSim(gui=False, output_dir=None, sample_hz=8.0)
    sim.playback_speed = 1000.0
    sim.motion_speed = settings["motion_speed"]
    sim.dynamic_closed_friction = settings.get("dynamic_closed_friction")
    sim.cube_xy_center_before_release = settings.get("cube_xy_center_before_release", False)
    try:
        sim.setup()
        if settings["finger_friction"] is not None:
            for link in (sim.left_finger_joint, sim.right_finger_joint):
                pb.changeDynamics(
                    sim.panda,
                    link,
                    lateralFriction=settings["finger_friction"],
                    spinningFriction=0.02,
                    rollingFriction=0.0001,
                )
        sim.reset_task_state(spec["box_initial_position"])
        success, details = sim.run_scripted_transport_and_release(
            spec,
            save=False,
            demo_index=demo_index,
        )
        return {
            "participant_id": participant_id,
            "demo_index": demo_index,
            "attempt_index": attempt_index,
            "seed": seed,
            "variant": variant_name,
            "settings": settings,
            "success": bool(success),
            "spec": spec,
            "details": details,
            "phase_snapshots": sim.phase_snapshots,
            "centering_events": sim.centering_events,
        }
    finally:
        if sim.client is not None:
            pb.disconnect(sim.client)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--participants", nargs="+", default=["T01", "T02", "T03"])
    parser.add_argument("--variants", nargs="+", choices=sorted(VARIANTS), default=list(VARIANTS))
    parser.add_argument("--demo-index", type=int, default=2)
    parser.add_argument("--attempt-index", type=int, default=0)
    parser.add_argument("--seed", type=int, default=20260806)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    results = []
    for participant_id in args.participants:
        for variant_name in args.variants:
            result = run_case(
                participant_id,
                args.demo_index,
                args.attempt_index,
                args.seed,
                variant_name,
            )
            results.append(result)
            success_details = result["details"].get("success", {})
            print(
                participant_id,
                variant_name,
                "success=",
                result["success"],
                "target_xy_error=",
                success_details.get("target_xy_error"),
                flush=True,
            )

    source_paths = [
        EXAMPLES_DIR / "main_obstacle_transport.py",
        EXAMPLES_DIR / "main_obstacle_transport_target_participants.py",
        Path(__file__).resolve(),
    ]
    payload = {
        "diagnostic_only": True,
        "formal_experiment_data": False,
        "source_hashes": {str(path): sha256(path) for path in source_paths},
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
