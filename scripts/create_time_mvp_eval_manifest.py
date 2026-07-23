#!/usr/bin/env python3
import argparse
import json
from pathlib import Path


CONDITION_ORDER = ("VR1P5", "V050_200", "VR3", "VR4")
DEFAULT_MODEL_ROOT = Path(
    "/scratch/prj/eng_demt_robot_learning/trained_models/temporal_vref_reciprocal_spatial_v2"
)


def checkpoint_epoch(path):
    try:
        return int(path.stem.rsplit("_", 1)[-1])
    except (IndexError, ValueError):
        return -1


def latest_checkpoint(model_root, condition, experiment_template):
    experiment_root = model_root / experiment_template.format(condition=condition)
    run_dirs = sorted(path for path in experiment_root.iterdir() if path.is_dir())
    if not run_dirs:
        raise FileNotFoundError(f"No training runs under {experiment_root}")
    candidates = sorted(
        (run_dirs[-1] / "models").glob("model_epoch_*.pth"), key=checkpoint_epoch
    )
    if not candidates:
        raise FileNotFoundError(f"No checkpoints under {run_dirs[-1] / 'models'}")
    return candidates[-1]


def parse_args():
    parser = argparse.ArgumentParser(description="Create explicit reciprocal temporal checkpoint manifest.")
    parser.add_argument("--model-root", type=Path, default=DEFAULT_MODEL_ROOT)
    parser.add_argument(
        "--experiment-template", default="{condition}/temporal_{condition}_d30_seed1_2gap"
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--training-job-ids",
        nargs=4,
        default=None,
        metavar=("VR1P5", "V050_200", "VR3", "VR4"),
        help="Slurm training job IDs in the fixed reciprocal condition order.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    checkpoints = {}
    training_job_ids = dict(zip(CONDITION_ORDER, args.training_job_ids or [None] * 4))
    for condition in CONDITION_ORDER:
        checkpoint = latest_checkpoint(args.model_root, condition, args.experiment_template)
        checkpoints[condition] = {
            "path": str(checkpoint.resolve()),
            "source": "corrected_spatial_v2_training_latest_checkpoint",
            "training_job_id": training_job_ids[condition],
        }

    manifest = {
        "schema_version": 1,
        "condition_order": list(CONDITION_ORDER),
        "baseline_condition": "V050_200",
        "old_fixed_point_checkpoint_reused": False,
        "checkpoints": {condition: checkpoints[condition] for condition in CONDITION_ORDER},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {args.output}")
    for condition in CONDITION_ORDER:
        print(f"{condition}: {manifest['checkpoints'][condition]['path']}")


if __name__ == "__main__":
    main()
