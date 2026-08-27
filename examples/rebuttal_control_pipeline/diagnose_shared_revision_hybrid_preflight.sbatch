#!/usr/bin/env bash
#SBATCH --job-name=simulation_control_group_hybrid_preflight
#SBATCH --partition=interruptible_cpu
#SBATCH --account=er_prj_eng_demt_robot_learning
#SBATCH --qos=normal
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:20:00
#SBATCH --output=/scratch/prj/eng_demt_robot_learning/polymetics_demt/rebuttal_dataset/simulation_control_group/full_seed20260806/diagnostics/shared_revision_hybrid_preflight/job_%j.out
#SBATCH --error=/scratch/prj/eng_demt_robot_learning/polymetics_demt/rebuttal_dataset/simulation_control_group/full_seed20260806/diagnostics/shared_revision_hybrid_preflight/job_%j.err

set -euo pipefail

repo_root=/scratch/prj/eng_demt_robot_learning/polymetics_demt
python_bin=/scratch/users/k23114984/conda/arcap/bin/python
diagnostic_root="$repo_root/rebuttal_dataset/simulation_control_group/full_seed20260806/diagnostics/shared_revision_hybrid_preflight"

cd "$repo_root"
export PYTHONDONTWRITEBYTECODE=1
export PYTHONUNBUFFERED=1
export OMP_NUM_THREADS=2
export OPENBLAS_NUM_THREADS=2

date --iso-8601=seconds
printf 'group=simulation_control_group formal_data=false participant=C03 job_id=%s host=%s\n' \
  "$SLURM_JOB_ID" "$SLURMD_NODENAME"

"$python_bin" examples/rebuttal_control_pipeline/diagnose_shared_revision.py \
  --participants C03 \
  --demo-indices 18 21 25 28 \
  --seed 20260806 \
  --release-z 0.04 \
  --max-attempts 30 \
  --output "$diagnostic_root/C03.json"

date --iso-8601=seconds
