import math
import sys
import unittest
from fractions import Fraction
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES_DIR = REPO_ROOT / "examples"
if str(EXAMPLES_DIR) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_DIR))

from main_time_mvp import (  # noqa: E402
    RECIPROCAL_VREF_N,
    RECIPROCAL_VREF_TIME_CONDITIONS,
    VREF_PHASES,
    map_common_uniform,
    paired_p6_p7_duration_inputs,
    reciprocal_condition_metadata,
    sample_phase_multipliers,
)


class ReciprocalVrefDefinitionsTest(unittest.TestCase):
    def test_exact_reciprocal_definitions(self):
        expected = {
            "VR1P5": Fraction(3, 2),
            "V050_200": Fraction(2, 1),
            "VR3": Fraction(3, 1),
            "VR4": Fraction(4, 1),
        }
        self.assertEqual(RECIPROCAL_VREF_N, expected)
        for condition, reciprocal_n in expected.items():
            low, high = RECIPROCAL_VREF_TIME_CONDITIONS[condition]
            self.assertEqual(low, float(1 / reciprocal_n))
            self.assertEqual(high, float(reciprocal_n))
            self.assertTrue(math.isclose(low * high, 1.0, abs_tol=1e-12))
            metadata = reciprocal_condition_metadata(condition)
            self.assertEqual(
                metadata["condition_multiplier_range_exact"],
                [str(1 / reciprocal_n), str(reciprocal_n)],
            )

    def test_each_vref_phase_is_sampled_independently(self):
        draws = [0.7, 0.8, 0.9, 1.0]
        with mock.patch("main_time_mvp.np.random.uniform", side_effect=draws) as uniform:
            sampled = sample_phase_multipliers("VR1P5", phases=VREF_PHASES)
        self.assertEqual(list(sampled.values()), draws)
        self.assertEqual(uniform.call_count, len(VREF_PHASES))
        low, high = RECIPROCAL_VREF_TIME_CONDITIONS["VR1P5"]
        for call in uniform.call_args_list:
            self.assertEqual(call.args, (low, high))

    def test_common_uniform_mapping_uses_exact_reciprocal_endpoints(self):
        for condition, reciprocal_n in RECIPROCAL_VREF_N.items():
            self.assertEqual(map_common_uniform(condition, 0.0), float(1 / reciprocal_n))
            self.assertEqual(map_common_uniform(condition, 1.0), float(reciprocal_n))
        self.assertEqual(map_common_uniform("VR1P5", 0.0), float(Fraction(2, 3)))
        self.assertEqual(map_common_uniform("VR3", 0.0), float(Fraction(1, 3)))

    def test_p6_p7_are_independent_common_uniform_streams(self):
        candidate = {
            "candidate_id": "candidate_0000",
            "common_uniforms": {"P6": 0.125, "P7": 0.875},
            "condition_group_multipliers": {
                condition: {
                    "P6": map_common_uniform(condition, 0.125),
                    "P7": map_common_uniform(condition, 0.875),
                }
                for condition in RECIPROCAL_VREF_N
            },
        }
        source = REPO_ROOT / "outputs/week2_human_phase_reference_p6p7_v2/v_ref_phase_reference.json"
        pooled, effective, group_multipliers, references = paired_p6_p7_duration_inputs(
            source, "VR4", candidate
        )
        self.assertNotEqual(group_multipliers["P6"], group_multipliers["P7"])
        self.assertEqual(set(references), {"P6", "P7"})
        self.assertEqual(set(pooled), set(VREF_PHASES))
        self.assertEqual(set(effective), set(VREF_PHASES))
        for value in effective.values():
            self.assertGreaterEqual(value, 0.25)
            self.assertLessEqual(value, 4.0)


if __name__ == "__main__":
    unittest.main()
