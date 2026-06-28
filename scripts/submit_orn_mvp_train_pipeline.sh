#!/bin/bash -l

set -euo pipefail

PROJECT_DIR=${PROJECT_DIR:-"/scratch/prj/eng_demt_robot_learning/polymetics_demt"}
ARCAP_TRAIN_DIR=${ARCAP_TRAIN_DIR:-"/users/k23114984/code/arcap_policy/STEP2_train_policy"}
RUN_SCRIPT=${RUN_SCRIPT:-"${ARCAP_TRAIN_DIR}/run_pybullet_dp.sh"}
CONFIG_DIR=${CONFIG_DIR:-"${PROJECT_DIR}/training_config/orn_mvp"}
OUTPUT_DIR=${OUTPUT_DIR:-"${ARCAP_TRAIN_DIR}/trained_models"}

conditions=(R00 R15 R30)

prev_job=""

for condition in "${conditions[@]}"; do
  config="${CONFIG_DIR}/orn_mvp_${condition}.json"
  exp_name="orn_mvp_${condition}_d30_seed1_2gap"
  slurm_name="orn_${condition}_dp"

  if [[ ! -f "${config}" ]]; then
    echo "[ERROR] Missing config: ${config}" >&2
    exit 1
  fi

  if [[ -n "${prev_job}" ]]; then
    job_id=$(sbatch --parsable \
      --job-name="${slurm_name}" \
      --dependency="afterok:${prev_job}" \
      "${RUN_SCRIPT}" \
      --config "${config}" \
      --name "${exp_name}" \
      --output "${OUTPUT_DIR}")
  else
    job_id=$(sbatch --parsable \
      --job-name="${slurm_name}" \
      "${RUN_SCRIPT}" \
      --config "${config}" \
      --name "${exp_name}" \
      --output "${OUTPUT_DIR}")
  fi

  echo "${condition}: submitted job ${job_id} with config ${config}"
  prev_job="${job_id}"
done
