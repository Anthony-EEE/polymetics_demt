#!/usr/bin/env bash
#SBATCH --job-name=simulation_control_group_release_diag
#SBATCH --partition=interruptible_cpu
#SBATCH --account=er_prj_eng_demt_robot_learning
#SBATCH --qos=normal
#SBATCH --array=1-10%3
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=02:00:00
#SBATCH --output=/scratch/prj/eng_demt_robot_learning/polymetics_demt/rebuttal_dataset/simulation_control_group/full_seed20260806/diagnostics/release_z008_all30/logs/diag_%A_%a.out
#SBATCH --error=/scratch/prj/eng_demt_robot_learning/polymetics_demt/rebuttal_dataset/simulation_control_group/full_seed20260806/diagnostics/release_z008_all30/logs/diag_%A_%a.err

set -euo pipefail

repo_root=/scratch/prj/eng_demt_robot_learning/polymetics_demt
python_bin=/scratch/users/k23114984/conda/arcap/bin/python
diagnostic_root="$repo_root/rebuttal_dataset/simulation_control_group/full_seed20260806/diagnostics/release_z008_all30"
printf -v participant 'C%02d' "$SLURM_ARRAY_TASK_ID"

cd "$repo_root"
export PYTHONDONTWRITEBYTECODE=1
export PYTHONUNBUFFERED=1
export OMP_NUM_THREADS=2
export OPENBLAS_NUM_THREADS=2

date --iso-8601=seconds
printf 'group=simulation_control_group formal_data=false participant=%s job_id=%s array_task_id=%s host=%s\n' \
  "$participant" "$SLURM_ARRAY_JOB_ID" "$SLURM_ARRAY_TASK_ID" "$SLURMD_NODENAME"

"$python_bin" examples/rebuttal_control_pipeline/diagnose_release_height.py \
  --participants "$participant" \
  --all-30 \
  --seed 20260806 \
  --release-z 0.08 \
  --max-attempts 30 \
  --output "$diagnostic_root/$participant.json"

date --iso-8601=seconds
