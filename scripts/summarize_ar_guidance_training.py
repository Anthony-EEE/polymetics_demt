#!/usr/bin/env python3
import argparse
import json
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt


TRACKS = {
    "spatial": {
        "model_root": Path(
            "/scratch/prj/eng_demt_robot_learning/trained_models/ar_guidance_spatial_S15_S35"
        ),
        "output_dir": Path(
            "/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/ar_guidance_spatial_S15_S35"
        ),
        "conditions": ("S15", "S20", "S25", "S30", "S35"),
        "experiment_template": "spatial_{condition}_d30_seed1_2gap",
    },
    "temporal": {
        "model_root": Path(
            "/scratch/prj/eng_demt_robot_learning/trained_models/ar_guidance_temporal_T00_T100"
        ),
        "output_dir": Path(
            "/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/ar_guidance_temporal_T00_T100"
        ),
        "conditions": ("T00", "T25", "T50", "T75", "T100"),
        "experiment_template": "temporal_{condition}_d30_seed1_2gap",
    },
    "temporal_reciprocal": {
        "model_root": Path(
            "/scratch/prj/eng_demt_robot_learning/trained_models/temporal_vref_reciprocal_spatial_v2"
        ),
        "output_dir": Path(
            "/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/temporal_vref_reciprocal_spatial_v2"
        ),
        "conditions": ("VR1P5", "V050_200", "VR3", "VR4"),
        "experiment_template": "temporal_{condition}_d30_seed1_2gap",
    },
}


EPOCH_RE = re.compile(r"^(Train|Validation) Epoch (\d+)\s*$")
LOSS_RE = re.compile(r'"Loss"\s*:\s*([-+0-9.eE]+)')
CKPT_RE = re.compile(r"model_epoch_(\d+)\.pth$")


def parse_args():
    parser = argparse.ArgumentParser(description="Summarize AR-guidance training logs and checkpoints.")
    parser.add_argument(
        "--track", choices=("spatial", "temporal", "temporal_reciprocal", "all"), default="all"
    )
    return parser.parse_args()


def selected_tracks(track):
    if track == "all":
        return ("spatial", "temporal")
    return (track,)


def latest_run_dir(exp_root):
    run_dirs = [p for p in exp_root.iterdir() if p.is_dir()]
    if not run_dirs:
        raise FileNotFoundError(f"No run directories found under {exp_root}")
    return sorted(run_dirs)[-1]


def checkpoint_epoch(path):
    match = CKPT_RE.search(path.name)
    return int(match.group(1)) if match else -1


def parse_log(log_path):
    lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    rows = []
    for idx, line in enumerate(lines):
        match = EPOCH_RE.match(line.strip())
        if not match:
            continue
        mode = "train" if match.group(1) == "Train" else "valid"
        epoch = int(match.group(2))
        loss = None
        for lookahead in lines[idx + 1 : idx + 20]:
            loss_match = LOSS_RE.search(lookahead)
            if loss_match:
                loss = float(loss_match.group(1))
                break
        if loss is not None:
            rows.append({"mode": mode, "epoch": epoch, "loss": loss})
    return rows


def summarize_condition(spec, condition):
    exp_name = spec["experiment_template"].format(condition=condition)
    exp_root = spec["model_root"] / condition / exp_name
    run_dir = latest_run_dir(exp_root)
    log_path = run_dir / "logs" / "log.txt"
    if not log_path.exists():
        raise FileNotFoundError(f"Missing training log: {log_path}")

    rows = parse_log(log_path)
    valid_rows = [row for row in rows if row["mode"] == "valid"]
    train_rows = [row for row in rows if row["mode"] == "train"]
    best_valid = min(valid_rows, key=lambda row: row["loss"]) if valid_rows else None
    latest_valid = max(valid_rows, key=lambda row: row["epoch"]) if valid_rows else None
    latest_train = max(train_rows, key=lambda row: row["epoch"]) if train_rows else None

    ckpts = sorted((run_dir / "models").glob("model_epoch_*.pth"), key=checkpoint_epoch)
    return {
        "condition": condition,
        "experiment_name": exp_name,
        "run_dir": str(run_dir),
        "log_path": str(log_path),
        "num_train_points": len(train_rows),
        "num_valid_points": len(valid_rows),
        "latest_train": latest_train,
        "latest_valid": latest_valid,
        "best_valid": best_valid,
        "checkpoints": [str(path) for path in ckpts],
        "latest_checkpoint": str(ckpts[-1]) if ckpts else None,
        "loss_rows": rows,
    }


def plot_track(track, summaries, output_path):
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.8), constrained_layout=True)
    fig.suptitle(f"{track} training loss")

    for summary in summaries:
        condition = summary["condition"]
        train = [row for row in summary["loss_rows"] if row["mode"] == "train"]
        valid = [row for row in summary["loss_rows"] if row["mode"] == "valid"]
        if train:
            axes[0].plot([r["epoch"] for r in train], [r["loss"] for r in train], label=condition)
        if valid:
            axes[1].plot([r["epoch"] for r in valid], [r["loss"] for r in valid], label=condition)

    axes[0].set_title("train")
    axes[1].set_title("valid")
    for ax in axes:
        ax.set_xlabel("epoch")
        ax.set_ylabel("loss")
        ax.grid(True, alpha=0.25)
        ax.legend()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def main():
    args = parse_args()
    for track in selected_tracks(args.track):
        spec = TRACKS[track]
        summaries = [summarize_condition(spec, condition) for condition in spec["conditions"]]
        output_dir = spec["output_dir"]
        output_dir.mkdir(parents=True, exist_ok=True)
        summary_path = output_dir / "training_loss_summary.json"
        plot_path = output_dir / "loss.png"
        summary_path.write_text(json.dumps({"track": track, "summaries": summaries}, indent=2), encoding="utf-8")
        plot_track(track, summaries, plot_path)
        print(f"[INFO] Wrote {summary_path}", flush=True)
        print(f"[INFO] Wrote {plot_path}", flush=True)


if __name__ == "__main__":
    main()
