#!/bin/bash -l

#SBATCH --job-name=tro_s2_idood
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=00:40:00
#SBATCH --partition=interruptible_gpu
#SBATCH --gres=gpu:1
#SBATCH --constraint="a100|l40s|h100|h200"
#SBATCH --exclude=erc-hpc-comp040,erc-hpc-comp035,erc-hpc-comp223
#SBATCH --hint=nomultithread
#SBATCH --output=/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/tro_position_stage2_axial_idood_rerollout/rmax40/logs/rollout-%A_%a.out
#SBATCH --error=/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/tro_position_stage2_axial_idood_rerollout/rmax40/logs/rollout-%A_%a.err

set -euo pipefail

PROJECT_DIR=${PROJECT_DIR:-"/scratch/prj/eng_demt_robot_learning/polymetics_demt"}
PYTHON=${PYTHON:-"/scratch/users/k23114984/conda/arcap/bin/python"}
TASK_ID=${SLURM_ARRAY_TASK_ID:?Submit as --array=0-249}
conditions=(START15_APP6 START35_APP6 START25_APP3P6 START25_APP6 START25_APP8P4)
banks=(id ood)

canonical_index=$(( TASK_ID / 50 ))
within_seed=$(( TASK_ID % 50 ))
condition_index=$(( within_seed / 10 ))
within_condition=$(( within_seed % 10 ))
rollout_index=$(( within_condition / 2 ))
bank_index=$(( within_condition % 2 ))

canonical_seed=$(( canonical_index + 1 ))
rollout_seed=$(( rollout_index + 1 ))
condition=${conditions[$condition_index]}
bank=${banks[$bank_index]}

case "${condition}" in
  START15_APP6) start_tag=start15; support_radius=0.15 ;;
  START35_APP6) start_tag=start35; support_radius=0.35 ;;
  START25_*) start_tag=start25; support_radius=0.25 ;;
  *) printf 'Unknown condition %s\n' "${condition}" >&2; exit 2 ;;
esac

if [[ "${bank}" == "id" ]]; then
  radius_min=0.0
  radius_max=${support_radius}
else
  radius_min=${support_radius}
  radius_max=0.40
fi

bank_id="tro_s2_idood_rmax40_${start_tag}_seed${rollout_seed}_${bank}_n25_v1"
manifest="${PROJECT_DIR}/experiments/tro_stage2_position_axial_idood_rerollout/manifests/rollout_5seed_rmax40/${bank_id}.json"
checkpoint_manifest="${PROJECT_DIR}/experiments/tro_stage2_position_axial_replication/manifests/checkpoints_seed${canonical_seed}.json"
output_dir="${PROJECT_DIR}/dataset/tro_position_stage2_axial_idood_rerollout/rmax40/rollouts/formal/seed${canonical_seed}/rollout_seed${rollout_seed}/${bank}"

cd "${PROJECT_DIR}"
export PYTHONUNBUFFERED=1
export OMP_NUM_THREADS=${SLURM_CPUS_PER_TASK:-8}
export TOKENIZERS_PARALLELISM=false
export HDF5_USE_FILE_LOCKING=FALSE

srun --export=ALL --cpu-bind=cores --ntasks=1 \
  "${PYTHON}" -u examples/eval_abla1_trained_policies.py \
  --experiment-profile tro_position_stage2_idood \
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
