import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "examples"))
sys.path.insert(0, str(ROOT / "scripts"))

from eval_abla1_trained_policies import (
    TRO_POSITION_STAGE2_CONDITIONS,
    TRO_POSITION_STAGE2_ORDER,
)
from main_abla_1 import TRO_POSITION_STAGE2_RADII, disk_offset
from tro_position_stage2 import (
    BANKS,
    CANONICAL_SEEDS,
    CONDITIONS,
    CONDITION_ORDER,
    FROZEN_HASHES,
    NEW_DATASET_CONDITIONS,
    NEW_POLICY_CONDITIONS,
    ROLLOUT_SEEDS,
    STAGE1_LATENTS,
    latent_payload,
    slot_plan,
)
from analyze_tro_position_stage2 import classify, contrast_pass


EXPERIMENT = ROOT / "experiments" / "tro_stage2_position_axial_replication"


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_exact_five_condition_radii_and_independent_profile():
    expected = {
        "START15_APP6": (0.15, 0.060),
        "START35_APP6": (0.35, 0.060),
        "START25_APP3P6": (0.25, 0.036),
        "START25_APP6": (0.25, 0.060),
        "START25_APP8P4": (0.25, 0.084),
    }
    assert CONDITIONS == expected
    assert TRO_POSITION_STAGE2_RADII == expected
    assert TRO_POSITION_STAGE2_ORDER == CONDITION_ORDER
    assert {
        key: (
            value["corridor_start_radius"],
            value["pre_grasp_radius"],
        )
        for key, value in TRO_POSITION_STAGE2_CONDITIONS.items()
    } == expected


def test_start_xz_approach_xy_and_uniform_disk_sqrt_mapping():
    angle = math.pi / 5
    quantile = 0.36
    xz = disk_offset(angle, quantile, 0.25, "xz")
    xy = disk_offset(angle, quantile, 0.060, "xy")
    assert xz[1] == 0.0
    assert xy[2] == 0.0
    assert np.isclose(np.linalg.norm(xz), 0.25 * math.sqrt(quantile))
    assert np.isclose(np.linalg.norm(xy), 0.060 * math.sqrt(quantile))


def test_exact_five_condition_normalized_latent_pairing():
    latent = {
        "start_angle": 1.23,
        "start_radial_quantile": 0.49,
        "approach_angle": 4.56,
        "approach_radial_quantile": 0.81,
    }
    normalized = []
    for start_radius, approach_radius in CONDITIONS.values():
        normalized.append(
            (
                disk_offset(
                    latent["start_angle"],
                    latent["start_radial_quantile"],
                    start_radius,
                    "xz",
                )
                / start_radius,
                disk_offset(
                    latent["approach_angle"],
                    latent["approach_radial_quantile"],
                    approach_radius,
                    "xy",
                )
                / approach_radius,
            )
        )
    for start, approach in normalized[1:]:
        assert np.allclose(start, normalized[0][0])
        assert np.allclose(approach, normalized[0][1])


def test_canonical_source_seed_mapping_and_aliases():
    assert CANONICAL_SEEDS[1]["collection"] == 1
    assert CANONICAL_SEEDS[1]["training"] == 1
    assert CANONICAL_SEEDS[2]["collection"] == 2
    assert CANONICAL_SEEDS[2]["training"] == 2
    assert CANONICAL_SEEDS[3]["collection"] == 3
    assert CANONICAL_SEEDS[3]["training"] == 3
    assert CANONICAL_SEEDS[4]["collection"] == 1702
    assert CANONICAL_SEEDS[4]["training"] == 2702
    assert CANONICAL_SEEDS[5]["collection"] == 1701
    assert CANONICAL_SEEDS[5]["training"] == 2701


def test_exact_slot_counts_are_16_9_and_20_5():
    rows = slot_plan()
    assert len(rows) == 25
    assert sum(not row["reused_dataset"] for row in rows) == 16
    assert sum(row["reused_dataset"] for row in rows) == 9
    assert sum(not row["reused_policy"] for row in rows) == 20
    assert sum(row["reused_policy"] for row in rows) == 5
    assert sum(len(value) for value in NEW_DATASET_CONDITIONS.values()) == 16
    assert sum(len(value) for value in NEW_POLICY_CONDITIONS.values()) == 20


def test_seed4_seed5_reference_use_exact_source_accepted_latents():
    for canonical_seed in (4, 5):
        payload = latent_payload(canonical_seed)
        source = json.loads(
            STAGE1_LATENTS[canonical_seed].read_text(encoding="utf-8")
        )
        by_id = {
            int(row["candidate_index"]): row for row in source["candidates"]
        }
        assert payload["locked_to_existing_accepted_records"] is True
        assert len(payload["candidates"]) == 30
        for row in payload["candidates"]:
            original = by_id[int(row["candidate_index"])]
            for field in (
                "start_angle",
                "start_radial_quantile",
                "approach_angle",
                "approach_radial_quantile",
                "collection_seed",
                "runtime_seed",
            ):
                assert row[field] == original[field]


