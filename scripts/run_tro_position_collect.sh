#!/bin/bash -l

#SBATCH --job-name=tro_pos_collect
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=08:00:00
#SBATCH --partition=interruptible_cpu
#SBATCH --hint=nomultithread
#SBATCH --output=/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/tro_position_mvp0/logs/collect-%j.out
#SBATCH --error=/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/tro_position_mvp0/logs/collect-%j.err

set -euo pipefail

PROJECT_DIR=${PROJECT_DIR:-"/scratch/prj/eng_demt_robot_learning/polymetics_demt"}
PYTHON=${PYTHON:-"/scratch/users/k23114984/conda/arcap/bin/python"}
BLOCK=${BLOCK:-0}
TARGET=${TARGET:-30}

cd "${PROJECT_DIR}"
export PYTHONUNBUFFERED=1
export OMP_NUM_THREADS=${SLURM_CPUS_PER_TASK:-4}
export OPENBLAS_NUM_THREADS=${SLURM_CPUS_PER_TASK:-4}
export MKL_NUM_THREADS=${SLURM_CPUS_PER_TASK:-4}

echo "[INFO] Stage 1 paired collection block=${BLOCK} target=${TARGET}"
echo "[INFO] Slurm job=${SLURM_JOB_ID:-N/A} node=${SLURM_NODELIST:-N/A}"

srun --export=ALL --cpu-bind=cores --ntasks=1 \
  "${PYTHON}" -u scripts/tro_position_mvp0.py collect \
  --block "${BLOCK}" \
  --target "${TARGET}" \
  --sample-hz 8 \
  --playback-speed 100

"${PYTHON}" scripts/tro_position_mvp0.py validate-raw \
  --block "${BLOCK}" \
  --target "${TARGET}"
