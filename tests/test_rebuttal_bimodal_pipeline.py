"""Focused deterministic-contract tests for the isolated Bimodal pipeline."""

import json
import random
import sys
from collections import Counter
from pathlib import Path


HELPER_ROOT = Path(__file__).resolve().parents[1] / "examples/rebuttal_bimodal_pipeline"
if str(HELPER_ROOT) not in sys.path:
    sys.path.insert(0, str(HELPER_ROOT))

from common import (  # noqa: E402
    DESIGN_SEED,
    EXPECTED_PAIRS,
    LEFT_SOURCES,
    PARTICIPANTS,
    RIGHT_SOURCES,
    SPLIT_SEED,
    canonical_hash,
)
from analyze_bimodal_results import (  # noqa: E402
    policy_sampling_seed,
    quaternion_distance_degrees,
    recompute_route,
    recompute_success,
    rate,
    vector_distance,
)


def test_frozen_pair_draw_is_exact_unique_stdlib_sample():
    candidates = [(left, right) for left in LEFT_SOURCES for right in RIGHT_SOURCES]
    selected = random.Random(DESIGN_SEED).sample(candidates, 10)
    assert selected == EXPECTED_PAIRS
    assert len(selected) == len(set(selected)) == len(PARTICIPANTS)


def test_each_mixed_shuffle_is_a_complete_30_left_30_right_permutation():
    for b_index, (left, right) in enumerate(EXPECTED_PAIRS, start=1):
        items = [
            (route, source, demo)
            for route, source in (("L", left), ("R", right))
            for demo in range(30)
        ]
        random.Random(DESIGN_SEED + 1000 + b_index).shuffle(items)
        assert Counter(route for route, _, _ in items) == Counter({"L": 30, "R": 30})
        assert len(items) == len(set(items)) == 60
        assert sorted(demo for route, source, demo in items if route == "L") == list(range(30))
        assert sorted(demo for route, source, demo in items if route == "R") == list(range(30))


def test_single_split_stream_produces_27_27_train_and_3_3_valid():
    split_rng = random.Random(SPLIT_SEED)
    for b_index, (left, right) in enumerate(EXPECTED_PAIRS, start=1):
        items = [
            (route, source, demo)
            for route, source in (("L", left), ("R", right))
            for demo in range(30)
        ]
        random.Random(DESIGN_SEED + 1000 + b_index).shuffle(items)
        left_indices = [index for index, row in enumerate(items) if row[0] == "L"]
        right_indices = [index for index, row in enumerate(items) if row[0] == "R"]
        valid = set(
            split_rng.sample(sorted(left_indices), 3)
            + split_rng.sample(sorted(right_indices), 3)
        )
        train = set(range(60)) - valid
        assert Counter(items[index][0] for index in train) == Counter({"L": 27, "R": 27})
        assert Counter(items[index][0] for index in valid) == Counter({"L": 3, "R": 3})


def test_canonical_hash_is_order_invariant_and_content_sensitive():
    left = {"b": [2, 3], "a": 1}
    right = json.loads('{"a": 1, "b": [2, 3]}')
    assert canonical_hash(left) == canonical_hash(right)
    right["b"].append(4)
    assert canonical_hash(left) != canonical_hash(right)


def test_all_200_policy_sampling_seeds_are_unique_and_repeat_specific():
    seeds = {
        policy_sampling_seed(participant, case, repeat)
        for participant in PARTICIPANTS
        for case in range(10)
        for repeat in (0, 1)
    }
    assert len(seeds) == 200
    assert policy_sampling_seed("B01", 0, 0) != policy_sampling_seed("B01", 0, 1)


def test_route_recomputation_uses_band_median_and_retains_indeterminate():
    class Task:
        OBSTACLE_XY = (0.5, 0.25)
        OBSTACLE_RADIUS = 0.04
        BOX_HALF_EXTENT = 0.035

    left_trace = [
        {"box_position": [0.2, 0.18, 0.03]},
        {"box_position": [0.3, 0.24, 0.03]},
        {"box_position": [0.4, 0.26, 0.03]},
    ]
    assert recompute_route(left_trace, Task)["realised_route"] == "L"
    never_reaches_band = [
        {"box_position": [0.9, -0.1, 0.03]},
        {"box_position": [0.9, 0.0, 0.03]},
    ]
    assert recompute_route(never_reaches_band, Task)["realised_route"] == "indeterminate"


def test_zero_route_denominator_is_null_not_zero():
    assert rate(0, 0) is None
    assert rate(1, 2) == 0.5


def test_success_recomputation_checks_target_settling_and_cylinder():
    class Task:
        TARGET_XY = (0.5, 0.5)
        BOX_HALF_EXTENT = 0.025
        CYLINDER_UPRIGHT_TOLERANCE_DEGREES = 10.0

        @staticmethod
        def quaternion_upright_error_degrees(quaternion):
            return float(quaternion[0])

    row = {
        "termination_reason": "success",
        "success_details": {
            "final_box_position": [0.5, 0.5, 0.025],
            "final_box_linear_velocity": [0.0, 0.0, 0.0],
            "final_box_angular_velocity": [0.0, 0.0, 0.0],
            "final_cylinder_quaternion_xyzw": [0.0, 0.0, 0.0, 1.0],
        },
    }
    assert recompute_success(row, Task)["success"] is True
    row["success_details"]["final_box_linear_velocity"] = [0.021, 0.0, 0.0]
    result = recompute_success(row, Task)
    assert result["success"] is False
    assert result["failure_reasons"] == ["box_not_settled"]


def test_repeat_physical_distance_helpers_are_sign_invariant_and_fail_closed():
    assert vector_distance([0.0, 0.0, 0.0], [3e-6, 4e-6, 0.0], 3) == 5e-6
    assert vector_distance([0.0], [0.0], 3) == float("inf")
    assert quaternion_distance_degrees([0.0, 0.0, 0.0, 1.0], [0.0, 0.0, 0.0, -1.0]) == 0.0
    assert quaternion_distance_degrees([], []) == float("inf")
