#!/bin/bash -l

#SBATCH --job-name=week2_human_diag
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=01:00:00
#SBATCH --partition=interruptible_cpu
#SBATCH --hint=nomultithread
#SBATCH --output=/scratch/prj/eng_demt_robot_learning/polymetics_demt/outputs/week2_human_diagnostics_keypoints_quick/logs/diag-%j.out
#SBATCH --error=/scratch/prj/eng_demt_robot_learning/polymetics_demt/outputs/week2_human_diagnostics_keypoints_quick/logs/diag-%j.err

set -euo pipefail

PROJECT_DIR=${PROJECT_DIR:-"/scratch/prj/eng_demt_robot_learning/polymetics_demt"}
CONDA_ENV=${CONDA_ENV:-"/scratch/users/k23114984/conda/arcap"}
OUTPUT_DIR=${OUTPUT_DIR:-"${PROJECT_DIR}/outputs/week2_human_diagnostics_keypoints_quick"}
FRAME_STRIDE=${FRAME_STRIDE:-10}

mkdir -p "${OUTPUT_DIR}/logs"
cd "${PROJECT_DIR}"

if command -v module >/dev/null 2>&1; then
  module purge || true
  module load anaconda3/2022.10-gcc-13.2.0 || true
fi

if command -v conda >/dev/null 2>&1; then
  source "$(conda info --base)/etc/profile.d/conda.sh"
  conda activate "${CONDA_ENV}"
else
  echo "[ERROR] conda command not found"
  exit 1
fi

export PYTHONUNBUFFERED=1
export OMP_NUM_THREADS=${SLURM_CPUS_PER_TASK:-8}
export MPLCONFIGDIR="${OUTPUT_DIR}/.matplotlib"

echo "[INFO] SLURM Job ID: ${SLURM_JOB_ID:-N/A}"
echo "[INFO] Node list: ${SLURM_NODELIST:-N/A}"
echo "[INFO] Python: $(command -v python)"
python --version

python scripts/analyze_week2_human_data.py \
  --frame-stride "${FRAME_STRIDE}" \
  --output-dir "${OUTPUT_DIR}" \
  "$@"

echo "[INFO] Finished Week 2 human diagnostics"
