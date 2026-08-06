# Execution Plan: T-RO Stage 2 Position Axial Replication

**Date:** 2026-07-25  
**Branch baseline:** `hpc-headless-tro @ 2f61da7`  
**Status:** Pre-implementation; explicitly authorised by the user  
**Scope:** Position only. Do not launch Rotation, Velocity, cross-task
compatibility modelling, AR guidance or human studies.

## 1. Objective

Stage 1b identified `START25_APP3P6` as the best observed single-block
early-stopped policy, but the original two learner blocks were unstable and
the legacy `START25_APP6` baseline had mismatched dataset/training provenance.

Stage 2 therefore performs a balanced five-condition, five-dataset-policy
replication of the axial Position design:

> Under a fixed learner and 30-demonstration budget, determine whether
> moderate Start variation and tighter Approach variation produce a
> reproducible deployment advantage across independent dataset-policy
> realisations.

This is a confirmatory replication of the existing axial conditions, not the
previously proposed corner/composition experiment. New corner conditions such
as `START15_APP3P6` and `START35_APP3P6` are out of scope until this axial
replication is complete.

## 2. Canonical seed policy

For all future experiments:

```text
K dataset-policy repeats -> canonical seeds 1, 2, ..., K
one dataset-policy repeat -> canonical seed 1
formal rollout seeds      -> 1, 2, 3, 4, 5
```

Within one canonical seed, all conditions use the same collection seed and the
same training seed. A collection seed and a training seed are two components
of one dataset-policy repeat; they are never counted as two independent
repeats.

Historical artifacts may be assigned a canonical slot for analysis and file
organisation, but manifests must preserve both the canonical alias and the
actual source seeds. A canonical alias never rewrites provenance.

## 3. Conditions

The five formal conditions are:

| Condition | Start radius | Approach radius | Role |
|---|---:|---:|---|
| `START15_APP6` | 0.15 m | 0.060 m | Start-tight |
| `START35_APP6` | 0.35 m | 0.060 m | Start-wide |
| `START25_APP3P6` | 0.25 m | 0.036 m | Approach-tight candidate |
| `START25_APP6` | 0.25 m | 0.060 m | Reference |
| `START25_APP8P4` | 0.25 m | 0.084 m | Approach-wide |

All five conditions must have five dataset-policy slots in the final balanced
analysis.

## 4. Five-repeat matrix and reuse

### 4.1 Canonical mapping

| Canonical slot | Actual collection seed | Actual training seed | Source |
|---|---:|---:|---|
| `seed1` | 1 | 1 | New for four axial conditions; legacy reference reused |
| `seed2` | 2 | 2 | Fully new five-condition repeat |
| `seed3` | 3 | 3 | Fully new five-condition repeat |
| `seed4` | 1702 | 2702 | Reuse old Block 1 data; retrain early-stopped policies |
| `seed5` | 1701 | 2701 | Reuse completed Stage 1b data and early-stopped policies |

Every manifest row must include:

```text
canonical_seed
source_collection_seed
source_training_seed
reused_dataset
reused_policy
source_artifact_path
source_artifact_sha256
```

### 4.2 Exact work by condition and seed

| Condition | seed1 | seed2 | seed3 | seed4 | seed5 |
|---|---|---|---|---|---|
| `START15_APP6` | new data + policy | new data + policy | new data + policy | reuse B1 data, retrain policy | reuse Stage 1b data + policy |
| `START35_APP6` | new data + policy | new data + policy | new data + policy | reuse B1 data, retrain policy | reuse Stage 1b data + policy |
| `START25_APP3P6` | new data + policy | new data + policy | new data + policy | reuse B1 data, retrain policy | reuse Stage 1b data + policy |
| `START25_APP6` | reuse legacy data + policy | new data + policy | new data + policy | new reference data + policy matched to B1 | new reference data + policy matched to Stage 1b |
| `START25_APP8P4` | new data + policy | new data + policy | new data + policy | reuse B1 data, retrain policy | reuse Stage 1b data + policy |

Final analysis slots:

```text
5 conditions x 5 dataset-policy slots = 25 policies
```

New work:

```text
new datasets:
  seed1 four non-reference conditions       4
  seed2 all five conditions                 5
  seed3 all five conditions                 5
  seed4 reference only                      1
  seed5 reference only                      1
  total                                    16

new successful demonstrations:
  16 datasets x 30                         480

new policies:
  seed1 four non-reference conditions       4
  seed2 all five conditions                 5
  seed3 all five conditions                 5
  seed4 four retrains + new reference       5
  seed5 new reference only                  1
  total                                    20

reused datasets:
  seed4 four Block 1 datasets               4
  seed5 four Block 0 datasets               4
  seed1 legacy reference                    1
  total                                     9

reused policies:
  seed5 four Stage 1b policies              4
  seed1 legacy reference                    1
  total                                     5
```

