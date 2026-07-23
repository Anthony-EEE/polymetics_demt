#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "examples"))

from eval_orn_mvp_trained_policies import CONDITION_ORDER, latest_checkpoint  # noqa: E402
from rollout_contract import file_sha256, write_json  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="Freeze Contact-degree supplement checkpoints.")
    parser.add_argument("--model-root", type=Path, default=Path("/scratch/prj/eng_demt_robot_learning/trained_models"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    checkpoints = {}
    for condition in CONDITION_ORDER:
        path = latest_checkpoint(args.model_root, condition, 40)
        checkpoints[condition] = {
            "path": str(path.resolve()),
            "epoch": 40,
            "sha256": file_sha256(path),
            "source": "accepted_orientation_mvp_n10_checkpoint",
        }
    write_json(args.output, {"schema_version": 1, "condition_order": list(CONDITION_ORDER), "checkpoints": checkpoints})
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
