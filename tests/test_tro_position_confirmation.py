import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "examples"))
sys.path.insert(0, str(ROOT / "scripts"))

from eval_abla1_trained_policies import (
    TRO_POSITION_CONFIRMATION_CONDITIONS,
    TRO_POSITION_CONFIRMATION_ORDER,
)
from tro_position_confirmation import (
    CONDITION_ORDER,
    TRAINED_CONDITIONS,
    WANDB_PROJECT,
)
from analyze_tro_position_confirmation import difference


def test_confirmation_has_baseline_and_four_new_training_conditions():
    assert TRO_POSITION_CONFIRMATION_ORDER == CONDITION_ORDER
    assert set(TRAINED_CONDITIONS) == set(CONDITION_ORDER) - {"START25_APP6"}
    assert TRO_POSITION_CONFIRMATION_CONDITIONS["START25_APP6"] == {
        "corridor_start_radius": 0.25,
        "pre_grasp_radius": 0.060,
    }


def test_confirmation_configs_use_tro_mvp_and_early_stopping_budget():
    config_root = (
        ROOT
        / "experiments"
        / "mvp0_position_event"
        / "confirmation_earlystop"
        / "configs"
        / "training"
    )
    if not config_root.exists():
        return
    for condition in TRAINED_CONDITIONS:
        config = json.loads(
            (config_root / f"{condition}.json").read_text(encoding="utf-8")
        )
        assert config["experiment"]["logging"]["wandb_proj_name"] == WANDB_PROJECT
        assert config["train"]["num_epochs"] == 3000
        assert config["experiment"]["save"]["every_n_epochs"] == 20
        assert config["experiment"]["save"]["epochs"] == []
        assert "block0" in config["train"]["data"][0]["path"]


def test_protocol_marks_baseline_reused_and_resume_unsupported():
    protocol_path = (
        ROOT
        / "experiments"
        / "mvp0_position_event"
        / "confirmation_earlystop"
        / "manifests"
        / "protocol.json"
    )
    if not protocol_path.exists():
        return
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    assert protocol["condition_order"] == list(CONDITION_ORDER)
    assert protocol["data_collection_performed"] is False
    assert protocol["training"]["wandb_project"] == WANDB_PROJECT
    assert protocol["training"]["strict_epoch40_resume_supported"] is False
    assert protocol["baseline"]["checkpoint_epoch"] == 80
    assert protocol["baseline"]["retraining_required"] is False
    assert len(protocol["rollout_manifests"]) == 10
    for record in protocol["rollout_manifests"].values():
        assert record["source_sha256"]


def test_confirmation_rollout_manifests_extend_only_condition_order():
    manifest_root = (
        ROOT
        / "experiments"
        / "mvp0_position_event"
        / "confirmation_earlystop"
        / "manifests"
        / "rollout_5seed"
    )
    if not manifest_root.exists():
        return
    for manifest_path in manifest_root.glob("*.json"):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert manifest["condition_order"] == list(CONDITION_ORDER)
        assert manifest["confirmation_reuse"]["state_and_rng_records_unchanged"]
        assert manifest["confirmation_reuse"]["only_condition_order_extended"]


def test_difference_uses_right_minus_left_sign():
    policies = {
        "left": {"inner": {"successes": 3, "rate": 0.3}},
        "right": {"inner": {"successes": 7, "rate": 0.7}},
    }
    row = difference(policies, "left", "right", "inner")
    assert row["success_difference_right_minus_left"] == 4
    assert abs(row["rate_difference_right_minus_left"] - 0.4) < 1e-12
