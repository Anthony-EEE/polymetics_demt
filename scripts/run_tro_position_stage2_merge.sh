#!/bin/bash -l

#SBATCH --job-name=tro_s2_merge
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=01:00:00
#SBATCH --partition=interruptible_cpu
#SBATCH --hint=nomultithread
#SBATCH --output=/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/tro_position_stage2_axial/logs/merge-%j.out
#SBATCH --error=/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/tro_position_stage2_axial/logs/merge-%j.err

set -euo pipefail

PROJECT_DIR=${PROJECT_DIR:-"/scratch/prj/eng_demt_robot_learning/polymetics_demt"}
PYTHON=${PYTHON:-"/scratch/users/k23114984/conda/arcap/bin/python"}
conditions=(START15_APP6 START35_APP6 START25_APP3P6 START25_APP6 START25_APP8P4)
banks=(inner outer)

cd "${PROJECT_DIR}"
for canonical_seed in 1 2 3 4 5; do
  for rollout_seed in 1 2 3 4 5; do
    for bank in "${banks[@]}"; do
      bank_id="tro_stage2_seed${rollout_seed}_${bank}_n25_v1"
      if [[ "${bank}" == "inner" ]]; then
        radius_min=0.0
        radius_max=0.25
      else
        radius_min=0.25
        radius_max=0.35
      fi
      "${PYTHON}" -u examples/eval_abla1_trained_policies.py \
        --experiment-profile tro_position_stage2 \
        --block "${canonical_seed}" \
        --bank-id "${bank_id}" \
        --conditions "${conditions[@]}" \
        --checkpoint-manifest "experiments/tro_stage2_position_axial_replication/manifests/checkpoints_seed${canonical_seed}.json" \
        --num-rollouts 25 \
        --seed "${rollout_seed}" \
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
        --output-dir "dataset/tro_position_stage2_axial/rollouts/formal/seed${canonical_seed}/rollout_seed${rollout_seed}/${bank}" \
        --start-manifest "experiments/tro_stage2_position_axial_replication/manifests/rollout_5seed/${bank_id}.json" \
        --merge-only
    done
  done
done
