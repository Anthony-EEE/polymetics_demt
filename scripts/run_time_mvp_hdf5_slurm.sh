#!/bin/bash -l

#SBATCH --job-name=time_mvp_hdf5
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=12:00:00
#SBATCH --partition=cpu
#SBATCH --hint=nomultithread
#SBATCH --output=/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/time_mvp_full/logs/hdf5-%j.out
#SBATCH --error=/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/time_mvp_full/logs/hdf5-%j.err

set -euo pipefail

PROJECT_DIR=${PROJECT_DIR:-"/scratch/prj/eng_demt_robot_learning/polymetics_demt"}
CONDA_ENV=${CONDA_ENV:-"/scratch/users/k23114984/conda/arcap"}
SCRIPT=${SCRIPT:-"scripts/create_time_mvp_hdf5.py"}
DATASET_ROOT=${DATASET_ROOT:-"${PROJECT_DIR}/dataset/time_mvp_full"}
LOG_DIR="${DATASET_ROOT}/logs"

mkdir -p "${LOG_DIR}"
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
export HDF5_USE_FILE_LOCKING=FALSE

echo "[INFO] SLURM Job ID: ${SLURM_JOB_ID:-N/A}"
echo "[INFO] Node list: ${SLURM_NODELIST:-N/A}"
echo "[INFO] Python: $(command -v python)"
python --version
python "${SCRIPT}" --dataset-root "${DATASET_ROOT}" "$@"
echo "[INFO] Finished temporal MVP HDF5 conversion"
