#!/bin/bash -l

#SBATCH --job-name=abla1_eval
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=2:00:00
#SBATCH --partition=gpu
#SBATCH --gres=gpu:1
#SBATCH --constraint="a100|l40s|h200|h100"
#SBATCH --exclude=erc-hpc-comp040,erc-hpc-comp035
#SBATCH --hint=nomultithread
#SBATCH --output=/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full_arcenter/logs/eval-%j.out
#SBATCH --error=/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full_arcenter/logs/eval-%j.err

set -euo pipefail

PROJECT_DIR=${PROJECT_DIR:-"/scratch/prj/eng_demt_robot_learning/polymetics_demt"}
PYTHON=${PYTHON:-"/scratch/users/k23114984/conda/arcap/bin/python"}
MODEL_ROOT=${MODEL_ROOT:-"${PROJECT_DIR}/dataset/abla1_full_arcenter/trained_models"}
OUTPUT_DIR=${OUTPUT_DIR:-"${PROJECT_DIR}/dataset/abla1_full_arcenter/policy_rollouts_seed628_latest"}
VIDEO_DIR=${VIDEO_DIR:-"${OUTPUT_DIR}/videos"}
EPOCH=${EPOCH:-999999}

mkdir -p "${PROJECT_DIR}/dataset/abla1_full_arcenter/logs" "${OUTPUT_DIR}" "${VIDEO_DIR}"
cd "${PROJECT_DIR}"

export PYTHONUNBUFFERED=1
export OMP_NUM_THREADS=${SLURM_CPUS_PER_TASK:-8}
export TOKENIZERS_PARALLELISM=false
export HDF5_USE_FILE_LOCKING=FALSE

echo "[INFO] SLURM Job ID: ${SLURM_JOB_ID:-N/A}"
echo "[INFO] Node list: ${SLURM_NODELIST:-N/A}"
echo "[INFO] Python: ${PYTHON}"
"${PYTHON}" --version
which nvidia-smi >/dev/null 2>&1 && nvidia-smi || true

"${PYTHON}" -u examples/eval_abla1_trained_policies.py \
  --model-root "${MODEL_ROOT}" \
  --conditions P00 P01 P10 P11 \
  --experiment-template 'abla1_arcenter_{condition}_d30_seed1_2gap' \
  --epoch "${EPOCH}" \
  --num-rollouts "${NUM_ROLLOUTS:-10}" \
  --seed "${SEED:-628}" \
  --horizon "${HORIZON:-80}" \
  --playback-speed "${PLAYBACK_SPEED:-100}" \
  --cuda \
  --save-videos \
  --video-fps "${VIDEO_FPS:-20}" \
  --video-every-n-actions "${VIDEO_EVERY_N_ACTIONS:-2}" \
  --video-width "${VIDEO_WIDTH:-320}" \
  --video-height "${VIDEO_HEIGHT:-320}" \
  --output-dir "${OUTPUT_DIR}" \
  --video-dir "${VIDEO_DIR}" \
  "$@"
