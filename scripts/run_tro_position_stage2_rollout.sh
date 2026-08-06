#!/bin/bash -l

#SBATCH --job-name=tro_s2_rollout
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=00:35:00
#SBATCH --partition=interruptible_gpu
#SBATCH --gres=gpu:1
#SBATCH --constraint="a100|l40s|h100|h200"
#SBATCH --exclude=erc-hpc-comp040,erc-hpc-comp035,erc-hpc-comp223
#SBATCH --hint=nomultithread
#SBATCH --output=/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/tro_position_stage2_axial/logs/rollout-%A_%a.out
#SBATCH --error=/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/tro_position_stage2_axial/logs/rollout-%A_%a.err

set -euo pipefail

PROJECT_DIR=${PROJECT_DIR:-"/scratch/prj/eng_demt_robot_learning/polymetics_demt"}
PYTHON=${PYTHON:-"/scratch/users/k23114984/conda/arcap/bin/python"}
TASK_ID=${SLURM_ARRAY_TASK_ID:?Submit as --array=0-249}
conditions=(START15_APP6 START35_APP6 START25_APP3P6 START25_APP6 START25_APP8P4)
banks=(inner outer)

canonical_index=$(( TASK_ID / 50 ))
within_seed=$(( TASK_ID % 50 ))
rollout_index=$(( within_seed / 10 ))
within_rollout=$(( within_seed % 10 ))
bank_index=$(( within_rollout / 5 ))
condition_index=$(( within_rollout % 5 ))

canonical_seed=$(( canonical_index + 1 ))
rollout_seed=$(( rollout_index + 1 ))
bank=${banks[$bank_index]}
condition=${conditions[$condition_index]}
bank_id="tro_stage2_seed${rollout_seed}_${bank}_n25_v1"
manifest="${PROJECT_DIR}/experiments/tro_stage2_position_axial_replication/manifests/rollout_5seed/${bank_id}.json"
checkpoint_manifest="${PROJECT_DIR}/experiments/tro_stage2_position_axial_replication/manifests/checkpoints_seed${canonical_seed}.json"
output_dir="${PROJECT_DIR}/dataset/tro_position_stage2_axial/rollouts/formal/seed${canonical_seed}/rollout_seed${rollout_seed}/${bank}"

if [[ "${bank}" == "inner" ]]; then
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

srun --export=ALL --cpu-bind=cores --ntasks=1 \
  "${PYTHON}" -u examples/eval_abla1_trained_policies.py \
  --experiment-profile tro_position_stage2 \
  --block "${canonical_seed}" \
  --bank-id "${bank_id}" \
  --conditions "${condition}" \
  --checkpoint-manifest "${checkpoint_manifest}" \
  --num-rollouts 25 \
  --seed "${rollout_seed}" \
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
