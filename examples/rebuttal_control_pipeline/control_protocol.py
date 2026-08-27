#!/usr/bin/env python3
"""Target-aligned success protocol for ``simulation_control_group``.

The shared simulator contains the approved physical trajectory, including the
fixed 8 cm release height, while its generic success radius remains 3 cm.  The
Target formal pipeline applies a group-owned 10 cm success classifier.  This
module implements the same classifier for Control without modifying shared or
Target-owned code.  The Control teaching-data manipulation remains exclusively
the independently sampled broad middle-waypoint distribution.
"""

import hashlib
import math
from pathlib import Path

import main_obstacle_transport as shared_task


GROUP = "simulation_control_group"
FORMAL_SEED = 20260806
REVISION_NAME = "protocol_release_z008_target_tol010_start_replenish"
REVISION_ROOT_RELATIVE = Path(
    "rebuttal_dataset/simulation_control_group/full_seed20260806"
) / REVISION_NAME

TARGET_XY_TOLERANCE = 0.10
EXPECTED_SHARED_TARGET_XY_TOLERANCE = 0.03
EXPECTED_RELEASE_Z = 0.08
CYLINDER_TILT_TOLERANCE_DEGREES = 10.0
CONTACTS_ARE_DIAGNOSTIC_ONLY = True
SUCCESS_CRITERION = (
    "target_xy_error<=0.10 and box_settled and cylinder_tilt<=10deg"
)

TARGET_PAIRED_ROLLOUT_MANIFEST_RELATIVE = Path(
    "rebuttal_dataset/simulation_target_group/analysis/paired_rollout_specs.json"
)
TARGET_PAIRED_ROLLOUT_MANIFEST_SHA256 = (
    "10dbbe16da06b4013899e350fece05687abc8c45471b584ac5a2473a0e486dad"
)


def repo_root():
    return Path(__file__).resolve().parents[2]


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def assert_target_aligned_dependencies(check_paired_manifest=False):
    """Fail closed when the approved shared/Target contract has drifted."""
    checks = (
        (
            "shared TARGET_XY_TOLERANCE",
            float(shared_task.TARGET_XY_TOLERANCE),
            EXPECTED_SHARED_TARGET_XY_TOLERANCE,
        ),
        ("shared RELEASE_Z", float(shared_task.RELEASE_Z), EXPECTED_RELEASE_Z),
        (
            "shared cylinder tilt tolerance",
            float(shared_task.CYLINDER_UPRIGHT_TOLERANCE_DEGREES),
            CYLINDER_TILT_TOLERANCE_DEGREES,
        ),
    )
    for label, actual, expected in checks:
        if not math.isclose(actual, expected, rel_tol=0.0, abs_tol=1e-12):
            raise RuntimeError(
                f"{label} changed: expected {expected!r}, observed {actual!r}; "
                "refusing to run the frozen Control revision"
            )
    if check_paired_manifest:
        manifest = repo_root() / TARGET_PAIRED_ROLLOUT_MANIFEST_RELATIVE
        if not manifest.is_file():
            raise FileNotFoundError(manifest)
        actual_hash = sha256(manifest)
        if actual_hash != TARGET_PAIRED_ROLLOUT_MANIFEST_SHA256:
            raise RuntimeError(
                "Target paired rollout manifest hash changed: "
                f"expected {TARGET_PAIRED_ROLLOUT_MANIFEST_SHA256}, "
                f"observed {actual_hash}"
            )


class ControlObstacleTransportSim(shared_task.ObstacleTransportSim):
    """Shared Target-aligned physics with the common 10 cm success radius."""

    def transport_success(self):
        assert_target_aligned_dependencies()
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
                "criterion": SUCCESS_CRITERION,
                "failure_reasons": failure_reasons,
                "target_xy_tolerance": TARGET_XY_TOLERANCE,
                "success_protocol_scope": GROUP,
                "shared_target_xy_tolerance_unchanged": (
                    EXPECTED_SHARED_TARGET_XY_TOLERANCE
                ),
                "contacts_are_diagnostic_only": CONTACTS_ARE_DIAGNOSTIC_ONLY,
            }
        )
        return success, details


assert_target_aligned_dependencies()
