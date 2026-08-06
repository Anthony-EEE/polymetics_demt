import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "examples"))

import tro_position_composition as composition
from eval_abla1_trained_policies import (
    TRO_POSITION_COMPOSITION_CONDITIONS,
    TRO_POSITION_COMPOSITION_ORDER,
    active_conditions,
)


def test_scope_is_exact_missing_cells_only():
    assert composition.NEW_CONDITIONS == (
        "START15_APP3P6",
        "START15_APP8P4",
        "START35_APP3P6",
        "START35_APP8P4",
    )
    assert "APP4P8" not in " ".join(composition.CONDITION_ORDER)
    assert len(composition.CONDITION_ORDER) == 9
    assert set(composition.NEW_CONDITIONS).isdisjoint(
        set(composition.AXIAL_CONDITIONS)
    )


def test_condition_order_is_frozen_row_major():
    assert composition.CONDITION_ORDER == (
        "START15_APP3P6", "START15_APP6", "START15_APP8P4",
        "START25_APP3P6", "START25_APP6", "START25_APP8P4",
        "START35_APP3P6", "START35_APP6", "START35_APP8P4",
    )
    assert TRO_POSITION_COMPOSITION_ORDER == composition.CONDITION_ORDER


def test_composition_profile_is_independent_and_complete():
    args = argparse.Namespace(experiment_profile="tro_position_composition")
    assert active_conditions(args) == TRO_POSITION_COMPOSITION_CONDITIONS
    assert tuple(active_conditions(args)) == composition.CONDITION_ORDER


def test_active_latents_are_exact_final_30_and_fallbacks_are_active():
    expected_namespaces = {
        1: "formal_fallback", 2: "formal", 3: "formal",
        4: "formal", 5: "formal_fallback",
    }
    for seed in composition.SEEDS:
        records, info = composition.accepted_latents(seed)
        assert len(records) == 30
        assert len({row["candidate_index"] for row in records}) == 30
        assert info["source_namespace"] == expected_namespaces[seed]
        assert len(info["paired_latent_manifest_sha256"]) == 64


def test_corner_offsets_preserve_planes_and_bounds():
    for seed in composition.SEEDS:
        records, _ = composition.accepted_latents(seed)
        for record in records:
            for condition in composition.NEW_CONDITIONS:
                start_radius, approach_radius = composition.CONDITIONS[condition]
                start = composition.disk_offset(
                    record["start_angle"], record["start_radial_quantile"],
                    start_radius, "xz"
                )
                approach = composition.disk_offset(
                    record["approach_angle"],
                    record["approach_radial_quantile"],
                    approach_radius, "xy"
                )
                assert np.isclose(start[1], 0.0)
                assert np.isclose(approach[2], 0.0)
                assert np.linalg.norm(start) <= start_radius + 1e-12
                assert np.linalg.norm(approach) <= approach_radius + 1e-12


def test_expected_counts_and_seed_aliases():
    assert composition.SEEDS == {
        1: {"collection": 1, "training": 1},
        2: {"collection": 2, "training": 2},
        3: {"collection": 3, "training": 3},
        4: {"collection": 1702, "training": 2702},
        5: {"collection": 1701, "training": 2701},
    }
    assert len(composition.NEW_CONDITIONS) * len(composition.SEEDS) == 20
    assert 20 * 30 == 600
    assert 20 * 5 * 2 == 200


def test_v2_attempt_seed_derivation_is_exact_and_deterministic():
    base = 305419896
    assert composition.composition_attempt_seed(base, 0) == base
    for attempt_index in (1, 2, 17, 1000):
        message = f"composition-v2:{base}:{attempt_index}".encode("ascii")
        expected = int.from_bytes(
            hashlib.sha256(message).digest()[:4], "big"
        )
        assert (
            composition.composition_attempt_seed(base, attempt_index)
            == expected
        )
        assert (
            composition.composition_attempt_seed(base, attempt_index)
            == composition.composition_attempt_seed(base, attempt_index)
        )


