#!/usr/bin/env python3
"""Control adapter for the exact frozen Target HDF5 validator."""

import hashlib
import sys
from pathlib import Path


EXAMPLES_DIR = Path(__file__).resolve().parents[1]
if str(EXAMPLES_DIR) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_DIR))

from rebuttal_target_pipeline import validate_target_hdf5 as implementation  # noqa: E402


EXPECTED_IMPLEMENTATION_SHA256 = (
    "2ad95026ae4f631f6bb26ccdd97f637252966096147a5b756b1aa9516c8daba7"
)
GROUP = "simulation_control_group"
PARTICIPANTS = [f"C{index:02d}" for index in range(1, 11)]


def main():
    actual = hashlib.sha256(Path(implementation.__file__).read_bytes()).hexdigest()
    if actual != EXPECTED_IMPLEMENTATION_SHA256:
        raise RuntimeError(
            "Frozen Target HDF5 validator changed: "
            f"expected {EXPECTED_IMPLEMENTATION_SHA256}, observed {actual}"
        )
    implementation.GROUP = GROUP
    implementation.PARTICIPANTS = PARTICIPANTS
    implementation.main()


if __name__ == "__main__":
    main()
