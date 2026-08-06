#!/bin/bash -l

#SBATCH --job-name=tro_s2_smoke
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=20G
#SBATCH --time=02:00:00
#SBATCH --partition=interruptible_cpu
#SBATCH --hint=nomultithread
#SBATCH --output=/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/tro_position_stage2_axial/logs/smoke-%A_%a.out
#SBATCH --error=/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/tro_position_stage2_axial/logs/smoke-%A_%a.err

set -euo pipefail

PROJECT_DIR=${PROJECT_DIR:-"/scratch/prj/eng_demt_robot_learning/polymetics_demt"}
PYTHON=${PYTHON:-"/scratch/users/k23114984/conda/arcap/bin/python"}
TASK_ID=${SLURM_ARRAY_TASK_ID:?Submit as --array=0-4}
canonical_seed=$(( TASK_ID + 1 ))

cd "${PROJECT_DIR}"
export PYTHONUNBUFFERED=1
export OMP_NUM_THREADS=${SLURM_CPUS_PER_TASK:-4}

srun --export=ALL --cpu-bind=cores --ntasks=1 \
  "${PYTHON}" -u scripts/tro_position_stage2.py collect \
  --canonical-seed "${canonical_seed}" \
  --target 3 \
  --smoke \
  --sample-hz 8 \
  --playback-speed 100

"${PYTHON}" -u scripts/tro_position_stage2.py validate-raw \
  --canonical-seed "${canonical_seed}" \
  --target 3 \
  --smoke
