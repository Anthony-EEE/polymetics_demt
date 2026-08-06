#!/usr/bin/env python3
"""Freeze and validate condition-relative ID/OOD Stage 2 rerollout inputs."""

import argparse
import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
import pybullet as pb


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "examples"))

from eval_abla1_trained_policies import (  # noqa: E402
    TRO_POSITION_STAGE2_ORDER,
    evaluation_protocol,
    solve_ik_with_error,
    stream_seed,
)
from main_abla_1 import PandaSim  # noqa: E402


EXPERIMENT = ROOT / "experiments" / "tro_stage2_position_axial_idood_rerollout"
MANIFESTS = EXPERIMENT / "manifests"
ROLLOUT_MANIFESTS = MANIFESTS / "rollout_5seed_rmax40"
PROTOCOL_PATH = MANIFESTS / "protocol_rmax40.json"
CHECKPOINT_REUSE_PATH = MANIFESTS / "checkpoint_reuse_rmax40.json"
FEASIBILITY_AUDIT_PATH = MANIFESTS / "feasibility_audit_rmax40.json"
SOURCE_EXPERIMENT = ROOT / "experiments" / "tro_stage2_position_axial_replication"
SOURCE_MANIFESTS = SOURCE_EXPERIMENT / "manifests"
SOURCE_CHECKPOINTS = SOURCE_MANIFESTS / "checkpoints.json"
SHARED_REGISTRY = ROOT / "experiments" / "shared_artifacts" / "rollout_manifest_registry.json"

CONDITIONS = {
    "START15_APP6": 0.15,
    "START35_APP6": 0.35,
    "START25_APP3P6": 0.25,
    "START25_APP6": 0.25,
    "START25_APP8P4": 0.25,
}
START_RADII = (0.15, 0.25, 0.35)
START_TAGS = {0.15: "start15", 0.25: "start25", 0.35: "start35"}
ROLLOUT_SEEDS = (1, 2, 3, 4, 5)
BANKS = ("id", "ood")
R_MAX = 0.40
PROTOCOL_ID = (
    "tro_stage2_position_axial_condition_relative_idood_rerollout_rmax40_v2"
)
NUM_STATES = 25
CHECKPOINT_MANIFEST_SHA256 = (
    "240a936999281f429dd1b043b19df5bd9291ed478933305a7c051c5183227580"
)
OLD_ANALYSIS = {
    SOURCE_EXPERIMENT / "analysis" / "comparison.json": (
        "c70020fe70ab5aae9959ea990e66a2e2f3c4af4c05f24557a79d64c973ef9113"
    ),
    SOURCE_EXPERIMENT / "analysis" / "summary.md": (
        "825a13e358b01e8707c99e1f19673b01d46df62edbacecce12bff6bbc6684370"
    ),
}
BASE_START = np.asarray([0.30, 0.0, 0.50], dtype=float)
IK_MAX_ERROR = 0.025
SPATIAL_STREAM_TAGS = {"id": 0x49440001, "ood": 0x4F4F4401}


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_frozen_json(path, payload):
    path = Path(path)
    rendered = json.dumps(payload, indent=2) + "\n"
    if path.exists() and path.read_text(encoding="utf-8") != rendered:
        raise ValueError(f"Refusing to overwrite frozen artifact: {path}")
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rendered, encoding="utf-8")


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_commit():
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()


def bank_bounds(start_radius, bank):
    start_radius = float(start_radius)
    if bank == "id":
        return 0.0, start_radius
    if bank == "ood":
        return start_radius, R_MAX
    raise KeyError(bank)


def radius_from_quantile(start_radius, bank, quantile):
    quantile = float(quantile)
    if not 0.0 <= quantile <= 1.0:
        raise ValueError("Area quantile must be in [0, 1]")
    if bank == "id":
        return float(start_radius) * math.sqrt(quantile)
    if bank == "ood":
        return math.sqrt(
            float(start_radius) ** 2
            + quantile * (R_MAX**2 - float(start_radius) ** 2)
        )
    raise KeyError(bank)


def delta_from_normalized(start_radius, bank, quantile, theta):
    radius = radius_from_quantile(start_radius, bank, quantile)
    return np.asarray(
        [radius * math.cos(theta), 0.0, radius * math.sin(theta)], dtype=float
    )


def manifest_id(start_radius, rollout_seed, bank):
    return (
        f"tro_s2_idood_rmax40_{START_TAGS[float(start_radius)]}_"
        f"seed{rollout_seed}_{bank}_n25_v1"
    )


