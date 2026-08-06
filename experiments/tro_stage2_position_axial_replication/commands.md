# T-RO Stage 2 Position axial replication commands

All commands run from the repository root. No commit, push or PR is part of
this experiment.

## Gate 0–1

```bash
/scratch/users/k23114984/conda/arcap/bin/python \
  scripts/tro_position_stage2.py freeze-protocol --skip-large-rehash

/scratch/users/k23114984/conda/arcap/bin/python \
  scripts/tro_position_stage2.py generate-rollout-manifests

/scratch/users/k23114984/conda/arcap/bin/python -m pytest -q \
  tests/test_tro_position_mvp0.py \
  tests/test_tro_position_confirmation.py \
  tests/test_tro_position_stage2.py
```

The `--skip-large-rehash` freeze followed an explicit same-session rehash of
the eight reused HDF5 files and four reused Stage 1b checkpoints. It avoids
repeating those large reads while still checking the four required frozen
hashes.

## Gate 2 smoke

```bash
sbatch --parsable --array=0-4%5 \
  scripts/run_tro_position_stage2_smoke.sh
```

Submitted as job array `36034912`.

Locked seed1 and seed5 records triggered the pre-registered whole-slot
fallback. The fallback smoke was:

```bash
/scratch/users/k23114984/conda/arcap/bin/python \
  scripts/tro_position_stage2.py activate-fallback --canonical-seed 1
/scratch/users/k23114984/conda/arcap/bin/python \
  scripts/tro_position_stage2.py activate-fallback --canonical-seed 5
sbatch --parsable --array=0,4%2 \
  scripts/run_tro_position_stage2_smoke.sh
```

Submitted as job array `36034982`; both tasks completed.

## Executed formal chain

```bash
sbatch --parsable --array=0-4%5 \
  scripts/run_tro_position_stage2_collect.sh
# job 36035006

sbatch --parsable --array=0-4%5 \
  scripts/run_tro_position_stage2_hdf5.sh
# job 36035085

/scratch/users/k23114984/conda/arcap/bin/python \
  scripts/tro_position_stage2.py validate-all-datasets

/scratch/users/k23114984/conda/arcap/bin/python \
  scripts/tro_position_stage2.py create-train-configs

bash scripts/submit_tro_position_stage2_training.sh
# jobs 36035267 through 36035291

/scratch/users/k23114984/conda/arcap/bin/python \
  scripts/tro_position_stage2.py freeze-checkpoints

sbatch --parsable --array=0-249%40 \
  scripts/run_tro_position_stage2_rollout.sh
# job 36036227

sbatch --parsable scripts/run_tro_position_stage2_merge.sh
# job 36036979
sbatch --parsable scripts/run_tro_position_stage2_analyze.sh
# job 36037013
```

The original rollout array had three infrastructure preemptions. Their partial
outputs were archived before the clean retries:

```bash
sbatch --parsable --array=24,28%2 \
  scripts/run_tro_position_stage2_rollout.sh
# retry job 36036368

sbatch --parsable --array=244 \
  scripts/run_tro_position_stage2_rollout.sh
# retry job 36036894
```

All formal and retry jobs reached terminal state. Exact states, nodes, retry
reasons and archived partial-artifact paths are recorded in
`manifests/jobs.json`.
