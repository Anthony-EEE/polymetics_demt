#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "examples"))

from eval_abla1_trained_policies import CONDITION_ORDER, latest_checkpoint  # noqa: E402
from rollout_contract import file_sha256, write_json  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="Freeze Position supplement checkpoints.")
    parser.add_argument("--model-root", type=Path, default=Path("/scratch/prj/eng_demt_robot_learning/trained_models/ar_guidance_spatial_S15_S35"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    epochs = {"S15": 40, "S20": 40, "S25": 80, "S30": 40, "S35": 40}
    checkpoints = {}
    for condition in CONDITION_ORDER:
        path = latest_checkpoint(args.model_root, condition, epochs[condition])
        checkpoints[condition] = {
            "path": str(path.resolve()),
            "epoch": epochs[condition],
            "sha256": file_sha256(path),
            "source": "accepted_shared_r35_n10_checkpoint",
        }
    write_json(args.output, {"schema_version": 1, "condition_order": list(CONDITION_ORDER), "checkpoints": checkpoints})
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
