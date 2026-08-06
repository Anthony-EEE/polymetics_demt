#!/bin/bash

set -euo pipefail

PROJECT_DIR=${PROJECT_DIR:-"/scratch/prj/eng_demt_robot_learning/polymetics_demt"}
TRAIN_SCRIPT=${TRAIN_SCRIPT:-"/users/k23114984/code/arcap_policy/STEP2_train_policy/run_pybullet_dp.sh"}
PARTITION=${PARTITION:-gpu}
MODEL_ROOT="/scratch/prj/eng_demt_robot_learning/trained_models/tro_position_stage2_axial"
LOG_DIR="${PROJECT_DIR}/dataset/tro_position_stage2_axial/logs"
conditions=(START15_APP6 START35_APP6 START25_APP3P6 START25_APP6 START25_APP8P4)

mkdir -p "${LOG_DIR}"
for canonical_seed in 1 2 3 4 5; do
  case "${canonical_seed}" in
    1) source_seed=1 ;;
    2) source_seed=2 ;;
    3) source_seed=3 ;;
    4) source_seed=2702 ;;
    5) source_seed=2701 ;;
  esac
  for condition in "${conditions[@]}"; do
    config="${PROJECT_DIR}/experiments/tro_stage2_position_axial_replication/configs/training/seed${canonical_seed}/${condition}.json"
    if [[ ! -f "${config}" ]]; then
      continue
    fi
    run_name="stage2_seed${canonical_seed}_source${source_seed}_${condition}"
    condition_root="${MODEL_ROOT}/seed${canonical_seed}/${condition}"
    if find "${condition_root}/${run_name}" -type f -name 'model_epoch_*.pth' -print -quit 2>/dev/null | grep -q .; then
      echo "[ERROR] Refusing duplicate Stage 2 training: seed${canonical_seed}/${condition}" >&2
      exit 1
    fi
    job_id=$(sbatch --parsable \
      --partition="${PARTITION}" \
      --constraint="a100|l40s|h100|h200" \
      --exclude=erc-hpc-comp040,erc-hpc-comp035,erc-hpc-comp223 \
      --export=ALL,WANDB_SILENT=true,WANDB_CONSOLE=off \
      --job-name="tro_s2_s${canonical_seed}_${condition}" \
      --output="${LOG_DIR}/train-s${canonical_seed}-${condition}-%j.out" \
      --error="${LOG_DIR}/train-s${canonical_seed}-${condition}-%j.err" \
      "${TRAIN_SCRIPT}" \
      --config "${config}" \
      --name "${run_name}" \
      --output "${condition_root}")
    printf '%s %s %s\n' "${canonical_seed}" "${condition}" "${job_id}"
  done
done
