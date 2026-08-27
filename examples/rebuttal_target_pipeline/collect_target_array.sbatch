#!/usr/bin/env bash
#SBATCH --job-name=simulation_target_group_collect
#SBATCH --partition=interruptible_cpu
#SBATCH --account=er_prj_eng_demt_robot_learning
#SBATCH --qos=normal
#SBATCH --array=1-10%3
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=08:00:00
#SBATCH --output=/scratch/prj/eng_demt_robot_learning/polymetics_demt/rebuttal_dataset/simulation_target_group/full_seed20260806/protocol_release_z008_target_tol010_start_replenish/logs/collect_%A_%a.out
#SBATCH --error=/scratch/prj/eng_demt_robot_learning/polymetics_demt/rebuttal_dataset/simulation_target_group/full_seed20260806/protocol_release_z008_target_tol010_start_replenish/logs/collect_%A_%a.err

set -euo pipefail

repo_root=/scratch/prj/eng_demt_robot_learning/polymetics_demt
python_bin=/scratch/users/k23114984/conda/arcap/bin/python
output_root="$repo_root/rebuttal_dataset/simulation_target_group/full_seed20260806/protocol_release_z008_target_tol010_start_replenish"
printf -v participant 'T%02d' "$SLURM_ARRAY_TASK_ID"

cd "$repo_root"
export PYTHONDONTWRITEBYTECODE=1
export PYTHONUNBUFFERED=1
export OMP_NUM_THREADS=2
export OPENBLAS_NUM_THREADS=2

date --iso-8601=seconds
printf 'group=simulation_target_group participant=%s job_id=%s array_task_id=%s host=%s\n' \
  "$participant" "$SLURM_ARRAY_JOB_ID" "$SLURM_ARRAY_TASK_ID" "$SLURMD_NODENAME"

"$python_bin" examples/main_obstacle_transport_target_participants.py \
  --participants "$participant" \
  --all-30 \
  --seed 20260806 \
  --max-attempts-per-demo 30 \
  --output-dir "$output_root" \
  --save-raw-frames \
  --save-videos \
  --skip-preview \
  --skip-group-summary

date --iso-8601=seconds
