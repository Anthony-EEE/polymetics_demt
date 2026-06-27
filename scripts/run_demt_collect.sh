#!/bin/bash -l

# SLURM job script for DEMT raw data collection with PyBullet DIRECT mode.
#
# Submit examples:
#   sbatch scripts/run_demt_collect.sh
#   TASK=insert NUM_DEMOS=100 SEED=2 sbatch scripts/run_demt_collect.sh
#   TASK=grasp APPROACH_NOISE_MODE=xz_grid APPROACH_NOISE_RADIUS=0.04 APPROACH_GRID_SIZE=5 sbatch scripts/run_demt_collect.sh
#
# Extra Python args can be appended after "--":
#   sbatch scripts/run_demt_collect.sh -- --gripper-orientation tilt

# ===== SLURM DIRECTIVES =====
#SBATCH --job-name=demt_collect
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=08:00:00
#SBATCH --partition=cpu
#SBATCH --hint=nomultithread
#SBATCH --output=/scratch/prj/eng_demt_robot_learning/polymetics_demt/logs/collect-%j.out
#SBATCH --error=/scratch/prj/eng_demt_robot_learning/polymetics_demt/logs/collect-%j.err

set -euo pipefail

echo "[INFO] SLURM Job ID: ${SLURM_JOB_ID:-N/A}"
echo "[INFO] Node list: ${SLURM_NODELIST:-N/A}"
echo "[INFO] CPUs per task: ${SLURM_CPUS_PER_TASK:-N/A}"
echo "[INFO] Working dir at submit: $(pwd)"

# ===== USER CONFIGURABLE SECTION =====
PROJECT_DIR=${PROJECT_DIR:-"/scratch/prj/eng_demt_robot_learning/polymetics_demt"}
CONDA_ENV=${CONDA_ENV:-"/scratch/users/k23114984/conda/envs/polymetis38"}
OUTPUT_ROOT=${OUTPUT_ROOT:-"${PROJECT_DIR}/dataset"}
LOG_DIR=${LOG_DIR:-"${PROJECT_DIR}/logs"}
MODULES=${MODULES:-"anaconda3/2022.10-gcc-13.2.0"}

# TASK selects the collection script:
#   grasp  -> examples/main.py
#   insert -> examples/main_insert.py
TASK=${TASK:-"grasp"}
RUN_NAME=${RUN_NAME:-}
NUM_DEMOS=${NUM_DEMOS:-100}
SEED=${SEED:-1}
SAMPLE_HZ=${SAMPLE_HZ:-30}
MODE=${MODE:-"success"}
GRIPPER_ORIENTATION=${GRIPPER_ORIENTATION:-"default"}
MAX_COLLECTION_ATTEMPTS=${MAX_COLLECTION_ATTEMPTS:-0}

# Grasp-only approach noise controls.
APPROACH_NOISE_MODE=${APPROACH_NOISE_MODE:-"none"}
APPROACH_NOISE_RADIUS=${APPROACH_NOISE_RADIUS:-0.0}
APPROACH_GRID_SIZE=${APPROACH_GRID_SIZE:-3}
SUCCESS_LIFT_HEIGHT=${SUCCESS_LIFT_HEIGHT:-0.20}

# Insert-only success controls.
START_WITH_PEG=${START_WITH_PEG:-true}
SUCCESS_XY_TOLERANCE=${SUCCESS_XY_TOLERANCE:-0.012}
SUCCESS_MAX_PEG_CENTER_Z=${SUCCESS_MAX_PEG_CENTER_Z:-0.12}
SUCCESS_MIN_VERTICAL_DOT=${SUCCESS_MIN_VERTICAL_DOT:-0.95}

# ===== ENV/SETUP =====
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
  ln -sf "${LOG_DIR}/collect-${SLURM_JOB_ID}.out" "logs/collect-${SLURM_JOB_ID}.out" 2>/dev/null || true
  ln -sf "${LOG_DIR}/collect-${SLURM_JOB_ID}.err" "logs/collect-${SLURM_JOB_ID}.err" 2>/dev/null || true
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

case "${TASK}" in
  grasp|cube|cube_grasp|cube_grasp_lift)
    PY_SCRIPT="examples/main.py"
    TASK_LABEL="grasp"
    if [[ -z "${RUN_NAME}" ]]; then
      RUN_NAME="grasp_d${NUM_DEMOS}_seed${SEED}_${APPROACH_NOISE_MODE}_r${APPROACH_NOISE_RADIUS}"
    fi
    args=(
      "--output-dir" "${OUTPUT_ROOT}/${RUN_NAME}"
      "--num-demos" "${NUM_DEMOS}"
      "--seed" "${SEED}"
      "--sample-hz" "${SAMPLE_HZ}"
      "--mode" "${MODE}"
      "--gripper-orientation" "${GRIPPER_ORIENTATION}"
      "--approach-noise-mode" "${APPROACH_NOISE_MODE}"
      "--approach-noise-radius" "${APPROACH_NOISE_RADIUS}"
      "--approach-grid-size" "${APPROACH_GRID_SIZE}"
      "--success-lift-height" "${SUCCESS_LIFT_HEIGHT}"
      "--max-collection-attempts" "${MAX_COLLECTION_ATTEMPTS}"
      "--no-gui"
    )
    ;;
  insert|peg|peg_insert)
    PY_SCRIPT="examples/main_insert.py"
    TASK_LABEL="insert"
    if [[ -z "${RUN_NAME}" ]]; then
      RUN_NAME="insert_d${NUM_DEMOS}_seed${SEED}"
    fi
    args=(
      "--output-dir" "${OUTPUT_ROOT}/${RUN_NAME}"
      "--num-demos" "${NUM_DEMOS}"
      "--seed" "${SEED}"
      "--sample-hz" "${SAMPLE_HZ}"
      "--mode" "${MODE}"
      "--gripper-orientation" "${GRIPPER_ORIENTATION}"
      "--success-xy-tolerance" "${SUCCESS_XY_TOLERANCE}"
      "--success-max-peg-center-z" "${SUCCESS_MAX_PEG_CENTER_Z}"
      "--success-min-vertical-dot" "${SUCCESS_MIN_VERTICAL_DOT}"
      "--max-collection-attempts" "${MAX_COLLECTION_ATTEMPTS}"
      "--no-gui"
    )
    if [[ "${START_WITH_PEG}" == "true" || "${START_WITH_PEG}" == "1" || "${START_WITH_PEG}" == "yes" ]]; then
      args+=("--start-with-peg")
    fi
    ;;
  *)
    echo "[ERROR] Unknown TASK='${TASK}'. Use TASK=grasp or TASK=insert."
    exit 1
    ;;
esac

if [[ ! -f "${PY_SCRIPT}" ]]; then
  echo "[ERROR] Could not find ${PY_SCRIPT} in ${PROJECT_DIR}."
  exit 1
fi

args+=("$@")

echo "[INFO] Starting DEMT data collection"
echo "[INFO] Task: ${TASK_LABEL}"
echo "[INFO] Output directory: ${OUTPUT_ROOT}/${RUN_NAME}"
echo "[INFO] Command: python ${PY_SCRIPT} ${args[*]}"

srun --export=ALL \
  --cpu-bind=cores \
  --ntasks=1 \
  python "${PY_SCRIPT}" "${args[@]}"

exit_code=$?
echo "[INFO] Data collection finished with exit code: ${exit_code}"
exit ${exit_code}
