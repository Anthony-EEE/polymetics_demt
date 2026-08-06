# Execution Plan: T-RO Stage 1 Position MVP

**Mode:** Codex YOLO/autonomous execution
**Branch baseline:** `hpc-headless-tro @ 2f61da7`
**Status:** Stage 1 complete after the user-authorised five-seed rollout
correction; final classification `null/unstable`
**Scope:** Stage 1 only. Do not execute Stage 2, cross-task modelling, Rotation,
Velocity, AR guidance or human studies.

## User-authorised rollout correction (2026-07-24)

This correction supersedes the original single-seed Gate 5–7 rollout evidence
for final comparison, but does not recollect demonstrations or retrain any
policy.

- Inspect the existing eight policy directories before evaluation.
- For each policy, select the checkpoint with the highest numeric
  `model_epoch_*.pth` suffix already present in its sole training run.
- Use the same five seeds for all eight policies: `628`, `629`, `630`, `631`
  and `632`.
- For every seed and policy, run 25 inner states in `[0.00, 0.25] m` and 25
  outer states in `(0.25, 0.35] m`.
- Required corrected coverage is therefore 250 rollouts per policy and 2,000
  rollouts total.
- Preserve the original epoch-40 rollout artifacts for provenance, but mark
  their policy comparison and conclusion as superseded after the corrected
  evaluation passes strict validation.

Completed corrected coverage:

```text
8 existing policies × 5 shared seeds × (25 inner + 25 outer) = 2,000 rollouts
strict validation: passed
corrected classification: null/unstable
```

## 1. Objective

Keep the accepted PyBullet grasping trajectory unchanged:

```text
Start → Approach → Descent → Grasp → Lift
```

The old S15–S35 sweep changed Start radius and Approach/pre-grasp radius
together. The new experiment changes only one radius at a time to answer:

1. Does wider Start variation improve outer-start coverage?
2. Does tighter Approach variation improve grasp/lift success?
3. Do Start and Approach variations have different deployment effects?

This is a low-cost mechanism screen. Stop if the first block has no
pre-registered directional signal.

## 2. Existing semantics that must not change

The accepted generator is `examples/main_abla_1.py`.

```text
base corridor start = (0.30, 0.00, 0.50)
corridor_start = base corridor start + XZ disk sample
base pre_grasp = (cube_x, cube_y, 0.22)
pre_grasp = base pre_grasp + XY disk sample
grasp = (cube_x, cube_y, 0.04)
lift = (cube_x, cube_y, 0.30)
success = final cube z >= 0.20 m
```

Execution remains:

```text
reset robot to corridor_start
save corridor_start
open gripper
move to pre_grasp
descend to fixed grasp
close gripper
move to fixed lift
check success
```

Do not add geometric event boundaries, contact state machines, mid-episode
perturbations, subepisodes, learned phase segmentation or new grasp targets.

## 3. Reused legacy evidence

The closed S15–S35 experiment is immutable. Reuse its artifacts read-only.

Legacy formal root:

```text
dataset/ar_guidance_spatial_S15_S35/
  policy_rollouts_seed628_shared_r35_paired_n50_h200/
```

Frozen legacy provenance:

```text
summary_seed628_n50.json SHA-256:
ec9c95ba26e3a4b9f18ae7c34966a8d55dc3acca2af10c18bdbc43d12c827d78

shared_start_manifest_seed628_n50_r35.json SHA-256:
84316b36922ea71225615d285bffccdfef4b99289650e302c963deb761f516ce

S25 epoch-80 checkpoint SHA-256:
e666ab6a53f87f8d0f2e0a5ba29bd34b28cc39930d57cc848abfa5745465d60f
```

### Historical S25 reference

Old S25 is exactly:

```text
Start radius = 0.25 m
Approach radius = 0.060 m
30 successful demonstrations
50 frozen shared-state rollouts
success = 18/50
```

Reuse it as a historical reference only. Do not recollect or retrain S25.
Because its old checkpoint is epoch 80 and its demonstrations are not paired
with the new blocks, do not use it as an independent new replicate or in the
primary Start/Approach contrasts.

### Historical coupled diagonal

The legacy results may be reported as secondary context:

