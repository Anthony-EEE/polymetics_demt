# Executed command contract

All commands were run from:

```text
/scratch/prj/eng_demt_robot_learning/polymetics_demt
```

Python:

```text
/scratch/users/k23114984/conda/arcap/bin/python
```

## Gate 0–2

```bash
python scripts/tro_position_mvp0.py freeze-legacy
python scripts/tro_position_mvp0.py make-latents --block 0
python scripts/tro_position_mvp0.py collect --block 0 --target 3 --smoke \
  --sample-hz 8
python scripts/tro_position_mvp0.py validate-raw --block 0 --target 3 --smoke
```

## Block 0

```bash
sbatch scripts/run_tro_position_collect.sh
sbatch scripts/run_tro_position_hdf5.sh
BLOCK=0 PARTITION=interruptible_gpu \
  scripts/submit_tro_position_training.sh
BLOCK=0 sbatch --array=0-7 scripts/run_tro_position_eval.sh
BLOCK=0 sbatch scripts/run_tro_position_eval_merge.sh
python scripts/analyze_tro_position_mvp0.py validate-block --block 0
```

Key successful Slurm jobs:

```text
collection: 35974550
HDF5:      35975917
training:  35976515–35976518
evaluation array: 35976686
evaluation clean retry: 35976740
merge: 35976778
```

The Block 0 continuation result was:

```text
delta_start_outer = 0/25
delta_approach_reference = 7/25
continue_block1 = true
```

## Block 1

Block 1 commands were run only after the strict Block 0 validation and exact
continuation decision above.

```bash
python scripts/tro_position_mvp0.py make-latents --block 1
BLOCK=1 sbatch scripts/run_tro_position_collect.sh
BLOCK=1 sbatch scripts/run_tro_position_hdf5.sh
BLOCK=1 PARTITION=interruptible_gpu \
  scripts/submit_tro_position_training.sh
BLOCK=1 sbatch --array=0-7 scripts/run_tro_position_eval.sh
BLOCK=1 sbatch scripts/run_tro_position_eval_merge.sh
python scripts/analyze_tro_position_mvp0.py validate-block --block 1
python scripts/analyze_tro_position_mvp0.py final
```

Key successful Slurm jobs:

```text
collection: 35976782
HDF5:      35976870
training:  35976937–35976940
evaluation base array: 35977871
evaluation clean retries: 35978252, 35978596, 35980850
merge: 35982569
```

Pending evaluation tasks were shortened to a 20-minute Slurm walltime for
safe backfill. This did not change any scientific setting.

## Validation and audit

```bash
python scripts/tro_position_mvp0.py validate-raw --block 0 --target 30
python scripts/tro_position_mvp0.py validate-raw --block 1 --target 30
python scripts/analyze_tro_position_mvp0.py validate-block --block 0
python scripts/analyze_tro_position_mvp0.py validate-block --block 1
python scripts/analyze_tro_position_mvp0.py final
```

The final strict validation contains exactly 200 rollout rows per block.

## Corrected five-seed rollout evaluation

User-authorised correction on 2026-07-24: no dataset collection or policy
training is repeated. Existing checkpoints are inventoried and each run's
highest numeric `model_epoch_*.pth` is selected.

```bash
/scratch/users/k23114984/conda/arcap/bin/python \
  scripts/tro_position_mvp0.py freeze-latest-existing-checkpoints --block 0
/scratch/users/k23114984/conda/arcap/bin/python \
  scripts/tro_position_mvp0.py freeze-latest-existing-checkpoints --block 1

sbatch --parsable --array=0-79%40 \
  scripts/run_tro_position_5seed_eval.sh
```

The 80 array tasks cover:

```text
2 blocks × 4 conditions × 5 seeds × 2 banks × 25 rollouts = 2,000 rows
```

Seeds are `628`, `629`, `630`, `631`, `632`; every seed has 25 inner and 25
outer states shared exactly across all eight policies. Formal output is under
`dataset/tro_position_mvp0/rollouts_5seed_n50/`.

Executed jobs:

```text
36007304  block 0 tasks 0–39, interruptible_gpu, complete
36008307  block 1 tasks 40–79, gpu, complete
36010576  merge, interruptible_cpu, complete
```

Final validation and analysis:

```bash
/scratch/users/k23114984/conda/arcap/bin/python \
  scripts/analyze_tro_position_5seed.py
```

Result: 80/80 tasks, 20/20 aggregate summaries and 2,000/2,000 rollout rows
strictly validated.
Infrastructure partials are archived under
`dataset/tro_position_mvp0/block{0,1}/infrastructure_retries/` and are
excluded from both aggregate summaries.
