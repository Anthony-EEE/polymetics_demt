#!/bin/bash -l

set -euo pipefail

PROJECT_DIR=${PROJECT_DIR:-"/scratch/prj/eng_demt_robot_learning/polymetics_demt"}
ARCAP_TRAIN_DIR=${ARCAP_TRAIN_DIR:-"/users/k23114984/code/arcap_policy/STEP2_train_policy"}
RUN_SCRIPT=${RUN_SCRIPT:-"${ARCAP_TRAIN_DIR}/run_pybullet_dp.sh"}
CONFIG_DIR=${CONFIG_DIR:-"${PROJECT_DIR}/training_config/temporal_vref_reciprocal_spatial_v2"}
OUTPUT_DIR=${OUTPUT_DIR:-"/scratch/prj/eng_demt_robot_learning/trained_models/temporal_vref_reciprocal_spatial_v2"}
LOG_DIR=${LOG_DIR:-"${PROJECT_DIR}/dataset/temporal_vref_reciprocal_spatial_v2/logs"}
SBATCH_PARTITION=${SBATCH_PARTITION:-"interruptible_gpu"}
SBATCH_DEPENDENCY=${SBATCH_DEPENDENCY:-}
SBATCH_EXCLUDE=${SBATCH_EXCLUDE:-}
CONDITIONS=${CONDITIONS:-"VR1P5 V050_200 VR3 VR4"}
RUN_TEMPLATE=${RUN_TEMPLATE:-"temporal_{condition}_d30_seed1_2gap"}
WANDB_MODE=${WANDB_MODE:-"disabled"}
WANDB_DIR=${WANDB_DIR:-"${PROJECT_DIR}/dataset/temporal_vref_reciprocal_spatial_v2/wandb"}
WANDB_CACHE_DIR=${WANDB_CACHE_DIR:-"${WANDB_DIR}/cache"}

read -r -a conditions <<< "${CONDITIONS}"
mkdir -p "${LOG_DIR}" "${OUTPUT_DIR}" "${WANDB_DIR}" "${WANDB_CACHE_DIR}"
export WANDB_MODE WANDB_DIR WANDB_CACHE_DIR

for condition in "${conditions[@]}"; do
  config="${CONFIG_DIR}/temporal_${condition}.json"
  exp_name="${RUN_TEMPLATE//\{condition\}/${condition}}"
  slurm_name="time_${condition}_dp"

  if [[ ! -f "${config}" ]]; then
    echo "[ERROR] Missing config: ${config}" >&2
    exit 1
  fi

  sbatch_args=(
    --parsable
    --partition="${SBATCH_PARTITION}"
    --job-name="${slurm_name}"
    --output="${LOG_DIR}/train-${condition}-%j.out"
    --error="${LOG_DIR}/train-${condition}-%j.err"
  )
  if [[ -n "${SBATCH_DEPENDENCY}" ]]; then
    sbatch_args+=(--dependency="${SBATCH_DEPENDENCY}")
  fi
  if [[ -n "${SBATCH_EXCLUDE}" ]]; then
    sbatch_args+=(--exclude="${SBATCH_EXCLUDE}")
  fi

  job_id=$(sbatch "${sbatch_args[@]}" \
    "${RUN_SCRIPT}" \
    --config "${config}" \
    --name "${exp_name}" \
    --output "${OUTPUT_DIR}/${condition}")

  echo "${condition}: submitted job ${job_id} with config ${config}"
done
