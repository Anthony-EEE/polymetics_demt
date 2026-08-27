#!/usr/bin/env python3
"""Control adapter for the exact frozen Target raw-to-HDF5 implementation."""

import hashlib
import sys
from pathlib import Path


EXAMPLES_DIR = Path(__file__).resolve().parents[1]
if str(EXAMPLES_DIR) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_DIR))

from rebuttal_target_pipeline import convert_target_hdf5 as implementation  # noqa: E402


EXPECTED_IMPLEMENTATION_SHA256 = (
    "8bc6376bd03160d4de49fb56a9dc0ccb51279c281f86bde439bbda2ee789f42a"
)
GROUP = "simulation_control_group"
PARTICIPANTS = [f"C{index:02d}" for index in range(1, 11)]


def sha256(path):
    digest = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    return digest


def main():
    actual = sha256(implementation.__file__)
    if actual != EXPECTED_IMPLEMENTATION_SHA256:
        raise RuntimeError(
            "Frozen Target converter changed: "
            f"expected {EXPECTED_IMPLEMENTATION_SHA256}, observed {actual}"
        )
    implementation.GROUP = GROUP
    implementation.PARTICIPANTS = PARTICIPANTS
    implementation.main()


if __name__ == "__main__":
    main()
