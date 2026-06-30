#!/bin/bash -l

set -euo pipefail

PROJECT_DIR=${PROJECT_DIR:-"/scratch/prj/eng_demt_robot_learning/polymetics_demt"}
ARCAP_TRAIN_DIR=${ARCAP_TRAIN_DIR:-"/users/k23114984/code/arcap_policy/STEP2_train_policy"}
RUN_SCRIPT=${RUN_SCRIPT:-"${ARCAP_TRAIN_DIR}/run_pybullet_dp.sh"}
CONFIG_DIR=${CONFIG_DIR:-"${PROJECT_DIR}/training_config/abla1_arcenter"}
OUTPUT_DIR=${OUTPUT_DIR:-"${PROJECT_DIR}/dataset/abla1_full_arcenter/trained_models"}

conditions=(P00 P01 P10 P11)

for condition in "${conditions[@]}"; do
  config="${CONFIG_DIR}/abla1_arcenter_${condition}.json"
  exp_name="abla1_arcenter_${condition}_d30_seed1_2gap"
  slurm_name="abla1c_${condition}_dp"

  if [[ ! -f "${config}" ]]; then
    echo "[ERROR] Missing config: ${config}" >&2
    exit 1
  fi

  job_id=$(sbatch --parsable \
    --job-name="${slurm_name}" \
    "${RUN_SCRIPT}" \
    --config "${config}" \
    --name "${exp_name}" \
    --output "${OUTPUT_DIR}")

  echo "${condition}: submitted job ${job_id} with config ${config}"
done
