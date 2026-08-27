#!/usr/bin/env bash
#SBATCH --job-name=target-policy-retry2
#SBATCH --partition=interruptible_gpu
#SBATCH --gres=gpu:1
#SBATCH --constraint="a100|l40s|h100|h200"
#SBATCH --exclude=erc-hpc-comp223
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=08:00:00
#SBATCH --array=4-6%1
#SBATCH --output=/scratch/prj/eng_demt_robot_learning/polymetics_demt/rebuttal_dataset/simulation_target_group/models/slurm_logs/infra_retry2_%A_%a.out
#SBATCH --error=/scratch/prj/eng_demt_robot_learning/polymetics_demt/rebuttal_dataset/simulation_target_group/models/slurm_logs/infra_retry2_%A_%a.err

set -euo pipefail

repo=/scratch/prj/eng_demt_robot_learning/polymetics_demt
models_root="${repo}/rebuttal_dataset/simulation_target_group/models"
participant=$(printf 'T%02d' "$((10#${SLURM_ARRAY_TASK_ID}))")

cd "${repo}"
/scratch/users/k23114984/conda/arcap/bin/python \
  examples/rebuttal_target_pipeline/train_target_one.py \
  --participant "${participant}" \
  --models-root "${models_root}" \
  --infrastructure-retry-index 2