### 4.3 Frozen reuse evidence

Stage 1b analysis must remain unchanged:

```text
experiments/mvp0_position_event/confirmation_earlystop/analysis/comparison.json
SHA-256 0c17c65330b8ab25867e75b1409553e1ad2dfbb33ad52789acc586d1f7a9d1d1

experiments/mvp0_position_event/confirmation_earlystop/analysis/summary.md
SHA-256 c285ea524ac8ef795b073f6f2e54925745ae2e0ddef4a7238192407b7b6c1d29
```

Legacy `START25_APP6` seed-1 reference:

```text
raw:
dataset/ar_guidance_spatial_S15_S35/spatial_S25_d30_seed1/

HDF5:
dataset/ar_guidance_spatial_S15_S35/spatial_S25_d30_seed1_2gap.hdf5
SHA-256 2f2a3ed8c6b99e0dd83cdddd11d43a414bf38ed89b7128a63d30a7d7974877e5

checkpoint:
/scratch/prj/eng_demt_robot_learning/trained_models/
  ar_guidance_spatial_S15_S35/S25/spatial_S25_d30_seed1_2gap/
  20260704004132/models/model_epoch_80.pth
SHA-256 e666ab6a53f87f8d0f2e0a5ba29bd34b28cc39930d57cc848abfa5745465d60f
```

Stage 1b seed-5 policies are the four non-reference conditions in:

```text
experiments/mvp0_position_event/confirmation_earlystop/manifests/checkpoints.json
```

Their actual source seeds are collection `1701` and training `2701`.

Seed-4 datasets are the four Block 1 datasets in:

```text
experiments/mvp0_position_event/manifests/datasets.json
experiments/mvp0_position_event/manifests/paired_latents_b1.json
```

Their actual source collection seed is `1702`. Existing Block 1 epoch-40
policies are not valid primary Stage 2 policies. The four Block 1 HDF5 files
must be reused, but the policies must be retrained from scratch with the
Stage 1b early-stopping rule and actual training seed `2702`.

### 4.4 Reference pairing for reused slots

- `seed4/START25_APP6` must use actual collection seed `1702`, the exact
  accepted paired latent records reconstructed from old Block 1, and actual
  training seed `2702`.
- `seed5/START25_APP6` must use actual collection seed `1701`, the exact
  accepted paired latent records reconstructed from old Block 0, and actual
  training seed `2701`.
- `seed1` four new non-reference conditions must first attempt to use the
  exact 30 normalised latent records reconstructed from the legacy seed-1
  reference.
- `seed2` and `seed3` use new five-condition whole-repeat paired latent
  manifests.

Exact within-slot data pairing is mandatory for the primary comparison. If a
reused-slot reference latent has a persistent scientific failure, do not
replace a state for only one condition and do not admit an inexact slot to the
primary analysis. Rebuild that entire five-condition canonical slot in a new
namespace using the same actual source collection/training seeds and the
whole-slot rejection/replacement rule. This fallback sacrifices reuse for
that slot but preserves the strict comparison. Infrastructure failures may
retry the same latent without changing it.

## 5. Fixed task and learner protocol

Trajectory:

```text
Start -> Approach -> Descent -> Grasp -> Lift
```

Task semantics:

```text
base corridor start = (0.30, 0.00, 0.50)
Start offset plane  = XZ disk
Approach offset     = XY disk around pre-grasp
Descent target      = fixed
Grasp target        = fixed
Lift target         = fixed
success             = final cube z >= 0.20 m
```

Collection and learner:

```text
successful demonstrations per dataset = 30
sample_hz                            = 8
action_gap                           = 2
architecture/preprocessing          = accepted legacy S15-S35 learner
augmentation                        = accepted two-episode-per-demo procedure
train/valid masks                    = exact accepted 54/6 semantics
```

Training for every new policy:

```text
from scratch                         = true
max_epochs                           = 3000
validation early-stopping patience  = repository original 41
checkpoint interval                 = 20 epochs
selected checkpoint                 = highest numeric emitted model_epoch_*.pth
W&B project                          = TRO_MVP
```

Checkpoint selection occurs before any Stage 2 rollout outcome is inspected.
Warm starts, fixed epoch-40 selection and rollout-based checkpoint selection
are prohibited.

## 6. Formal rollout protocol

Formal rollout seeds:

```text
1, 2, 3, 4, 5
```

For each rollout seed:

```text
inner bank: 25 states in [0.00, 0.25] m
outer bank: 25 states in (0.25, 0.35] m
```

All 25 policies use the exact same state IDs, initial states, order, runtime
RNG and point-cloud RNG for every seed/bank/trial.

Fixed evaluation:

```text
horizon              = 200
sample_hz            = 8
action_gap           = 2
action_dt            = 0.25 s
num_points           = 10000
terminate_on_success = true
success              = final cube z >= 0.20 m
formal videos        = disabled
```

Required coverage:

```text
25 policies x 5 rollout seeds x (25 inner + 25 outer)
= 6,250 rollout rows

array task unit:
5 canonical seeds x 5 conditions x 5 rollout seeds x 2 banks
= 250 tasks, 25 rows per task
```

Rollout manifests `seed1` through `seed5` are new canonical shared artifacts.
They must be frozen before evaluation and registered for reuse by later
experiments with exactly identical task/evaluation semantics.

## 7. Pre-registered analysis

The independent learner unit is one dataset-policy slot. Individual rollout
rows and rollout seeds are nested deployment trials, not independent trained
policies.

Primary outcome:

```text
combined success rate over 250 rollouts per policy
```

Per canonical dataset-policy seed:

```text
D_candidate_reference =
  rate(START25_APP3P6) - rate(START25_APP6)

D_candidate_wide =
  rate(START25_APP3P6) - rate(START25_APP8P4)
```

Stage diagnostics:

```text
D_start_outer =
  outer_rate(START35_APP6) - outer_rate(START15_APP6)

D_approach_inner =
  inner_rate(START25_APP3P6) - inner_rate(START25_APP8P4)
```

Practical margin:

```text
delta_min = 0.05
```

A primary contrast passes only when:

1. its mean across the five dataset-policy slots is at least `+0.05`; and
2. it is positive in at least four of five slots.

Classification:

- `strong`: both primary contrasts pass and `START25_APP3P6` has the highest
  five-policy mean combined success.
- `partial`: at least one primary contrast passes, but the strong rule fails.
- `null/unstable`: neither primary contrast passes.

Report without substituting outcomes:

- each policy's successes/250;
- each policy's five rollout-seed rates and mean +/- sample standard deviation;
- each condition's five policy rates and mean +/- sample standard deviation;
- all four deltas for every canonical seed;
- inner, outer and combined rankings;
- paired success discordances;
- Wilson intervals as rollout-level descriptive intervals;
- policy-level cluster bootstrap with canonical seed as the top-level unit;
- checkpoint epoch and validation-loss histories;
- full five-slot result;
- fresh canonical seed1-3 sensitivity;
- reused alias seed4-5 sensitivity;
- an assertion that every primary canonical slot has exact accepted-latent
  pairing across all five conditions.

Do not change conditions, margins, outcomes or classification after seeing
results. Do not treat canonical aliases as literal RNG seeds.

## 8. Artifact layout

Small artifacts:

```text
experiments/tro_stage2_position_axial_replication/
  PLAN.md
  commands.md
  implementation_notes.md
  configs/
  manifests/
    protocol.json
    artifact_reuse.json
    datasets.json
    policies.json
    checkpoints.json
    jobs.json
    paired_latents/
    rollout_5seed/
  analysis/
    comparison.json
    summary.md
    figures/
```

New data and logs:

```text
dataset/tro_position_stage2_axial/
```

Large new models:

```text
/scratch/prj/eng_demt_robot_learning/trained_models/
  tro_position_stage2_axial/
```

Shared reuse registries:

```text
experiments/shared_artifacts/dataset_policy_registry.json
experiments/shared_artifacts/rollout_manifest_registry.json
```

Handoff:

```text
handoffs/tro-stage2-position-axial-replication.md
```

Existing large artifacts must be referenced by canonical path and hash rather
than copied into the new namespace.

## 9. Execution gates

### Gate 0: Freeze protocol and reuse audit

1. Preserve the dirty worktree and unrelated files.
2. Verify all frozen Stage 1b and legacy reference hashes.
3. Audit the eight reusable Block 0/1 datasets, four reusable Stage 1b
   policies and one reusable legacy reference policy.
4. Write `protocol.json`, `artifact_reuse.json` and tests before new jobs.
5. Freeze canonical/source seed mappings and expected coverage.

Pass: every reused artifact is hash-addressed and no historical provenance is
rewritten.

### Gate 1: Implement profiles, manifests and tests