def _fake_staging(root, demo_index, candidate_index, attempt_index):
    staging = composition.attempt_staging_path(
        root, demo_index, candidate_index, attempt_index
    )
    for condition in composition.NEW_CONDITIONS:
        demo = staging / condition / f"demo_{candidate_index}"
        demo.mkdir(parents=True)
        (demo / "payload.txt").write_text(
            f"{condition}:{attempt_index}\n", encoding="utf-8"
        )
    return staging


def _fake_result(demo_index, candidate_index, attempt_index, failed=()):
    base = 123456
    return {
        "schema_version": 2,
        "protocol_id": composition.PROTOCOL_ID,
        "canonical_seed": 1,
        "demo_index": demo_index,
        "candidate_index": candidate_index,
        "accepted_candidate_id": f"candidate_{candidate_index}",
        "base_runtime_seed": base,
        "attempt_index": attempt_index,
        "attempt_runtime_seed": composition.composition_attempt_seed(
            base, attempt_index
        ),
        "condition_results": {
            condition: {
                "success": condition not in set(failed),
                "details": {"condition": condition},
            }
            for condition in composition.NEW_CONDITIONS
        },
        "failed_conditions": list(failed),
        "same_attempt_seed_across_four_corners": True,
    }


def test_atomic_rejection_archives_all_four_and_accepts_no_rows(tmp_path):
    staging = _fake_staging(tmp_path, 0, 7, 0)
    result = _fake_result(
        0, 7, 0, failed=("START35_APP8P4",)
    )
    (staging / "attempt_result.json").write_text(
        json.dumps(result), encoding="utf-8"
    )
    disposition, archive = composition.finalize_attempt(
        tmp_path, staging, result
    )
    assert disposition == "scientific_failure"
    assert archive == composition.failed_bundle_path(tmp_path, 0, 7, 0)
    assert not staging.exists()
    assert all((archive / condition).is_dir()
               for condition in composition.NEW_CONDITIONS)
    assert not (tmp_path / "raw").exists()
    second_disposition, second_archive = composition.finalize_attempt(
        tmp_path, staging, result
    )
    assert (second_disposition, second_archive) == (disposition, archive)


def test_atomic_acceptance_and_crash_resume_are_idempotent(tmp_path):
    staging = _fake_staging(tmp_path, 0, 7, 1)
    result = _fake_result(0, 7, 1)
    (staging / "attempt_result.json").write_text(
        json.dumps(result), encoding="utf-8"
    )
    recovered = composition.attempt_record(
        staging / "attempt_result.json"
    )
    disposition, bundle = composition.finalize_attempt(
        tmp_path, staging, recovered
    )
    assert disposition == "accepted"
    assert bundle == composition.accepted_bundle_path(tmp_path, 0, 7, 1)
    for condition in composition.NEW_CONDITIONS:
        row = tmp_path / "raw" / condition / "demo_0"
        assert row.is_symlink()
        assert row.resolve() == (
            bundle / condition / "demo_7"
        ).resolve()
    second_disposition, second_bundle = composition.finalize_attempt(
        tmp_path, staging, recovered
    )
    assert (second_disposition, second_bundle) == (disposition, bundle)


def test_attempt_provenance_preserves_exact_30_frozen_latents():
    for seed in composition.SEEDS:
        records, _ = composition.accepted_latents(seed)
        original_ids = [int(row["candidate_index"]) for row in records]
        assert len(original_ids) == 30
        assert len(set(original_ids)) == 30
        for attempt_index in (0, 1, 9):
            transformed = [
                composition.attempt_latent(row, attempt_index)
                for row in records
            ]
            assert [
                int(row["candidate_index"]) for row in transformed
            ] == original_ids
            for original, actual in zip(records, transformed):
                composition.assert_frozen_latent_identity(actual, original)
                assert actual["composition_v2"]["attempt_index"] == attempt_index


def test_one_attempt_seed_is_shared_by_all_four_corners():
    latent = composition.accepted_latents(4)[0][2]
    for attempt_index in (0, 1, 2):
        values = [
            composition.attempt_latent(latent, attempt_index)["runtime_seed"]
            for _condition in composition.NEW_CONDITIONS
        ]
        assert len(set(values)) == 1
