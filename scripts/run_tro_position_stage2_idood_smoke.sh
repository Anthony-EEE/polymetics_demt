#!/bin/bash -l

#SBATCH --job-name=tro_s2_idood_smoke
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=00:30:00
#SBATCH --partition=interruptible_gpu
#SBATCH --gres=gpu:1
#SBATCH --constraint="a100|l40s|h100|h200"
#SBATCH --exclude=erc-hpc-comp040,erc-hpc-comp035,erc-hpc-comp223
#SBATCH --hint=nomultithread
#SBATCH --output=/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/tro_position_stage2_axial_idood_rerollout/rmax40/logs/smoke-%A_%a.out
#SBATCH --error=/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/tro_position_stage2_axial_idood_rerollout/rmax40/logs/smoke-%A_%a.err

set -euo pipefail

PROJECT_DIR=${PROJECT_DIR:-"/scratch/prj/eng_demt_robot_learning/polymetics_demt"}
PYTHON=${PYTHON:-"/scratch/users/k23114984/conda/arcap/bin/python"}
TASK_ID=${SLURM_ARRAY_TASK_ID:?Submit as --array=0-5}
conditions=(START15_APP6 START15_APP6 START25_APP6 START25_APP6 START35_APP6 START35_APP6)
start_tags=(start15 start15 start25 start25 start35 start35)
support_radii=(0.15 0.15 0.25 0.25 0.35 0.35)
banks=(id ood id ood id ood)

condition=${conditions[$TASK_ID]}
start_tag=${start_tags[$TASK_ID]}
support_radius=${support_radii[$TASK_ID]}
bank=${banks[$TASK_ID]}
if [[ "${bank}" == "id" ]]; then
  radius_min=0.0
  radius_max=${support_radius}
else
  radius_min=${support_radius}
  radius_max=0.40
fi

bank_id="tro_s2_idood_rmax40_${start_tag}_seed1_${bank}_n25_v1"
cd "${PROJECT_DIR}"
mkdir -p dataset/tro_position_stage2_axial_idood_rerollout/rmax40/smoke

srun --export=ALL --cpu-bind=cores --ntasks=1 \
  "${PYTHON}" -u examples/eval_abla1_trained_policies.py \
  --experiment-profile tro_position_stage2_idood \
  --block 1 \
  --bank-id "${bank_id}" \
  --conditions "${condition}" \
  --checkpoint-manifest experiments/tro_stage2_position_axial_replication/manifests/checkpoints_seed1.json \
  --num-rollouts 25 \
  --seed 1 \
  --horizon 200 \
  --sample-hz 8 \
  --action-gap 2 \
  --action-dt 0.25 \
  --num-points 10000 \
  --success-lift-height 0.20 \
  --shared-start-radius-min "${radius_min}" \
  --shared-start-radius "${radius_max}" \
  --corridor-start-max-error 0.025 \
  --playback-speed 100 \
  --cuda \
  --terminate-on-success \
  --output-dir "dataset/tro_position_stage2_axial_idood_rerollout/rmax40/smoke/${start_tag}/${bank}" \
  --start-manifest "experiments/tro_stage2_position_axial_idood_rerollout/manifests/rollout_5seed_rmax40/${bank_id}.json" \
  --skip-aggregate
