#!/bin/bash -l

#SBATCH --job-name=time_mvp_eval_merge
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=0:20:00
#SBATCH --partition=interruptible_cpu
#SBATCH --hint=nomultithread
#SBATCH --output=/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/temporal_vref_reciprocal_spatial_v2/logs/eval-merge-%j.out
#SBATCH --error=/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/temporal_vref_reciprocal_spatial_v2/logs/eval-merge-%j.err

set -euo pipefail

PROJECT_DIR=${PROJECT_DIR:-"/scratch/prj/eng_demt_robot_learning/polymetics_demt"}
PYTHON=${PYTHON:-"/scratch/users/k23114984/conda/arcap/bin/python"}
OUTPUT_DIR=${OUTPUT_DIR:-"${PROJECT_DIR}/dataset/temporal_vref_reciprocal_spatial_v2/policy_rollouts_seed628_paired_n50_h200"}
CHECKPOINT_MANIFEST=${CHECKPOINT_MANIFEST:-"${OUTPUT_DIR}/checkpoint_manifest.json"}
PAIRED_MANIFEST=${PAIRED_MANIFEST:-"${OUTPUT_DIR}/paired_manifest_seed628_n50_h200.json"}

mkdir -p "${PROJECT_DIR}/dataset/temporal_vref_reciprocal_spatial_v2/logs" "${OUTPUT_DIR}"
cd "${PROJECT_DIR}"

export PYTHONUNBUFFERED=1
export OMP_NUM_THREADS=${SLURM_CPUS_PER_TASK:-2}

"${PYTHON}" -u examples/eval_time_mvp_trained_policies.py \
  --conditions VR1P5 V050_200 VR3 VR4 \
  --checkpoint-manifest "${CHECKPOINT_MANIFEST}" \
  --paired-manifest "${PAIRED_MANIFEST}" \
  --num-rollouts 50 \
  --seed 628 \
  --horizon 200 \
  --sample-hz 8 \
  --action-gap 2 \
  --action-dt 0.25 \
  --terminate-on-success \
  --output-dir "${OUTPUT_DIR}" \
  --merge-only \
  "$@"
