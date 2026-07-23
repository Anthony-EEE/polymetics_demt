#!/bin/bash -l

#SBATCH --job-name=ar_guidance_check
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=24G
#SBATCH --time=02:00:00
#SBATCH --partition=interruptible_cpu
#SBATCH --hint=nomultithread
#SBATCH --output=/scratch/prj/eng_demt_robot_learning/polymetics_demt/logs/ar-guidance-postcheck-%j.out
#SBATCH --error=/scratch/prj/eng_demt_robot_learning/polymetics_demt/logs/ar-guidance-postcheck-%j.err

set -euo pipefail

PROJECT_DIR=${PROJECT_DIR:-"/scratch/prj/eng_demt_robot_learning/polymetics_demt"}
CONDA_ENV=${CONDA_ENV:-"/scratch/users/k23114984/conda/envs/polymetis38"}
MODULES=${MODULES:-"anaconda3/2022.10-gcc-13.2.0"}
TRACK=${TRACK:-"all"}
SPATIAL_ROOT=${SPATIAL_ROOT:-"${PROJECT_DIR}/dataset/ar_guidance_spatial_S15_S35"}
TEMPORAL_ROOT=${TEMPORAL_ROOT:-"${PROJECT_DIR}/dataset/ar_guidance_temporal_T00_T100"}
TEMPORAL_CONDITIONS=${TEMPORAL_CONDITIONS:-"T00 T25 T50 T75 T100"}
TEMPORAL_DATASET_TEMPLATE=${TEMPORAL_DATASET_TEMPLATE:-"temporal_{condition}_d30_seed1"}
TEMPORAL_PLOT_STRIDE=${TEMPORAL_PLOT_STRIDE:-1}
RECIPROCAL_ROOT=${RECIPROCAL_ROOT:-"${PROJECT_DIR}/dataset/temporal_vref_reciprocal_spatial_v2"}
RECIPROCAL_MANIFEST=${RECIPROCAL_MANIFEST:-"${RECIPROCAL_ROOT}/shared_collection_manifest_seed1.json"}

mkdir -p "${PROJECT_DIR}/logs" "${SPATIAL_ROOT}/logs" "${TEMPORAL_ROOT}/logs"
cd "${PROJECT_DIR}"

if command -v module >/dev/null 2>&1; then
  module purge || true
  for m in ${MODULES}; do
    module load "${m}" || true
  done
fi

if command -v conda >/dev/null 2>&1; then
  source "$(conda info --base)/etc/profile.d/conda.sh"
  conda activate "${CONDA_ENV}"
fi

export PYTHONUNBUFFERED=1
export OMP_NUM_THREADS=${SLURM_CPUS_PER_TASK:-4}
export MPLBACKEND=Agg

run_spatial() {
  for cond in S15 S20 S25 S30 S35; do
    python scripts/check_abla1_dataset.py \
      "${SPATIAL_ROOT}/spatial_${cond}_d30_seed1" \
      --expected-demos 30 \
      --expected-condition "${cond}"
  done
  python examples/plot_abla1_ee_trajectories.py \
    --dataset-root "${SPATIAL_ROOT}" \
    --conditions S15 S20 S25 S30 S35 \
    --dataset-template 'spatial_{condition}_d30_seed1' \
    --output-dir "${SPATIAL_ROOT}/trajectory_plots"
}

run_temporal() {
  read -r -a temporal_conditions <<< "${TEMPORAL_CONDITIONS}"
  for cond in "${temporal_conditions[@]}"; do
    dataset_name="${TEMPORAL_DATASET_TEMPLATE//\{condition\}/${cond}}"
    python scripts/check_time_mvp_dataset.py \
      "${TEMPORAL_ROOT}/${dataset_name}" \
      --expected-demos 30 \
      --expected-condition "${cond}"
  done
  python examples/plot_time_mvp_temporal.py \
    --dataset-root "${TEMPORAL_ROOT}" \
    --conditions "${temporal_conditions[@]}" \
    --dataset-template "${TEMPORAL_DATASET_TEMPLATE}" \
    --output-dir "${TEMPORAL_ROOT}/temporal_plots" \
    --stride "${TEMPORAL_PLOT_STRIDE}"
}

run_temporal_reciprocal() {
  python scripts/check_time_mvp_dataset.py \
    --root "${RECIPROCAL_ROOT}" \
    --conditions VR1P5 V050_200 VR3 VR4 \
    --expected-demos 30 \
    --manifest "${RECIPROCAL_MANIFEST}"
  python examples/plot_time_mvp_temporal.py \
    --dataset-root "${RECIPROCAL_ROOT}" \
    --conditions VR1P5 V050_200 VR3 VR4 \
    --dataset-template 'temporal_{condition}_d30_seed1' \
    --output-dir "${RECIPROCAL_ROOT}/temporal_plots" \
    --stride "${TEMPORAL_PLOT_STRIDE}"
}

case "${TRACK}" in
  spatial)
    run_spatial
    ;;
  temporal)
    run_temporal
    ;;
  temporal_reciprocal)
    run_temporal_reciprocal
    ;;
  all)
    run_spatial
    run_temporal
    ;;
  *)
    echo "[ERROR] Unknown TRACK='${TRACK}'. Use spatial, temporal, temporal_reciprocal, or all." >&2
    exit 1
    ;;
esac

echo "[INFO] AR guidance post-collection checks complete for TRACK=${TRACK}"
