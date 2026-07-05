#!/bin/bash -l

#SBATCH --job-name=ar_guidance_split
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=24G
#SBATCH --time=02:00:00
#SBATCH --partition=interruptible_cpu
#SBATCH --hint=nomultithread
#SBATCH --output=/scratch/prj/eng_demt_robot_learning/polymetics_demt/logs/ar-guidance-split-%j.out
#SBATCH --error=/scratch/prj/eng_demt_robot_learning/polymetics_demt/logs/ar-guidance-split-%j.err

set -euo pipefail

PROJECT_DIR=${PROJECT_DIR:-"/scratch/prj/eng_demt_robot_learning/polymetics_demt"}
CONDA_ENV=${CONDA_ENV:-"/scratch/users/k23114984/conda/arcap"}
PYTHON=${PYTHON:-"/scratch/users/k23114984/conda/arcap/bin/python"}
MODULES=${MODULES:-"anaconda3/2022.10-gcc-13.2.0"}
TRACK=${TRACK:-"all"}
RATIO=${RATIO:-"0.1"}
ACTION_GAP=${ACTION_GAP:-"2"}
DATASET_ROOT=${DATASET_ROOT:-}
GROUPS=${GROUPS:-}

mkdir -p "${PROJECT_DIR}/logs"
cd "${PROJECT_DIR}"

if command -v module >/dev/null 2>&1; then
  module purge || true
  for m in ${MODULES}; do
    module load "${m}" || true
  done
fi

if command -v conda >/dev/null 2>&1; then
  source "$(conda info --base)/etc/profile.d/conda.sh"
  conda activate "${CONDA_ENV}"
fi

export PYTHONUNBUFFERED=1
export OMP_NUM_THREADS=${SLURM_CPUS_PER_TASK:-4}
export HDF5_USE_FILE_LOCKING=FALSE

args=(
  scripts/split_ar_guidance_hdf5.py
  --track "${TRACK}"
  --python "${PYTHON}"
  --ratio "${RATIO}"
  --action-gap "${ACTION_GAP}"
)
if [[ -n "${DATASET_ROOT}" || -n "${GROUPS}" ]]; then
  if [[ -z "${DATASET_ROOT}" || -z "${GROUPS}" ]]; then
    echo "[ERROR] DATASET_ROOT and GROUPS must be set together." >&2
    exit 1
  fi
  read -r -a group_args <<< "${GROUPS}"
  args+=(--dataset-root "${DATASET_ROOT}" --groups "${group_args[@]}")
fi

"${PYTHON}" "${args[@]}"

echo "[INFO] AR guidance HDF5 split complete for TRACK=${TRACK}"
