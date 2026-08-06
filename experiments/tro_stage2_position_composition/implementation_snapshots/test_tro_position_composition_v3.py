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


def test_v3_candidate_generator_matches_all_800_frozen_source_records():
    verification = composition.verify_candidate_stream_sources()
    assert len(verification) == 5
    assert all(row["verified_records"] == 160 for row in verification)
    for seed in composition.SEEDS:
        source = json.loads(
            composition.CANDIDATE_SOURCE_PATHS[seed].read_text(
                encoding="utf-8"
            )
        )["candidates"]
        for candidate_index in (0, 1, 31, 159):
            composition.assert_candidate_stream_identity(
                source[candidate_index],
                composition.generated_candidate(seed, candidate_index),
            )


def test_v3_candidate_stream_extends_deterministically_beyond_159():
    for seed in composition.SEEDS:
        first = composition.v3_candidate(seed, 160)
        second = composition.v3_candidate(seed, 160)
        assert first == second
        assert first["candidate_index"] == 160
        assert first["collection_seed"] == composition.SEEDS[seed]["collection"]
        composition.assert_candidate_stream_identity(
            first, composition.generated_candidate(seed, 160)
        )


def _v3_fake_staging(root, decision_index, demo_index, candidate_index):
    staging = composition.candidate_staging_path(
        root, decision_index, candidate_index
    )
    for condition in composition.NEW_CONDITIONS:
        demo = staging / condition / f"demo_{candidate_index}"
        demo.mkdir(parents=True)
        (demo / "payload.txt").write_text(
            f"{condition}:{candidate_index}\n", encoding="utf-8"
        )
    return staging


def _v3_fake_result(
    decision_index, demo_index, candidate_index, failed=()
):
    latent = composition.generated_candidate(1, candidate_index)
    source = {
        "phase": "candidate_stream_extension",
        "frozen_position": None,
        "old_anchor_paired": False,
    }
    return {
        "schema_version": 3,
        "protocol_id": composition.V3_PROTOCOL_ID,
        "canonical_seed": 1,
        "decision_index": decision_index,
        "demo_index": demo_index,
        "candidate_index": candidate_index,
        "accepted_candidate_id": latent["accepted_candidate_id"],
        "candidate_runtime_seed": latent["runtime_seed"],
        "candidate_source": source,
        "latent": latent,
        "condition_results": {
            condition: {
                "success": condition not in set(failed),
                "details": {"condition": condition},
            }
            for condition in composition.NEW_CONDITIONS
        },
        "failed_conditions": list(failed),
        "same_candidate_across_four_corners": True,
    }


def test_v3_atomic_reject_advances_no_rows_and_preserves_all_corners(tmp_path):
    staging = _v3_fake_staging(tmp_path, 0, 0, 54)
    result = _v3_fake_result(
        0, 0, 54, failed=("START15_APP8P4",)
    )
    (staging / "candidate_result.json").write_text(
        json.dumps(result), encoding="utf-8"
    )
    disposition, archive = composition.finalize_candidate(
        tmp_path, staging, result
    )
    assert disposition == "scientific_failure"
    assert archive == composition.rejected_candidate_bundle_path(
        tmp_path, 0, 54
    )
    assert not (tmp_path / "raw").exists()
    assert all(
        (archive / condition / "demo_54").is_dir()
        for condition in composition.NEW_CONDITIONS
    )
    assert composition.finalize_candidate(
        tmp_path, staging, result
    ) == (disposition, archive)


def test_v3_atomic_accept_and_crash_resume_are_idempotent(tmp_path):
    staging = _v3_fake_staging(tmp_path, 1, 0, 55)
    result = _v3_fake_result(1, 0, 55)
    (staging / "candidate_result.json").write_text(
        json.dumps(result), encoding="utf-8"
    )
    recovered = composition.candidate_record(
        staging / "candidate_result.json"
    )
    disposition, bundle = composition.finalize_candidate(
        tmp_path, staging, recovered
    )
    assert disposition == "accepted"
    for condition in composition.NEW_CONDITIONS:
        row = tmp_path / "raw" / condition / "demo_0"
        assert row.is_symlink()
        assert row.resolve() == (
            bundle / condition / "demo_55"
        ).resolve()
    assert composition.finalize_candidate(
        tmp_path, staging, recovered
    ) == (disposition, bundle)


