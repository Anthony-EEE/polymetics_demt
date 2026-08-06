#!/bin/bash -l

#SBATCH --job-name=tro_pos_hdf5
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=12:00:00
#SBATCH --partition=interruptible_cpu
#SBATCH --hint=nomultithread
#SBATCH --output=/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/tro_position_mvp0/logs/hdf5-%j.out
#SBATCH --error=/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/tro_position_mvp0/logs/hdf5-%j.err

set -euo pipefail

PROJECT_DIR=${PROJECT_DIR:-"/scratch/prj/eng_demt_robot_learning/polymetics_demt"}
PYTHON=${PYTHON:-"/scratch/users/k23114984/conda/arcap/bin/python"}
BLOCK=${BLOCK:-0}

cd "${PROJECT_DIR}"
export PYTHONUNBUFFERED=1
export OMP_NUM_THREADS=${SLURM_CPUS_PER_TASK:-8}
export HDF5_USE_FILE_LOCKING=FALSE

srun --export=ALL --cpu-bind=cores --ntasks=1 \
  "${PYTHON}" -u scripts/tro_position_mvp0.py create-hdf5 --block "${BLOCK}"

"${PYTHON}" scripts/tro_position_mvp0.py create-train-configs --block "${BLOCK}"
