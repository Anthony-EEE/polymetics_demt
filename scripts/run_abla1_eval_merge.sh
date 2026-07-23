#!/bin/bash -l

#SBATCH --job-name=abla1_eval_merge
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=0:20:00
#SBATCH --partition=interruptible_cpu
#SBATCH --hint=nomultithread
#SBATCH --output=/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/ar_guidance_spatial_S15_S35/logs/eval-merge-%j.out
#SBATCH --error=/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/ar_guidance_spatial_S15_S35/logs/eval-merge-%j.err

set -euo pipefail

PROJECT_DIR=${PROJECT_DIR:-"/scratch/prj/eng_demt_robot_learning/polymetics_demt"}
PYTHON=${PYTHON:-"/scratch/users/k23114984/conda/arcap/bin/python"}
OUTPUT_DIR=${OUTPUT_DIR:-"${PROJECT_DIR}/dataset/ar_guidance_spatial_S15_S35/policy_rollouts_seed628_shared_r35_paired_n50_h200"}
START_MANIFEST=${START_MANIFEST:-"${OUTPUT_DIR}/shared_start_manifest_seed${SEED:-628}_n${NUM_ROLLOUTS:-50}_r35.json"}
CHECKPOINT_MANIFEST=${CHECKPOINT_MANIFEST:-"${OUTPUT_DIR}/checkpoint_manifest.json"}
CONDITIONS=${CONDITIONS:-"S15 S20 S25 S30 S35"}
SHARED_START_RADIUS_MIN=${SHARED_START_RADIUS_MIN:-0.0}
SHARED_START_RADIUS=${SHARED_START_RADIUS:-0.35}
CORRIDOR_START_MAX_ERROR=${CORRIDOR_START_MAX_ERROR:-0.025}
MAX_START_SAMPLE_ATTEMPTS=${MAX_START_SAMPLE_ATTEMPTS:-1000}

read -r -a CONDITION_ARGS <<< "${CONDITIONS}"

mkdir -p "${PROJECT_DIR}/dataset/ar_guidance_spatial_S15_S35/logs" "${OUTPUT_DIR}"
cd "${PROJECT_DIR}"

export PYTHONUNBUFFERED=1
export OMP_NUM_THREADS=${SLURM_CPUS_PER_TASK:-2}
export TOKENIZERS_PARALLELISM=false
export HDF5_USE_FILE_LOCKING=FALSE

echo "[INFO] SLURM Job ID: ${SLURM_JOB_ID:-N/A}"
echo "[INFO] Node list: ${SLURM_NODELIST:-N/A}"
echo "[INFO] Python: ${PYTHON}"
echo "[INFO] Output dir: ${OUTPUT_DIR}"
echo "[INFO] Start manifest: ${START_MANIFEST}"
echo "[INFO] Shared start radius min/max: ${SHARED_START_RADIUS_MIN}/${SHARED_START_RADIUS}"
"${PYTHON}" --version

"${PYTHON}" -u examples/eval_abla1_trained_policies.py \
  --conditions "${CONDITION_ARGS[@]}" \
  --checkpoint-manifest "${CHECKPOINT_MANIFEST}" \
  --num-rollouts "${NUM_ROLLOUTS:-50}" \
  --seed "${SEED:-628}" \
  --horizon "${HORIZON:-200}" \
  --sample-hz "${SAMPLE_HZ:-8}" \
  --action-gap "${ACTION_GAP:-2}" \
  --action-dt "${ACTION_DT:-0.25}" \
  --num-points "${NUM_POINTS:-10000}" \
  --playback-speed "${PLAYBACK_SPEED:-100}" \
  --shared-start-radius-min "${SHARED_START_RADIUS_MIN}" \
  --shared-start-radius "${SHARED_START_RADIUS}" \
  --corridor-start-max-error "${CORRIDOR_START_MAX_ERROR}" \
  --max-start-sample-attempts "${MAX_START_SAMPLE_ATTEMPTS}" \
  --success-lift-height "${SUCCESS_LIFT_HEIGHT:-0.20}" \
  --output-dir "${OUTPUT_DIR}" \
  --start-manifest "${START_MANIFEST}" \
  --terminate-on-success \
  --merge-only \
  "$@"
