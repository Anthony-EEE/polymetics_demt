#!/usr/bin/env python3
"""Create the shared spatial/timing candidate manifest for reciprocal v_ref data."""

import argparse
import hashlib
import json
import math
import sys
from fractions import Fraction
from pathlib import Path

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES_DIR = REPO_ROOT / "examples"
if str(EXAMPLES_DIR) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_DIR))

from main_time_mvp import RECIPROCAL_VREF_N, TimeMvpSim  # noqa: E402


CONDITIONS = ("VR1P5", "V050_200", "VR3", "VR4")
BASE_CORRIDOR_START = np.array([0.30, 0.15, 0.28], dtype=float)
BASE_PRE_GRASP = np.array([0.50, 0.50, 0.22], dtype=float)


def stream_seed(seed, label):
    digest = hashlib.sha256(f"{seed}:{label}".encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "little")


def exact_condition_record(condition):
    reciprocal_n = RECIPROCAL_VREF_N[condition]
    low = 1 / reciprocal_n
    return {
        "n": {"numerator": reciprocal_n.numerator, "denominator": reciprocal_n.denominator},
        "n_exact": str(reciprocal_n),
        "bounds": [
            {"numerator": low.numerator, "denominator": low.denominator},
            {"numerator": reciprocal_n.numerator, "denominator": reciprocal_n.denominator},
        ],
        "bounds_exact": [str(low), str(reciprocal_n)],
        "bounds_float": [float(low), float(reciprocal_n)],
    }


def mapped_multiplier(condition, common_u):
    reciprocal_n = RECIPROCAL_VREF_N[condition]
    low = 1 / reciprocal_n
    return float(low) + float(common_u) * (float(reciprocal_n) - float(low))


def ik_info(sim, position, max_error):
    current_q = sim.solve_ik(position, sim.default_orientation_quat)
    saved_q = [
        __import__("pybullet").getJointState(sim.panda, joint)[0]
        for joint in sim.arm_joint_indices
    ]
    sim.reset_arm_joints(current_q)
    realised = sim.ee_pos()
    sim.reset_arm_joints(saved_q)
    error = float(np.linalg.norm(realised - np.asarray(position, dtype=float)))
    return current_q, realised, error, error <= float(max_error)


