#!/bin/bash -l

#SBATCH --job-name=tro_pos_merge
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:20:00
#SBATCH --partition=interruptible_cpu
#SBATCH --hint=nomultithread
#SBATCH --output=/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/tro_position_mvp0/logs/merge-%j.out
#SBATCH --error=/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/tro_position_mvp0/logs/merge-%j.err

set -euo pipefail

PROJECT_DIR=${PROJECT_DIR:-"/scratch/prj/eng_demt_robot_learning/polymetics_demt"}
PYTHON=${PYTHON:-"/scratch/users/k23114984/conda/arcap/bin/python"}
BLOCK=${BLOCK:-0}
conditions=(START15_APP6 START35_APP6 START25_APP3P6 START25_APP8P4)
banks=(
  legacy_seed628_reference_r00_r25_n25_v1
  legacy_seed628_outer_r25_r35_n25_v1
)

cd "${PROJECT_DIR}"
for bank_index in 0 1; do
  bank_id=${banks[$bank_index]}
  if (( bank_index == 0 )); then
    radius_min=0.0
    radius_max=0.25
  else
    radius_min=0.25
    radius_max=0.35
  fi
  "${PYTHON}" -u examples/eval_abla1_trained_policies.py \
    --experiment-profile tro_position_mvp0 \
    --block "${BLOCK}" \
    --bank-id "${bank_id}" \
    --conditions "${conditions[@]}" \
    --checkpoint-manifest "experiments/mvp0_position_event/manifests/checkpoints_b${BLOCK}.json" \
    --num-rollouts 25 \
    --seed 628 \
    --horizon 200 \
    --sample-hz 8 \
    --action-gap 2 \
    --action-dt 0.25 \
    --num-points 10000 \
    --success-lift-height 0.20 \
    --shared-start-radius-min "${radius_min}" \
    --shared-start-radius "${radius_max}" \
    --corridor-start-max-error 0.025 \
    --max-start-sample-attempts 1000 \
    --playback-speed 100 \
    --terminate-on-success \
    --output-dir "dataset/tro_position_mvp0/block${BLOCK}/rollouts/${bank_id}" \
    --start-manifest "experiments/mvp0_position_event/manifests/${bank_id}.json" \
    --merge-only
done
