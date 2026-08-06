# T-RO Stage 2 Position condition-relative ID/OOD rerollout commands

All commands run from the repository root. No commit, push, PR or training is
part of this experiment.

## Executed

```bash
/scratch/users/k23114984/conda/arcap/bin/python \
  scripts/tro_position_stage2_idood.py freeze-protocol

/scratch/users/k23114984/conda/arcap/bin/python \
  scripts/tro_position_stage2_idood.py generate-manifests

/scratch/users/k23114984/conda/arcap/bin/python -m pytest -q \
  tests/test_tro_position_mvp0.py \
  tests/test_tro_position_confirmation.py \
  tests/test_tro_position_stage2.py \
  tests/test_tro_position_stage2_idood.py

sbatch --parsable --array=0-5%6 \
  scripts/run_tro_position_stage2_idood_smoke.sh
# job 36042451; failed before rollout because the original smoke horizon did
# not match the frozen protocol; no rows produced
```

The smoke script was corrected. This RMAX45 array remains rejected pilot
evidence and was not retried under the old protocol.

## RMAX40 v2 amendment

```bash
/scratch/users/k23114984/conda/arcap/bin/python \
  scripts/tro_position_stage2_idood.py freeze-protocol

/scratch/users/k23114984/conda/arcap/bin/python \
  scripts/tro_position_stage2_idood.py generate-manifests

/scratch/users/k23114984/conda/arcap/bin/python -m pytest -q \
  tests/test_tro_position_mvp0.py \
  tests/test_tro_position_confirmation.py \
  tests/test_tro_position_stage2.py \
  tests/test_tro_position_stage2_idood.py
# 32 passed

sbatch --parsable --array=0-5%6 \
  scripts/run_tro_position_stage2_idood_smoke.sh
# job 36043096; six tasks COMPLETED 0:0, 25 rows per path

sbatch --parsable --array=0-249%40 \
  scripts/run_tro_position_stage2_idood_rollout.sh
# job 36043712; 249 completed, task 245 PREEMPTED

# After archiving task 245's one partial row and logs:
sbatch --parsable --array=245 \
  scripts/run_tro_position_stage2_idood_rollout.sh
# job 36049746; COMPLETED 0:0 with identical frozen inputs
```

## Strict merge and analysis

```bash
sbatch --parsable scripts/run_tro_position_stage2_idood_merge.sh
# job 36050142; validator implementation failed before writing merge output

# After correcting the validator's single-condition summary field:
sbatch --parsable scripts/run_tro_position_stage2_idood_merge.sh
# job 36050269; COMPLETED 0:0, 250 tasks and 6,250 rows valid

sbatch --parsable scripts/run_tro_position_stage2_idood_analyze.sh
# job 36050433; COMPLETED 0:0
```

The only formal rollout retry was the infrastructure-preempted task 245.
There were no scientific-performance retries.
