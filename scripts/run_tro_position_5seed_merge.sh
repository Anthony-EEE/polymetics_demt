#!/bin/bash -l

#SBATCH --job-name=tro_pos_5seed_merge
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:30:00
#SBATCH --partition=interruptible_cpu
#SBATCH --hint=nomultithread
#SBATCH --output=/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/tro_position_mvp0/logs/merge-5seed-%j.out
#SBATCH --error=/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/tro_position_mvp0/logs/merge-5seed-%j.err

set -euo pipefail

PROJECT_DIR=${PROJECT_DIR:-"/scratch/prj/eng_demt_robot_learning/polymetics_demt"}
PYTHON=${PYTHON:-"/scratch/users/k23114984/conda/arcap/bin/python"}
conditions=(START15_APP6 START35_APP6 START25_APP3P6 START25_APP8P4)
seeds=(628 629 630 631 632)
banks=(inner outer)

cd "${PROJECT_DIR}"
for block in 0 1; do
  for seed in "${seeds[@]}"; do
    for bank in "${banks[@]}"; do
      bank_id="tro_pos_seed${seed}_${bank}_n25_v1"
      if [[ "${bank}" == "inner" ]]; then
        radius_min=0.0
        radius_max=0.25
      else
        radius_min=0.25
        radius_max=0.35
      fi
      "${PYTHON}" -u examples/eval_abla1_trained_policies.py \
        --experiment-profile tro_position_mvp0 \
        --block "${block}" \
        --bank-id "${bank_id}" \
        --conditions "${conditions[@]}" \
        --checkpoint-manifest "experiments/mvp0_position_event/manifests/checkpoints_latest_existing_b${block}.json" \
        --num-rollouts 25 \
        --seed "${seed}" \
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
        --output-dir "dataset/tro_position_mvp0/rollouts_5seed_n50/block${block}/seed${seed}/${bank}" \
        --start-manifest "experiments/mvp0_position_event/manifests/rollout_5seed/${bank_id}.json" \
        --merge-only
    done
  done
done
