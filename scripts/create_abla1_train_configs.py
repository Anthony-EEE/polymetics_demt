#!/usr/bin/env python3
import argparse
import json
from pathlib import Path


DEFAULT_TEMPLATE = Path(
    "/users/k23114984/code/arcap_policy/STEP2_train_policy/robomimic/training_config/sim_test_00.json"
)
DEFAULT_DATASET_ROOT = Path(
    "/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full_arcenter"
)
DEFAULT_OUTPUT_DIR = Path("training_config/abla1_arcenter")
CONDITIONS = ("P00", "P01", "P10", "P11")


def parse_args():
    parser = argparse.ArgumentParser(description="Create robomimic configs for corrected Ablation-1 training.")
    parser.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE)
    parser.add_argument("--dataset-root", type=Path, default=DEFAULT_DATASET_ROOT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--action-gap", type=int, default=2)
    return parser.parse_args()


def main():
    args = parse_args()
    with open(args.template, "r", encoding="utf-8") as f:
        template = json.load(f)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    for condition in CONDITIONS:
        config = json.loads(json.dumps(template))
        dataset_path = args.dataset_root / f"abla1_{condition}_d30_seed1_{args.action_gap}gap.hdf5"
        exp_name = f"abla1_arcenter_{condition}_d30_seed1_{args.action_gap}gap"
        config["train"]["data"][0]["path"] = str(dataset_path)
        config["experiment"]["name"] = exp_name

        output_path = args.output_dir / f"abla1_arcenter_{condition}.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
            f.write("\n")
        print(f"Wrote {output_path} -> {dataset_path}", flush=True)


if __name__ == "__main__":
    main()
