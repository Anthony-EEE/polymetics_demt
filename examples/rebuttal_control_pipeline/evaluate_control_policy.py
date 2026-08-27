#!/usr/bin/env python3
"""Control adapter for Target's frozen learned-policy rollout evaluator.

The exact Target paired-manifest file and its ten eval cases are consumed
without rewriting or copying.  Only group-owned metadata is adapted in memory:
the result/checkpoint group is Control and the checkpoint gate points to the
Control selected-checkpoint manifest.  Canonical verification is performed
against the untouched Target content and file hash before evaluation.
"""

import copy
import hashlib
import sys
from pathlib import Path


EXAMPLES_DIR = Path(__file__).resolve().parents[1]
if str(EXAMPLES_DIR) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_DIR))

from rebuttal_control_pipeline.control_protocol import (  # noqa: E402
    ControlObstacleTransportSim,
    GROUP,
    SUCCESS_CRITERION,
    TARGET_PAIRED_ROLLOUT_MANIFEST_SHA256,
    TARGET_XY_TOLERANCE,
    assert_target_aligned_dependencies,
)
from rebuttal_target_pipeline import evaluate_target_policy as implementation  # noqa: E402


EXPECTED_IMPLEMENTATION_SHA256 = (
    "59881ae2fdf00156a50bbb212a4c24e266757f4e83b9ed9b6ebabaa2e3f4202d"
)
TARGET_GROUP = "simulation_target_group"
PARTICIPANTS = [f"C{index:02d}" for index in range(1, 11)]


def main():
    actual = hashlib.sha256(Path(implementation.__file__).read_bytes()).hexdigest()
    if actual != EXPECTED_IMPLEMENTATION_SHA256:
        raise RuntimeError(
            "Frozen Target evaluator changed: "
            f"expected {EXPECTED_IMPLEMENTATION_SHA256}, observed {actual}"
        )
    assert_target_aligned_dependencies(check_paired_manifest=True)

    implementation.GROUP = GROUP
    implementation.PARTICIPANTS = PARTICIPANTS
    implementation.TargetObstacleTransportSim = ControlObstacleTransportSim
    implementation.TARGET_XY_TOLERANCE = TARGET_XY_TOLERANCE
    implementation.TARGET_SUCCESS_CRITERION = SUCCESS_CRITERION

    original_load_json = implementation.load_json
    original_canonical_hash = implementation.canonical_hash
    state = {
        "control_checkpoint_manifest_sha256": None,
        "target_checkpoint_gate_sha256": None,
    }

    def control_load_json(path):
        path = Path(path)
        payload = original_load_json(path)
        if (
            isinstance(payload, dict)
            and payload.get("group") == GROUP
            and payload.get("participant_order") == PARTICIPANTS
            and "checkpoints" in payload
        ):
            state["control_checkpoint_manifest_sha256"] = implementation.sha256(path)
            return payload
        if (
            isinstance(payload, dict)
            and payload.get("group") == TARGET_GROUP
            and len(payload.get("eval_cases", [])) == 10
            and implementation.sha256(path) == TARGET_PAIRED_ROLLOUT_MANIFEST_SHA256
        ):
            if state["control_checkpoint_manifest_sha256"] is None:
                raise RuntimeError("Control checkpoint manifest was not loaded before paired specs")
            adapted = copy.deepcopy(payload)
            adapted["group"] = GROUP
            adapted["frozen_task"]["success_protocol_scope"] = GROUP
            state["target_checkpoint_gate_sha256"] = adapted["checkpoint_gate"][
                "selected_checkpoints_manifest_sha256"
            ]
            adapted["checkpoint_gate"]["selected_checkpoints_manifest_sha256"] = state[
                "control_checkpoint_manifest_sha256"
            ]
            return adapted
        return payload

    def control_canonical_hash(payload):
        restored = copy.deepcopy(payload)
        if restored.get("group") == GROUP and "eval_cases" in restored:
            restored["group"] = TARGET_GROUP
            restored["frozen_task"]["success_protocol_scope"] = TARGET_GROUP
            restored["checkpoint_gate"]["selected_checkpoints_manifest_sha256"] = state[
                "target_checkpoint_gate_sha256"
            ]
        return original_canonical_hash(restored)

    implementation.load_json = control_load_json
    implementation.canonical_hash = control_canonical_hash
    try:
        implementation.main()
    finally:
        implementation.load_json = original_load_json
        implementation.canonical_hash = original_canonical_hash


if __name__ == "__main__":
    main()
