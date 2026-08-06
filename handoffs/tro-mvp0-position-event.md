# Handoff: T-RO Stage 1 Position MVP

_Last updated: 2026-07-25 · Branch: `hpc-headless-tro` · baseline:
`2f61da7`_

## Preliminary early-stopping confirmation result frozen (2026-07-25)

The user authorised one new single-block Position confirmation without new
data collection and added the missing `START25_APP6` baseline. The experiment
reuses the pre-registered mandatory Block 0 HDF5 datasets for the four
decoupled conditions:

```text
START15_APP6
START35_APP6
START25_APP3P6
START25_APP8P4
```

No raw demonstrations were recollected and no HDF5 file was rebuilt. New
training uses seed `2701`, the repository's original validation early stopping
with patience 41, a 3,000-epoch safety ceiling and checkpoints every 20
epochs. All four configs use W&B project `TRO_MVP`; neither the project nor run
names use `rebuttal`.

The old epoch-40 checkpoints cannot be strictly continued. Their checkpoint
dictionaries contain model/config/shape/normalisation state only and omit
optimizer, scheduler, current epoch, best validation loss and early-stopping
patience. The available `--resume` path only warm-starts model weights with a
new optimizer and resets epoch/patience, so the confirmation trains the four
policies from scratch rather than mislabelling a warm start as continuation.

`START25_APP6` is exactly the accepted legacy `S25` condition
(`25 cm`, `6.0 cm`). Its existing early-stopping run contains epoch 20, 40, 60
and 80 checkpoints; epoch 80 is reused without retraining:

```text
/scratch/prj/eng_demt_robot_learning/trained_models/
  ar_guidance_spatial_S15_S35/S25/spatial_S25_d30_seed1_2gap/
  20260704004132/models/model_epoch_80.pth
SHA-256:
e666ab6a53f87f8d0f2e0a5ba29bd34b28cc39930d57cc848abfa5745465d60f
```

Training and checkpoint selection completed as follows:

```text
36011865  START15_APP6 training     complete, selected epoch 60
36011866  START35_APP6 training     complete, selected epoch 40
36011867  START25_APP3P6 training   complete, selected epoch 60
36011868  START25_APP8P4 training   complete, selected epoch 80
36011888  checkpoint freeze         complete
```

The rollout comparison is five policies × five shared seeds ×
`(25 inner + 25 outer)`, or 1,250 rows. Ten confirmation manifests preserve
the prior states and RNG records exactly and extend only `condition_order` to
include `START25_APP6`. Baseline deployment states/RNG are paired with the four
new policies, but its demonstration dataset and training seed differ, so
baseline differences must not be described as a dataset-controlled causal
contrast.

Key confirmation files:

```text
experiments/mvp0_position_event/confirmation_earlystop/manifests/protocol.json
scripts/tro_position_confirmation.py
scripts/submit_tro_position_confirmation_training.sh
scripts/run_tro_position_confirmation_{freeze,eval,merge,analyze}.sh
scripts/analyze_tro_position_confirmation.py
tests/test_tro_position_confirmation.py
```

The original evaluation array `36011889` failed before producing a valid
rollout because the submitted job inherited the old four-condition
`condition_order`. The confirmation manifests were corrected to add only the
missing baseline condition while preserving the frozen deployment states and
RNG records. No demonstration was recollected and no policy was retrained.

The corrected dependency chain completed successfully:

```text
36033919  corrected 50-task five-seed rollout array   50/50 complete
36033920  strict ten-bank merge                       complete, exit 0
36033921  final validation and analysis               complete, exit 0
```

Strict validation passed for all five policies, five shared seeds and both
banks: 50/50 policy/seed/bank tasks, 10/10 aggregate summaries, and exactly
1,250/1,250 rollout rows.

The user froze this as a **preliminary result** on 2026-07-25. These artifacts
must remain unchanged and must not be overwritten by a future retrained
`START25_APP6` comparison:

```text
experiments/mvp0_position_event/confirmation_earlystop/analysis/comparison.json
SHA-256 0c17c65330b8ab25867e75b1409553e1ad2dfbb33ad52789acc586d1f7a9d1d1

experiments/mvp0_position_event/confirmation_earlystop/analysis/summary.md
SHA-256 c285ea524ac8ef795b073f6f2e54925745ae2e0ddef4a7238192407b7b6c1d29
```

