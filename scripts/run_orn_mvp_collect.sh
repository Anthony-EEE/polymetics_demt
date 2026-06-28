#!/bin/bash -l

# SLURM job script for orientation/grasp-cue MVP cube data collection.
#
# Submit examples:
#   CONDITION=R00 NUM_DEMOS=1 SEED=7 OUTPUT_ROOT=/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/orn_mvp_debug sbatch scripts/run_orn_mvp_collect.sh
#   CONDITION=R30 NUM_DEMOS=30 SEED=1 OUTPUT_ROOT=/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/orn_mvp_full sbatch scripts/run_orn_mvp_collect.sh

#SBATCH --job-name=orn_mvp_collect
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=08:00:00
#SBATCH --partition=cpu
#SBATCH --hint=nomultithread
#SBATCH --output=/scratch/prj/eng_demt_robot_learning/polymetics_demt/logs/orn-mvp-%j.out
#SBATCH --error=/scratch/prj/eng_demt_robot_learning/polymetics_demt/logs/orn-mvp-%j.err

set -euo pipefail

echo "[INFO] SLURM Job ID: ${SLURM_JOB_ID:-N/A}"
echo "[INFO] Node list: ${SLURM_NODELIST:-N/A}"
echo "[INFO] CPUs per task: ${SLURM_CPUS_PER_TASK:-N/A}"
echo "[INFO] Working dir at submit: $(pwd)"

PROJECT_DIR=${PROJECT_DIR:-"/scratch/prj/eng_demt_robot_learning/polymetics_demt"}
CONDA_ENV=${CONDA_ENV:-"/scratch/users/k23114984/conda/envs/polymetis38"}
OUTPUT_ROOT=${OUTPUT_ROOT:-"${PROJECT_DIR}/dataset/orn_mvp"}
LOG_DIR=${LOG_DIR:-"${PROJECT_DIR}/logs"}
MODULES=${MODULES:-"anaconda3/2022.10-gcc-13.2.0"}

CONDITION=${CONDITION:-"R00"}
NUM_DEMOS=${NUM_DEMOS:-5}
SEED=${SEED:-1}
SAMPLE_HZ=${SAMPLE_HZ:-30}
RUN_NAME=${RUN_NAME:-"orn_mvp_${CONDITION}_d${NUM_DEMOS}_seed${SEED}"}
MAX_COLLECTION_ATTEMPTS=${MAX_COLLECTION_ATTEMPTS:-0}
SUCCESS_LIFT_HEIGHT=${SUCCESS_LIFT_HEIGHT:-0.20}

CORRIDOR_START_RADIUS=${CORRIDOR_START_RADIUS:-0.05}
PRE_GRASP_RADIUS=${PRE_GRASP_RADIUS:-0.0}
ENTRY_DX=${ENTRY_DX:-0.20}
CORRIDOR_START_Y=${CORRIDOR_START_Y:-0.15}
ENTRY_DZ=${ENTRY_DZ:-0.06}
RANDOM_START_X_MIN=${RANDOM_START_X_MIN:-0.20}
RANDOM_START_X_MAX=${RANDOM_START_X_MAX:-0.60}
RANDOM_START_Z_MIN=${RANDOM_START_Z_MIN:-0.20}
RANDOM_START_Z_MAX=${RANDOM_START_Z_MAX:-0.60}
RANDOM_START_MAX_ATTEMPTS=${RANDOM_START_MAX_ATTEMPTS:-200}
ORIENTATION_MAX_DEGREES=${ORIENTATION_MAX_DEGREES:-}

mkdir -p "${LOG_DIR}" "${OUTPUT_ROOT}"

echo "[INFO] Changing directory to: ${PROJECT_DIR}"
cd "${PROJECT_DIR}"

if command -v module >/dev/null 2>&1; then
  echo "[INFO] Modules detected. Purging and loading requested modules."
  module purge || true
  for m in ${MODULES}; do
    echo "[INFO] module load ${m}"
    module load "${m}" || true
  done
fi

if command -v conda >/dev/null 2>&1; then
  echo "[INFO] Conda detected. Activating environment: ${CONDA_ENV}"
  if [[ -f "/users/${USER}/.bashrc" ]]; then
    source "/users/${USER}/.bashrc"
  fi
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

if [[ -n "${SLURM_JOB_ID:-}" ]]; then
  ln -sf "${LOG_DIR}/orn-mvp-${SLURM_JOB_ID}.out" "logs/orn-mvp-${SLURM_JOB_ID}.out" 2>/dev/null || true
  ln -sf "${LOG_DIR}/orn-mvp-${SLURM_JOB_ID}.err" "logs/orn-mvp-${SLURM_JOB_ID}.err" 2>/dev/null || true
fi

echo "[INFO] Python: $(command -v python)"
python --version || true
echo "[INFO] Environment summary:"
uname -a || true
free -h || true
df -h "${PROJECT_DIR}" || true
df -h "${OUTPUT_ROOT}" || true

if [[ "${1-}" == "--" ]]; then
  shift
fi

case "${CONDITION}" in
  R00|R15|R30)
    ;;
  *)
    echo "[ERROR] Unknown CONDITION='${CONDITION}'. Use one of: R00 R15 R30."
    exit 1
    ;;
esac

PY_SCRIPT="examples/main_orn_mvp.py"
if [[ ! -f "${PY_SCRIPT}" ]]; then
  echo "[ERROR] Could not find ${PY_SCRIPT} in ${PROJECT_DIR}."
  exit 1
fi

args=(
  "--output-dir" "${OUTPUT_ROOT}/${RUN_NAME}"
  "--num-demos" "${NUM_DEMOS}"
  "--seed" "${SEED}"
  "--sample-hz" "${SAMPLE_HZ}"
  "--orientation-condition" "${CONDITION}"
  "--corridor-start-radius" "${CORRIDOR_START_RADIUS}"
  "--pre-grasp-radius" "${PRE_GRASP_RADIUS}"
  "--entry-dx" "${ENTRY_DX}"
  "--corridor-start-y" "${CORRIDOR_START_Y}"
  "--entry-dz" "${ENTRY_DZ}"
  "--random-start-x-min" "${RANDOM_START_X_MIN}"
  "--random-start-x-max" "${RANDOM_START_X_MAX}"
  "--random-start-z-min" "${RANDOM_START_Z_MIN}"
  "--random-start-z-max" "${RANDOM_START_Z_MAX}"
  "--random-start-max-attempts" "${RANDOM_START_MAX_ATTEMPTS}"
  "--success-lift-height" "${SUCCESS_LIFT_HEIGHT}"
  "--max-collection-attempts" "${MAX_COLLECTION_ATTEMPTS}"
  "--no-gui"
)

if [[ -n "${ORIENTATION_MAX_DEGREES}" ]]; then
  args+=("--orientation-max-degrees" "${ORIENTATION_MAX_DEGREES}")
fi

args+=("$@")

echo "[INFO] Starting orientation MVP data collection"
echo "[INFO] Condition: ${CONDITION}"
echo "[INFO] Run name: ${RUN_NAME}"
echo "[INFO] Output directory: ${OUTPUT_ROOT}/${RUN_NAME}"
echo "[INFO] Command: python ${PY_SCRIPT} ${args[*]}"

srun --export=ALL \
  --cpu-bind=cores \
  --ntasks=1 \
  python "${PY_SCRIPT}" "${args[@]}"

exit_code=$?
echo "[INFO] Orientation MVP data collection finished with exit code: ${exit_code}"
exit ${exit_code}
