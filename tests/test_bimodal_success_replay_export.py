import csv
import importlib.util
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "examples/rebuttal_bimodal_pipeline/export_success_replays.py"


def load_module():
    spec = importlib.util.spec_from_file_location("export_success_replays", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_formal_success_counts_and_frozen_random_selection():
    module = load_module()
    successes = module.successful_lr_rows()
    assert {route: len(rows) for route, rows in successes.items()} == {
        "L": 20,
        "R": 53,
    }
    selected = module.select_successes(successes, 20260809)
    assert (
        selected["L"]["participant_id"],
        selected["L"]["eval_case_id"],
        selected["L"]["repeat_index"],
    ) == ("B05", "4", "1")
    assert (
        selected["R"]["participant_id"],
        selected["R"]["eval_case_id"],
        selected["R"]["repeat_index"],
    ) == ("B03", "8", "0")
    orders = module.ordered_success_candidates(successes, 20260809)
    assert (
        orders["R"][1]["participant_id"],
        orders["R"][1]["eval_case_id"],
        orders["R"][1]["repeat_index"],
    ) == ("B04", "8", "0")


def test_intervention_schema_matches_existing_file():
    module = load_module()
    with (REPO / "intervention.csv").open("r", encoding="utf-8", newline="") as stream:
        existing_fields = next(csv.reader(stream))
    assert module.CSV_FIELDS == existing_fields