Final overall ranking:

| Rank | Condition | Successes | Five-seed mean ± std |
|---:|---|---:|---:|
| 1 | `START25_APP3P6` | 144/250 | 0.576 ± 0.038 |
| 2 | `START25_APP8P4` | 126/250 | 0.504 ± 0.062 |
| 3 | `START25_APP6` baseline | 116/250 | 0.464 ± 0.086 |
| 4 | `START15_APP6` | 112/250 | 0.448 ± 0.097 |
| 5 | `START35_APP6` | 69/250 | 0.276 ± 0.052 |

`START25_APP3P6` also ranks first on the inner bank
(`78/125`, `0.624 ± 0.083`) and outer bank
(`66/125`, `0.528 ± 0.052`). Against `START25_APP8P4`, tightening the
approach radius improves the observed combined rate by `18/250` (`+0.072`),
inner by `7/125` (`+0.056`) and outer by `11/125` (`+0.088`). Widening the
start radius from 15 cm to 35 cm reduces outer success by `15/125`
(`-0.120`) and combined success by `43/250` (`-0.172`).

This single-block confirmation supports `START25_APP3P6` as the best observed
policy and provides positive confirmation for a tighter approach distribution.
It also provides negative evidence for widening the start distribution to
35 cm. It does not erase the earlier B0/B1 learner-block instability or prove
a universally reproducible causal mechanism; another independent training
replicate would be required for that stronger claim.

The legacy `START25_APP6` deployment comparison is exactly paired in states
and RNG, but its demonstration dataset and training seed differ from the four
new policies. Its `+0.112` observed deficit to `START25_APP3P6` therefore
cannot be interpreted as a clean dataset-controlled causal contrast.

Accordingly, the frozen preliminary ranking is valid as an observed
five-policy deployment ranking, but the relative placement of legacy
`START25_APP6` is not part of the primary causal conclusion. No replacement
`START25_APP6` training or evaluation job was created or submitted in this
handoff-only update.

Final artifacts:

```text
experiments/mvp0_position_event/confirmation_earlystop/analysis/summary.md
experiments/mvp0_position_event/confirmation_earlystop/analysis/comparison.json
experiments/mvp0_position_event/confirmation_earlystop/manifests/checkpoints.json
```

## Corrected rollout evaluation complete (2026-07-24)

The user explicitly superseded the original single-seed rollout comparison and
authorised a rollout-only correction. Do **not** recollect demonstrations or
retrain policies.

Existing checkpoint audit:

- all eight policy runs contain exactly `model_epoch_20.pth` and
  `model_epoch_40.pth`;
- there are no additional best/early-stop checkpoint files;
- the corrected instruction selects the highest numeric existing
  `model_epoch_*.pth`, therefore all eight selected checkpoints are the
  existing epoch-40 files;
- complete inventories and hashes are frozen in
  `manifests/checkpoints_latest_existing_b{0,1}.json`;
- `retraining_performed` is explicitly `false`.

Corrected evaluation protocol:

```text
policies: 2 blocks × 4 conditions = 8
shared seeds: 628, 629, 630, 631, 632
per seed/policy: 25 inner [0.00, 0.25] m + 25 outer (0.25, 0.35] m
per policy: 250 rollouts
formal total: 2,000 rollouts
```

The ten frozen state/RNG manifests are under
`manifests/rollout_5seed/`. All eight policies use the exact same state IDs,
runtime RNG and point-cloud RNG for every seed/bank trial.

Slurm execution:

```text
36007304: tasks 0–39 on interruptible_gpu (block 0), complete
36008307: tasks 40–79 on gpu (block 1), complete
36010576: 20-way seed/bank/block merge, complete
```

The second array was moved to the normal GPU partition only to increase
throughput; scientific settings were identical. No corrected-evaluation task
failed, timed out, was preempted or required a retry.

Strict validation passed:

```text
80/80 policy/seed/bank tasks
20/20 aggregate summaries
250 exact shared deployment states per policy
2,000/2,000 rollout rows
checkpoint path/hash, seed, bank, state ID and RNG pairing all valid
```

