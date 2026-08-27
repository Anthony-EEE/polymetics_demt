#!/usr/bin/env python3
"""Control adapter for the exact frozen Target one-policy training runner."""

import argparse
import hashlib
import sys
from pathlib import Path


EXAMPLES_DIR = Path(__file__).resolve().parents[1]
if str(EXAMPLES_DIR) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_DIR))

from rebuttal_target_pipeline import train_target_one as implementation  # noqa: E402


EXPECTED_IMPLEMENTATION_SHA256 = (
    "2cd1c7d9f14fa3724ffeffff744c7ef7bf5a691550953b2a93f2a19bc3f156f9"
)
GROUP = "simulation_control_group"
TARGET_PARTICIPANTS = [f"T{index:02d}" for index in range(1, 11)]
CONTROL_PARTICIPANTS = [f"C{index:02d}" for index in range(1, 11)]


def main():
    actual = hashlib.sha256(Path(implementation.__file__).read_bytes()).hexdigest()
    if actual != EXPECTED_IMPLEMENTATION_SHA256:
        raise RuntimeError(
            "Frozen Target training runner changed: "
            f"expected {EXPECTED_IMPLEMENTATION_SHA256}, observed {actual}"
        )
    implementation.GROUP = GROUP

    original_add_argument = argparse.ArgumentParser.add_argument

    def control_add_argument(parser, *args, **kwargs):
        if args == ("--participant",) and kwargs.get("choices") == TARGET_PARTICIPANTS:
            kwargs = dict(kwargs)
            kwargs["choices"] = CONTROL_PARTICIPANTS
        return original_add_argument(parser, *args, **kwargs)

    argparse.ArgumentParser.add_argument = control_add_argument
    try:
        implementation.main()
    finally:
        argparse.ArgumentParser.add_argument = original_add_argument


if __name__ == "__main__":
    main()