def manifest_path(start_radius, rollout_seed, bank):
    return ROLLOUT_MANIFESTS / f"{manifest_id(start_radius, rollout_seed, bank)}.json"


def evaluator_args(start_radius, rollout_seed, bank, bank_id=None):
    inner, outer = bank_bounds(start_radius, bank)
    return argparse.Namespace(
        experiment_profile="tro_position_stage2_idood",
        conditions=list(TRO_POSITION_STAGE2_ORDER),
        seed=int(rollout_seed),
        num_rollouts=NUM_STATES,
        horizon=200,
        sample_hz=8.0,
        action_gap=2,
        action_dt=0.25,
        terminate_on_success=True,
        success_lift_height=0.20,
        num_points=10000,
        corridor_start_center=BASE_START.tolist(),
        shared_start_radius_min=inner,
        shared_start_radius=outer,
        corridor_start_max_error=IK_MAX_ERROR,
        bank_id=bank_id or manifest_id(start_radius, rollout_seed, bank),
        max_start_sample_attempts=1000,
        gui=False,
        playback_speed=100.0,
    )


def audit_inputs():
    if sha256(SOURCE_CHECKPOINTS) != CHECKPOINT_MANIFEST_SHA256:
        raise ValueError("Unified Stage 2 checkpoint manifest hash changed")
    unified = read_json(SOURCE_CHECKPOINTS)
    if len(unified.get("checkpoints", [])) != 25:
        raise ValueError("Expected exactly 25 frozen Stage 2 checkpoints")
    checkpoint_rows = []
    for row in unified["checkpoints"]:
        path = Path(row["checkpoint_path"])
        actual = sha256(path)
        if actual != row["checkpoint_sha256"]:
            raise ValueError(f"Checkpoint hash mismatch: {path}")
        checkpoint_rows.append(
            {
                "canonical_seed": int(row["canonical_seed"]),
                "condition": row["condition"],
                "path": str(path.resolve()),
                "sha256": actual,
                "epoch": int(row["epoch"]),
            }
        )
    old_hashes = {}
    for path, expected in OLD_ANALYSIS.items():
        actual = sha256(path)
        if actual != expected:
            raise ValueError(f"Completed Stage 2 analysis changed: {path}")
        old_hashes[str(path.resolve())] = actual
    return checkpoint_rows, old_hashes


def freeze_protocol(_args):
    checkpoint_rows, old_hashes = audit_inputs()
    protocol = {
        "schema_version": 1,
        "protocol_id": PROTOCOL_ID,
        "experiment": "tro_stage2_position_axial_idood_rerollout",
        "authority": str((EXPERIMENT / "PLAN.md").resolve()),
        "git_commit_at_freeze": git_commit(),
        "source_experiment": str(SOURCE_EXPERIMENT.resolve()),
        "source_checkpoint_manifest": str(SOURCE_CHECKPOINTS.resolve()),
        "source_checkpoint_manifest_sha256": CHECKPOINT_MANIFEST_SHA256,
        "source_analysis_sha256": old_hashes,
        "condition_order": list(CONDITIONS),
        "conditions": {
            condition: {
                "start_support_radius_m": radius,
                "id_range_m": f"[0.00, {radius:.2f}]",
                "ood_range_m": f"({radius:.2f}, {R_MAX:.2f}]",
            }
            for condition, radius in CONDITIONS.items()
        },
        "global_deployment_boundary_m": R_MAX,
        "formal_rollout": {
            "rollout_seeds": list(ROLLOUT_SEEDS),
            "banks": list(BANKS),
            "states_per_manifest": NUM_STATES,
            "manifest_count": 30,
            "task_count": 250,
            "row_count": 6250,
            "horizon": 200,
            "sample_hz": 8,
            "action_gap": 2,
            "action_dt": 0.25,
            "num_points": 10000,
            "terminate_on_success": True,
            "success": "final cube z >= 0.20 m",
            "videos": False,
        },
        "pairing": {
            "same_start_family": "identical absolute manifest, state order, runtime RNG and point-cloud RNG",
            "cross_start_family": "identical area quantile, XZ direction, normalized state index, runtime RNG and point-cloud RNG",
            "joint_replacement": "one failed IK realization rejects the normalized candidate for all three Start families",
        },
        "analysis": {
            "independent_unit": "dataset-policy slot",
            "primary_presentation": "two-dimensional ID/OOD table and Pareto interpretation",
            "balanced_score": "descriptive condition-relative summary only",
        },
    }
    reuse = {
        "schema_version": 1,
        "status": "verified",
        "training_performed": False,
        "models_copied": False,
        "source_manifest": str(SOURCE_CHECKPOINTS.resolve()),
        "source_manifest_sha256": CHECKPOINT_MANIFEST_SHA256,
        "checkpoints": checkpoint_rows,
        "old_stage2_analysis_sha256": old_hashes,
    }
    write_frozen_json(PROTOCOL_PATH, protocol)
    write_frozen_json(CHECKPOINT_REUSE_PATH, reuse)
    print(json.dumps({"status": "verified", "checkpoints": 25}, indent=2))