def test_v3_queue_finishes_frozen_order_then_extends_until_30_accepts():
    frozen, _ = composition.accepted_latents(1)
    progress = {
        "canonical_seed": 1,
        "frozen_cursor": 28,
        "next_extension_candidate_index":
            max(row["candidate_index"] for row in frozen) + 1,
    }
    first, source = composition.next_v3_candidate(progress, frozen)
    assert first["candidate_index"] == frozen[28]["candidate_index"]
    assert source["old_anchor_paired"] is True
    composition.advance_v3_candidate(progress, source)
    second, source = composition.next_v3_candidate(progress, frozen)
    assert second["candidate_index"] == frozen[29]["candidate_index"]
    composition.advance_v3_candidate(progress, source)
    extension, source = composition.next_v3_candidate(progress, frozen)
    assert extension["candidate_index"] == max(
        row["candidate_index"] for row in frozen
    ) + 1
    assert source["old_anchor_paired"] is False

    accepted = []
    rejected = []
    while len(accepted) < 30:
        candidate, source = composition.next_v3_candidate(progress, frozen)
        if candidate["candidate_index"] % 4 == 0:
            rejected.append(candidate["candidate_index"])
        else:
            accepted.append(candidate["candidate_index"])
        composition.advance_v3_candidate(progress, source)
    assert len(accepted) == 30
    assert len(set(accepted)) == 30
    assert set(accepted).isdisjoint(rejected)
    assert accepted[-1] >= progress["next_extension_candidate_index"] - 1


def test_v3_progress_migration_preserves_v2_bytes_and_rejects_frontier(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(composition, "DATA_ROOT", tmp_path / "data")
    run_root = composition.collection_root(1, False)
    run_root.mkdir(parents=True)
    frozen = [
        composition.generated_candidate(1, index) for index in range(30)
    ]
    info = {
        "canonical_seed": 1,
        "source_collection_seed": 1,
        "source_training_seed": 1,
        "paired_latent_manifest_path": "/frozen/source.json",
        "paired_latent_manifest_sha256": "a" * 64,
        "accepted_candidate_indices": list(range(30)),
        "source_progress_path": "/frozen/progress.json",
        "source_progress_sha256": "b" * 64,
        "source_namespace": "test",
    }
    monkeypatch.setattr(
        composition, "accepted_latents", lambda seed: (frozen, info)
    )
    old = {
        "schema_version": 2,
        "protocol_id": composition.PROTOCOL_ID,
        "accepted_candidate_indices": [0, 1],
        "accepted_bundles": [
            {
                "demo_index": index,
                "candidate_index": index,
                "source": "retained_complete_v1_attempt_zero_bundle",
            }
            for index in range(2)
        ],
        "scientific_attempts": [
            {
                "demo_index": 2,
                "candidate_index": 2,
                "attempt_index": attempt,
                "failed_conditions": ["START35_APP8P4"],
                "archived_path": f"/archive/{attempt}",
                "archive_tree_sha256": f"{attempt:064x}",
            }
            for attempt in range(3)
        ],
        "infrastructure_retries": [{"reason": "old retry"}],
    }
    old_path = composition.progress_v2_path(run_root)
    old_path.write_text(json.dumps(old, indent=2) + "\n", encoding="utf-8")
    before = old_path.read_bytes()
    migrated = composition.migrate_v2_progress(1)
    assert old_path.read_bytes() == before
    assert migrated["accepted_candidate_indices"] == [0, 1]
    assert migrated["frozen_cursor"] == 3
    assert migrated["rejected_candidates"][0]["candidate_index"] == 2
    assert (
        migrated["rejected_candidates"][0]
        ["preserved_v2_scientific_attempt_count"]
        == 3
    )
    assert migrated["next_extension_candidate_index"] == 30
    assert composition.migrate_v2_progress(1) == migrated
