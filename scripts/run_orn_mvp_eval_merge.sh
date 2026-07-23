#!/bin/bash -l
#SBATCH --job-name=orn_mvp_eval_merge
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=0:20:00
#SBATCH --partition=interruptible_cpu
#SBATCH --hint=nomultithread
#SBATCH --output=/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/orn_mvp_full/logs/eval-merge-%j.out
#SBATCH --error=/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/orn_mvp_full/logs/eval-merge-%j.err

set -euo pipefail
PROJECT_DIR=${PROJECT_DIR:-"/scratch/prj/eng_demt_robot_learning/polymetics_demt"}
PYTHON=${PYTHON:-"/scratch/users/k23114984/conda/arcap/bin/python"}
OUTPUT_DIR=${OUTPUT_DIR:-"${PROJECT_DIR}/dataset/orn_mvp_full/policy_rollouts_seed628_paired_n50_h200"}
CHECKPOINT_MANIFEST=${CHECKPOINT_MANIFEST:-"${OUTPUT_DIR}/checkpoint_manifest.json"}
PAIRED_MANIFEST=${PAIRED_MANIFEST:-"${OUTPUT_DIR}/paired_manifest_seed628_n50_h200.json"}
mkdir -p "${PROJECT_DIR}/dataset/orn_mvp_full/logs" "${OUTPUT_DIR}"
cd "${PROJECT_DIR}"
export PYTHONUNBUFFERED=1
export OMP_NUM_THREADS=${SLURM_CPUS_PER_TASK:-2}
"${PYTHON}" -u examples/eval_orn_mvp_trained_policies.py \
  --conditions R00 R15 R30 \
  --checkpoint-manifest "${CHECKPOINT_MANIFEST}" \
  --paired-manifest "${PAIRED_MANIFEST}" \
  --num-rollouts "${NUM_ROLLOUTS:-50}" \
  --seed "${SEED:-628}" \
  --horizon "${HORIZON:-200}" \
  --sample-hz "${SAMPLE_HZ:-8}" \
  --action-gap "${ACTION_GAP:-2}" \
  --action-dt "${ACTION_DT:-0.25}" \
  --num-points "${NUM_POINTS:-10000}" \
  --success-lift-height "${SUCCESS_LIFT_HEIGHT:-0.20}" \
  --terminate-on-success \
  --output-dir "${OUTPUT_DIR}" \
  --merge-only \
  "$@"