Primary robustness ranking: for each of the eight policies, average its five
`successes/50` rollout-seed rates and report mean ± sample standard deviation
(`ddof=1`).

| Rank | Policy | Five-seed mean ± std |
|---:|---|---:|
| 1 | `block0/START25_APP3P6` | 0.548 ± 0.058 |
| 2 | `block0/START15_APP6` | 0.456 ± 0.050 |
| 3 | `block0/START25_APP8P4` | 0.400 ± 0.079 |
| 4 | `block1/START25_APP8P4` | 0.372 ± 0.064 |
| 5 | `block1/START25_APP3P6` | 0.324 ± 0.074 |
| 6 | `block0/START35_APP6` | 0.284 ± 0.082 |
| 7 | `block1/START15_APP6` | 0.252 ± 0.048 |
| 8 | `block1/START35_APP6` | 0.112 ± 0.052 |

Inner ranking (five-seed mean ± std):

```text
B0 START15_APP6      0.640 ± 0.075
B0 START25_APP3P6    0.584 ± 0.061
B1 START25_APP8P4    0.440 ± 0.089
B1 START25_APP3P6    0.376 ± 0.073
B0 START25_APP8P4    0.368 ± 0.111
B1 START15_APP6      0.328 ± 0.033
B0 START35_APP6      0.280 ± 0.085
B1 START35_APP6      0.096 ± 0.073
```

Outer ranking (five-seed mean ± std):

```text
B0 START25_APP3P6    0.512 ± 0.072
B0 START25_APP8P4    0.432 ± 0.107
B1 START25_APP8P4    0.304 ± 0.083
B0 START35_APP6      0.288 ± 0.087
B0 START15_APP6      0.272 ± 0.066
B1 START25_APP3P6    0.272 ± 0.087
B1 START15_APP6      0.176 ± 0.092
B1 START35_APP6      0.128 ± 0.033
```

Hierarchical condition comparison: B0/B1 cells are five-rollout-seed
mean ± std; the final column is mean ± std across the two policy means.

| Rank | Condition | B0 rollout seeds | B1 rollout seeds | Across blocks |
|---:|---|---:|---:|---:|
| 1 | `START25_APP3P6` | 0.548 ± 0.058 | 0.324 ± 0.074 | 0.436 ± 0.158 |
| 2 | `START25_APP8P4` | 0.400 ± 0.079 | 0.372 ± 0.064 | 0.386 ± 0.020 |
| 3 | `START15_APP6` | 0.456 ± 0.050 | 0.252 ± 0.048 | 0.354 ± 0.144 |
| 4 | `START35_APP6` | 0.284 ± 0.082 | 0.112 ± 0.052 | 0.198 ± 0.122 |

Individual policies:

| Rank | Policy | Combined | Inner | Outer |
|---:|---|---:|---:|---:|
| 1 | `block0/START25_APP3P6` | 137/250 | 73/125 | 64/125 |
| 2 | `block0/START15_APP6` | 114/250 | 80/125 | 34/125 |
| 3 | `block0/START25_APP8P4` | 100/250 | 46/125 | 54/125 |
| 4 | `block1/START25_APP8P4` | 93/250 | 55/125 | 38/125 |
| 5 | `block1/START25_APP3P6` | 81/250 | 47/125 | 34/125 |
| 6 | `block0/START35_APP6` | 71/250 | 35/125 | 36/125 |
| 7 | `block1/START15_APP6` | 63/250 | 41/125 | 22/125 |
| 8 | `block1/START35_APP6` | 28/250 | 12/125 | 16/125 |

Corrected primary effects:

```text
Start outer, wide - tight:  block 0 +2/125 (+0.016), block 1 -6/125 (-0.048)
Approach inner, tight-wide: block 0 +27/125 (+0.216), block 1 -8/125 (-0.064)
```

Neither effect is positive in both learner blocks. Final corrected
classification is **`null/unstable`**. The earlier single-seed comparison is
preserved but superseded.

## Deployment interpretation agreed with the user

The eight-policy ranking and the separate inner/outer rankings support the
following engineering interpretation:

