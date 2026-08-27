#!/usr/bin/env bash
#SBATCH --job-name=control_bimodal_min_error_R_replay
#SBATCH --partition=interruptible_gpu
#SBATCH --gres=gpu:1
#SBATCH --constraint="a100|l40s|h100|h200"
#SBATCH --exclude=erc-hpc-comp223
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=01:00:00
#SBATCH --output=/scratch/prj/eng_demt_robot_learning/polymetics_demt/control_bimodal_replay/logs/replay_%j.out
#SBATCH --error=/scratch/prj/eng_demt_robot_learning/polymetics_demt/control_bimodal_replay/logs/replay_%j.err

set -euo pipefail

repo=/scratch/prj/eng_demt_robot_learning/polymetics_demt
cd "${repo}"
export PYTHONDONTWRITEBYTECODE=1
export PYTHONUNBUFFERED=1
export OMP_NUM_THREADS=2
export OPENBLAS_NUM_THREADS=2

/scratch/users/k23114984/conda/arcap/bin/python \
  examples/rebuttal_control_bimodal_pipeline/export_min_error_r_replay.py \
  --output-root "${repo}/control_bimodal_replay/min_error_R" \
  --max-reproduction-attempts 1 \
  --record-hz 30 \
  --save-videos \
  --cuda
