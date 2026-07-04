#!/bin/bash -l

set -euo pipefail

PROJECT_DIR=${PROJECT_DIR:-"/scratch/prj/eng_demt_robot_learning/polymetics_demt"}
ARCAP_TRAIN_DIR=${ARCAP_TRAIN_DIR:-"/users/k23114984/code/arcap_policy/STEP2_train_policy"}
RUN_SCRIPT=${RUN_SCRIPT:-"${ARCAP_TRAIN_DIR}/run_pybullet_dp.sh"}
CONFIG_DIR=${CONFIG_DIR:-"${PROJECT_DIR}/training_config/ar_guidance_spatial_S15_S35"}
OUTPUT_DIR=${OUTPUT_DIR:-"/scratch/prj/eng_demt_robot_learning/trained_models/ar_guidance_spatial_S15_S35"}
SBATCH_DEPENDENCY=${SBATCH_DEPENDENCY:-}

conditions=(S15 S20 S25 S30 S35)

for condition in "${conditions[@]}"; do
  config="${CONFIG_DIR}/spatial_${condition}.json"
  exp_name="spatial_${condition}_d30_seed1_2gap"
  slurm_name="spat_${condition}_dp"

  if [[ ! -f "${config}" ]]; then
    echo "[ERROR] Missing config: ${config}" >&2
    exit 1
  fi

  sbatch_args=(--parsable --job-name="${slurm_name}")
  if [[ -n "${SBATCH_DEPENDENCY}" ]]; then
    sbatch_args+=(--dependency="${SBATCH_DEPENDENCY}")
  fi

  job_id=$(sbatch "${sbatch_args[@]}" \
    "${RUN_SCRIPT}" \
    --config "${config}" \
    --name "${exp_name}" \
    --output "${OUTPUT_DIR}/${condition}")

  echo "${condition}: submitted job ${job_id} with config ${config}"
done