> Use moderate variation early in the trajectory to cover deployment start
> states, then make demonstrations increasingly consistent near the
> approach/grasp phase. This “front wider, back tighter” pattern is the best
> observed balance between fitting the inner bank and retaining robustness on
> the outer bank.

The clearest individual policy is `block0/START25_APP3P6`:

```text
inner   0.584 ± 0.061
outer   0.512 ± 0.072
overall 0.548 ± 0.058
inner–outer gap: 0.072
```

It is the highest-ranked individual policy and has a substantially smaller
inner/outer imbalance than `block0/START15_APP6` (inner `0.640`, outer
`0.272`). The latter fits the inner bank best but generalizes poorly to the
outer bank. `START35_APP6` is weak on both banks, showing that increasing
early-stage variation without limit does not improve robustness and can leave
the finite demonstration set under-covering the task. `APP8P4` is more stable
across B0/B1 than `APP3P6`, but its best observed performance is lower,
consistent with excessive variation near grasp trading away precision.

This is a deployment-design takeaway, **not a proven causal mechanism**.
`START25_APP3P6` drops from `0.548` in B0 to `0.324` in B1, and neither
pre-registered primary contrast is positive in both learner blocks. The
scientific result therefore remains `null/unstable`; independent training
replicates would be required before claiming that “front wider, back tighter”
is a reproducible causal law.

## User override for all future experiments

The following protocol supersedes the B0/B1 replication structure and the
fixed epoch-40 model-selection rule for **future experiments only**. It does
not alter, delete or reinterpret the completed Stage 1 artifacts above.

1. Run one experiment/training block for the condition set. Do not create
   separate B0 and B1 independent learner blocks.
2. Restore the original early-stopping training procedure. Do not force every
   run to stop at epoch 40 and do not select `model_epoch_40.pth` merely
   because it is epoch 40.
3. Let every condition train under the same early-stopping rule. For each
   condition, select the final checkpoint actually emitted by that run,
   defined operationally as the highest-epoch existing
   `model_epoch_*.pth`. Inventory and hash the selected file before rollout.
   This selected final early-stopped checkpoint is the condition's model for
   comparison; do not choose a checkpoint after inspecting rollout outcomes.
4. Evaluate every selected condition model with the same five rollout seeds.
   Each seed has exactly 50 rollouts: 25 inner plus 25 outer. Therefore each
   condition model receives 250 rollouts in total.
5. Reuse exactly paired deployment states and RNG inputs across conditions
   within every seed/bank/trial. Rank the condition models by the mean ±
   sample standard deviation across the five seed-level `successes/50`
   rates, and also report inner and outer results separately.
6. **Mandatory seed comparability:** every policy included in one primary
   comparison must use exactly the same training seed. A policy trained with
   a different seed is a historical/secondary baseline and must not be mixed
   into the primary causal ranking.
7. If future data collection is performed, every compared condition must also
   use the same collection seed and the same paired latent manifest. If data
   are reused instead, any dataset-seed/provenance mismatch must be stated
   explicitly and the affected comparison must not be called fully
   data-controlled.
8. Evaluation must use the same rollout seed list, start-state IDs, runtime
   RNG and point-cloud RNG for every compared policy. Changing any one of
   these requires a new comparison namespace rather than overwriting a frozen
   result.

In short, the future comparison unit is:

```text
one condition → one early-stopped training run → its last emitted checkpoint
              → 5 shared seeds × (25 inner + 25 outer)
              → 250 rollouts
```

## Status

**Stage 1 and its corrected five-seed evaluation are complete. The
single-block early-stopping confirmation is frozen as a preliminary result.
The original cross-block classification remains `null/unstable`.**

The corrected comparison used eight existing policies, five shared seeds and
2,000 rollouts. No demonstrations were recollected and no policy was
retrained. Neither primary contrast replicated across the two independent
learner blocks. Stage 2, Rotation, Velocity, AR and human experiments were not
launched.

The later single-block confirmation used four newly trained seed-2701 policies
plus the legacy seed-1 `START25_APP6` baseline and 1,250 strictly validated
rollouts. Its observed ranking is preserved above, but the APP6 placement is
seed- and dataset-confounded. The user considered, then explicitly cancelled,
creation of an APP6 seed-2701 supplemental experiment for now. There is no
new APP6 training, evaluation or analysis job to monitor.