def generate_triplet(rollout_seed, bank):
    spatial_rng = np.random.default_rng(
        stream_seed(rollout_seed, 0, SPATIAL_STREAM_TAGS[bank])
    )
    accepted = {radius: [] for radius in START_RADII}
    rejection_log = []
    sim = PandaSim(gui=False, output_dir=None, sample_hz=8.0)
    sim.playback_speed = 100.0
    sim.setup()
    candidate_index = 0
    try:
        while len(accepted[START_RADII[0]]) < NUM_STATES:
            if candidate_index >= NUM_STATES * 1000:
                raise RuntimeError(
                    f"Could not obtain {NUM_STATES} jointly reachable {bank} states"
                )
            quantile = float(spatial_rng.uniform(0.0, 1.0))
            theta = float(spatial_rng.uniform(0.0, 2.0 * math.pi))
            realized = {}
            for radius in START_RADII:
                delta = delta_from_normalized(radius, bank, quantile, theta)
                target = BASE_START + delta
                _, actual, error = solve_ik_with_error(sim, target)
                realized[radius] = {
                    "delta": delta,
                    "target": target,
                    "realised": actual,
                    "error": float(error),
                }
            failed = [
                radius
                for radius in START_RADII
                if realized[radius]["error"] > IK_MAX_ERROR
            ]
            if failed:
                rejection_log.append(
                    {
                        "candidate_index": candidate_index,
                        "area_quantile": quantile,
                        "theta_rad": theta,
                        "failed_start_radii_m": failed,
                        "ik_error_by_start_radius_m": {
                            str(radius): realized[radius]["error"]
                            for radius in START_RADII
                        },
                    }
                )
                candidate_index += 1
                continue
            normalized_index = len(accepted[START_RADII[0]])
            runtime_seed = stream_seed(rollout_seed, normalized_index, 0x52554E)
            point_cloud_seed = stream_seed(
                rollout_seed, normalized_index, 0x504344
            )
            for radius in START_RADII:
                inner, outer = bank_bounds(radius, bank)
                value = realized[radius]
                record = {
                    "rollout_index": normalized_index,
                    "normalized_state_index": normalized_index,
                    "normalized_state_id": (
                        f"tro_s2_idood_rmax40_seed{rollout_seed}_{bank}_"
                        f"normalized_{normalized_index:03d}"
                    ),
                    "state_id": (
                        f"{manifest_id(radius, rollout_seed, bank)}_"
                        f"state_{normalized_index:03d}"
                    ),
                    "candidate_index": candidate_index,
                    "area_quantile": quantile,
                    "theta_rad": theta,
                    "attempts": len(rejection_log) + normalized_index + 1,
                    "max_error": IK_MAX_ERROR,
                    "start_sampling_mode": (
                        "xz_disk" if bank == "id" else "xz_annulus"
                    ),
                    "evaluation_distribution": manifest_id(
                        radius, rollout_seed, bank
                    ),
                    "bank": bank,
                    "start_support_radius_m": radius,
                    "global_max_radius_m": R_MAX,
                    "shared_start_radius_min": inner,
                    "shared_start_radius_max": outer,
                    "shared_start_radius": outer,
                    "normalized_delta": (value["delta"] / outer).tolist(),
                    "corridor_start_delta": value["delta"].tolist(),
                    "radial_distance_from_center": float(
                        np.linalg.norm(value["delta"][[0, 2]])
                    ),
                    "start_angle_rad": theta,
                    "corridor_start": value["target"].tolist(),
                    "realised_start": value["realised"].tolist(),
                    "ik_error": value["error"],
                    "rejected_count": len(rejection_log),
                    "recent_rejections": rejection_log[-10:],
                    "rng_seed": runtime_seed,
                    "point_cloud_rng_seed": point_cloud_seed,
                }
                accepted[radius].append(record)
            candidate_index += 1
    finally:
        if sim.client is not None:
            pb.disconnect(sim.client)
    return accepted, rejection_log, candidate_index