def test_seed1_latents_reconstruct_exact_raw_normalized_offsets():
    payload = latent_payload(1)
    assert payload["locked_to_existing_accepted_records"] is True
    assert len(payload["candidates"]) == 30
    for row in payload["candidates"]:
        source = row["source_exact_offsets"]
        start = disk_offset(
            row["start_angle"], row["start_radial_quantile"], 0.25, "xz"
        )
        approach = disk_offset(
            row["approach_angle"], row["approach_radial_quantile"], 0.060, "xy"
        )
        assert np.allclose(start, source["start_xz"], atol=1e-12)
        assert np.allclose(approach, source["approach_xy"], atol=1e-12)


def test_protocol_and_planned_manifests_have_required_provenance():
    protocol_path = EXPERIMENT / "manifests" / "protocol.json"
    datasets_path = EXPERIMENT / "manifests" / "datasets.json"
    policies_path = EXPERIMENT / "manifests" / "policies.json"
    if not protocol_path.exists():
        return
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    assert protocol["condition_order"] == list(CONDITION_ORDER)
    assert protocol["formal_rollout"]["seeds"] == list(ROLLOUT_SEEDS)
    required = {
        "canonical_seed",
        "source_collection_seed",
        "source_training_seed",
        "reused_dataset",
        "reused_policy",
        "source_artifact_path",
        "source_artifact_sha256",
    }
    for path, key in ((datasets_path, "datasets"), (policies_path, "policies")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert len(payload[key]) == 25
        assert all(required <= set(row) for row in payload[key])


def test_early_stopping_protocol_and_no_fixed_epoch40_seed4():
    protocol_path = EXPERIMENT / "manifests" / "protocol.json"
    if not protocol_path.exists():
        return
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    training = protocol["training"]
    assert training["max_epochs"] == 3000
    assert training["validation_early_stopping_patience"] == 41
    assert training["checkpoint_interval_epochs"] == 20
    assert training["checkpoint_selection"] == (
        "highest numeric emitted model_epoch_*.pth"
    )
    assert training["rollout_based_checkpoint_selection"] is False
    assert training["wandb_project"] == "TRO_MVP"
    for condition in CONDITION_ORDER:
        assert condition in NEW_POLICY_CONDITIONS[4]


def test_highest_emitted_checkpoint_selection_if_frozen():
    path = EXPERIMENT / "manifests" / "checkpoints.json"
    if not path.exists():
        return
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["frozen_before_rollout"] is True
    assert len(payload["checkpoints"]) == 25
    for row in payload["checkpoints"]:
        assert sha256(row["checkpoint_path"]) == row["checkpoint_sha256"]
        if not row["reused_policy"]:
            epochs = [item["epoch"] for item in row["available_checkpoints"]]
            assert row["epoch"] == max(epochs)


def test_rollout_seeds_banks_pairing_and_expected_coverage():
    assert ROLLOUT_SEEDS == (1, 2, 3, 4, 5)
    assert BANKS == ("inner", "outer")
    assert 5 * 5 * 5 * 2 == 250
    assert 25 * 5 * 50 == 6250
    root = EXPERIMENT / "manifests" / "rollout_5seed"
    if not root.exists():
        return
    manifests = list(root.glob("*.json"))
    if not manifests:
        return
    assert len(manifests) == 10
    for seed in ROLLOUT_SEEDS:
        records_by_bank = {}
        for bank in BANKS:
            path = root / f"tro_stage2_seed{seed}_{bank}_n25_v1.json"
            manifest = json.loads(path.read_text(encoding="utf-8"))
            assert manifest["seed"] == seed
            assert manifest["condition_order"] == list(CONDITION_ORDER)
            assert manifest["num_rollouts"] == 25
            records = manifest["shared_start_records"]
            assert len(records) == 25
            assert len({row["state_id"] for row in records}) == 25
            assert all("rng_seed" in row for row in records)
            assert all("point_cloud_rng_seed" in row for row in records)
            radii = [row["radial_distance_from_center"] for row in records]
            if bank == "inner":
                assert all(0.0 <= radius <= 0.25 for radius in radii)
            else:
                assert all(0.25 < radius <= 0.35 for radius in radii)
            records_by_bank[bank] = records
        assert not (
            {row["state_id"] for row in records_by_bank["inner"]}
            & {row["state_id"] for row in records_by_bank["outer"]}
        )


def test_frozen_stage1b_hashes_unchanged():
    for path, expected in FROZEN_HASHES.items():
        assert sha256(path) == expected


def test_contrast_signs_margin_and_classification_rules():
    passing = contrast_pass([0.10, 0.08, 0.06, 0.04, -0.01])
    assert passing["mean_delta"] >= 0.05
    assert passing["positive_slots"] == 4
    assert passing["passed"] is True
    insufficient_signs = contrast_pass([0.20, 0.20, 0.20, -0.01, -0.01])
    assert insufficient_signs["mean_delta"] >= 0.05
    assert insufficient_signs["positive_slots"] == 3
    assert insufficient_signs["passed"] is False
    rankings = {"combined": ["START25_APP3P6", "START25_APP6"]}
    assert classify(passing, passing, rankings) == "strong"
    assert classify(passing, {"passed": False}, rankings) == "partial"
    assert classify({"passed": False}, {"passed": False}, rankings) == (
        "null/unstable"
    )
    nonwinning = {"combined": ["START25_APP6", "START25_APP3P6"]}
    assert classify(passing, passing, nonwinning) == "partial"
