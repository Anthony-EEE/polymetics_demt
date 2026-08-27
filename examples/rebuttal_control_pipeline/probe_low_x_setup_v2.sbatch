#!/usr/bin/env bash
#SBATCH --job-name=simulation_control_group_low_x_probe_v2
#SBATCH --partition=interruptible_cpu
#SBATCH --account=er_prj_eng_demt_robot_learning
#SBATCH --qos=normal
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:30:00
#SBATCH --output=/scratch/prj/eng_demt_robot_learning/polymetics_demt/rebuttal_dataset/simulation_control_group/full_seed20260806/diagnostics/low_x_setup_probe_v2/job_%j.out
#SBATCH --error=/scratch/prj/eng_demt_robot_learning/polymetics_demt/rebuttal_dataset/simulation_control_group/full_seed20260806/diagnostics/low_x_setup_probe_v2/job_%j.err

set -euo pipefail

repo_root=/scratch/prj/eng_demt_robot_learning/polymetics_demt
python_bin=/scratch/users/k23114984/conda/arcap/bin/python
diagnostic_root="$repo_root/rebuttal_dataset/simulation_control_group/full_seed20260806/diagnostics/low_x_setup_probe_v2"

cd "$repo_root"
export PYTHONDONTWRITEBYTECODE=1
export PYTHONUNBUFFERED=1
export OMP_NUM_THREADS=2
export OPENBLAS_NUM_THREADS=2

date --iso-8601=seconds
printf 'group=simulation_control_group formal_data=false job_id=%s host=%s\n' \
  "$SLURM_JOB_ID" "$SLURMD_NODENAME"

"$python_bin" examples/rebuttal_control_pipeline/probe_low_x_setup.py \
  --output "$diagnostic_root/probe.json"

date --iso-8601=seconds
