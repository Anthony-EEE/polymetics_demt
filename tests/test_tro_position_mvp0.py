import json
import math
import sys
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "examples"))
sys.path.insert(0, str(ROOT / "scripts"))

from main_abla_1 import TRO_POSITION_MVP0_RADII, disk_offset
from tro_position_mvp0 import BANKS, CONDITION_ORDER, CONDITIONS


def test_exact_frozen_condition_radii():
    assert tuple(CONDITIONS) == CONDITION_ORDER
    assert CONDITIONS == TRO_POSITION_MVP0_RADII
    assert CONDITIONS == {
        "START15_APP6": (0.15, 0.060),
        "START35_APP6": (0.35, 0.060),
        "START25_APP3P6": (0.25, 0.036),
        "START25_APP8P4": (0.25, 0.084),
    }


def test_uniform_disk_quantile_mapping_and_planes():
    angle = math.pi / 3.0
    quantile = 0.36
    radius = 0.25
    expected_norm = radius * math.sqrt(quantile)
    xz = disk_offset(angle, quantile, radius, "xz")
    xy = disk_offset(angle, quantile, radius, "xy")
    assert np.isclose(np.linalg.norm(xz), expected_norm)
    assert np.isclose(np.linalg.norm(xy), expected_norm)
    assert xz[1] == 0.0
    assert xy[2] == 0.0
    assert np.allclose(xz[[0, 2]], xy[[0, 1]])


def test_same_latent_preserves_normalized_pairing_across_conditions():
    latent = {
        "start_angle": 1.234,
        "start_radial_quantile": 0.49,
        "approach_angle": 5.678,
        "approach_radial_quantile": 0.81,
    }
    normalized = []
    for start_radius, approach_radius in CONDITIONS.values():
        start = disk_offset(
            latent["start_angle"], latent["start_radial_quantile"], start_radius, "xz"
        )
        approach = disk_offset(
            latent["approach_angle"],
            latent["approach_radial_quantile"],
            approach_radius,
            "xy",
        )
        normalized.append((start / start_radius, approach / approach_radius))
    for start, approach in normalized[1:]:
        assert np.allclose(start, normalized[0][0])
        assert np.allclose(approach, normalized[0][1])


def test_frozen_bank_indices_partition_legacy_fifty():
    reference = BANKS["legacy_seed628_reference_r00_r25_n25_v1"]["indices"]
    outer = BANKS["legacy_seed628_outer_r25_r35_n25_v1"]["indices"]
    assert len(reference) == len(outer) == 25
    assert sorted(reference + outer) == list(range(50))


def test_frozen_latent_manifest_has_required_fields():
    path = ROOT / "experiments/mvp0_position_event/manifests/paired_latents_b0.json"
    if not path.exists():
        return
    manifest = json.loads(path.read_text(encoding="utf-8"))
    assert manifest["condition_order"] == list(CONDITION_ORDER)
    assert len(manifest["candidates"]) >= 30
    required = {
        "candidate_index",
        "start_angle",
        "start_radial_quantile",
        "approach_angle",
        "approach_radial_quantile",
        "collection_seed",
        "runtime_seed",
    }
    assert all(required <= set(candidate) for candidate in manifest["candidates"])


def test_existing_checkpoint_inventory_selects_latest_without_retraining():
    for block in (0, 1):
        path = (
            ROOT
            / "experiments"
            / "mvp0_position_event"
            / "manifests"
            / f"checkpoints_latest_existing_b{block}.json"
        )
        if not path.exists():
            continue
        manifest = json.loads(path.read_text(encoding="utf-8"))
        assert manifest["condition_order"] == list(CONDITION_ORDER)
        assert manifest["retraining_performed"] is False
        for condition in CONDITION_ORDER:
            record = manifest["checkpoints"][condition]
            available_epochs = [
                row["epoch"] for row in record["available_checkpoints"]
            ]
            assert available_epochs == sorted(available_epochs)
            assert record["epoch"] == max(available_epochs)
            assert Path(record["path"]).is_file()


def test_five_seed_rollout_manifests_are_exact_inner_outer_pairs():
    manifest_root = (
        ROOT
        / "experiments"
        / "mvp0_position_event"
        / "manifests"
        / "rollout_5seed"
    )
    if not manifest_root.exists():
        return
    for seed in (628, 629, 630, 631, 632):
        for bank in ("inner", "outer"):
            bank_id = f"tro_pos_seed{seed}_{bank}_n25_v1"
            manifest = json.loads(
                (manifest_root / f"{bank_id}.json").read_text(encoding="utf-8")
            )
            assert manifest["seed"] == seed
            assert manifest["protocol"]["bank_id"] == bank_id
            assert manifest["num_rollouts"] == 25
            assert manifest["condition_order"] == list(CONDITION_ORDER)
            records = manifest["shared_start_records"]
            assert len(records) == 25
            assert len({row["state_id"] for row in records}) == 25
            radii = [row["radial_distance_from_center"] for row in records]
            if bank == "inner":
                assert all(0.0 <= radius <= 0.25 for radius in radii)
            else:
                assert all(0.25 < radius <= 0.35 for radius in radii)
