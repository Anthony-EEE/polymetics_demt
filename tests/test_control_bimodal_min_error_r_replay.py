import importlib.util
from pathlib import Path

import numpy as np
import pybullet as pb


REPO = Path(__file__).resolve().parents[1]
SCRIPT = (
    REPO
    / "examples/rebuttal_control_bimodal_pipeline/export_min_error_r_replay.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "export_min_error_r_replay", SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_minimum_error_successful_r_selection_is_frozen():
    module = load_module()
    candidates = module.successful_r_candidates()
    assert len(candidates) == 47
    selected = candidates[0]
    assert (
        selected["participant_id"],
        selected["eval_case_id"],
        selected["repeat_index"],
        selected["policy_sampling_seed"],
    ) == ("CB10", "7", "1", "20360878")
    assert float(selected["target_xy_error"]) == 0.004982
    assert all(
        float(candidates[index]["target_xy_error"])
        <= float(candidates[index + 1]["target_xy_error"])
        for index in range(len(candidates) - 1)
    )


def test_left_handed_pose_reflection_is_geometrically_consistent():
    trace_script = (
        REPO
        / "examples/rebuttal_control_bimodal_pipeline/"
        "export_min_error_r_trace_replay.py"
    )
    spec = importlib.util.spec_from_file_location("trace_replay", trace_script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    position = module.mirror_position([0.2, 0.4, 0.6])
    assert np.allclose(position, [0.2, -0.4, 0.6])
    quaternion = np.asarray(pb.getQuaternionFromEuler([0.3, -0.2, 0.7]))
    mirrored = module.mirror_quaternion(quaternion)
    source_rotation = np.asarray(pb.getMatrixFromQuaternion(quaternion)).reshape(3, 3)
    target_rotation = np.asarray(pb.getMatrixFromQuaternion(mirrored)).reshape(3, 3)
    reflection = np.diag([1.0, -1.0, 1.0])
    assert np.allclose(target_rotation, reflection @ source_rotation @ reflection)