No commit or push was made. The unrelated zero-byte untracked files `[`,
`count=0`, `done` and `fi` remain present.

## Original single-seed protocol (superseded for policy comparison)

- Trajectory stayed
  `Start → Approach → Descent → Grasp → Lift`.
- Descent, grasp and lift targets were not changed.
- Only these four new conditions were run:

  | Condition | Start radius | Approach radius |
  |---|---:|---:|
  | `START15_APP6` | 0.15 m | 0.060 m |
  | `START35_APP6` | 0.35 m | 0.060 m |
  | `START25_APP3P6` | 0.25 m | 0.036 m |
  | `START25_APP8P4` | 0.25 m | 0.084 m |

- Each block used four paired 30-success demonstration datasets, four
  independently trained policies, exactly 40 epochs and
  `model_epoch_40.pth`.
- Evaluation reused the frozen legacy 50-state manifest, split at the exact
  PLAN indices into two ordered 25-state child banks.
- Each block has exactly 200 validated rollout rows:
  four policies × two banks × 25 states.
- Evaluation remained horizon 200, 8 Hz, action gap 2, action dt 0.25 s,
  terminate-on-success and `final cube z >= 0.20 m`.
- Historical S25 was not recollected or retrained.
- The closed `dataset/ar_guidance_spatial_S15_S35/` artifacts were never
  modified.

## Legacy freeze

Verified immutable evidence:

```text
summary_seed628_n50.json
ec9c95ba26e3a4b9f18ae7c34966a8d55dc3acca2af10c18bdbc43d12c827d78

shared_start_manifest_seed628_n50_r35.json
84316b36922ea71225615d285bffccdfef4b99289650e302c963deb761f516ce

historical S25 model_epoch_80.pth
e666ab6a53f87f8d0f2e0a5ba29bd34b28cc39930d57cc848abfa5745465d60f
```

Frozen child manifests:

```text
legacy_seed628_reference_r00_r25_n25_v1
13856c9f93254514914c0a9b5e9ae681ab15120e556d63fcba335c8c5cc165bd

legacy_seed628_outer_r25_r35_n25_v1
6eae03148557d67761369a76c7acaa11f4041fdb308d677546295e56bb40e139
```

The exact PLAN index partition and parent SHA-256 are asserted in the child
manifests and `manifests/legacy_evidence.json`.

## Dataset and learner execution

### Block 0

- collection seed `1701`; training seed `2701`;
- paired manifest:
  `experiments/mvp0_position_event/manifests/paired_latents_b0.json`;
- 30 accepted canonical candidates per condition, with 8 whole-block
  rejections;
- four raw datasets validated at 8 Hz;
- four HDF5 files each contain 60 augmented episodes and the exact read-only
  legacy S25 `54/6` train/valid masks;
- training jobs `35976515–35976518` completed at epoch 40.

Frozen Block 0 epoch-40 checkpoint hashes:

```text
START15_APP6    d653e77f6372aa9bf47d6131c54908742762415e0691c0dd718cb5e5ab2e054f
START35_APP6    40a12752d1d5d34b902f81bd01da37c825e4771f599ab024318b0e8250940430
START25_APP3P6  ff16150e0f67b36e73d86eb9bbc4a167a3cff3b9a6ecb78bfd7a8e5592d5d4d1
START25_APP8P4  6e007249642ecadb20ef8b8d3d8b4508bf948767dd178188a2920d1c2f7d3009
```

### Block 1

Block 1 was run only after Block 0 strict validation and the exact continuation
decision.

- collection seed `1702`; training seed `2702`;
- paired manifest SHA-256:
  `56740c1895ca58070c59e57a503e13ef911da1080f1468d6d25d349325808aeb`;
- collection job `35976782` completed with 30 accepted candidates per
  condition and 21 whole-block rejections;
- HDF5 job `35976870` completed; all four files have 60 episodes and the same
  exact legacy S25 `54/6` masks;
- training jobs `35976937–35976940` all completed at epoch 40.

