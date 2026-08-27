import sys
import unittest
from pathlib import Path

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES_DIR = REPO_ROOT / "examples"
if str(EXAMPLES_DIR) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_DIR))

import main_obstacle_transport_control_participants as control  # noqa: E402
import main_obstacle_transport_target_participants as target  # noqa: E402


class ControlParticipantProtocolTest(unittest.TestCase):
    def test_ten_participants_have_balanced_routes(self):
        control.validate_participant_manifest()
        self.assertEqual(
            list(control.CONTROL_PARTICIPANTS),
            [f"C{index:02d}" for index in range(1, 11)],
        )
        routes = [row["route"] for row in control.CONTROL_PARTICIPANTS.values()]
        self.assertEqual(routes.count("L"), 5)
        self.assertEqual(routes.count("R"), 5)

    def test_cube_starts_match_target_group_exactly(self):
        for demo_index in range(control.NUM_DEMOS_PER_PARTICIPANT):
            self.assertEqual(
                control.shared_cube_start(20260806, demo_index),
                target.shared_cube_start(20260806, demo_index),
            )

    def test_control_waypoints_are_broad_unique_and_non_converging(self):
        for participant_id, participant in control.CONTROL_PARTICIPANTS.items():
            specs = [
                control.participant_task_spec(
                    participant_id,
                    demo_index,
                    0,
                    20260806,
                )
                for demo_index in range(control.NUM_DEMOS_PER_PARTICIPANT)
            ]
            points = np.asarray([spec["middle_waypoint"] for spec in specs])
            spread = control.waypoint_spread(points)
            self.assertEqual(spread["unique_count"], 30)
            self.assertGreater(spread["x_span"], 0.15)
            self.assertGreater(spread["z_span"], 0.075)
            x_low, x_high = control.WAYPOINT_ROUTE_X_BOUNDS[participant["route"]]
            self.assertTrue(np.all(points[:, 0] >= x_low))
            self.assertTrue(np.all(points[:, 0] <= x_high))
            self.assertTrue(np.all(points[:, 1] == control.OBSTACLE_XY[1]))
            self.assertTrue(np.all(points[:, 2] >= control.WAYPOINT_Z_BOUNDS[0]))
            self.assertTrue(np.all(points[:, 2] <= control.WAYPOINT_Z_BOUNDS[1]))
            for spec in specs:
                sampling = spec["waypoint_sampling"]
                self.assertIsNone(spec["participant_waypoint_center"])
                self.assertFalse(sampling["position_consistency_guidance"])
                self.assertFalse(sampling["across_demo_contraction"])
                self.assertEqual(
                    sampling["x_bounds"],
                    list(control.WAYPOINT_ROUTE_X_BOUNDS[participant["route"]]),
                )
                self.assertEqual(
                    sampling["z_bounds"],
                    list(control.WAYPOINT_Z_BOUNDS),
                )

    def test_failed_attempt_replenishment_changes_only_waypoint(self):
        first = control.participant_task_spec("C01", 7, 0, 20260806)
        retry = control.participant_task_spec("C01", 7, 1, 20260806)
        self.assertEqual(first["box_initial_position"], retry["box_initial_position"])
        self.assertNotEqual(first["middle_waypoint"], retry["middle_waypoint"])
        self.assertEqual(first["group"], "simulation_control_group")
        self.assertEqual(retry["group"], "simulation_control_group")

    def test_single_demo_spread_is_finite(self):
        spread = control.waypoint_spread([[0.2, 0.25, 0.24]])
        self.assertEqual(spread["x_std"], 0.0)
        self.assertEqual(spread["z_std"], 0.0)


if __name__ == "__main__":
    unittest.main()
