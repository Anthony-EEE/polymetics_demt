#!/usr/bin/env python3
import argparse
import hashlib
import json
import math
import random
import shutil
from fractions import Fraction
from pathlib import Path

import numpy as np

from main_abla_1 import PandaSim


LADDER_TIME_CONDITIONS = {
    "T00": (1.00, 1.00),
    "T25": (0.75, 1.25),
    "T50": (0.50, 1.50),
    "T75": (0.25, 1.75),
    "T100": (0.00, 2.00),
}
HISTORICAL_VREF_TIME_CONDITIONS = {
    "V075_150": (0.75, 1.50),
    "V050_200": (0.50, 2.00),
    "V025_250": (0.25, 2.50),
}
RECIPROCAL_VREF_N = {
    "VR1P5": Fraction(3, 2),
    "V050_200": Fraction(2, 1),
    "VR3": Fraction(3, 1),
    "VR4": Fraction(4, 1),
}
RECIPROCAL_VREF_TIME_CONDITIONS = {
    condition: (float(1 / reciprocal_n), float(reciprocal_n))
    for condition, reciprocal_n in RECIPROCAL_VREF_N.items()
}
VREF_TIME_CONDITIONS = {
    **HISTORICAL_VREF_TIME_CONDITIONS,
    **RECIPROCAL_VREF_TIME_CONDITIONS,
}
TIME_CONDITIONS = {
    **LADDER_TIME_CONDITIONS,
    **VREF_TIME_CONDITIONS,
}
MIN_PHASE_DURATION_FRAMES = 1


def reciprocal_condition_metadata(condition):
    reciprocal_n = RECIPROCAL_VREF_N.get(condition)
    if reciprocal_n is None:
        return {}
    low = 1 / reciprocal_n
    return {
        "reciprocal_n": float(reciprocal_n),
        "reciprocal_n_exact": str(reciprocal_n),
        "condition_multiplier_range_exact": [str(low), str(reciprocal_n)],
        "condition_multiplier_range_rational": [
            {"numerator": low.numerator, "denominator": low.denominator},
            {
                "numerator": reciprocal_n.numerator,
                "denominator": reciprocal_n.denominator,
            },
        ],
        "reciprocal_range_product": float(low * reciprocal_n),
    }

PHASES = (
    "open_gripper",
    "corridor_start",
    "pre_grasp",
    "pick_grasp",
    "close_gripper",
    "lift",
)
VREF_PHASES = (
    "start_to_corridor",
    "corridor_to_pregrasp",
    "pregrasp_to_first_close",
    "first_close_to_end",
)
VREF_SIMULATOR_PHASES = (
    "corridor_start",
    "pre_grasp",
    "pick_grasp",
    "close_gripper",
    "lift",
)

BASE_DURATIONS = {
    "open_gripper": 0.8,
    "corridor_start": 2.4,
    "pre_grasp": 3.2,
    "pick_grasp": 1.75,
    "close_gripper": 1.2,
    "lift": 2.5,
}
DEFAULT_V_REF_SOURCE_JSON = Path(
    "outputs/week2_human_phase_reference_p6p7_v2/v_ref_phase_reference.json"
)
DEFAULT_V_REF_GROUP = "P6P7_post_valid_order"
P6_V_REF_GROUP = "P6_target_post_skill1_valid_order"
P7_V_REF_GROUP = "P7_target_post_skill2_valid_order"
_CLOSE_LIFT_TOTAL = BASE_DURATIONS["close_gripper"] + BASE_DURATIONS["lift"]
VREF_CLOSE_FRACTION = BASE_DURATIONS["close_gripper"] / _CLOSE_LIFT_TOTAL
SIMULATOR_PHASE_MAPPING = {
    "start_to_corridor": {
        "simulator_phases": ["corridor_start"],
        "rule": "use the near-zero human event duration for the fixed random_start-to-corridor_start setup motion; no long artificial setup phase",
    },
    "corridor_to_pregrasp": {
        "simulator_phases": ["pre_grasp"],
        "rule": "assign the full human event duration to move_ee(corridor_start -> pre_grasp)",
    },
    "pregrasp_to_first_close": {
        "simulator_phases": ["pick_grasp"],
        "rule": "assign the full human event duration to descend from pre_grasp to grasp, ending at close onset",
    },
    "first_close_to_end": {
        "simulator_phases": ["close_gripper", "lift"],
        "rule": "split the human event duration between close_gripper and lift using the legacy close:lift duration ratio 1.2:2.5",
        "close_fraction": float(VREF_CLOSE_FRACTION),
        "lift_fraction": float(1.0 - VREF_CLOSE_FRACTION),
    },
}


def sample_phase_multipliers(condition, phases=PHASES):
    low, high = TIME_CONDITIONS[condition]
    if abs(low - high) <= 1e-12:
        return {phase: 1.0 for phase in phases}
    return {phase: float(np.random.uniform(low, high)) for phase in phases}


