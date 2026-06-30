#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path


ARCAP_STEP1 = Path("/users/k23114984/code/arcap_policy/STEP1_build_dataset")
if str(ARCAP_STEP1) not in sys.path:
    sys.path.insert(0, str(ARCAP_STEP1))

from dataset_utils import process_hdf5_arcap_multi


DEFAULT_DATASET_ROOT = Path(
    "/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/time_mvp_full"
)
DEFAULT_GROUPS = (
    "time_mvp_T00_d30_seed1",
    "time_mvp_T20_d30_seed1",
    "time_mvp_Twide_d30_seed1",
)


def parse_args():
    parser = argparse.ArgumentParser(description="Convert temporal MVP raw demos to HDF5.")
    parser.add_argument("--dataset-root", type=Path, default=DEFAULT_DATASET_ROOT)
    parser.add_argument("--groups", nargs="+", default=list(DEFAULT_GROUPS))
    parser.add_argument("--action-gap", type=int, default=2)
    parser.add_argument("--point-cloud-data", type=int, default=10000)
    return parser.parse_args()


def main():
    args = parse_args()
    for group_name in args.groups:
        dataset_folder = args.dataset_root / group_name
        output_hdf5_file = args.dataset_root / f"{group_name}_{args.action_gap}gap.hdf5"
        if not dataset_folder.exists():
            raise FileNotFoundError(f"Missing dataset folder: {dataset_folder}")
        print(f"Converting {dataset_folder} -> {output_hdf5_file}", flush=True)
        process_hdf5_arcap_multi(
            output_hdf5_file=str(output_hdf5_file),
            dataset_folders=[str(dataset_folder)],
            action_gap=args.action_gap,
            num_points_to_sample=args.point_cloud_data,
            hand_ahead=0,
            last_mean=1,
            visualize=False,
        )
    print("[INFO] Finished temporal MVP HDF5 conversion", flush=True)


if __name__ == "__main__":
    main()
