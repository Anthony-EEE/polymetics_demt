#!/bin/bash -l

#SBATCH --job-name=ar_guidance_loss
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=01:00:00
#SBATCH --partition=interruptible_cpu
#SBATCH --hint=nomultithread
#SBATCH --output=/scratch/prj/eng_demt_robot_learning/polymetics_demt/logs/ar-guidance-loss-%j.out
#SBATCH --error=/scratch/prj/eng_demt_robot_learning/polymetics_demt/logs/ar-guidance-loss-%j.err

set -euo pipefail

PROJECT_DIR=${PROJECT_DIR:-"/scratch/prj/eng_demt_robot_learning/polymetics_demt"}
CONDA_ENV=${CONDA_ENV:-"/scratch/users/k23114984/conda/envs/polymetis38"}
MODULES=${MODULES:-"anaconda3/2022.10-gcc-13.2.0"}
TRACK=${TRACK:-"all"}

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
export MPLBACKEND=Agg

python scripts/summarize_ar_guidance_training.py --track "${TRACK}"