def map_common_uniform(condition, common_u):
    reciprocal_n = RECIPROCAL_VREF_N[condition]
    low = 1 / reciprocal_n
    return float(low) + float(common_u) * (float(reciprocal_n) - float(low))


def file_sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_collection_manifest(path):
    path = Path(path)
    with open(path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    expected_order = list(RECIPROCAL_VREF_N)
    if manifest.get("schema_version") != 2:
        raise ValueError(f"{path}: expected collection manifest schema_version=2")
    if manifest.get("condition_order") != expected_order:
        raise ValueError(f"{path}: condition_order must be {expected_order}")
    candidates = manifest.get("candidates", [])
    if len(candidates) != int(manifest.get("num_candidates", -1)):
        raise ValueError(f"{path}: candidate count disagrees with num_candidates")
    ids = [candidate.get("candidate_id") for candidate in candidates]
    if len(ids) != len(set(ids)):
        raise ValueError(f"{path}: duplicate candidate IDs")
    return manifest, file_sha256(path)


def load_v_ref_group_record(v_ref_source_json, group):
    source_path = Path(v_ref_source_json)
    with open(source_path, "r", encoding="utf-8") as f:
        reference = json.load(f)
    record = reference.get("groups", {}).get(group)
    if record is None:
        raise KeyError(f"{group!r} not found in {source_path}")
    durations = record.get("phase_mean_durations_s", {})
    missing = [phase for phase in VREF_PHASES if phase not in durations]
    if missing:
        raise KeyError(f"{source_path} group {group!r} missing phases: {missing}")
    return {
        "group": group,
        "n": int(record["n"]),
        "phase_mean_durations_s": {phase: float(durations[phase]) for phase in VREF_PHASES},
    }


def paired_p6_p7_duration_inputs(v_ref_source_json, condition, candidate_spec):
    uniforms = candidate_spec["common_uniforms"]
    stored = candidate_spec["condition_group_multipliers"][condition]
    group_multipliers = {
        "P6": map_common_uniform(condition, uniforms["P6"]),
        "P7": map_common_uniform(condition, uniforms["P7"]),
    }
    for group in ("P6", "P7"):
        if not math.isclose(group_multipliers[group], float(stored[group]), abs_tol=1e-15):
            raise ValueError(
                f"{candidate_spec['candidate_id']}: stored {group} multiplier does not map from common U"
            )
    p6 = load_v_ref_group_record(v_ref_source_json, P6_V_REF_GROUP)
    p7 = load_v_ref_group_record(v_ref_source_json, P7_V_REF_GROUP)
    total_n = p6["n"] + p7["n"]
    pooled = {
        phase: (
            p6["n"] * p6["phase_mean_durations_s"][phase]
            + p7["n"] * p7["phase_mean_durations_s"][phase]
        )
        / total_n
        for phase in VREF_PHASES
    }
    scaled = {
        phase: (
            p6["n"] * p6["phase_mean_durations_s"][phase] * group_multipliers["P6"]
            + p7["n"] * p7["phase_mean_durations_s"][phase] * group_multipliers["P7"]
        )
        / total_n
        for phase in VREF_PHASES
    }
    effective = {phase: scaled[phase] / pooled[phase] for phase in VREF_PHASES}
    return pooled, effective, group_multipliers, {"P6": p6, "P7": p7}


def phase_duration_plan(multipliers, sample_period):
    min_duration = float(MIN_PHASE_DURATION_FRAMES) * float(sample_period)
    before = {
        phase: float(BASE_DURATIONS[phase] * multipliers[phase])
        for phase in PHASES
    }
    after = {
        phase: max(duration, min_duration)
        for phase, duration in before.items()
    }
    before_frames = {
        phase: 0 if duration <= 0.0 else int(math.ceil(duration / float(sample_period) - 1e-12))
        for phase, duration in before.items()
    }
    after_frames = {
        phase: max(MIN_PHASE_DURATION_FRAMES, int(math.ceil(duration / float(sample_period) - 1e-12)))
        for phase, duration in after.items()
    }
    clamped = {
        phase: after[phase] > before[phase] + 1e-12
        for phase in PHASES
    }
    return before, after, before_frames, after_frames, clamped, min_duration


def load_v_ref_phase_durations(v_ref_source_json, v_ref_group):
    source_path = Path(v_ref_source_json)
    with open(source_path, "r", encoding="utf-8") as f:
        reference = json.load(f)
    groups = reference.get("groups", {})
    if v_ref_group not in groups:
        raise KeyError(f"{v_ref_group!r} not found in {source_path}")
    durations = groups[v_ref_group].get("phase_mean_durations_s", {})
    missing = [phase for phase in VREF_PHASES if phase not in durations]
    if missing:
        raise KeyError(f"{source_path} group {v_ref_group!r} missing phases: {missing}")
    return {phase: float(durations[phase]) for phase in VREF_PHASES}


def vref_duration_plan(v_ref_phase_durations, multipliers, sample_period):
    min_duration = float(MIN_PHASE_DURATION_FRAMES) * float(sample_period)
    target_phase_durations = {
        phase: float(v_ref_phase_durations[phase] * multipliers[phase])
        for phase in VREF_PHASES
    }
    target_phase_durations_after_clamp = {
        phase: max(duration, min_duration)
        for phase, duration in target_phase_durations.items()
    }
    target_phase_duration_frames = {
        phase: max(MIN_PHASE_DURATION_FRAMES, int(math.ceil(duration / float(sample_period) - 1e-12)))
        for phase, duration in target_phase_durations_after_clamp.items()
    }
    phase_duration_clamped = {
        phase: target_phase_durations_after_clamp[phase] > target_phase_durations[phase] + 1e-12
        for phase in VREF_PHASES
    }

    sim_before = {
        "corridor_start": target_phase_durations["start_to_corridor"],
        "pre_grasp": target_phase_durations["corridor_to_pregrasp"],
        "pick_grasp": target_phase_durations["pregrasp_to_first_close"],
        "close_gripper": target_phase_durations["first_close_to_end"] * VREF_CLOSE_FRACTION,
        "lift": target_phase_durations["first_close_to_end"] * (1.0 - VREF_CLOSE_FRACTION),
    }
    sim_after = {
        phase: max(duration, min_duration)
        for phase, duration in sim_before.items()
    }
    sim_before_frames = {
        phase: 0 if duration <= 0.0 else int(math.ceil(duration / float(sample_period) - 1e-12))
        for phase, duration in sim_before.items()
    }
    sim_after_frames = {
        phase: max(MIN_PHASE_DURATION_FRAMES, int(math.ceil(duration / float(sample_period) - 1e-12)))
        for phase, duration in sim_after.items()
    }
    sim_clamped = {
        phase: sim_after[phase] > sim_before[phase] + 1e-12
        for phase in VREF_SIMULATOR_PHASES
    }
    v_ref_simulator_reference = {
        "corridor_start": float(v_ref_phase_durations["start_to_corridor"]),
        "pre_grasp": float(v_ref_phase_durations["corridor_to_pregrasp"]),
        "pick_grasp": float(v_ref_phase_durations["pregrasp_to_first_close"]),
        "close_gripper": float(v_ref_phase_durations["first_close_to_end"] * VREF_CLOSE_FRACTION),
        "lift": float(v_ref_phase_durations["first_close_to_end"] * (1.0 - VREF_CLOSE_FRACTION)),
    }
    return {
        "min_phase_duration_seconds": min_duration,
        "target_phase_durations_s": target_phase_durations,
        "target_phase_durations_after_clamp_s": target_phase_durations_after_clamp,
        "target_phase_duration_frames": target_phase_duration_frames,
        "phase_duration_clamped": phase_duration_clamped,
        "target_simulator_phase_durations_before_clamp_s": sim_before,
        "target_simulator_phase_durations_s": sim_after,
        "target_simulator_phase_duration_frames_before_clamp": sim_before_frames,
        "target_simulator_phase_duration_frames": sim_after_frames,
        "simulator_phase_duration_clamped": sim_clamped,
        "v_ref_simulator_reference_durations_s": v_ref_simulator_reference,
    }


class TimeMvpSim(PandaSim):
    def run_pick_and_lift_time_mvp(
        self,
        condition_label="T00",
        corridor_start_radius=0.05,
        pre_grasp_radius=0.0,
        entry_dx=0.20,
        corridor_start_y=0.15,
        entry_dz=0.06,
        random_start=(0.40, 0.0, 0.40),
        random_start_max_attempts=200,
        success_lift_height=0.20,
        v_ref_source_json=DEFAULT_V_REF_SOURCE_JSON,
        v_ref_group=DEFAULT_V_REF_GROUP,
        candidate_spec=None,
        collection_manifest_metadata=None,
    ):
        if condition_label not in TIME_CONDITIONS:
            raise ValueError(f"Unknown temporal condition {condition_label!r}")
        if abs(float(pre_grasp_radius)) > 1e-12:
            raise ValueError("Temporal MVP fixes pre_grasp_radius at 0.0.")
        if condition_label in VREF_TIME_CONDITIONS:
            return self.run_pick_and_lift_time_vref(
                condition_label=condition_label,
                corridor_start_radius=corridor_start_radius,
                pre_grasp_radius=pre_grasp_radius,
                entry_dx=entry_dx,
                corridor_start_y=corridor_start_y,
                entry_dz=entry_dz,
                random_start=random_start,
                random_start_max_attempts=random_start_max_attempts,
                success_lift_height=success_lift_height,
                v_ref_source_json=v_ref_source_json,
                v_ref_group=v_ref_group,
                candidate_spec=candidate_spec,
                collection_manifest_metadata=collection_manifest_metadata,
            )

        cube = self.cube_pos()
        print(f"Cube at: {cube}")

        random_start = np.asarray(random_start, dtype=float)
        random_start, random_start_q, random_start_info = self.sample_reachable_random_start(
            x_bounds=(random_start[0], random_start[0]),
            z_bounds=(random_start[2], random_start[2]),
            max_attempts=random_start_max_attempts,
        )
        self.reset_to_ee_pose(random_start_q, gripper_width=0.04)

        base_pre_grasp = np.array([cube[0], cube[1], 0.22])
        base_corridor_start = np.array(
            [cube[0] - float(entry_dx), float(corridor_start_y), base_pre_grasp[2] + float(entry_dz)]
        )
        delta_start = np.zeros(3, dtype=float)
        delta_pre = np.zeros(3, dtype=float)
        corridor_start = base_corridor_start + delta_start
        pre_grasp = base_pre_grasp + delta_pre
        grasp = np.array([cube[0], cube[1], 0.04])
        lift = np.array([cube[0], cube[1], 0.30])

        waypoints_ok = {
            "corridor_start": self.ik_reachable(corridor_start),
            "pre_grasp": self.ik_reachable(pre_grasp),
            "grasp": self.ik_reachable(grasp),
            "lift": self.ik_reachable(lift),
        }
        multipliers = sample_phase_multipliers(condition_label)
        (
            target_durations_before_clamp,
            target_durations,
            target_duration_frames_before_clamp,
            target_duration_frames,
            phase_duration_clamped,
            min_phase_duration_seconds,
        ) = phase_duration_plan(multipliers, self.sample_period)

        self.write_time_metadata(
            condition_label=condition_label,
            cube=cube,
            random_start=random_start,
            random_start_info=random_start_info,
            base_corridor_start=base_corridor_start,
            corridor_start=corridor_start,
            delta_start=delta_start,
            corridor_start_radius=corridor_start_radius,
            base_pre_grasp=base_pre_grasp,
            pre_grasp=pre_grasp,
            delta_pre=delta_pre,
            pre_grasp_radius=pre_grasp_radius,
            grasp=grasp,
            lift=lift,
            entry_dx=entry_dx,
            corridor_start_y=corridor_start_y,
            entry_dz=entry_dz,
            phase_duration_multipliers=multipliers,
            base_phase_durations=BASE_DURATIONS,
            target_phase_durations_before_clamp=target_durations_before_clamp,
            target_phase_durations=target_durations,
            target_phase_duration_frames_before_clamp=target_duration_frames_before_clamp,
            target_phase_duration_frames=target_duration_frames,
            phase_duration_clamped=phase_duration_clamped,
            min_phase_duration_frames=MIN_PHASE_DURATION_FRAMES,
            min_phase_duration_seconds=min_phase_duration_seconds,
            condition_multiplier_range=TIME_CONDITIONS[condition_label],
            waypoint_reachability=waypoints_ok,
        )
        if not all(waypoints_ok.values()):
            details = {
                "success": False,
                "criterion": "waypoint IK reachability before rollout",
                "waypoint_reachability": waypoints_ok,
            }
            self.write_demo_metadata({"success": details})
            return False, details

        print("1) Save random start")
        self.save_frame(gripper_state=-1.0, phase_name="random_start")

        print("2) Open gripper")
        self.open_gripper(duration=target_durations["open_gripper"], phase_name="open_gripper")

        print("3) Corridor start")
        self.move_ee(
            corridor_start,
            duration=target_durations["corridor_start"],
            gripper_state=-1.0,
            phase_name="corridor_start",
        )

        print("4) Pre-grasp")
        self.move_ee(
            pre_grasp,
            duration=target_durations["pre_grasp"],
            gripper_state=-1.0,
            phase_name="pre_grasp",
        )

        print("5) Descend")
        self.move_ee(
            grasp,
            duration=target_durations["pick_grasp"],
            gripper_state=-1.0,
            phase_name="pick_grasp",
        )

        print("6) Close gripper")
        self.close_gripper(duration=target_durations["close_gripper"], phase_name="close_gripper")

        print("7) Lift")
        self.move_ee(
            lift,
            duration=target_durations["lift"],
            gripper_state=1.0,
            phase_name="lift",
        )

        is_success, success_details = self.success(min_cube_z=success_lift_height)
        self.write_demo_metadata({"success": success_details})
        print(
            "Success check: "
            f"success={is_success}, final_cube_z={success_details['final_cube_z']:.4f} m, "
            f"min_cube_z={success_details['min_cube_z']:.4f} m",
            flush=True,
        )
        return is_success, success_details

    def run_pick_and_lift_time_vref(
        self,
        condition_label,
        corridor_start_radius,
        pre_grasp_radius,
        entry_dx,
        corridor_start_y,
        entry_dz,
        random_start,
        random_start_max_attempts,
        success_lift_height,
        v_ref_source_json,
        v_ref_group,
        candidate_spec=None,
        collection_manifest_metadata=None,
    ):
        cube = self.cube_pos()
        print(f"Cube at: {cube}")

        if condition_label in RECIPROCAL_VREF_N and candidate_spec is None:
            raise ValueError(
                f"Corrected reciprocal condition {condition_label} requires --collection-manifest"
            )
        random_start = np.asarray(
            candidate_spec["random_start"] if candidate_spec is not None else random_start,
            dtype=float,
        )
        random_start, random_start_q, random_start_info = self.sample_reachable_random_start(
            x_bounds=(random_start[0], random_start[0]),
            z_bounds=(random_start[2], random_start[2]),
            max_attempts=random_start_max_attempts,
        )
        self.reset_to_ee_pose(random_start_q, gripper_width=0.04)

        base_pre_grasp = np.array(
            candidate_spec["base_pre_grasp"]
            if candidate_spec is not None
            else [cube[0], cube[1], 0.22],
            dtype=float,
        )
        base_corridor_start = np.array(
            candidate_spec["base_corridor_start"]
            if candidate_spec is not None
            else [cube[0] - float(entry_dx), float(corridor_start_y), base_pre_grasp[2] + float(entry_dz)],
            dtype=float,
        )
        delta_start = np.array(
            candidate_spec["corridor_start_delta"]
            if candidate_spec is not None
            else [0.0, 0.0, 0.0],
            dtype=float,
        )
        delta_pre = np.zeros(3, dtype=float)
        corridor_start = base_corridor_start + delta_start
        pre_grasp = base_pre_grasp + delta_pre
        grasp = np.array([cube[0], cube[1], 0.04])
        lift = np.array([cube[0], cube[1], 0.30])

        waypoints_ok = {
            "corridor_start": self.ik_reachable(corridor_start),
            "pre_grasp": self.ik_reachable(pre_grasp),
            "grasp": self.ik_reachable(grasp),
            "lift": self.ik_reachable(lift),
        }
        group_multipliers = None
        group_references = None
        if candidate_spec is not None:
            (
                v_ref_phase_durations,
                multipliers,
                group_multipliers,
                group_references,
            ) = paired_p6_p7_duration_inputs(v_ref_source_json, condition_label, candidate_spec)
        else:
            v_ref_phase_durations = load_v_ref_phase_durations(v_ref_source_json, v_ref_group)
            multipliers = sample_phase_multipliers(condition_label, phases=VREF_PHASES)
        duration_plan = vref_duration_plan(v_ref_phase_durations, multipliers, self.sample_period)

        self.write_vref_time_metadata(
            condition_label=condition_label,
            cube=cube,
            random_start=random_start,
            random_start_info=random_start_info,
            base_corridor_start=base_corridor_start,
            corridor_start=corridor_start,
            delta_start=delta_start,
            corridor_start_radius=corridor_start_radius,
            base_pre_grasp=base_pre_grasp,
            pre_grasp=pre_grasp,
            delta_pre=delta_pre,
            pre_grasp_radius=pre_grasp_radius,
            grasp=grasp,
            lift=lift,
            entry_dx=entry_dx,
            corridor_start_y=corridor_start_y,
            entry_dz=entry_dz,
            v_ref_source_json=v_ref_source_json,
            v_ref_group=v_ref_group,
            v_ref_phase_durations=v_ref_phase_durations,
            sampled_phase_multipliers=multipliers,
            duration_plan=duration_plan,
            condition_multiplier_range=TIME_CONDITIONS[condition_label],
            waypoint_reachability=waypoints_ok,
            candidate_spec=candidate_spec,
            collection_manifest_metadata=collection_manifest_metadata,
            sampled_group_multipliers=group_multipliers,
            group_references=group_references,
        )
        if not all(waypoints_ok.values()):
            details = {
                "success": False,
                "criterion": "waypoint IK reachability before rollout",
                "waypoint_reachability": waypoints_ok,
            }
            self.write_demo_metadata({"success": details})
            return False, details

        durations = duration_plan["target_simulator_phase_durations_s"]

        print("1) Save random start")
        self.save_frame(gripper_state=-1.0, phase_name="random_start")

        print("2) Corridor start (v_ref start_to_corridor)")
        self.move_ee(
            corridor_start,
            duration=durations["corridor_start"],
            gripper_state=-1.0,
            phase_name="corridor_start",
        )

        print("3) Pre-grasp (v_ref corridor_to_pregrasp)")
        self.move_ee(
            pre_grasp,
            duration=durations["pre_grasp"],
            gripper_state=-1.0,
            phase_name="pre_grasp",
        )

        print("4) Descend (v_ref pregrasp_to_first_close)")
        self.move_ee(
            grasp,
            duration=durations["pick_grasp"],
            gripper_state=-1.0,
            phase_name="pick_grasp",
        )

        print("5) Close gripper (v_ref first_close_to_end split)")
        self.close_gripper(duration=durations["close_gripper"], phase_name="close_gripper")

        print("6) Lift (v_ref first_close_to_end split)")
        self.move_ee(
            lift,
            duration=durations["lift"],
            gripper_state=1.0,
            phase_name="lift",
        )

        is_success, success_details = self.success(min_cube_z=success_lift_height)
        self.write_demo_metadata({"success": success_details})
        print(
            "Success check: "
            f"success={is_success}, final_cube_z={success_details['final_cube_z']:.4f} m, "
            f"min_cube_z={success_details['min_cube_z']:.4f} m",
            flush=True,
        )
        return is_success, success_details

    def write_time_metadata(
        self,
        condition_label,
        cube,
        random_start,
        random_start_info,
        base_corridor_start,
        corridor_start,
        delta_start,
        corridor_start_radius,
        base_pre_grasp,
        pre_grasp,
        delta_pre,
        pre_grasp_radius,
        grasp,
        lift,
        entry_dx,
        corridor_start_y,
        entry_dz,
        phase_duration_multipliers,
        base_phase_durations,
        target_phase_durations_before_clamp,
        target_phase_durations,
        target_phase_duration_frames_before_clamp,
        target_phase_duration_frames,
        phase_duration_clamped,
        min_phase_duration_frames,
        min_phase_duration_seconds,
        condition_multiplier_range,
        waypoint_reachability,
    ):
        metadata = {
            "task": "cube_grasp_lift_time_mvp",
            "experiment_track": "temporal",
            "condition": condition_label,
            "condition_label": condition_label,
            "sample_hz": float(self.sample_hz),
            "sample_period": float(self.sample_period),
            "condition_multiplier_range": [float(v) for v in condition_multiplier_range],
            "phase_duration_multipliers": {k: float(v) for k, v in phase_duration_multipliers.items()},
            "base_phase_durations": {k: float(v) for k, v in base_phase_durations.items()},
            "target_phase_durations_before_clamp": {
                k: float(v) for k, v in target_phase_durations_before_clamp.items()
            },
            "target_phase_durations": {k: float(v) for k, v in target_phase_durations.items()},
            "target_phase_duration_frames_before_clamp": {
                k: int(v) for k, v in target_phase_duration_frames_before_clamp.items()
            },
            "target_phase_duration_frames": {k: int(v) for k, v in target_phase_duration_frames.items()},
            "phase_duration_clamped": {k: bool(v) for k, v in phase_duration_clamped.items()},
            "min_phase_duration_frames": int(min_phase_duration_frames),
            "min_phase_duration_seconds": float(min_phase_duration_seconds),
            "phase_duration_clamp_rule": "target_phase_duration_seconds = max(raw_duration_seconds, min_phase_duration_frames / sample_hz)",
            "timing_applied_phases": list(PHASES),
            "orientation_mode": "default_full_trajectory",
            "default_quat_xyzw": list(self.default_orientation_quat),
            "cube_position": cube.tolist(),
            "random_start": random_start.tolist(),
            "random_start_info": random_start_info,
            "base_corridor_start": base_corridor_start.tolist(),
            "corridor_start": corridor_start.tolist(),
            "corridor_start_delta": delta_start.tolist(),
            "corridor_start_radius": float(corridor_start_radius),
            "base_pre_grasp": base_pre_grasp.tolist(),
            "pre_grasp": pre_grasp.tolist(),
            "pre_grasp_delta": delta_pre.tolist(),
            "pre_grasp_radius": float(pre_grasp_radius),
            "grasp": grasp.tolist(),
            "lift": lift.tolist(),
            "entry_dx": float(entry_dx),
            "corridor_start_y": float(corridor_start_y),
            "entry_dz": float(entry_dz),
            "waypoint_reachability": waypoint_reachability,
        }
        self.write_demo_metadata(metadata)

    def write_vref_time_metadata(
        self,
        condition_label,
        cube,
        random_start,
        random_start_info,
        base_corridor_start,
        corridor_start,
        delta_start,
        corridor_start_radius,
        base_pre_grasp,
        pre_grasp,
        delta_pre,
        pre_grasp_radius,
        grasp,
        lift,
        entry_dx,
        corridor_start_y,
        entry_dz,
        v_ref_source_json,
        v_ref_group,
        v_ref_phase_durations,
        sampled_phase_multipliers,
        duration_plan,
        condition_multiplier_range,
        waypoint_reachability,
        candidate_spec=None,
        collection_manifest_metadata=None,
        sampled_group_multipliers=None,
        group_references=None,
    ):
        metadata = {
            "task": "cube_grasp_lift_time_mvp",
            "experiment_track": "temporal_v_ref",
            "time_condition_family": "v_ref_p6p7_event_phases",
            "condition": condition_label,
            "condition_label": condition_label,
            "sample_hz": float(self.sample_hz),
            "sample_period": float(self.sample_period),
            "v_ref_source_json": str(Path(v_ref_source_json)),
            "v_ref_group": str(v_ref_group),
            "v_ref_phase_order": list(VREF_PHASES),
            "v_ref_phase_durations_s": {k: float(v) for k, v in v_ref_phase_durations.items()},
            "v_ref_simulator_reference_durations_s": {
                k: float(v) for k, v in duration_plan["v_ref_simulator_reference_durations_s"].items()
            },
            "condition_multiplier_range": [float(v) for v in condition_multiplier_range],
            "sampled_phase_multipliers": {k: float(v) for k, v in sampled_phase_multipliers.items()},
            "target_phase_durations_s": {
                k: float(v) for k, v in duration_plan["target_phase_durations_s"].items()
            },
            "target_phase_durations_after_clamp_s": {
                k: float(v) for k, v in duration_plan["target_phase_durations_after_clamp_s"].items()
            },
            "target_phase_duration_frames": {
                k: int(v) for k, v in duration_plan["target_phase_duration_frames"].items()
            },
            "phase_duration_clamped": {
                k: bool(v) for k, v in duration_plan["phase_duration_clamped"].items()
            },
            "target_simulator_phase_durations_before_clamp_s": {
                k: float(v) for k, v in duration_plan["target_simulator_phase_durations_before_clamp_s"].items()
            },
            "target_simulator_phase_durations_s": {
                k: float(v) for k, v in duration_plan["target_simulator_phase_durations_s"].items()
            },
            "target_simulator_phase_duration_frames_before_clamp": {
                k: int(v) for k, v in duration_plan["target_simulator_phase_duration_frames_before_clamp"].items()
            },
            "target_simulator_phase_duration_frames": {
                k: int(v) for k, v in duration_plan["target_simulator_phase_duration_frames"].items()
            },
            "simulator_phase_duration_clamped": {
                k: bool(v) for k, v in duration_plan["simulator_phase_duration_clamped"].items()
            },
            "min_phase_duration_frames": int(MIN_PHASE_DURATION_FRAMES),
            "min_phase_duration_seconds": float(duration_plan["min_phase_duration_seconds"]),
            "phase_duration_clamp_rule": "target duration is clamped to at least min_phase_duration_frames / sample_hz before simulator execution",
            "timing_applied_phases": list(VREF_PHASES),
            "simulator_timing_applied_phases": list(VREF_SIMULATOR_PHASES),
            "simulator_phase_mapping": SIMULATOR_PHASE_MAPPING,
            "phase_duration_multipliers": {k: float(v) for k, v in sampled_phase_multipliers.items()},
            "base_phase_durations": {k: float(v) for k, v in v_ref_phase_durations.items()},
            "target_phase_durations": {
                k: float(v) for k, v in duration_plan["target_phase_durations_s"].items()
            },
            "orientation_mode": "default_full_trajectory",
            "default_quat_xyzw": list(self.default_orientation_quat),
            "cube_position": cube.tolist(),
            "random_start": random_start.tolist(),
            "random_start_info": random_start_info,
            "base_corridor_start": base_corridor_start.tolist(),
            "corridor_start": corridor_start.tolist(),
            "corridor_start_delta": delta_start.tolist(),
            "corridor_start_radius": float(corridor_start_radius),
            "base_pre_grasp": base_pre_grasp.tolist(),
            "pre_grasp": pre_grasp.tolist(),
            "pre_grasp_delta": delta_pre.tolist(),
            "pre_grasp_radius": float(pre_grasp_radius),
            "grasp": grasp.tolist(),
            "lift": lift.tolist(),
            "entry_dx": float(entry_dx),
            "corridor_start_y": float(corridor_start_y),
            "entry_dz": float(entry_dz),
            "waypoint_reachability": waypoint_reachability,
        }
        metadata.update(reciprocal_condition_metadata(condition_label))
        if candidate_spec is not None:
            metadata.update(
                {
                    "collection_manifest": collection_manifest_metadata,
                    "candidate_id": candidate_spec["candidate_id"],
                    "candidate_index": int(candidate_spec["candidate_index"]),
                    "source_draw_index": int(candidate_spec["source_draw_index"]),
                    "random_start_bounds": candidate_spec["random_start_bounds"],
                    "corridor_disk_latents": candidate_spec["corridor_disk_latents"],
                    "common_uniforms": candidate_spec["common_uniforms"],
                    "sampled_group_multipliers": {
                        group: float(value)
                        for group, value in sampled_group_multipliers.items()
                    },
                    "group_reference_records": group_references,
                    "timing_sampling_protocol": (
                        "P6 and P7 use independent common uniforms; each reciprocal condition "
                        "maps the same uniforms through m=1/n+U*(n-1/n), scales the two "
                        "human group references independently, then pools them by group n"
                    ),
                    "spatial_sampling_protocol": (
                        "shared manifest: reachable y=0 random start; uniform-area XZ corridor "
                        "disk r=0.05*sqrt(U); fixed pre-grasp"
                    ),
                }
            )
        self.write_demo_metadata(metadata)


def parse_args():
    parser = argparse.ArgumentParser(description="Collect cube pick-and-lift temporal-threshold MVP data.")
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--num-demos", type=int, default=1)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--sample-hz", type=float, default=30.0)
    parser.add_argument("--time-condition", choices=sorted(TIME_CONDITIONS), default="T00")
    parser.add_argument("--corridor-start-radius", type=float, default=0.05)
    parser.add_argument("--pre-grasp-radius", type=float, default=0.0)
    parser.add_argument("--entry-dx", type=float, default=0.20)
    parser.add_argument("--corridor-start-y", type=float, default=0.15)
    parser.add_argument("--entry-dz", type=float, default=0.06)
    parser.add_argument("--random-start-x", type=float, default=0.40)
    parser.add_argument("--random-start-z", type=float, default=0.40)
    parser.add_argument("--random-start-max-attempts", type=int, default=200)
    parser.add_argument("--success-lift-height", type=float, default=0.20)
    parser.add_argument("--v-ref-source-json", type=Path, default=DEFAULT_V_REF_SOURCE_JSON)
    parser.add_argument("--v-ref-group", default=DEFAULT_V_REF_GROUP)
    parser.add_argument("--collection-manifest", type=Path, default=None)
    parser.add_argument("--candidate-offset", type=int, default=0)
    parser.add_argument("--allow-candidate-failures", action="store_true")
    parser.add_argument("--max-collection-attempts", type=int, default=0)
    parser.add_argument("--no-gui", action="store_true")
    parser.add_argument("--preview", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    if abs(float(args.pre_grasp_radius)) > 1e-12:
        raise ValueError("Temporal MVP intentionally fixes --pre-grasp-radius at 0.0.")

    random.seed(args.seed)
    np.random.seed(args.seed)

    collection_manifest_metadata = None
    candidate_specs = None
    if args.collection_manifest is not None:
        collection_manifest, manifest_sha256 = load_collection_manifest(args.collection_manifest)
        start = int(args.candidate_offset)
        stop = start + int(args.num_demos)
        candidate_specs = collection_manifest["candidates"][start:stop]
        if len(candidate_specs) != int(args.num_demos):
            raise ValueError(
                f"Requested candidates [{start}:{stop}], but manifest contains "
                f"{len(collection_manifest['candidates'])}"
            )
        collection_manifest_metadata = {
            "path": str(args.collection_manifest.resolve()),
            "sha256": manifest_sha256,
            "schema_version": int(collection_manifest["schema_version"]),
            "seed": int(collection_manifest["seed"]),
        }
    elif args.time_condition in RECIPROCAL_VREF_N:
        raise ValueError(
            f"Corrected reciprocal condition {args.time_condition} requires --collection-manifest"
        )

    max_attempts = args.max_collection_attempts
    if max_attempts <= 0:
        max_attempts = max(args.num_demos * 10, args.num_demos + 10)

    success_count = 0
    attempt_count = 0
    while (
        attempt_count < len(candidate_specs)
        if candidate_specs is not None
        else success_count < args.num_demos
    ):
        if attempt_count >= max_attempts:
            raise RuntimeError(
                f"Collected {success_count}/{args.num_demos} successful demos after "
                f"{attempt_count} attempts."
            )

        candidate_spec = candidate_specs[attempt_count] if candidate_specs is not None else None
        demo_idx = int(candidate_spec["candidate_index"]) if candidate_spec else success_count
        attempt_count += 1
        print(
            f"Collecting demo_{demo_idx}: attempt {attempt_count}/{max_attempts}, "
            f"condition={args.time_condition}",
            flush=True,
        )

        sim = TimeMvpSim(
            gui=not args.no_gui,
            gripper_orientation="default",
            output_dir=args.output_dir,
            sample_hz=args.sample_hz,
        )
        try:
            sim.setup()
            sim.begin_demo(demo_idx)
            if sim.gui and (args.preview or args.output_dir is None):
                sim.start_pcd_viewer()
                sim.show_camera_view()
                sim.update_live_views(force=True)

            is_success, _ = sim.run_pick_and_lift_time_mvp(
                condition_label=args.time_condition,
                corridor_start_radius=args.corridor_start_radius,
                pre_grasp_radius=args.pre_grasp_radius,
                entry_dx=args.entry_dx,
                corridor_start_y=args.corridor_start_y,
                entry_dz=args.entry_dz,
                random_start=(args.random_start_x, 0.0, args.random_start_z),
                random_start_max_attempts=args.random_start_max_attempts,
                success_lift_height=args.success_lift_height,
                v_ref_source_json=args.v_ref_source_json,
                v_ref_group=args.v_ref_group,
                candidate_spec=candidate_spec,
                collection_manifest_metadata=collection_manifest_metadata,
            )
            if is_success:
                if args.output_dir is not None:
                    print(f"Saved demo_{demo_idx} with {sim.frame_index} frames to {sim.demo_dir}")
                success_count += 1
            else:
                failed_dir = sim.demo_dir
                if failed_dir is not None and failed_dir.exists():
                    shutil.rmtree(failed_dir)
                    print(f"Deleted failed demo directory: {failed_dir}", flush=True)
        finally:
            sim.close()

    if candidate_specs is not None and success_count != len(candidate_specs):
        message = f"Manifest batch produced {success_count}/{len(candidate_specs)} successes"
        if not args.allow_candidate_failures:
            raise RuntimeError(message)
        print(f"[WARN] {message}", flush=True)

    print(
        f"Collection complete: {success_count}/{args.num_demos} successful demos "
        f"from {attempt_count} attempts.",
        flush=True,
    )


if __name__ == "__main__":
    main()
