#!/usr/bin/env python3
import argparse
import json
from pathlib import Path


DEFAULT_TEMPLATE = Path(
    "/users/k23114984/code/arcap_policy/STEP2_train_policy/robomimic/training_config/sim_test_00.json"
)
DEFAULT_DATASET_ROOT = Path(
    "/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/ar_guidance_temporal_T00_T100"
)
DEFAULT_CONFIG_DIR = Path("training_config/ar_guidance_temporal_T00_T100")
DEFAULT_MODEL_ROOT = Path(
    "/scratch/prj/eng_demt_robot_learning/trained_models/ar_guidance_temporal_T00_T100"
)
CONDITIONS = ("T00", "T25", "T50", "T75", "T100")


def parse_args():
    parser = argparse.ArgumentParser(description="Create robomimic configs for temporal MVP training.")
    parser.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE)
    parser.add_argument("--dataset-root", type=Path, default=DEFAULT_DATASET_ROOT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_CONFIG_DIR)
    parser.add_argument("--model-root", type=Path, default=DEFAULT_MODEL_ROOT)
    parser.add_argument("--conditions", nargs="+", default=list(CONDITIONS))
    parser.add_argument("--run-template", default="temporal_{condition}_d30_seed1")
    parser.add_argument("--action-gap", type=int, default=2)
    return parser.parse_args()


def main():
    args = parse_args()
    with open(args.template, "r", encoding="utf-8") as f:
        template = json.load(f)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    for condition in args.conditions:
        config = json.loads(json.dumps(template))
        run_name = args.run_template.format(condition=condition)
        experiment_name = f"{run_name}_{args.action_gap}gap"
        dataset_path = args.dataset_root / f"{experiment_name}.hdf5"
        config["train"]["data"][0]["path"] = str(dataset_path)
        config["train"]["output_dir"] = str(args.model_root / condition)
        config["experiment"]["name"] = experiment_name

        output_path = args.output_dir / f"temporal_{condition}.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
            f.write("\n")
        print(f"Wrote {output_path} -> {dataset_path}", flush=True)


if __name__ == "__main__":
    main()
