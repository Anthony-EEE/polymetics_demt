import json
import math
import sys
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "examples"))
sys.path.insert(0, str(ROOT / "scripts"))

from eval_abla1_trained_policies import TRO_POSITION_STAGE2_ORDER, active_conditions
from tro_position_stage2_idood import (
    BANKS,
    CONDITIONS,
    NUM_STATES,
    R_MAX,
    ROLLOUT_SEEDS,
    START_RADII,
    bank_bounds,
    delta_from_normalized,
    evaluator_args,
    manifest_path,
    radius_from_quantile,
    validate_manifests,
)


def test_exact_condition_relative_bounds_and_global_maximum():
    assert R_MAX == 0.40
    assert CONDITIONS == {
        "START15_APP6": 0.15,
        "START35_APP6": 0.35,
        "START25_APP3P6": 0.25,
        "START25_APP6": 0.25,
        "START25_APP8P4": 0.25,
    }
    for radius in START_RADII:
        assert bank_bounds(radius, "id") == (0.0, radius)
        assert bank_bounds(radius, "ood") == (radius, R_MAX)


def test_area_uniform_disk_and_annulus_mappings():
    for radius in START_RADII:
        for quantile in (0.0, 0.25, 0.5, 1.0):
            assert math.isclose(
                radius_from_quantile(radius, "id", quantile),
                radius * math.sqrt(quantile),
            )
            assert math.isclose(
                radius_from_quantile(radius, "ood", quantile),
                math.sqrt(radius**2 + quantile * (R_MAX**2 - radius**2)),
            )
    with np.testing.assert_raises(ValueError):
        radius_from_quantile(0.25, "id", -0.01)


def test_cross_start_normalized_direction_and_family_specific_radius():
    quantile = 0.41
    theta = 1.7
    id_deltas = [
        delta_from_normalized(radius, "id", quantile, theta)
        for radius in START_RADII
    ]
    for radius, delta in zip(START_RADII, id_deltas):
        assert np.isclose(np.linalg.norm(delta[[0, 2]]), radius * math.sqrt(quantile))
        assert np.isclose(math.atan2(delta[2], delta[0]), theta)


def test_new_evaluator_profile_is_independent_but_reuses_stage2_conditions():
    args = evaluator_args(0.25, 1, "id")
    assert args.experiment_profile == "tro_position_stage2_idood"
    assert tuple(active_conditions(args)) == TRO_POSITION_STAGE2_ORDER


def test_exact_manifest_task_and_row_counts():
    assert len(START_RADII) * len(ROLLOUT_SEEDS) * len(BANKS) == 30
    assert 5 * len(CONDITIONS) * len(ROLLOUT_SEEDS) * len(BANKS) == 250
    assert 250 * NUM_STATES == 6250


def test_frozen_manifests_when_present():
    paths = [
        manifest_path(radius, seed, bank)
        for radius in START_RADII
        for seed in ROLLOUT_SEEDS
        for bank in BANKS
    ]
    if not any(path.exists() for path in paths):
        return
    assert all(path.exists() for path in paths)
    report = validate_manifests()
    assert report["manifest_count"] == 30
    assert report["same_start_absolute_pairing"] is True
    assert report["cross_start_normalized_pairing"] is True


def test_start25_conditions_reference_the_same_absolute_manifest():
    if not manifest_path(0.25, 1, "id").exists():
        return
    payload = json.loads(manifest_path(0.25, 1, "id").read_text())
    assert payload["start_support_radius_m"] == 0.25
    assert payload["condition_order"] == list(TRO_POSITION_STAGE2_ORDER)
    assert {
        condition
        for condition, radius in CONDITIONS.items()
        if radius == 0.25
    } == {"START25_APP3P6", "START25_APP6", "START25_APP8P4"}
