#!/usr/bin/env bash
#SBATCH --job-name=bimodal_target_success_replay_export
#SBATCH --partition=interruptible_gpu
#SBATCH --gres=gpu:1
#SBATCH --constraint="a100|l40s|h100|h200"
#SBATCH --exclude=erc-hpc-comp223
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=01:00:00
#SBATCH --output=/scratch/prj/eng_demt_robot_learning/polymetics_demt/bimodal_target_replays/logs/replay_%j.out
#SBATCH --error=/scratch/prj/eng_demt_robot_learning/polymetics_demt/bimodal_target_replays/logs/replay_%j.err

set -euo pipefail

repo=/scratch/prj/eng_demt_robot_learning/polymetics_demt
cd "${repo}"
export PYTHONDONTWRITEBYTECODE=1
export PYTHONUNBUFFERED=1
export OMP_NUM_THREADS=2
export OPENBLAS_NUM_THREADS=2

/scratch/users/k23114984/conda/arcap/bin/python \
  examples/rebuttal_bimodal_pipeline/export_success_replays.py \
  --selection-seed 20260809 \
  --output-root "${repo}/bimodal_target_replays/seed_20260809" \
  --record-hz 30 \
  --save-videos \
  --cuda
