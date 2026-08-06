#!/bin/bash

set -euo pipefail

PROJECT_DIR=${PROJECT_DIR:-"/scratch/prj/eng_demt_robot_learning/polymetics_demt"}
TRAIN_SCRIPT=${TRAIN_SCRIPT:-"/users/k23114984/code/arcap_policy/STEP2_train_policy/run_pybullet_dp.sh"}
BLOCK=${BLOCK:-0}
PARTITION=${PARTITION:-interruptible_gpu}
CONFIG_DIR="${PROJECT_DIR}/experiments/mvp0_position_event/configs/training_generated/block${BLOCK}"
MODEL_ROOT="/scratch/prj/eng_demt_robot_learning/trained_models/tro_position_mvp0/block${BLOCK}"
LOG_DIR="${PROJECT_DIR}/dataset/tro_position_mvp0/logs"

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
    echo "[ERROR] Missing frozen training config: ${config}" >&2
    exit 1
  fi
  name="tro_pos_b${BLOCK}_${condition}"
  job_id=$(sbatch --parsable \
    --partition="${PARTITION}" \
    --job-name="${name}" \
    --output="${LOG_DIR}/train-${name}-%j.out" \
    --error="${LOG_DIR}/train-${name}-%j.err" \
    "${TRAIN_SCRIPT}" \
    --config "${config}" \
    --name "tro_pos_b${BLOCK}_${condition}_d30" \
    --output "${MODEL_ROOT}/${condition}")
  echo "${condition} ${job_id}"
done