Frozen Block 1 epoch-40 checkpoint hashes:

```text
START15_APP6    277406ec37e2366ef9075c090e76c6e0926b44ad184825e471be7e4ab8d70736
START35_APP6    49b4c3f5d9246d92a3ef4580c5a33581121c28837792b3195e16ace27e2323c8
START25_APP3P6  a690298a8aa30570c5f881d177ca3a69d7dded1554fe1eacfc1db6031059a86b
START25_APP8P4  03af1476df98c6002ab76cb7358443fe4bc790e46435a7147de15b1a839a98bf
```

Complete raw/HDF5 paths and SHA-256 values are in
`experiments/mvp0_position_event/manifests/datasets.json`; complete policy
provenance is in `policies.json`, `checkpoints.json` and
`checkpoints_b{0,1}.json`.

## Superseded single-seed results (provenance only)

### Successes per 25 states

| Block | Condition | Reference bank | Outer bank |
|---:|---|---:|---:|
| 0 | `START15_APP6` | 15 | 8 |
| 0 | `START35_APP6` | 5 | 8 |
| 0 | `START25_APP3P6` | 16 | 10 |
| 0 | `START25_APP8P4` | 9 | 8 |
| 1 | `START15_APP6` | 8 | 1 |
| 1 | `START35_APP6` | 3 | 4 |
| 1 | `START25_APP3P6` | 9 | 4 |
| 1 | `START25_APP8P4` | 14 | 8 |

### Pre-registered contrasts

| Block | `delta_start_outer` | `delta_start_reference` | `delta_approach_reference` | `delta_approach_outer` |
|---:|---:|---:|---:|---:|
| 0 | 0/25 | -10/25 | +7/25 | +2/25 |
| 1 | +3/25 | -5/25 | -5/25 | -4/25 |

Block 0 passed the continuation rule only through
`delta_approach_reference = 7/25 >= 4/25`; the Start primary was `0/25`.

The final replication rule required a primary contrast to be positive in both
blocks and have a mean rate difference of at least `0.15`.

- Start primary did not replicate: `0.00` then `+0.12`.
- Approach primary did not replicate: `+0.28` then `-0.20`, a direction
  conflict.
- Final classification: **`null/unstable`**.

This is sequential engineering screening, not a formal significance test.
Wilson intervals and paired discordances are preserved in the block reports.

## Final artifacts

```text
experiments/mvp0_position_event/analysis/
  block0_screening.json
  block1_screening.json
  screening_decision.json
  summary.md
  rollout_5seed_comparison.json
  rollout_5seed_comparison.md
  figures/
    sampled_start_approach_offsets.png
    success_by_bank.png
    success_by_policy_5seed.png
```

Large outputs:

```text
dataset/tro_position_mvp0/
dataset/tro_position_mvp0/rollouts_5seed_n50/
/scratch/prj/eng_demt_robot_learning/trained_models/tro_position_mvp0/
```

## Infrastructure corrections and retries

All invalid or interrupted outputs were preserved outside formal roots and
excluded from analysis.

- Initial 30 Hz smoke/formal data were rejected after auditing legacy S25 as
  8 Hz. They were archived under
  `dataset/tro_position_mvp0/invalid_protocol_sample_hz30/`; corrected
  collection used 8 Hz.
- Initial HDF5 training attempts lacked `mask/train` and `mask/valid`. Their
  model directories were archived under
  `/scratch/prj/eng_demt_robot_learning/trained_models/tro_position_mvp0/invalid_missing_hdf5_masks_jobs35976429_35976432`.
  Corrected HDF5 files use the exact read-only legacy S25 masks.
- Block 0 Outer × `START15_APP6` evaluation was preempted twice. Partial
  21/25 and 2/25 outputs/logs are under
  `block0/infrastructure_retries/`; job `35976740` completed the clean retry.
- Block 1 Reference × `START35_APP6` was preempted at 7/25 and
  Reference × `START25_APP3P6` at 24/25. Both partial sets are under
  `block1/infrastructure_retries/`; jobs `35978252` and `35978596` completed
  clean retries.
