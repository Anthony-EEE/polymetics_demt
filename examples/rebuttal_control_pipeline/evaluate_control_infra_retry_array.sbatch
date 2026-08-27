#!/usr/bin/env bash
#SBATCH --job-name=control-rollout-infra-retry
#SBATCH --partition=interruptible_gpu
#SBATCH --gres=gpu:1
#SBATCH --constraint="a100|l40s|h100|h200"
#SBATCH --exclude=erc-hpc-comp223
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=06:00:00
#SBATCH --array=1-10%1
#SBATCH --output=/scratch/prj/eng_demt_robot_learning/polymetics_demt/rebuttal_dataset/simulation_control_group/policy_rollouts/logs/infra_retry_%A_%a.out
#SBATCH --error=/scratch/prj/eng_demt_robot_learning/polymetics_demt/rebuttal_dataset/simulation_control_group/policy_rollouts/logs/infra_retry_%A_%a.err

set -euo pipefail

repo=/scratch/prj/eng_demt_robot_learning/polymetics_demt
control_root="${repo}/rebuttal_dataset/simulation_control_group"
target_root="${repo}/rebuttal_dataset/simulation_target_group"
participant=$(printf 'C%02d' "$((10#${SLURM_ARRAY_TASK_ID}))")

cd "${repo}"
export PYTHONDONTWRITEBYTECODE=1
export PYTHONUNBUFFERED=1
export OMP_NUM_THREADS=2
export OPENBLAS_NUM_THREADS=2

/scratch/users/k23114984/conda/arcap/bin/python \
  examples/rebuttal_control_pipeline/evaluate_control_policy.py \
  --participant "${participant}" \
  --checkpoint-manifest "${control_root}/models/selected_checkpoints_manifest.json" \
  --spec-manifest "${target_root}/analysis/paired_rollout_specs.json" \
  --output-root "${control_root}/policy_rollouts" \
  --horizon 200 \
  --sample-hz 8 \
  --action-gap 2 \
  --action-dt 0.25 \
  --num-points 10000 \
  --settle-seconds 1.5 \
  --save-videos \
  --cuda \
  --resume-after-reviewed-infrastructure-failure
