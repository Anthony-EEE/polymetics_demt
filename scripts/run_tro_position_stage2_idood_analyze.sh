#!/bin/bash -l

#SBATCH --job-name=tro_s2_idood_analyze
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=02:00:00
#SBATCH --partition=interruptible_cpu
#SBATCH --hint=nomultithread
#SBATCH --output=/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/tro_position_stage2_axial_idood_rerollout/rmax40/logs/analyze-%j.out
#SBATCH --error=/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/tro_position_stage2_axial_idood_rerollout/rmax40/logs/analyze-%j.err

set -euo pipefail

PROJECT_DIR=${PROJECT_DIR:-"/scratch/prj/eng_demt_robot_learning/polymetics_demt"}
PYTHON=${PYTHON:-"/scratch/users/k23114984/conda/arcap/bin/python"}

cd "${PROJECT_DIR}"
"${PYTHON}" -u scripts/analyze_tro_position_stage2_idood.py
