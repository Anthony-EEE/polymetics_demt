#!/bin/bash

set -euo pipefail

PROJECT_DIR=${PROJECT_DIR:-"/scratch/prj/eng_demt_robot_learning/polymetics_demt"}
TRAIN_SCRIPT=${TRAIN_SCRIPT:-"/users/k23114984/code/arcap_policy/STEP2_train_policy/run_pybullet_dp.sh"}
PARTITION=${PARTITION:-gpu}
CONFIG_DIR="${PROJECT_DIR}/experiments/mvp0_position_event/confirmation_earlystop/configs/training"
MODEL_ROOT="/scratch/prj/eng_demt_robot_learning/trained_models/tro_position_confirmation"
LOG_DIR="${PROJECT_DIR}/dataset/tro_position_confirmation/logs"

conditions=(
  START15_APP6
  START35_APP6
  START25_APP3P6
  START25_APP8P4
)

mkdir -p "${LOG_DIR}"
for condition in "${conditions[@]}"; do
  config="${CONFIG_DIR}/${condition}.json"
  if [[ ! -f "${config}" ]]; then
    echo "[ERROR] Missing confirmation training config: ${config}" >&2
    exit 1
  fi
  name="tro_pos_confirm_${condition}"
  condition_root="${MODEL_ROOT}/${condition}"
  if find "${condition_root}" -type f -name 'model_epoch_*.pth' -print -quit 2>/dev/null | grep -q .; then
    echo "[ERROR] Refusing duplicate training; checkpoint already exists under ${condition_root}" >&2
    exit 1
  fi
  job_id=$(sbatch --parsable \
    --partition="${PARTITION}" \
    --export=ALL,WANDB_SILENT=true,WANDB_CONSOLE=off \
    --job-name="${name}" \
    --output="${LOG_DIR}/train-${name}-%j.out" \
    --error="${LOG_DIR}/train-${name}-%j.err" \
    "${TRAIN_SCRIPT}" \
    --config "${config}" \
    --name "tro_pos_confirm_${condition}_d30_seed2701_2gap" \
    --output "${condition_root}")
  echo "${condition} ${job_id}"
done
