#!/usr/bin/env python3
"""Control-Bimodal-only success protocol matching the frozen Target 10 cm criterion."""

import math

import main_obstacle_transport as shared_task


GROUP = "simulation_control_bimodal_group"
CONTROL_BIMODAL_XY_TOLERANCE = 0.10
SHARED_TARGET_XY_TOLERANCE = 0.03
CONTROL_BIMODAL_SUCCESS_CRITERION = (
    "target_xy_error<=0.10 and box_settled and cylinder_tilt<=10deg"
)


def assert_shared_protocol_unchanged():
    if not math.isclose(
        float(shared_task.TARGET_XY_TOLERANCE),
        SHARED_TARGET_XY_TOLERANCE,
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        raise RuntimeError("Shared 3 cm tolerance changed; Control-Bimodal protocol fails closed")


class ControlBimodalObstacleTransportSim(shared_task.ObstacleTransportSim):
    """Shared dynamics with the frozen Control-Bimodal/Target 10 cm success radius."""

    def transport_success(self):
        assert_shared_protocol_unchanged()
        _, details = super().transport_success()
        shared_failures = list(details.get("failure_reasons", []))
        target_reached = float(details["target_xy_error"]) <= CONTROL_BIMODAL_XY_TOLERANCE
        box_settled = "box_not_settled" not in shared_failures
        cylinder_upright = "cylinder_toppled" not in shared_failures
        failure_reasons = []
        if not target_reached:
            failure_reasons.append("target_miss")
        if not box_settled:
            failure_reasons.append("box_not_settled")
        if not cylinder_upright:
            failure_reasons.append("cylinder_toppled")
        success = bool(target_reached and box_settled and cylinder_upright)
        details.update(
            {
                "success": success,
                "criterion": CONTROL_BIMODAL_SUCCESS_CRITERION,
                "failure_reasons": failure_reasons,
                "target_xy_tolerance": CONTROL_BIMODAL_XY_TOLERANCE,
                "success_protocol_scope": GROUP,
                "shared_target_xy_tolerance_unchanged": SHARED_TARGET_XY_TOLERANCE,
            }
        )
        return success, details


assert_shared_protocol_unchanged()
