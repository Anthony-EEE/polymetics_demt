#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

import h5py


ARCAP_STEP1 = Path("/users/k23114984/code/arcap_policy/STEP1_build_dataset")
if str(ARCAP_STEP1) not in sys.path:
    sys.path.insert(0, str(ARCAP_STEP1))

from dataset_utils import process_hdf5_arcap_multi


DEFAULT_DATASET_ROOT = Path(
    "/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/temporal_vref_reciprocal_spatial_v2"
)
DEFAULT_GROUPS = (
    "temporal_VR1P5_d30_seed1",
    "temporal_V050_200_d30_seed1",
    "temporal_VR3_d30_seed1",
    "temporal_VR4_d30_seed1",
)


def parse_args():
    parser = argparse.ArgumentParser(description="Convert temporal MVP raw demos to HDF5.")
    parser.add_argument("--dataset-root", type=Path, default=DEFAULT_DATASET_ROOT)
    parser.add_argument("--groups", nargs="+", default=list(DEFAULT_GROUPS))
    parser.add_argument("--action-gap", type=int, default=2)
    parser.add_argument("--point-cloud-data", type=int, default=10000)
    return parser.parse_args()


def demo_index(path):
    return int(path.name.split("_", 1)[1])


def annotate_source_candidates(hdf5_path, dataset_folder, action_gap):
    raw_dirs = sorted(
        [path for path in dataset_folder.glob("demo_*") if path.is_dir()], key=demo_index
    )
    raw_metadata = [
        json.loads((demo_dir / "metadata.json").read_text(encoding="utf-8"))
        for demo_dir in raw_dirs
    ]
    with h5py.File(hdf5_path, "r+") as hdf5:
        names = sorted(hdf5["data"], key=lambda name: int(name.split("_", 1)[1]))
        if len(names) != 2 * len(raw_metadata):
            raise ValueError(
                f"{hdf5_path}: expected exactly two augmented demos per raw source; "
                f"got {len(names)} HDF5 demos for {len(raw_metadata)} raw demos"
            )
        manifest_records = {json.dumps(row.get("collection_manifest"), sort_keys=True) for row in raw_metadata}
        if len(manifest_records) != 1:
            raise ValueError(f"{dataset_folder}: inconsistent collection manifest identities")
        hdf5["data"].attrs["collection_manifest_json"] = next(iter(manifest_records))
        hdf5["data"].attrs["source_raw_demo_count"] = len(raw_metadata)
        hdf5["data"].attrs["augmentation_factor"] = 2
        hdf5["data"].attrs["action_gap"] = int(action_gap)
        for output_index, name in enumerate(names):
            source_index = output_index // 2
            row = raw_metadata[source_index]
            demo = hdf5["data"][name]
            demo.attrs["source_raw_demo_index"] = source_index
            demo.attrs["source_raw_demo_name"] = raw_dirs[source_index].name
            demo.attrs["candidate_id"] = row["candidate_id"]
            demo.attrs["augmentation_index"] = output_index % 2
            demo.attrs["source_raw_frame_count"] = len(
                [path for path in raw_dirs[source_index].glob("frame_*") if path.is_dir()]
            )


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
        annotate_source_candidates(output_hdf5_file, dataset_folder, args.action_gap)
        print(f"Annotated source candidate IDs in {output_hdf5_file}", flush=True)
    print("[INFO] Finished temporal MVP HDF5 conversion", flush=True)


if __name__ == "__main__":
    main()
