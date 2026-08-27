import importlib.util
from pathlib import Path

import numpy as np


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "examples/rebuttal_bimodal_pipeline/mirror_intervention_y.py"


def load_module():
    spec = importlib.util.spec_from_file_location("mirror_intervention_y", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_slerp_endpoints_and_unit_norm():
    module = load_module()
    a = np.asarray([0.0, 0.0, 0.0, 1.0])
    b = np.asarray([0.0, 0.0, 1.0, 0.0])
    np.testing.assert_allclose(module.slerp(a, b, 0.0), a)
    np.testing.assert_allclose(module.slerp(a, b, 1.0), b)
    assert np.isclose(np.linalg.norm(module.slerp(a, b, 0.37)), 1.0)


def test_default_inputs_are_the_requested_L_and_R_csvs():
    module = load_module()
    assert [path.parent.name for path in module.DEFAULT_INPUTS] == ["L", "R"]
    assert all(path.name == "intervention.csv" for path in module.DEFAULT_INPUTS)
    assert module.SOURCE_BASE_POSITION.tolist() == [0.0, 0.15, 0.0]
    assert module.MIRRORED_BASE_POSITION.tolist() == [0.0, -0.15, 0.0]
