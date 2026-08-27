#!/usr/bin/env python3
"""Run the shared-revision diagnostic with a grasp offset supplied by the wrapper."""

import os

import numpy as np

import diagnose_shared_revision as diagnostic


if __name__ == "__main__":
    values = [float(value) for value in os.environ["CONTROL_GRASP_OFFSET"].split(",")]
    if len(values) != 3:
        raise ValueError("CONTROL_GRASP_OFFSET must contain exactly three values")
    diagnostic.ProposedSharedRevisionSim.grasp_offset = np.asarray(values, dtype=float)
    diagnostic.main()