def create_manifest(seed, num_candidates, max_source_draws, corridor_radius, ik_max_error):
    seeds = {
        name: stream_seed(seed, name)
        for name in ("random_start", "corridor_radius", "corridor_theta", "P6", "P7")
    }
    rngs = {name: np.random.default_rng(value) for name, value in seeds.items()}

    sim = TimeMvpSim(gui=False, output_dir=None, sample_hz=8.0)
    sim.playback_speed = 1000.0
    sim.setup()
    candidates = []
    try:
        for source_index in range(int(max_source_draws)):
            random_start = np.array(
                [
                    rngs["random_start"].uniform(0.2, 0.6),
                    0.0,
                    rngs["random_start"].uniform(0.2, 0.6),
                ],
                dtype=float,
            )
            u_radius = float(rngs["corridor_radius"].uniform())
            u_theta = float(rngs["corridor_theta"].uniform())
            radius = float(corridor_radius) * math.sqrt(u_radius)
            theta = 2.0 * math.pi * u_theta
            corridor_delta = np.array(
                [radius * math.cos(theta), 0.0, radius * math.sin(theta)], dtype=float
            )
            corridor_start = BASE_CORRIDOR_START + corridor_delta
            u_p6 = float(rngs["P6"].uniform())
            u_p7 = float(rngs["P7"].uniform())

            _, realised_random, random_error, random_ok = ik_info(
                sim, random_start, ik_max_error
            )
            _, realised_corridor, corridor_error, corridor_ok = ik_info(
                sim, corridor_start, ik_max_error
            )
            _, realised_pre, pre_error, pre_ok = ik_info(
                sim, BASE_PRE_GRASP, ik_max_error
            )
            if not (random_ok and corridor_ok and pre_ok):
                continue

            candidate_index = len(candidates)
            timing = {}
            for condition in CONDITIONS:
                timing[condition] = {
                    "P6": mapped_multiplier(condition, u_p6),
                    "P7": mapped_multiplier(condition, u_p7),
                }
            candidates.append(
                {
                    "candidate_id": f"candidate_{candidate_index:04d}",
                    "candidate_index": candidate_index,
                    "source_draw_index": source_index,
                    "random_start": random_start.tolist(),
                    "random_start_bounds": {"x": [0.2, 0.6], "y": [0.0, 0.0], "z": [0.2, 0.6]},
                    "corridor_disk_latents": {"u_radius": u_radius, "u_theta": u_theta},
                    "corridor_start_delta": corridor_delta.tolist(),
                    "base_corridor_start": BASE_CORRIDOR_START.tolist(),
                    "corridor_start": corridor_start.tolist(),
                    "corridor_start_radius": float(corridor_radius),
                    "pre_grasp_delta": [0.0, 0.0, 0.0],
                    "base_pre_grasp": BASE_PRE_GRASP.tolist(),
                    "pre_grasp": BASE_PRE_GRASP.tolist(),
                    "pre_grasp_radius": 0.0,
                    "common_uniforms": {"P6": u_p6, "P7": u_p7},
                    "condition_group_multipliers": timing,
                    "ik_validation": {
                        "max_error": float(ik_max_error),
                        "random_start": {
                            "reachable": True,
                            "realised": realised_random.tolist(),
                            "error": random_error,
                        },
                        "corridor_start": {
                            "reachable": True,
                            "realised": realised_corridor.tolist(),
                            "error": corridor_error,
                        },
                        "pre_grasp": {
                            "reachable": True,
                            "realised": realised_pre.tolist(),
                            "error": pre_error,
                        },
                    },
                }
            )
            if len(candidates) == int(num_candidates):
                break
    finally:
        sim.close()

    if len(candidates) != int(num_candidates):
        raise RuntimeError(
            f"Generated only {len(candidates)}/{num_candidates} IK-valid candidates "
            f"from {max_source_draws} source draws"
        )
    p6 = np.asarray([c["common_uniforms"]["P6"] for c in candidates])
    p7 = np.asarray([c["common_uniforms"]["P7"] for c in candidates])
    if np.array_equal(p6, p7) or np.allclose(p6, p7, rtol=0.0, atol=0.0):
        raise RuntimeError("P6 and P7 timing streams are not independent")
    return {
        "schema_version": 2,
        "experiment": "temporal_vref_reciprocal_spatial_v2",
        "seed": int(seed),
        "rng_protocol": "five independent SHA256-derived NumPy Generator streams",
        "rng_stream_seeds": seeds,
        "condition_order": list(CONDITIONS),
        "conditions": {condition: exact_condition_record(condition) for condition in CONDITIONS},
        "spatial_protocol": {
            "random_start": "y=0; x,z uniform on [0.2,0.6], retained only after IK validation",
            "corridor_start": "base + XZ disk; r=0.05*sqrt(U_radius), theta=2*pi*U_theta",
            "corridor_start_radius": float(corridor_radius),
            "pre_grasp_radius": 0.0,
        },
        "timing_protocol": (
            "independent common U_P6 and U_P7; for condition n, "
            "m=1/n+U*(n-1/n); P6 and P7 human references are scaled separately"
        ),
        "num_candidates": len(candidates),
        "candidates": candidates,
    }


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--num-candidates", type=int, default=48)
    parser.add_argument("--max-source-draws", type=int, default=1000)
    parser.add_argument("--corridor-radius", type=float, default=0.05)
    parser.add_argument("--ik-max-error", type=float, default=0.025)
    return parser.parse_args()


def main():
    args = parse_args()
    if not math.isclose(args.corridor_radius, 0.05, abs_tol=1e-12):
        raise ValueError("Corrected reciprocal experiment requires corridor radius exactly 0.05")
    manifest = create_manifest(
        args.seed,
        args.num_candidates,
        args.max_source_draws,
        args.corridor_radius,
        args.ik_max_error,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {args.output} with {len(manifest['candidates'])} IK-valid candidates")


if __name__ == "__main__":
    main()
