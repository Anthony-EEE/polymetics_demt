#!/bin/bash -l

#SBATCH --job-name=tro_pos_eval
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=02:00:00
#SBATCH --partition=interruptible_gpu
#SBATCH --gres=gpu:1
#SBATCH --constraint="a100|l40s|h200|h100"
#SBATCH --exclude=erc-hpc-comp040,erc-hpc-comp035,erc-hpc-comp223
#SBATCH --hint=nomultithread
#SBATCH --output=/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/tro_position_mvp0/logs/eval-%A_%a.out
#SBATCH --error=/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/tro_position_mvp0/logs/eval-%A_%a.err

set -euo pipefail

PROJECT_DIR=${PROJECT_DIR:-"/scratch/prj/eng_demt_robot_learning/polymetics_demt"}
PYTHON=${PYTHON:-"/scratch/users/k23114984/conda/arcap/bin/python"}
BLOCK=${BLOCK:-0}
TASK_ID=${SLURM_ARRAY_TASK_ID:?Submit as --array=0-7}
conditions=(START15_APP6 START35_APP6 START25_APP3P6 START25_APP8P4)
banks=(
  legacy_seed628_reference_r00_r25_n25_v1
  legacy_seed628_outer_r25_r35_n25_v1
)

condition_index=$(( TASK_ID % 4 ))
bank_index=$(( TASK_ID / 4 ))
condition=${conditions[$condition_index]}
bank_id=${banks[$bank_index]}
manifest="${PROJECT_DIR}/experiments/mvp0_position_event/manifests/${bank_id}.json"
checkpoint_manifest="${PROJECT_DIR}/experiments/mvp0_position_event/manifests/checkpoints_b${BLOCK}.json"
output_dir="${PROJECT_DIR}/dataset/tro_position_mvp0/block${BLOCK}/rollouts/${bank_id}"

if (( bank_index == 0 )); then
  radius_min=0.0
  radius_max=0.25
else
  radius_min=0.25
  radius_max=0.35
fi

cd "${PROJECT_DIR}"
export PYTHONUNBUFFERED=1
export OMP_NUM_THREADS=${SLURM_CPUS_PER_TASK:-8}
export TOKENIZERS_PARALLELISM=false
export HDF5_USE_FILE_LOCKING=FALSE

echo "[INFO] block=${BLOCK} condition=${condition} bank=${bank_id}"
srun --export=ALL --cpu-bind=cores --ntasks=1 \
  "${PYTHON}" -u examples/eval_abla1_trained_policies.py \
  --experiment-profile tro_position_mvp0 \
  --block "${BLOCK}" \
  --bank-id "${bank_id}" \
  --conditions "${condition}" \
  --checkpoint-manifest "${checkpoint_manifest}" \
  --epoch 40 \
  --num-rollouts 25 \
  --seed 628 \
  --horizon 200 \
  --sample-hz 8 \
  --action-gap 2 \
  --action-dt 0.25 \
  --num-points 10000 \
  --success-lift-height 0.20 \
  --shared-start-radius-min "${radius_min}" \
  --shared-start-radius "${radius_max}" \
  --corridor-start-max-error 0.025 \
  --max-start-sample-attempts 1000 \
  --playback-speed 100 \
  --cuda \
  --terminate-on-success \
  --output-dir "${output_dir}" \
  --start-manifest "${manifest}" \
  --skip-aggregate