- A controlled 0-row attempt to use an idle RTX PRO 6000 Blackwell node
  exposed frozen-environment incompatibility (`sm_120` vs supported `sm_90`).
  It was stopped before any row, archived, and task 3 was completed as job
  `35980850` on the original supported constraint.
- Evaluation walltime was safely reduced from two hours to 20 minutes for
  backfill. No scientific setting changed.

## Historical context only

The legacy coupled diagonal remains:

| Legacy condition | Reference bank | Outer bank |
|---|---:|---:|
| S15 `(15 cm, 3.6 cm)` | 14/25 | 4/25 |
| S25 `(25 cm, 6.0 cm)` | 8/25 | 10/25 |
| S35 `(35 cm, 8.4 cm)` | 5/25 | 2/25 |

S15/S35 changed both radii. Historical S25 used epoch 80. None is treated as a
new single-stage policy or independent replicate.

## Resume guidance

There is no remaining Stage 1 execution. A fresh session should read:

1. `experiments/mvp0_position_event/PLAN.md`
2. this handoff
3. `experiments/mvp0_position_event/analysis/summary.md`
4. `experiments/mvp0_position_event/analysis/screening_decision.json`
5. `experiments/mvp0_position_event/analysis/rollout_5seed_comparison.md`

Then stop unless the user explicitly authorises a new scope. Do not launch
Stage 2 automatically under this classification. If the user authorises a
new experiment, follow **User override for all future experiments** above
rather than copying the historical B0/B1 and fixed epoch-40 protocol.
Do not modify the frozen preliminary confirmation artifacts. A future
seed-matched `START25_APP6` supplement must use a new experiment, model and
rollout namespace and must use the same training seed as all policies in its
primary comparison.

## Changelog

- 2026-07-23: Created the pre-implementation handoff and froze the lean
  sequential design.
- 2026-07-23: Completed Gates 0–5 and mandatory Block 0.
- 2026-07-23: Applied the exact `4/25` rule; the Approach primary triggered
  one independent Block 1.
- 2026-07-23: Completed Block 1, final analysis and Stage 1 stop with
  classification `null/unstable`.
- 2026-07-24: Began the user-authorised rollout-only correction using five
  shared seeds, 25 inner plus 25 outer states per seed, eight existing
  latest-checkpoint policies and 2,000 total rollouts.
- 2026-07-24: Completed and strictly validated all 2,000 corrected rollouts;
  updated the final policy ranking and retained `null/unstable` because both
  primary mechanisms conflict across learner blocks.
- 2026-07-24: Added the user-requested condition ranking using Block 0/1
  mean ± sample standard deviation (`ddof=1`).
- 2026-07-24: Corrected the primary ranking to eight separate policies, each
  summarized across its five rollout seeds as mean ± sample standard
  deviation; retained the Block 0/1 condition average as secondary only.
- 2026-07-24: Added separate inner and outer five-seed mean ± std rankings for
  all eight policies.
- 2026-07-24: Recorded the user-agreed deployment interpretation: moderate
  early variation plus tighter pre-grasp consistency best balances inner
  fitting and outer robustness in the observed ranking, while preserving the
  `null/unstable` scientific classification and its replication caveat.
- 2026-07-24: Recorded the mandatory protocol for future experiments: one
  training block only, original early stopping, each condition's final
  emitted checkpoint, and five shared rollout seeds with 25 inner plus 25
  outer trials per seed.
- 2026-07-24: Launched the user-authorised single-block early-stopping
  confirmation using existing Block 0 data and W&B project `TRO_MVP`; reused
  the legacy S25 epoch-80 policy as `START25_APP6`, and submitted the guarded
  1,250-rollout dependency chain.
- 2026-07-25: Completed the corrected 50-task confirmation rollout array,
  strict ten-bank merge and final analysis. Validated all 1,250 rollout rows;
  `START25_APP3P6` ranks first overall and on both banks. Recorded the legacy
  baseline confound and retained the independent-replication caveat.
- 2026-07-25: Froze the 1,250-rollout confirmation as a preliminary result
  with exact analysis hashes. Added the mandatory rule that all policies in
  every future primary comparison use the same training seed, with paired
  collection and evaluation randomness; recorded that no supplemental APP6
  experiment was created or submitted.