def write_manifest(start_radius, rollout_seed, bank, records, rejections, candidates):
    args = evaluator_args(start_radius, rollout_seed, bank)
    payload = {
        "schema_version": 3,
        "protocol_id": PROTOCOL_ID,
        "condition_order": list(TRO_POSITION_STAGE2_ORDER),
        "start_family": START_TAGS[start_radius].upper(),
        "start_support_radius_m": start_radius,
        "bank": bank,
        "protocol": evaluation_protocol(args),
        "seed": rollout_seed,
        "num_rollouts": NUM_STATES,
        "sample_hz": 8.0,
        "corridor_start_center": BASE_START.tolist(),
        "start_sampling_mode": "xz_disk" if bank == "id" else "xz_annulus",
        "shared_start_radius_min": bank_bounds(start_radius, bank)[0],
        "shared_start_radius_max": bank_bounds(start_radius, bank)[1],
        "shared_start_radius": bank_bounds(start_radius, bank)[1],
        "corridor_start_max_error": IK_MAX_ERROR,
        "max_start_sample_attempts": 1000,
        "evaluation_distribution": manifest_id(start_radius, rollout_seed, bank),
        "joint_triplet_candidate_count": candidates,
        "joint_triplet_rejection_count": len(rejections),
        "joint_triplet_rejections": rejections,
        "shared_corridor_starts": [row["corridor_start"] for row in records],
        "shared_start_records": records,
    }
    write_frozen_json(manifest_path(start_radius, rollout_seed, bank), payload)


def register_manifests(rows):
    registry = (
        read_json(SHARED_REGISTRY)
        if SHARED_REGISTRY.exists()
        else {"schema_version": 1, "artifacts": []}
    )
    existing = {
        row["artifact_id"]: row for row in registry.get("artifacts", [])
    }
    for row in rows:
        old = existing.get(row["artifact_id"])
        if old is not None and old != row:
            raise ValueError(f"Rollout registry conflict: {row['artifact_id']}")
        existing[row["artifact_id"]] = row
    registry["artifacts"] = [existing[key] for key in sorted(existing)]
    write_json(SHARED_REGISTRY, registry)


def generate_manifests(_args):
    protocol_path = PROTOCOL_PATH
    if not protocol_path.exists():
        raise FileNotFoundError("Run freeze-protocol before manifest generation")
    registry_rows = []
    for rollout_seed in ROLLOUT_SEEDS:
        for bank in BANKS:
            paths = [
                manifest_path(radius, rollout_seed, bank)
                for radius in START_RADII
            ]
            if any(path.exists() for path in paths):
                if not all(path.exists() for path in paths):
                    raise ValueError("Incomplete frozen Start-family triplet")
            else:
                accepted, rejected, candidates = generate_triplet(
                    rollout_seed, bank
                )
                for radius in START_RADII:
                    write_manifest(
                        radius,
                        rollout_seed,
                        bank,
                        accepted[radius],
                        rejected,
                        candidates,
                    )
            for radius in START_RADII:
                path = manifest_path(radius, rollout_seed, bank)
                registry_rows.append(
                    {
                        "artifact_id": manifest_id(radius, rollout_seed, bank),
                        "protocol_id": PROTOCOL_ID,
                        "experiment": (
                            "tro_stage2_position_axial_idood_rerollout"
                        ),
                        "path": str(path.resolve()),
                        "sha256": sha256(path),
                        "rollout_seed": rollout_seed,
                        "bank": bank,
                        "start_support_radius_m": radius,
                        "num_states": NUM_STATES,
                        "protocol_sha256": sha256(protocol_path),
                    }
                )
    report = validate_manifests()
    write_frozen_json(
        FEASIBILITY_AUDIT_PATH,
        {
            "schema_version": 1,
            "status": "valid",
            "decision": "proceed_to_rmax40_smoke",
            "authority": str((EXPERIMENT / "PLAN.md").resolve()),
            "protocol_id": PROTOCOL_ID,
            "global_max_radius_m": R_MAX,
            "reachable_conditioned_distribution": True,
            "angle_uniform_after_ik_conditioning_claimed": False,
            "validation": report,
        },
    )
    register_manifests(registry_rows)
    print(json.dumps(report, indent=2))