1. Add a new Stage 2 experiment profile without changing old Stage 1/1b maps.
2. Reconstruct accepted latent records for legacy seed1, Block 1 and Block 0.
3. Generate new paired manifests for canonical seeds 2 and 3.
4. Generate new rollout manifests for seeds 1 through 5.
5. Add strict tests for conditions, radii, seeds, reuse and coverage.

Pass: all tests succeed and manifests are frozen before formal outcomes.

### Gate 2: Smoke

Use a separate smoke namespace. Validate 2-3 demonstrations per new
condition/seed class, exact trajectory phases, 8 Hz sampling and latent
mapping. Smoke artifacts never enter formal HDF5 or analysis.

### Gate 3: Formal data

Collect exactly the 16 new datasets specified in Section 4.2. Reuse the other
nine by manifest reference. Strictly validate all 25 dataset slots.

Pass: 16 new datasets each have 30 successes; all 25 slots have valid
provenance and expected pairing status.

### Gate 4: HDF5 and training configs

Create 16 new HDF5 files, reuse nine existing files and validate all 25
dataset slots. Create configs for exactly 20 new policy runs.

Pass: HDF5 counts, masks, hashes and configs are frozen.

### Gate 5: Training and checkpoint freeze

Train exactly 20 new early-stopped policies. Reuse five existing policies.
After all training terminates, select the highest numeric emitted checkpoint
for each new run and freeze all 25 checkpoint hashes before rollout.

Pass: exactly 25 valid policy slots and no mixed epoch-40 primary policy.

### Gate 6: Formal rollouts

Run 250 policy/rollout-seed/bank tasks, each with 25 trials. Monitor through
terminal states and retry only infrastructure failures.

### Gate 7: Strict merge and analysis

Validate exactly 250/250 tasks and 6,250/6,250 rows. Produce the frozen
analysis, classification, figures, commands, job ledger and final hashes.

### Gate 8: Handoff and stop

Update the Stage 2 handoff and `docs/tro_plan.md`. Stop without launching
composition conditions, Stage 3, Rotation, Velocity, AR or human experiments.

## 10. Slurm and infrastructure policy

- Use `sbatch --parsable` and record every job ID/dependency in `jobs.json`.
- Monitor with `squeue`, `sacct` and logs until the full chain is terminal.
- Do not stop after job submission.
- Cleanly retry `PREEMPTED`, `TIMEOUT`, GPU ECC, node failure or other
  infrastructure-only failures.
- Never retry because a policy or condition performs poorly.
- Archive stale/partial attempts under this Stage 2 namespace and exclude them
  from formal merge.
- Existing frozen environment is incompatible with RTX PRO 6000 Blackwell
  `sm_120`; use supported A100/L40S/H100/H200-class constraints and avoid known
  faulty nodes.
- Scheduler settings, walltime and concurrency may change; scientific settings
  may not.

## 11. Storage policy

- Do not copy reused raw data, HDF5 or model checkpoints.
- Use manifest references or symlinks with hashes.
- Disable formal rollout videos.
- Register reusable rollout manifests and policy artifacts.
- Do not delete old or intermediate artifacts automatically.
- At completion, report a storage inventory and safe cleanup candidates for
  separate user approval.

## 12. Safety and authority

The executing agent is authorised to implement this Stage 2 scope, collect the
16 new datasets, train the 20 new policies, run 6,250 rollouts, submit and
monitor Slurm jobs, and safely retry infrastructure failures.

The agent is not authorised to:

- modify or delete frozen Stage 1/1b/legacy artifacts;
- reinterpret `1701` and `2701` as two independent repeats;
- use old fixed epoch-40 Block 1 policies in the primary comparison;
- change conditions, seeds, learner, data budget, checkpoint rule, rollout
  banks or decision thresholds after seeing outcomes;
- commit, push or open a PR;
- launch any later research stage.

## 13. Definition of Done

- [ ] Stage 1b and legacy reference hashes are unchanged.
- [ ] Protocol, reuse map, tests and canonical/source seeds are frozen.
- [ ] 25/25 dataset slots validate: 16 new and 9 reused.
- [ ] 25/25 policy slots validate: 20 new and 5 reused.
- [ ] All selected checkpoints are frozen before rollout.
- [ ] 250/250 rollout tasks complete.
- [ ] 6,250/6,250 rollout rows strictly validate.
- [ ] Primary and sensitivity analyses follow Section 7 exactly.
- [ ] Final classification, figures, commands, jobs and hashes are written.
- [ ] Shared artifact registries are updated without duplicating large files.
- [ ] The handoff is updated.
- [ ] No out-of-scope experiment is launched.
