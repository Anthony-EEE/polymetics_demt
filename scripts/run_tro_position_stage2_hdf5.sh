#!/bin/bash -l

#SBATCH --job-name=tro_s2_hdf5
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=12:00:00
#SBATCH --partition=interruptible_cpu
#SBATCH --hint=nomultithread
#SBATCH --output=/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/tro_position_stage2_axial/logs/hdf5-%A_%a.out
#SBATCH --error=/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/tro_position_stage2_axial/logs/hdf5-%A_%a.err

set -euo pipefail

PROJECT_DIR=${PROJECT_DIR:-"/scratch/prj/eng_demt_robot_learning/polymetics_demt"}
PYTHON=${PYTHON:-"/scratch/users/k23114984/conda/arcap/bin/python"}
TASK_ID=${SLURM_ARRAY_TASK_ID:?Submit as --array=0-4}
canonical_seed=$(( TASK_ID + 1 ))

cd "${PROJECT_DIR}"
export PYTHONUNBUFFERED=1
export OMP_NUM_THREADS=${SLURM_CPUS_PER_TASK:-8}
export HDF5_USE_FILE_LOCKING=FALSE

srun --export=ALL --cpu-bind=cores --ntasks=1 \
  "${PYTHON}" -u scripts/tro_position_stage2.py create-hdf5 \
  --canonical-seed "${canonical_seed}"
