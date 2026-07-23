#!/bin/bash -l

#SBATCH --job-name=time_mvp_eval
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=2:00:00
#SBATCH --partition=interruptible_gpu
#SBATCH --gres=gpu:1
#SBATCH --constraint="a100|l40s|h200|h100"
#SBATCH --exclude=erc-hpc-comp040,erc-hpc-comp035
#SBATCH --hint=nomultithread
#SBATCH --output=/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/temporal_vref_reciprocal_spatial_v2/logs/eval-%A_%a.out
#SBATCH --error=/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/temporal_vref_reciprocal_spatial_v2/logs/eval-%A_%a.err

set -euo pipefail

PROJECT_DIR=${PROJECT_DIR:-"/scratch/prj/eng_demt_robot_learning/polymetics_demt"}
PYTHON=${PYTHON:-"/scratch/users/k23114984/conda/arcap/bin/python"}
MODEL_ROOT=${MODEL_ROOT:-"/scratch/prj/eng_demt_robot_learning/trained_models/temporal_vref_reciprocal_spatial_v2"}
OUTPUT_DIR=${OUTPUT_DIR:-"${PROJECT_DIR}/dataset/temporal_vref_reciprocal_spatial_v2/policy_rollouts_seed628_paired_n50_h200"}
VIDEO_DIR=${VIDEO_DIR:-"${OUTPUT_DIR}/videos"}
EPOCH=${EPOCH:-999999}
CONDITIONS=${CONDITIONS:-"VR1P5 V050_200 VR3 VR4"}
EXPERIMENT_TEMPLATE=${EXPERIMENT_TEMPLATE:-"{condition}/temporal_{condition}_d30_seed1_2gap"}
CHECKPOINT_MANIFEST=${CHECKPOINT_MANIFEST:-"${OUTPUT_DIR}/checkpoint_manifest.json"}
PAIRED_MANIFEST=${PAIRED_MANIFEST:-"${OUTPUT_DIR}/paired_manifest_seed628_n50_h200.json"}

if [[ -n "${CONDITION:-}" ]]; then
  CONDITIONS="${CONDITION}"
fi
if [[ -n "${SLURM_ARRAY_TASK_ID:-}" ]]; then
  read -r -a CONDITION_LIST <<< "${CONDITIONS}"
  if (( SLURM_ARRAY_TASK_ID < 0 || SLURM_ARRAY_TASK_ID >= ${#CONDITION_LIST[@]} )); then
    echo "[ERROR] SLURM_ARRAY_TASK_ID=${SLURM_ARRAY_TASK_ID} is out of range" >&2
    exit 2
  fi
  CONDITIONS="${CONDITION_LIST[$SLURM_ARRAY_TASK_ID]}"
fi
read -r -a CONDITION_ARGS <<< "${CONDITIONS}"

mkdir -p "${PROJECT_DIR}/dataset/temporal_vref_reciprocal_spatial_v2/logs" "${OUTPUT_DIR}" "${VIDEO_DIR}"
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

"${PYTHON}" -u examples/eval_time_mvp_trained_policies.py \
  --model-root "${MODEL_ROOT}" \
  --conditions "${CONDITION_ARGS[@]}" \
  --checkpoint-manifest "${CHECKPOINT_MANIFEST}" \
  --paired-manifest "${PAIRED_MANIFEST}" \
  --experiment-template "${EXPERIMENT_TEMPLATE}" \
  --epoch "${EPOCH}" \
  --latest-checkpoint \
  --num-rollouts "${NUM_ROLLOUTS:-50}" \
  --seed "${SEED:-628}" \
  --horizon "${HORIZON:-200}" \
  --action-dt "${ACTION_DT:-0.25}" \
  --playback-speed "${PLAYBACK_SPEED:-100}" \
  --cuda \
  --terminate-on-success \
  --skip-aggregate \
  --save-videos \
  --video-fps "${VIDEO_FPS:-20}" \
  --video-every-n-actions "${VIDEO_EVERY_N_ACTIONS:-2}" \
  --video-width "${VIDEO_WIDTH:-320}" \
  --video-height "${VIDEO_HEIGHT:-320}" \
  --output-dir "${OUTPUT_DIR}" \
  --video-dir "${VIDEO_DIR}" \
  "$@"
