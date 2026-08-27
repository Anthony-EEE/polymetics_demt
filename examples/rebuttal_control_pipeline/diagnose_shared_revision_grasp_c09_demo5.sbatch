#!/usr/bin/env bash
#SBATCH --job-name=simulation_control_group_grasp_c09_demo5
#SBATCH --partition=interruptible_cpu
#SBATCH --account=er_prj_eng_demt_robot_learning
#SBATCH --qos=normal
#SBATCH --array=1-4
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:30:00
#SBATCH --output=/scratch/prj/eng_demt_robot_learning/polymetics_demt/rebuttal_dataset/simulation_control_group/full_seed20260806/diagnostics/shared_revision_grasp_c09_demo5/logs/probe_%A_%a.out
#SBATCH --error=/scratch/prj/eng_demt_robot_learning/polymetics_demt/rebuttal_dataset/simulation_control_group/full_seed20260806/diagnostics/shared_revision_grasp_c09_demo5/logs/probe_%A_%a.err

set -euo pipefail

repo_root=/scratch/prj/eng_demt_robot_learning/polymetics_demt
python_bin=/scratch/users/k23114984/conda/arcap/bin/python
diagnostic_root="$repo_root/rebuttal_dataset/simulation_control_group/full_seed20260806/diagnostics/shared_revision_grasp_c09_demo5"

case "$SLURM_ARRAY_TASK_ID" in
  1) label=x004_y016_zm005; offset=0.004,-0.016,-0.005 ;;
  2) label=x008_y012_zm005; offset=0.008,-0.012,-0.005 ;;
  3) label=x012_y012_zm005; offset=0.012,-0.012,-0.005 ;;
  4) label=x012_y012_z000; offset=0.012,-0.012,0.000 ;;
  *) printf 'invalid array task id: %s\n' "$SLURM_ARRAY_TASK_ID" >&2; exit 2 ;;
esac

cd "$repo_root"
export PYTHONDONTWRITEBYTECODE=1
export PYTHONUNBUFFERED=1
export OMP_NUM_THREADS=2
export OPENBLAS_NUM_THREADS=2
export CONTROL_GRASP_OFFSET="$offset"

date --iso-8601=seconds
printf 'group=simulation_control_group formal_data=false participant=C09 demo=5 grasp_offset=%s job_id=%s array_task_id=%s host=%s\n' \
  "$offset" "$SLURM_ARRAY_JOB_ID" "$SLURM_ARRAY_TASK_ID" "$SLURMD_NODENAME"

"$python_bin" examples/rebuttal_control_pipeline/diagnose_shared_revision_grasp_env.py \
  --participants C09 \
  --demo-indices 5 \
  --seed 20260806 \
  --release-z 0.04 \
  --max-attempts 30 \
  --output "$diagnostic_root/$label.json"

date --iso-8601=seconds
