#!/usr/bin/env python3
"""Run the shared-revision diagnostic with the low-x cutoff narrowed to 0.23 m."""

import diagnose_shared_revision as diagnostic


if __name__ == "__main__":
    diagnostic.ProposedSharedRevisionSim.low_x_threshold = 0.23
    diagnostic.main()