def validate_manifests():
    paths = sorted(ROLLOUT_MANIFESTS.glob("*.json"))
    if len(paths) != 30:
        raise ValueError(f"Expected 30 manifests, found {len(paths)}")
    total_rejections = 0
    per_manifest = {}
    pooled_quantiles = {bank: [] for bank in BANKS}
    for rollout_seed in ROLLOUT_SEEDS:
        for bank in BANKS:
            normalized_by_radius = {}
            rng_by_radius = {}
            for radius in START_RADII:
                path = manifest_path(radius, rollout_seed, bank)
                payload = read_json(path)
                if payload["protocol"] != evaluation_protocol(
                    evaluator_args(radius, rollout_seed, bank)
                ):
                    raise ValueError(f"{path}: evaluator protocol mismatch")
                records = payload["shared_start_records"]
                if len(records) != NUM_STATES:
                    raise ValueError(f"{path}: state count mismatch")
                if len({row["state_id"] for row in records}) != NUM_STATES:
                    raise ValueError(f"{path}: duplicate state IDs")
                inner, outer = bank_bounds(radius, bank)
                for row in records:
                    value = float(row["radial_distance_from_center"])
                    if bank == "id" and not (inner <= value <= outer + 1e-12):
                        raise ValueError(f"{path}: ID bound violation")
                    if bank == "ood" and not (inner < value <= outer + 1e-12):
                        raise ValueError(f"{path}: OOD bound violation")
                    expected = radius_from_quantile(
                        radius, bank, row["area_quantile"]
                    )
                    if not math.isclose(value, expected, abs_tol=1e-12):
                        raise ValueError(f"{path}: area mapping mismatch")
                    if float(row["ik_error"]) > IK_MAX_ERROR:
                        raise ValueError(f"{path}: IK error violation")
                    pooled_quantiles[bank].append(float(row["area_quantile"]))
                quadrants = np.bincount(
                    np.floor(
                        np.asarray([row["theta_rad"] for row in records])
                        / (math.pi / 2.0)
                    ).astype(int),
                    minlength=4,
                )
                if np.any(quadrants == 0):
                    raise ValueError(
                        f"{path}: RMAX40 requires all four XZ quadrants, "
                        f"got {quadrants.tolist()}"
                    )
                normalized_by_radius[radius] = [
                    (
                        row["normalized_state_index"],
                        row["normalized_state_id"],
                        row["candidate_index"],
                        row["area_quantile"],
                        row["theta_rad"],
                    )
                    for row in records
                ]
                rng_by_radius[radius] = [
                    (row["rng_seed"], row["point_cloud_rng_seed"])
                    for row in records
                ]
                per_manifest[path.name] = {
                    "sha256": sha256(path),
                    "states": len(records),
                    "rejections": int(payload["joint_triplet_rejection_count"]),
                    "radius_min_m": min(
                        row["radial_distance_from_center"] for row in records
                    ),
                    "radius_max_m": max(
                        row["radial_distance_from_center"] for row in records
                    ),
                    "quadrant_counts": quadrants.tolist(),
                }
            if any(
                normalized_by_radius[radius] != normalized_by_radius[START_RADII[0]]
                for radius in START_RADII[1:]
            ):
                raise ValueError("Cross-Start normalized pairing mismatch")
            if any(
                rng_by_radius[radius] != rng_by_radius[START_RADII[0]]
                for radius in START_RADII[1:]
            ):
                raise ValueError("Cross-Start RNG pairing mismatch")
            rejection_counts = {
                read_json(manifest_path(radius, rollout_seed, bank))[
                    "joint_triplet_rejection_count"
                ]
                for radius in START_RADII
            }
            if len(rejection_counts) != 1:
                raise ValueError("Whole-triplet replacement log mismatch")
            total_rejections += rejection_counts.pop()
    pooled_coverage = {}
    for bank, values in pooled_quantiles.items():
        minimum = min(values)
        maximum = max(values)
        if minimum > 0.05 or maximum < 0.95:
            raise ValueError(
                f"{bank}: pooled area quantiles do not cover [0.05, 0.95]"
            )
        pooled_coverage[bank] = {
            "area_quantile_min": minimum,
            "area_quantile_max": maximum,
        }
    return {
        "status": "valid",
        "protocol_id": PROTOCOL_ID,
        "global_max_radius_m": R_MAX,
        "manifest_count": len(paths),
        "total_joint_rejections_across_seed_bank_groups": total_rejections,
        "manifests": per_manifest,
        "same_start_absolute_pairing": True,
        "cross_start_normalized_pairing": True,
        "runtime_and_point_cloud_rng_pairing": True,
        "explicit_gate2_coverage": {
            "all_four_quadrants_per_manifest": True,
            "pooled_area_quantiles": pooled_coverage,
        },
    }


def validate_command(_args):
    print(json.dumps(validate_manifests(), indent=2))


def parse_args():
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("freeze-protocol").set_defaults(func=freeze_protocol)
    commands.add_parser("generate-manifests").set_defaults(func=generate_manifests)
    commands.add_parser("validate-manifests").set_defaults(func=validate_command)
    return parser.parse_args()


def main():
    args = parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
