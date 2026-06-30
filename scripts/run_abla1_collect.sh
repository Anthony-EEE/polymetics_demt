#!/bin/bash -l

# SLURM job script for Ablation 1 cube corridor data collection.
#
# Submit examples:
#   CONDITION=P00 NUM_DEMOS=5 SEED=1 sbatch scripts/run_abla1_collect.sh
#   CONDITION=P11 NUM_DEMOS=30 SEED=3 OUTPUT_ROOT=/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full sbatch scripts/run_abla1_collect.sh
#
# Extra Python args can be appended after "--":
#   CONDITION=P00 sbatch scripts/run_abla1_collect.sh -- --corridor-start-radius 0.15
#   CONDITION=P00 CORRIDOR_START_CENTER_X=0.30 CORRIDOR_START_CENTER_Y=0.0 CORRIDOR_START_CENTER_Z=0.50 sbatch scripts/run_abla1_collect.sh

# ===== SLURM DIRECTIVES =====
#SBATCH --job-name=abla1_collect
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=08:00:00
#SBATCH --partition=interruptible_cpu
#SBATCH --hint=nomultithread
#SBATCH --output=/scratch/prj/eng_demt_robot_learning/polymetics_demt/logs/abla1-%j.out
#SBATCH --error=/scratch/prj/eng_demt_robot_learning/polymetics_demt/logs/abla1-%j.err

set -euo pipefail

echo "[INFO] SLURM Job ID: ${SLURM_JOB_ID:-N/A}"
echo "[INFO] Node list: ${SLURM_NODELIST:-N/A}"
echo "[INFO] CPUs per task: ${SLURM_CPUS_PER_TASK:-N/A}"
echo "[INFO] Working dir at submit: $(pwd)"

# ===== USER CONFIGURABLE SECTION =====
PROJECT_DIR=${PROJECT_DIR:-"/scratch/prj/eng_demt_robot_learning/polymetics_demt"}
CONDA_ENV=${CONDA_ENV:-"/scratch/users/k23114984/conda/envs/polymetis38"}
OUTPUT_ROOT=${OUTPUT_ROOT:-"${PROJECT_DIR}/dataset/abla1"}
LOG_DIR=${LOG_DIR:-"${PROJECT_DIR}/logs"}
MODULES=${MODULES:-"anaconda3/2022.10-gcc-13.2.0"}

CONDITION=${CONDITION:-"P00"}
NUM_DEMOS=${NUM_DEMOS:-5}
SEED=${SEED:-1}
SAMPLE_HZ=${SAMPLE_HZ:-30}
RUN_NAME=${RUN_NAME:-"abla1_${CONDITION}_d${NUM_DEMOS}_seed${SEED}"}
MAX_COLLECTION_ATTEMPTS=${MAX_COLLECTION_ATTEMPTS:-0}
SUCCESS_LIFT_HEIGHT=${SUCCESS_LIFT_HEIGHT:-0.20}

CORRIDOR_START_CENTER_X=${CORRIDOR_START_CENTER_X:-0.30}
CORRIDOR_START_CENTER_Y=${CORRIDOR_START_CENTER_Y:-0.0}
CORRIDOR_START_CENTER_Z=${CORRIDOR_START_CENTER_Z:-0.50}
ENTRY_DX=${ENTRY_DX:-}
CORRIDOR_START_Y=${CORRIDOR_START_Y:-}
ENTRY_DZ=${ENTRY_DZ:-}
# Optional radius overrides. Leave empty to use the condition table in examples/main_abla_1.py.
CORRIDOR_START_RADIUS=${CORRIDOR_START_RADIUS:-}
PRE_GRASP_RADIUS=${PRE_GRASP_RADIUS:-}

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
  ln -sf "${LOG_DIR}/abla1-${SLURM_JOB_ID}.out" "logs/abla1-${SLURM_JOB_ID}.out" 2>/dev/null || true
  ln -sf "${LOG_DIR}/abla1-${SLURM_JOB_ID}.err" "logs/abla1-${SLURM_JOB_ID}.err" 2>/dev/null || true
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
  P00|P10|P01|P11)
    ;;
  *)
    echo "[ERROR] Unknown CONDITION='${CONDITION}'. Use one of: P00 P10 P01 P11."
    exit 1
    ;;
esac

PY_SCRIPT="examples/main_abla_1.py"
if [[ ! -f "${PY_SCRIPT}" ]]; then
  echo "[ERROR] Could not find ${PY_SCRIPT} in ${PROJECT_DIR}."
  exit 1
fi

args=(
  "--mode" "ablation"
  "--output-dir" "${OUTPUT_ROOT}/${RUN_NAME}"
  "--num-demos" "${NUM_DEMOS}"
  "--seed" "${SEED}"
  "--sample-hz" "${SAMPLE_HZ}"
  "--ablation-condition" "${CONDITION}"
  "--corridor-start-center-x" "${CORRIDOR_START_CENTER_X}"
  "--corridor-start-center-y" "${CORRIDOR_START_CENTER_Y}"
  "--corridor-start-center-z" "${CORRIDOR_START_CENTER_Z}"
  "--success-lift-height" "${SUCCESS_LIFT_HEIGHT}"
  "--max-collection-attempts" "${MAX_COLLECTION_ATTEMPTS}"
  "--no-gui"
)

if [[ -n "${CORRIDOR_START_RADIUS}" ]]; then
  args+=("--corridor-start-radius" "${CORRIDOR_START_RADIUS}")
fi
if [[ -n "${PRE_GRASP_RADIUS}" ]]; then
  args+=("--pre-grasp-radius" "${PRE_GRASP_RADIUS}")
fi
if [[ -n "${ENTRY_DX}${CORRIDOR_START_Y}${ENTRY_DZ}" ]]; then
  echo "[WARN] ENTRY_DX, CORRIDOR_START_Y, and ENTRY_DZ are deprecated and ignored."
  echo "[WARN] Use CORRIDOR_START_CENTER_X/Y/Z for the AR guidance corridor-start center."
fi

args+=("$@")

echo "[INFO] Starting Ablation 1 data collection"
echo "[INFO] Condition: ${CONDITION}"
echo "[INFO] Run name: ${RUN_NAME}"
echo "[INFO] Output directory: ${OUTPUT_ROOT}/${RUN_NAME}"
echo "[INFO] Corridor start center: (${CORRIDOR_START_CENTER_X}, ${CORRIDOR_START_CENTER_Y}, ${CORRIDOR_START_CENTER_Z})"
echo "[INFO] Command: python ${PY_SCRIPT} ${args[*]}"

srun --export=ALL \
  --cpu-bind=cores \
  --ntasks=1 \
  python "${PY_SCRIPT}" "${args[@]}"

exit_code=$?
echo "[INFO] Ablation 1 data collection finished with exit code: ${exit_code}"
exit ${exit_code}