| Legacy condition | Bank A, 0–25 cm | Bank B, 25–35 cm |
|---|---:|---:|
| S15 `(15 cm, 3.6 cm)` | 14/25 | 4/25 |
| S25 `(25 cm, 6.0 cm)` | 8/25 | 10/25 |
| S35 `(35 cm, 8.4 cm)` | 5/25 | 2/25 |

Do not relabel S15 or S35 as a new single-stage condition. Both radii changed,
and their old normalized demonstration samples are not paired across
conditions.

## 4. New conditions

Create only these four new conditions:

| Condition ID | Start radius | Approach radius | Meaning |
|---|---:|---:|---|
| `START15_APP6` | 0.15 m | 0.060 m | Start-tight |
| `START35_APP6` | 0.35 m | 0.060 m | Start-wide |
| `START25_APP3P6` | 0.25 m | 0.036 m | Approach-tight |
| `START25_APP8P4` | 0.25 m | 0.084 m | Approach-wide |

All other task and generator parameters must match legacy S25.

The values preserve the old S15/S25/S35 levels:

```text
tight = 0.6 × reference
wide  = 1.4 × reference
```

Start and Approach are offsets in different planes. No numerical ordering such
as `Approach <= Start` is required.

## 5. Sequential experimental design

### Mandatory Block 0

```text
4 new conditions
30 successful demonstrations per condition
4 datasets
4 independently trained policies
50 shared-state rollouts per policy
200 new rollouts
```

### Conditional Block 1

Run only if Block 0 meets the pre-registered continuation rule in Section 9.

```text
4 new conditions
new collection seed
new training seed
30 successful demonstrations per condition
4 new datasets and policies
200 additional rollouts
```

Maximum new work:

```text
8 datasets/policies
240 successful demonstrations
400 new rollouts
```

The dataset-policy block is the independent learner replicate. Individual
rollouts are paired deployment trials, not independent policy replicates.

Within each block:

- all four conditions use the same normalized Start samples;
- all four conditions use the same normalized Approach samples;
- all policies use the same block training seed and protocol;
- only the configured Start or Approach radius changes.

Block 1 uses different collection and training seeds from Block 0.

## 6. Paired demonstration sampling

Before collecting a block, freeze a manifest with at least 30 accepted
canonical samples plus replacements.

For each candidate save:

```text
candidate_index
start_angle
start_radial_quantile
approach_angle
approach_radial_quantile
collection/runtime seed
```

For uniform disk sampling:

```text
realised radial fraction = sqrt(radial_quantile)
offset radius = realised radial fraction × condition radius
```

The four conditions must have identical candidate indices, directions and
relative radial fractions.

If a candidate is unreachable or unsuccessful in any condition:

1. record the condition and failure reason;
2. reject that candidate for the entire block;
3. advance all four conditions to the same replacement candidate.

Do not let one condition advance its RNG independently.

## 7. Reused evaluation banks

Do not generate new evaluation states. Derive two read-only child manifests
from the frozen legacy 50-state manifest using only
`radial_distance_from_center`.

### Bank A: reference range

```text
ID: legacy_seed628_reference_r00_r25_n25_v1
range: 0.00–0.25 m, inclusive
states: 25
legacy rollout indices:
[0, 1, 2, 3, 9, 12, 13, 14, 16, 17, 18, 20, 21, 27, 29, 33, 34,
 35, 37, 40, 41, 42, 45, 46, 48]
```

### Bank B: outer range

```text
ID: legacy_seed628_outer_r25_r35_n25_v1
range: greater than 0.25 m and at most 0.35 m
states: 25
legacy rollout indices:
[4, 5, 6, 7, 8, 10, 11, 15, 19, 22, 23, 24, 25, 26, 28, 30, 31,
 32, 36, 38, 39, 43, 44, 47, 49]
```

For each child manifest:

- copy the exact legacy state records and preserve their order;
- record the parent path and parent SHA-256;
- record the deterministic radius predicate;
- calculate and store the child SHA-256;
- never modify the parent manifest;
- use the exact same state IDs for every new policy.

Evaluation protocol remains:

```text
horizon = 200
sample_hz = 8
action_gap = 2
action_dt = 0.25 s
terminate_on_success = true
success = final cube z >= 0.20 m
```

