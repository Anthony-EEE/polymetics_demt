#!/bin/bash -l

# SLURM job script for temporal-threshold MVP cube data collection.
#
# Submit examples:
#   CONDITION=T00 NUM_DEMOS=1 SEED=7 sbatch scripts/run_time_mvp_collect.sh
#   CONDITION=V050_200 NUM_DEMOS=30 SEED=1 OUTPUT_ROOT=... sbatch scripts/run_time_mvp_collect.sh

#SBATCH --job-name=time_mvp_collect
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=08:00:00
#SBATCH --partition=interruptible_cpu
#SBATCH --hint=nomultithread
#SBATCH --output=/scratch/prj/eng_demt_robot_learning/polymetics_demt/logs/time-mvp-%j.out
#SBATCH --error=/scratch/prj/eng_demt_robot_learning/polymetics_demt/logs/time-mvp-%j.err

set -euo pipefail

PROJECT_DIR=${PROJECT_DIR:-"/scratch/prj/eng_demt_robot_learning/polymetics_demt"}
CONDA_ENV=${CONDA_ENV:-"/scratch/users/k23114984/conda/envs/polymetis38"}
OUTPUT_ROOT=${OUTPUT_ROOT:-"${PROJECT_DIR}/dataset/ar_guidance_temporal_T00_T100"}
LOG_DIR=${LOG_DIR:-"${PROJECT_DIR}/logs"}
MODULES=${MODULES:-"anaconda3/2022.10-gcc-13.2.0"}

CONDITION=${CONDITION:-"T00"}
NUM_DEMOS=${NUM_DEMOS:-5}
SEED=${SEED:-1}
SAMPLE_HZ=${SAMPLE_HZ:-30}
RUN_NAME=${RUN_NAME:-"temporal_${CONDITION}_d${NUM_DEMOS}_seed${SEED}"}
MAX_COLLECTION_ATTEMPTS=${MAX_COLLECTION_ATTEMPTS:-0}
SUCCESS_LIFT_HEIGHT=${SUCCESS_LIFT_HEIGHT:-0.20}

CORRIDOR_START_RADIUS=${CORRIDOR_START_RADIUS:-0.05}
PRE_GRASP_RADIUS=${PRE_GRASP_RADIUS:-0.0}
ENTRY_DX=${ENTRY_DX:-0.20}
CORRIDOR_START_Y=${CORRIDOR_START_Y:-0.15}
ENTRY_DZ=${ENTRY_DZ:-0.06}
RANDOM_START_X=${RANDOM_START_X:-0.40}
RANDOM_START_Z=${RANDOM_START_Z:-0.40}
RANDOM_START_MAX_ATTEMPTS=${RANDOM_START_MAX_ATTEMPTS:-200}
V_REF_SOURCE_JSON=${V_REF_SOURCE_JSON:-"outputs/week2_human_phase_reference_p6p7_v2/v_ref_phase_reference.json"}
V_REF_GROUP=${V_REF_GROUP:-"P6P7_post_valid_order"}

mkdir -p "${LOG_DIR}" "${OUTPUT_ROOT}"

echo "[INFO] SLURM Job ID: ${SLURM_JOB_ID:-N/A}"
echo "[INFO] Node list: ${SLURM_NODELIST:-N/A}"
echo "[INFO] Changing directory to: ${PROJECT_DIR}"
cd "${PROJECT_DIR}"

if command -v module >/dev/null 2>&1; then
  module purge || true
  for m in ${MODULES}; do
    module load "${m}" || true
  done
fi

if command -v conda >/dev/null 2>&1; then
  [[ -f "/users/${USER}/.bashrc" ]] && source "/users/${USER}/.bashrc"
  source "$(conda info --base)/etc/profile.d/conda.sh"
  conda activate "${CONDA_ENV}"
else
  echo "[ERROR] conda command not found."
  exit 1
fi

export PYTHONUNBUFFERED=1
export OMP_NUM_THREADS=${SLURM_CPUS_PER_TASK:-4}
export OPENBLAS_NUM_THREADS=${SLURM_CPUS_PER_TASK:-4}
export MKL_NUM_THREADS=${SLURM_CPUS_PER_TASK:-4}

case "${CONDITION}" in
  T00|T25|T50|T75|T100|V075_150|V050_200|V025_250) ;;
  *)
    echo "[ERROR] Unknown CONDITION='${CONDITION}'. Use one of: T00 T25 T50 T75 T100 V075_150 V050_200 V025_250."
    exit 1
    ;;
esac

if [[ "${1-}" == "--" ]]; then
  shift
fi

args=(
  "--output-dir" "${OUTPUT_ROOT}/${RUN_NAME}"
  "--num-demos" "${NUM_DEMOS}"
  "--seed" "${SEED}"
  "--sample-hz" "${SAMPLE_HZ}"
  "--time-condition" "${CONDITION}"
  "--corridor-start-radius" "${CORRIDOR_START_RADIUS}"
  "--pre-grasp-radius" "${PRE_GRASP_RADIUS}"
  "--entry-dx" "${ENTRY_DX}"
  "--corridor-start-y" "${CORRIDOR_START_Y}"
  "--entry-dz" "${ENTRY_DZ}"
  "--random-start-x" "${RANDOM_START_X}"
  "--random-start-z" "${RANDOM_START_Z}"
  "--random-start-max-attempts" "${RANDOM_START_MAX_ATTEMPTS}"
  "--v-ref-source-json" "${V_REF_SOURCE_JSON}"
  "--v-ref-group" "${V_REF_GROUP}"
  "--success-lift-height" "${SUCCESS_LIFT_HEIGHT}"
  "--max-collection-attempts" "${MAX_COLLECTION_ATTEMPTS}"
  "--no-gui"
)
args+=("$@")

echo "[INFO] Starting temporal MVP data collection"
echo "[INFO] Condition: ${CONDITION}"
echo "[INFO] Run name: ${RUN_NAME}"
echo "[INFO] Command: python examples/main_time_mvp.py ${args[*]}"

srun --export=ALL --cpu-bind=cores --ntasks=1 python examples/main_time_mvp.py "${args[@]}"
