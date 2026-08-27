#!/usr/bin/env python3
"""Target-only success protocol for ``simulation_target_group``.

The shared simulator remains at its original 3 cm target tolerance because an
already-running Control collection imports it directly.  Target formal data
and Target learned-policy evaluation use the explicitly user-authorised 10 cm
target tolerance defined here.  All settling and cylinder-upright checks are
inherited unchanged from the shared simulator.
"""

import math

import main_obstacle_transport as shared_task


GROUP = "simulation_target_group"
TARGET_XY_TOLERANCE = 0.10
SHARED_TARGET_XY_TOLERANCE_AT_REVISION = 0.03
TARGET_SUCCESS_CRITERION = (
    "target_xy_error<=0.10 and box_settled and cylinder_tilt<=10deg"
)


def assert_shared_protocol_unchanged():
    """Fail closed if the shared/Control-visible tolerance was edited."""
    if not math.isclose(
        float(shared_task.TARGET_XY_TOLERANCE),
        SHARED_TARGET_XY_TOLERANCE_AT_REVISION,
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        raise RuntimeError(
            "Shared TARGET_XY_TOLERANCE changed; Target's 10 cm revision must "
            "remain isolated from the already-running Control protocol"
        )


class TargetObstacleTransportSim(shared_task.ObstacleTransportSim):
    """Shared simulator dynamics with a Target-only 10 cm success radius."""

    def transport_success(self):
        assert_shared_protocol_unchanged()
        _, details = super().transport_success()

        shared_failure_reasons = list(details.get("failure_reasons", []))
        target_reached = float(details["target_xy_error"]) <= TARGET_XY_TOLERANCE
        box_settled = "box_not_settled" not in shared_failure_reasons
        cylinder_upright = "cylinder_toppled" not in shared_failure_reasons

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
                "criterion": TARGET_SUCCESS_CRITERION,
                "failure_reasons": failure_reasons,
                "target_xy_tolerance": TARGET_XY_TOLERANCE,
                "success_protocol_scope": GROUP,
                "shared_target_xy_tolerance_unchanged": (
                    SHARED_TARGET_XY_TOLERANCE_AT_REVISION
                ),
            }
        )
        return success, details


assert_shared_protocol_unchanged()