## 8. Fixed learner and training rule

All new policies must use:

```text
legacy S15–S35 learner architecture and preprocessing
30 demonstrations
training seed fixed within block
40 training epochs
checkpoint = model_epoch_40.pth
```

Disable or configure early stopping so every valid new run reaches epoch 40.
Do not choose checkpoints using validation or rollout outcomes. Block 1 must
use the same 40-epoch rule.

The reused historical S25 epoch-80 checkpoint remains descriptive and is not
an apples-to-apples primary comparator.

## 9. Comparisons and pre-registered continuation rule

Report successes/25 and paired success discordances.

Primary Start contrast on Bank B:

```text
delta_start_outer =
success(START35_APP6) - success(START15_APP6)
```

Secondary Start contrast on Bank A:

```text
delta_start_reference =
success(START35_APP6) - success(START15_APP6)
```

Primary Approach contrast on Bank A:

```text
delta_approach_reference =
success(START25_APP3P6) - success(START25_APP8P4)
```

Secondary Approach contrast on Bank B:

```text
delta_approach_outer =
success(START25_APP3P6) - success(START25_APP8P4)
```

### Decision after Block 0

First validate all datasets, checkpoints and rollout pairing. Invalid or
incomplete artifacts are infrastructure failures and must be repaired without
changing scientific settings.

Run Block 1 only if at least one primary contrast reaches the predicted
directional threshold:

```text
delta_start_outer >= 4/25 = 0.16
OR
delta_approach_reference >= 4/25 = 0.16
```

If neither reaches `0.16`, write a futility/null Stage 1 report and stop. Do
not collect or train Block 1.

### Decision after Block 1

A contrast is replicated directional evidence only when:

- it is positive in both blocks; and
- its mean across blocks is at least `0.15`.

Classify:

- **strong:** both primary contrasts replicate;
- **partial:** exactly one primary contrast replicates;
- **null/unstable:** neither replicates or block directions conflict.

This is sequential engineering screening, not a formal significance test.
Report the stopping rule, Wilson intervals and paired discordances
descriptively. Preserve null and mixed results.

Do not launch Stage 2 automatically under any classification.

## 10. Required artifacts

Small artifacts:

```text
experiments/mvp0_position_event/
  PLAN.md
  implementation_notes.md
  commands.md
  configs/
    conditions.yaml
    blocks.yaml
    training.yaml
  manifests/
    legacy_evidence.json
    legacy_seed628_reference_r00_r25_n25_v1.json
    legacy_seed628_outer_r25_r35_n25_v1.json
    paired_latents_b0.json
    paired_latents_b1.json              # only if continuation passes
    datasets.json
    policies.json
    checkpoints.json
  analysis/
    block0_screening.json
    summary.md
    screening_decision.json
    figures/
```

New large outputs:

```text
/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/tro_position_mvp0/
/scratch/prj/eng_demt_robot_learning/trained_models/tro_position_mvp0/
```

Never write under the closed
`dataset/ar_guidance_spatial_S15_S35/` formal result directories.

Every dataset manifest records condition, block, seeds, canonical candidate
IDs, radii, failures/replacements, raw/HDF5 paths and hashes.

Every policy manifest records condition, block, seed, config, epoch-40
checkpoint path/hash and git commit.

Every rollout row records condition, block, bank/state ID, checkpoint hash,
success, final cube z and steps/time to success.

## 11. Gate-by-gate YOLO execution

Proceed autonomously through each gate. Do not start a later gate until the
current gate passes.

### Gate 0: Freeze legacy reuse and implementation notes

1. Preserve unrelated working-tree files.
2. Verify all three legacy hashes in Section 3.
3. Recompute the two 25-state radius splits and assert the exact indices in
   Section 7.
4. Create child manifests without modifying the legacy root.
5. Audit the minimal collection, HDF5, training and evaluation changes.
6. Write `implementation_notes.md` and `manifests/legacy_evidence.json`.

Pass: legacy provenance is verified, child banks are frozen and no closed
artifact can be overwritten.

### Gate 1: Four conditions and paired latents

1. Add the four new condition IDs without changing trajectory semantics.
2. Implement Block 0 paired latent sampling.
3. Update validation for the four conditions.
4. Add tests for exact radii, uniform-disk mapping and cross-condition pairing.

