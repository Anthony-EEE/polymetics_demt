#!/usr/bin/env python3
import argparse
import subprocess
import sys
from pathlib import Path


DEFAULT_SPLITTER = Path(
    "/users/k23114984/code/arcap_policy/STEP2_train_policy/robomimic/scripts/split_train_val.py"
)
TRACKS = {
    "spatial": {
        "root": Path(
            "/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/ar_guidance_spatial_S15_S35"
        ),
        "groups": (
            "spatial_S15_d30_seed1",
            "spatial_S20_d30_seed1",
            "spatial_S25_d30_seed1",
            "spatial_S30_d30_seed1",
            "spatial_S35_d30_seed1",
        ),
    },
    "temporal": {
        "root": Path(
            "/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/ar_guidance_temporal_T00_T100"
        ),
        "groups": (
            "temporal_T00_d30_seed1",
            "temporal_T25_d30_seed1",
            "temporal_T50_d30_seed1",
            "temporal_T75_d30_seed1",
            "temporal_T100_d30_seed1",
        ),
    },
}


def parse_args():
    parser = argparse.ArgumentParser(description="Split AR-guidance HDF5 files into train/valid masks.")
    parser.add_argument("--track", choices=("spatial", "temporal", "all"), default="all")
    parser.add_argument("--splitter", type=Path, default=DEFAULT_SPLITTER)
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--ratio", type=float, default=0.1)
    parser.add_argument("--action-gap", type=int, default=2)
    parser.add_argument("--skip-missing", action="store_true")
    return parser.parse_args()


def selected_tracks(track):
    if track == "all":
        return ("spatial", "temporal")
    return (track,)


def main():
    args = parse_args()
    if not args.splitter.exists():
        raise FileNotFoundError(f"Missing splitter script: {args.splitter}")

    for track in selected_tracks(args.track):
        spec = TRACKS[track]
        for group in spec["groups"]:
            hdf5_path = spec["root"] / f"{group}_{args.action_gap}gap.hdf5"
            if not hdf5_path.exists():
                message = f"Missing HDF5: {hdf5_path}"
                if args.skip_missing:
                    print(f"[WARN] {message}", flush=True)
                    continue
                raise FileNotFoundError(message)

            cmd = [
                args.python,
                str(args.splitter),
                "--dataset",
                str(hdf5_path),
                "--ratio",
                str(args.ratio),
            ]
            print("[INFO] " + " ".join(cmd), flush=True)
            subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()