Pass: the same candidate has equal normalized direction/fraction in all four
conditions.

### Gate 2: Smoke collection

1. Collect 2–3 Block 0 demonstrations per condition.
2. Confirm all original phases remain.
3. Verify sampled offsets and pairing.
4. Verify fixed Descent/Grasp/Lift targets and S25 task geometry.

Pass: all four conditions produce successful demonstrations and only the
intended radius changes.

### Gate 3: Block 0 datasets

1. Collect 4 × 30 successful demonstrations.
2. Validate pairing and rejection handling.
3. Convert to HDF5 and record hashes.
4. Generate configs from one frozen learner template.

Pass: four valid paired datasets/HDF5 files exist with no
condition-specific missing candidates.

### Gate 4: Block 0 training

1. Train all four policies for exactly 40 epochs.
2. Reject silent resume/reuse or early termination.
3. Freeze each epoch-40 checkpoint and SHA-256.

Pass: four traceable epoch-40 policies exist.

### Gate 5: Block 0 evaluation

1. Run all four policies on both 25-state child banks.
2. Preserve per-rollout JSON.
3. Strictly validate condition/block/bank/state/checkpoint coverage.
4. Produce `analysis/block0_screening.json`.

Pass: exactly 200 complete new rollout rows exist.

### Gate 6: Apply the sequential rule

1. Compute the two primary Block 0 contrasts.
2. Record whether either is at least `4/25`.
3. If neither passes, skip Block 1 and proceed to Gate 7.
4. If either passes, create a new paired latent manifest and complete Block 1:
   - four new 30-demo datasets;
   - four new epoch-40 policies;
   - 200 rollouts on the same child banks.
5. Do not alter conditions, thresholds, banks or training protocol.

Pass when either:

- a valid pre-registered futility stop is recorded; or
- Block 1 has four valid datasets/policies and 200 complete rollout rows.

### Gate 7: Final analysis and stop

1. Report all four contrasts by block.
2. Include the reused S25 and coupled S15/S35 rows as clearly labelled
   historical context.
3. Report Wilson intervals and paired success discordances descriptively.
4. Plot sampled Start/Approach offsets and success by bank.
5. Write `analysis/summary.md` and `screening_decision.json`.
6. Update `handoffs/tro-mvp0-position-event.md`.
7. Stop without launching Stage 2.

Pass: the sequential decision and all limitations are auditable.

## 12. YOLO authority and safety

The executing agent is authorised to:

- implement Stage 1 code/config/tests;
- create new Stage 1 artifacts under the new roots;
- submit, monitor and safely retry Stage 1 Slurm jobs;
- execute mandatory Block 0;
- execute Block 1 only when the exact Gate 6 rule passes;
- analyse results and update the handoff.

The agent must:

- preserve unrelated untracked files `[`, `count=0`, `done`, `fi`;
- keep the legacy S15–S35 tree read-only;
- use `apply_patch` for repository edits;
- retry infrastructure failures without changing scientific settings;
- stop and ask if an action would expand scope, overwrite material data or
  require a scientific choice not resolved here.

The agent is not authorised to:

- commit, push or open a PR unless separately requested;
- delete or modify legacy artifacts;
- train a new Reference/S25 policy;
- change radii, thresholds, banks, 40-epoch rule or success criterion after
  seeing results;
- execute Stage 2 or any Rotation, Velocity, AR or human experiment.

## 13. Definition of Done

Stage 1 is complete only when:

- [ ] legacy hashes and two 25-state child banks are verified;
- [ ] four new conditions are config-driven and tested;
- [ ] trajectory remains `Start → Approach → Descent → Grasp → Lift`;
- [ ] Block 0 has four paired 30-demo datasets and four epoch-40 policies;
- [ ] Block 0 has exactly 200 valid rollout rows;
- [ ] the continuation rule is recorded exactly;
- [ ] Block 1 is either correctly skipped or fully completed;
- [ ] historical evidence is clearly separated from new primary evidence;
- [ ] `summary.md` and `screening_decision.json` exist;
- [ ] the handoff is updated;
- [ ] the agent stops without starting Stage 2.
