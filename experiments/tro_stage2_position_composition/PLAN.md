# Execution Plan: T-RO Stage 2c Position Composition

**Date:** 2026-07-27  
**Branch baseline:** `hpc-headless-tro @ 2f61da7`  
**Protocol ID:** `tro_stage2_position_composition_missing_cells_v3_continue_candidate_stream_until_30_successes`  
**Status:** **Complete under user-authorised Protocol v3 (2026-07-27).**
All Gates 0--8 and every Definition of Done item passed. The final experiment
contains 20 new exact-30 datasets, 20 validated HDF5 files, 20 from-scratch
policies, a pre-rollout 45-slot checkpoint freeze, 400/400 new formal tasks
and 10,000/10,000 new rows. Both 45-policy surfaces strictly validate at
11,250 rows. The frozen classification is `interaction`. Protocol v1/v2
failures, blockers, progress and hashes remain immutable historical evidence.  
**Scope:** Position-only completion of the four missing cells in the existing
Start x Approach factorial. No additional radius search is authorised.

## 1. Authority, objective and stage gate

This PLAN is the sole execution authority for the Position composition
experiment that follows the completed Stage 2 axial replication and its
condition-relative ID/OOD rerollout.

The completed work established:

- a reproducible penalty for widening Approach support from `0.060 m` to
  `0.084 m`;
- equal mean ID performance and a mean OOD advantage for `APP6` relative to
  `APP3P6` at `START25`, with substantial policy-level uncertainty;
- a Start coverage trade-off between condition-relative ID and OOD;
- a valid scientific reason to test composition, without upgrading the
  completed Stage 2 classification from `partial` to `strong`.

The user approved a `GO-to-composition` stage gate on 2026-07-26. The gate
authorises completion of the missing factorial cells; it does not authorise
Rotation, Velocity, a cross-task model, AR guidance or a human study.

The experiment asks:

> Does the deployment effect of Approach variation depend on the Start
> training-support radius, or are the observed Start and Approach effects
> approximately separable over the tested grid?

This is an interaction/response-surface experiment, not a search for a
post-hoc winning radius.

## 2. Frozen inputs

The completed Stage 2 axial experiment is immutable:

```text
experiments/tro_stage2_position_axial_replication/
```

Freeze and revalidate before any new job:

```text
checkpoint manifest:
  experiments/tro_stage2_position_axial_replication/manifests/checkpoints.json
  SHA-256:
  240a936999281f429dd1b043b19df5bd9291ed478933305a7c051c5183227580

comparison:
  experiments/tro_stage2_position_axial_replication/analysis/comparison.json
  SHA-256:
  c70020fe70ab5aae9959ea990e66a2e2f3c4af4c05f24557a79d64c973ef9113

summary:
  experiments/tro_stage2_position_axial_replication/analysis/summary.md
  SHA-256:
  825a13e358b01e8707c99e1f19673b01d46df62edbacecce12bff6bbc6684370
```

The completed active ID/OOD rerollout is also immutable:

```text
experiments/tro_stage2_position_axial_idood_rerollout/

active protocol:
  tro_stage2_position_axial_condition_relative_idood_rerollout_rmax40_v2

comparison SHA-256:
  ae30a6133436654d6adee85dae14b8db490718df65a5e526638a68f75e3a2353

summary SHA-256:
  5d495bc11fc7a0ee1f4f912b816d3d143578f2bd38ce3caa50718d144ee73528

sorted active rollout-manifest hash-list SHA-256:
  d5de69778f91afad8cf49580b69aca2aa6bd19e3252c5635783cb9d1268a5953
```

Do not recollect, retrain, overwrite, relabel or selectively exclude any of
the 25 axial dataset-policy slots. Existing rollout rows are reused by
reference and are never copied into the new raw namespace.

## 3. Factorial conditions

The complete frozen grid is:

| Start support | `APP3P6` 0.036 m | `APP6` 0.060 m | `APP8P4` 0.084 m |
|---|---|---|---|
| `START15` 0.15 m | **new** `START15_APP3P6` | reuse `START15_APP6` | **new** `START15_APP8P4` |
| `START25` 0.25 m | reuse `START25_APP3P6` | reuse `START25_APP6` | reuse `START25_APP8P4` |
| `START35` 0.35 m | **new** `START35_APP3P6` | reuse `START35_APP6` | **new** `START35_APP8P4` |

Condition order is frozen row-major:

```text
START15_APP3P6
START15_APP6
START15_APP8P4
START25_APP3P6
START25_APP6
START25_APP8P4
START35_APP3P6
START35_APP6
START35_APP8P4
```

No `APP4P8`, additional Start radius, asymmetric distribution, corner
perturbation, contact perturbation or adaptive radius selection is in scope.

## 4. Canonical repeats, exact pairing and new work

Canonical/source seeds remain:

| Canonical seed | Source collection seed | Source training seed |
|---:|---:|---:|
| 1 | 1 | 1 |
| 2 | 2 | 2 |
| 3 | 3 | 3 |
| 4 | 1702 | 2702 |
| 5 | 1701 | 2701 |

For every canonical seed, use the exact final active Stage 2 paired-latent
manifest as the frozen source of the deterministic candidate stream:

```text
experiments/tro_stage2_position_axial_replication/manifests/paired_latents/
```

Seeds 1 and 5 must use their active whole-slot fallback manifests recorded in
`fallback_activations.json`, not the rejected pre-fallback candidates.

Before collection, audit the original 30 records for all four new conditions.
The Start XZ offset and Approach XY offset must be reconstructed from the same
normalised latent values used by the five axial anchors. If an original
candidate fails dynamically, Protocol v3 continues the same frozen PCG64
draw order at candidate 31, 32, 33, and so on; it does not add an accepted
row or change the final sample size.

Pairing is a hard gate:

- do not replace a latent for only a new condition;
- do not generate a separate or outcome-adaptive four-corner latent stream;
- do not rebuild any old axial dataset to rescue a corner;
- do not silently reduce the demonstration count or analyse an unpaired
  subset;
- accept candidates strictly in deterministic stream order until exactly 30
  candidates have succeeded per canonical seed;
- if any corner fails, archive that candidate's entire four-corner bundle,
  accept none of it, and advance to the next deterministic candidate;
- use the same candidate and runtime seed for all four new corners;
- cleanly retry the identical candidate only after an infrastructure
  interruption, without advancing the stream.

Protocol v3 was explicitly authorised by the user on 2026-07-26 after the v2
runtime-seed audit proved that repeated attempt seeds had no causal route to
the fixed simulator physics. It is a deterministic candidate-stream
continuation rule, not an accepted-sample-size expansion: every final dataset
still contains exactly 30 rows. Original-stream accepted candidates preserve
normalised-latent pairing to the old anchors. Replacement candidates beyond
the original 30 are paired exactly across the four new corners only and must
not be represented as paired to the immutable old anchors. All failed
candidates remain audit evidence and never enter HDF5, training or analysis.

New work:

```text
4 missing conditions x 5 dataset-policy seeds = 20 new datasets
20 datasets x 30 successful demonstrations   = 600 new demonstrations
20 new datasets                              = 20 new HDF5 files
20 new datasets                              = 20 new policies
```

Final response surface:

```text
9 conditions x 5 dataset-policy seeds = 45 policy slots
25 immutable axial anchors + 20 new corner policies
```

Every manifest row must preserve:

```text
canonical_seed
source_collection_seed
source_training_seed
condition
start_support_radius_m
approach_radius_m
paired_latent_manifest_path
paired_latent_manifest_sha256
reused_dataset
reused_policy
source_artifact_path
source_artifact_sha256
```

## 5. Fixed task, data and learner protocol

Trajectory and semantics remain:

```text
Start -> Approach -> Descent -> Grasp -> Lift

base corridor start = (0.30, 0.00, 0.50)
Start offset plane  = XZ disk
Approach offset     = XY disk around pre-grasp
Descent target      = fixed
Grasp target        = fixed
Lift target         = fixed
success             = final cube z >= 0.20 m
```

Collection:

```text
successful demonstrations per dataset = 30
sample_hz                            = 8
action_gap                           = 2
candidate order                      = frozen deterministic PCG64 stream
accepted order                       = successful candidates in stream order
accepted unit                        = one atomic four-corner success bundle
scientific candidate limit           = none; continue stream to 30 successes
```

For each canonical seed, execute candidate bundles in monotonically increasing
`candidate_index` order:

1. candidates 0--29 are the frozen active Stage 2 records;
2. later candidates are generated by continuing the same source seed, NumPy
   PCG64 generator and exact draw order frozen in
   `manifests/candidate_stream_v3.json`;
3. one candidate's frozen runtime seed is used for all four new corners;
4. if all four corners succeed, atomically accept the four trajectories;
5. if any corner fails, accept none, archive all attempted corner results and
   advance to the next candidate;
6. an infrastructure interruption resumes or cleanly retries the identical
   candidate without advancing, skipping or duplicating an accepted bundle;
7. stop only when the seed has exactly 30 accepted bundles.

The superseded v2 rule and its deterministic
`uint32_be(SHA256("composition-v2:{base_runtime_seed}:{attempt_index}")[0:4])`
derivation remain frozen historical evidence in `manifests/protocol_v2.json`.
They are not used to generate the final v3 datasets. Candidate generation
must not depend on condition outcome, wall-clock time, scheduler job ID or
host.

Learner:

```text
from scratch                         = true
architecture/preprocessing          = frozen Stage 2 learner
augmentation                        = accepted two-episode-per-demo procedure
train/valid masks                    = exact accepted 54/6 semantics
max_epochs                           = 3000
validation early-stopping patience  = repository original 41
checkpoint interval                 = 20 epochs
selected checkpoint                 = highest numeric emitted model_epoch_*.pth
W&B project                          = TRO_MVP
```

Checkpoint selection and hashes must be frozen before any new formal rollout
outcome is inspected. Warm starts, rollout-based checkpoint selection and
condition-specific training changes are prohibited.

## 6. Formal evaluation protocols

Two frozen evaluation views are required. They answer different questions
and must not be pooled as if they were independent trials.

### 6.1 Primary: common absolute deployment distribution

Reuse the ten original Stage 2 rollout manifests:

```text
experiments/tro_stage2_position_axial_replication/manifests/rollout_5seed/
```

For each rollout seed:

```text
common inner bank: 25 states in [0.00, 0.25] m
common outer bank: 25 states in (0.25, 0.35] m
```

All nine conditions therefore face the same absolute states, order, runtime
RNG and point-cloud RNG. This common distribution is the sole primary basis
for Start x Approach interaction contrasts.

Coverage:

```text
existing anchors: 25 policies x 5 rollout seeds x 2 banks x 25 = 6,250 rows
new corners:      20 policies x 5 rollout seeds x 2 banks x 25 = 5,000 rows
full grid:        45 policies x 5 rollout seeds x 2 banks x 25 = 11,250 rows

new array tasks = 20 x 5 x 2 = 200
```

### 6.2 Secondary: condition-relative ID/OOD at RMAX40

Reuse the active Start-family manifests:

```text
experiments/tro_stage2_position_axial_idood_rerollout/
  manifests/rollout_5seed_rmax40/
```

Each new corner uses the exact manifest of its Start family:

| Start family | ID | OOD |
|---|---|---|
| `START15` | `[0.00, 0.15]` m | `(0.15, 0.40]` m |
| `START35` | `[0.00, 0.35]` m | `(0.35, 0.40]` m |

Coverage is another 5,000 new rows and 200 new tasks. Same-Start conditions
use identical absolute states. Cross-Start summaries are condition-relative
and may be compared as a two-dimensional ID/OOD trade-off, but their balanced
scores do not represent one common absolute deployment distribution.

### 6.3 Shared rollout settings

```text
rollout seeds       = 1, 2, 3, 4, 5
horizon             = 200
sample_hz           = 8
action_gap          = 2
action_dt           = 0.25 s
num_points          = 10000
terminate_on_success = true
success             = final cube z >= 0.20 m
formal videos       = disabled
```

Total authorised new formal rollout work:

```text
400 tasks
10,000 rows
```

## 7. Pre-registered primary analysis

The independent learner unit is one canonical dataset-policy seed. Rollout
seeds and individual rollout rows are nested deployment trials.

For canonical seed `k`, let

```text
r_k(S, A)
```

be combined success over the 250 common-absolute rollout rows for Start level
`S` and Approach level `A`.

Within each Start row:

```text
T_k(S) = r_k(S, APP3P6) - r_k(S, APP6)
W_k(S) = r_k(S, APP8P4) - r_k(S, APP6)
```

The four primary difference-in-differences interaction contrasts are:

```text
I_tight_15_k = T_k(START15) - T_k(START25)
I_tight_35_k = T_k(START35) - T_k(START25)
I_wide_15_k  = W_k(START15) - W_k(START25)
I_wide_35_k  = W_k(START35) - W_k(START25)
```

These four contrasts are frozen before new outcomes. Do not select a
different baseline or report only the most favourable interaction.

For each contrast report:

- all five canonical-seed values;
- mean and sample standard deviation across the five policy seeds;
- canonical-seed cluster bootstrap percentile interval;
- sign consistency;
- common-inner and common-outer decomposition;
- exact paired success discordances.

Use the existing practical effect margin:

```text
delta_interaction = 0.05
```

A contrast has a reproducible interaction signal only when:

1. `abs(mean contrast) >= 0.05`; and
2. at least four of five canonical-seed contrasts have the same non-zero sign
   as the mean.

Experiment-level classification:

- `interaction`: at least one of the four frozen contrasts meets both rules;
- `no reproducible interaction`: none meets both rules.

The latter does not prove exact additivity or equivalence. The classification
does not depend on which individual condition ranks first.

Also report, without replacing the primary analysis:

- the full 9 x 5 policy-rate matrix on the common deployment distribution;
- within-row Approach contrasts and rankings;
- within-column Start contrasts and rankings;
- categorical Start, Approach and Start x Approach effect estimates as a
  descriptive model;
- condition-relative ID/OOD rates, gaps and Pareto front;
- policy-level variance and seed1-3 versus alias4-5 sensitivity;
- checkpoint epochs and validation-loss histories;
- Wilson intervals only as rollout-level descriptions;
- feasibility, pairing, manifest and RNG audits.

No individual rollout row, rollout seed or evaluation protocol may be treated
as an independently trained policy.

## 8. Artifact layout

Small artifacts:

```text
experiments/tro_stage2_position_composition/
  PLAN.md
  commands.md
  implementation_notes.md
  configs/
  manifests/
    protocol.json
    protocol_v2.json
    protocol_amendment_v2.json
    anchor_reuse.json
    feasibility_audit.json
    datasets.json
    policies.json
    checkpoints.json
    jobs.json
    common_absolute_rollout_reuse.json
    rmax40_rollout_reuse.json
  analysis/
    comparison.json
    summary.md
    figures/
```

New data:

```text
dataset/tro_position_stage2_composition/
```

New models:

```text
/scratch/prj/eng_demt_robot_learning/trained_models/
  tro_position_stage2_composition/
```

Handoff:

```text
handoffs/tro-stage2-position-composition.md
```

Large reused artifacts remain at their canonical paths and are referenced by
path and SHA-256.

## 9. Execution gates

### Execution record and v2 amendment (2026-07-26)

- Gate 0 passed: all five frozen top-level hashes, 25 checkpoint hashes and
  25 anchor HDF5 hashes were revalidated.
- Gate 1 passed: 600/600 prospective corner-latent records linked exactly to
  their five axial anchors and passed waypoint IK reachability.
- Gate 2 passed: 38 relevant tests passed; Slurm smoke array `36053326`
  completed 5/5 across all four new corners.
- Gate 3 v1 stopped. Formal collection array `36053381` recorded:
  - canonical seed 4, demo index 2, frozen candidate 4,
    `START35_APP8P4`, final cube z `0.03498996287124328 m`;
  - canonical seed 5, demo index 1, frozen candidate 1,
    `START35_APP8P4`, final cube z `0.03498985718810666 m`.
- Both were failed simulator attempts on frozen inputs, not infrastructure
  failures. The remaining seed1-3 tasks were cancelled immediately. There
  were no retries under v1. Partial rows are excluded from training and
  analysis.
- The user completed protocol review on 2026-07-26 and explicitly authorised
  v2 retry-until-success. The two failures remain immutable v1 attempt-0
  evidence; they are no longer terminal protocol blockers.
- The pre-resume requirement was to patch and test the collector's atomic
  four-corner attempt loop, freeze `protocol_v2.json`, and migrate progress
  without deleting or rewriting v1 evidence. Fully accepted four-corner
  bundles could be retained; incomplete/interrupted bundles and bundles
  containing a failed corner had to be archived and retried.
- The v2 implementation gate passed: 43/43 relevant tests passed,
  `protocol_v2.json` was frozen, and progress migration retained 17 complete
  v1 bundles, archived three interrupted v1 bundles, and preserved the two
  v1 scientific failures.
- Formal collection v2 array `36054403` then ran 90 new atomic scientific
  attempts. Stable accepted counts at stop were seed1=6, seed2=21, seed3=5,
  seed4=2 and seed5=1. The five currently blocked frozen latents saw 25, 3,
  18, 23 and 23 total ledger attempts respectively, including preserved v1
  attempt zero for seeds 4 and 5.
- For each blocked latent, every distinct derived attempt seed produced one
  identical failed outcome set. Code audit showed why:
  `run_candidate` seeds Python and NumPy, but the paired-latent execution path
  then uses a fixed cube, fixed reconstructed offsets, deterministic IK,
  controller and PyBullet settings, with no RNG draw affecting dynamics.
- This is not a stop based on poor results or a scientific-attempt limit.
  The attempt seed has no causal route to physics, so the authorised retry
  rule cannot generate a different simulator attempt. Adding a cube, contact,
  joint, waypoint, timing or solver perturbation would change the frozen
  protocol and is not authorised.
- A continuation audit compared 3,609 non-metadata files across four
  attempt-pairs from seeds 1, 4 and 5. Point clouds, joint/EE/cube
  trajectories, timestamps and commands were all content-identical; only
  seed/provenance metadata differed. The installed PyBullet build rejects
  both `randomSeed` and `solverRandomSeed`. No existing protocol-compatible
  seed-coupled physics RNG was found.
- Job `36054403` was cancelled after the causal audit and all 5/5 tasks were
  monitored to terminal `CANCELLED`. The five incomplete in-flight bundles
  were preserved under `protocol_blocker_attempts_v2/`.
- The user then explicitly authorised Protocol v3 candidate-stream
  continuation. A failed candidate's complete four-corner bundle is archived
  and the next candidate is tried; an infrastructure interruption cleanly
  retries the identical candidate without advancing. Exactly 30 accepted
  bundles per seed remains mandatory.
- Protocol v3 passed 49/49 relevant tests. All 800 persisted candidates
  (five streams x indices 0--159) matched deterministic regeneration exactly,
  and extension beyond index 159 is deterministic.
- `candidate_stream_v3.json` and `protocol_v3.json` are frozen. The five v3
  ledgers preserve all v1/v2 paths and hashes and resume at original-frozen
  positions 7, 22, 6, 3 and 2, with extension frontiers 54, 44, 41, 51 and
  39 respectively.
- Formal collection v3 array `36055938` completed 5/5. Each of the 20 raw
  datasets contains exactly 30 accepted demonstrations in deterministic
  stream order. The five seeds retain 28, 28, 24, 24 and 29 old-anchor-paired
  candidates respectively; the remaining 17 accepted replacements are
  paired only across the four new corners.
- The final v3 ledgers contain 25 rejected candidate identities: five migrated
  v2 frontier candidates plus 20 newly executed v3 rejections. The 92 legacy
  v1/v2 failed attempt executions remain preserved, so 112 actual failed
  simulator executions are auditable without double-counting the five
  migrated identities. All 150 accepted candidate bundles are complete.
- HDF5 array `36056459` completed 5/5. Exactly 20 new HDF5 files strictly
  validate with 60 episodes each and frozen 54/6 train/valid masks.
- The first training submission `36057059`--`36057078` failed or was
  cancelled before training due an exported code-root path; it created no
  checkpoint. Identical-config clean retry jobs `36057105`--`36057124`
  completed 20/20. All 45 selected checkpoint paths and hashes were frozen
  before formal rollout outcomes existed.
- Primary job `36059233` stopped before rollout because the composition loader
  rejected the immutable five-condition metadata order; it created zero rows.
  A profile-scoped compatibility fix passed tests and identical-input retry
  `36059244` completed 200/200 tasks and 5,000/5,000 rows.
- Secondary job `36061752` completed 188 tasks and recorded 12 `PREEMPTED`
  tasks on `erc-hpc-comp054`. Forty partial rows were archived by task
  ownership. Identical-input retry `36062210` completed 12/12, yielding exact
  200/200 tasks and 5,000/5,000 formal rows.
- Strict merge passed 400/400 new tasks and 10,000/10,000 new rows. Both
  common-absolute and RMAX40 surfaces contain 45 policies, 450 tasks and
  11,250 rows with their respective frozen pairing rules.
- Pre-registered analysis classified the surface as `interaction`.
  `I_tight_15` had mean `+0.1624` with 4/5 same-sign seeds and
  `I_wide_35` had mean `+0.1304` with 4/5; both passed the `0.05` margin and
  sign rule. The other two frozen contrasts did not pass.
- Final tests passed 52/52. Storage, jobs, hashes, figures, shared registry
  references and handoff were audited without copying large anchor artifacts.

### Gate 0: protocol, immutable-anchor and dirty-worktree audit

1. Preserve unrelated user changes and protected untracked files named `[`,
   `count=0`, `done` and `fi`.
2. Recompute all frozen source hashes and all 25 checkpoint hashes.
3. Freeze the nine-condition order, canonical/source seeds, expected work and
   output namespaces.
4. Record hashes for the ten common-absolute manifests and the active RMAX40
   manifests that will be reused.
5. Implement tests before formal jobs.

Pass: all anchors are unchanged and every reuse path is hash-addressed.

### Gate 1: four-corner feasibility and pairing audit

Reconstruct all four corner conditions for every one of the 30 active paired
latents in each canonical seed. Validate bounds, ordering, Start XZ and
Approach XY offsets, waypoint IK reachability and exact links to the five
anchor conditions.

Run only a separate smoke sufficient to test the four condition classes,
canonical/source seed plumbing, 8 Hz sampling and fixed-latent replay.

Pass: all 600 original-candidate corner records preserve exact old-anchor
pairing and pass static feasibility. Dynamic failures during formal collection
follow the Section 5 atomic candidate-stream rule; replacements remain exactly
paired across the four new corners but are not claimed as old-anchor paired.

### Gate 2: implementation and unit tests

Add an independent composition profile and composition-specific orchestration,
analysis and tests. Do not change the semantics or maps used by Stage 1,
Stage 2 axial or the RMAX40 rerollout.

Expected new implementation surfaces include:

```text
scripts/tro_position_composition.py
scripts/analyze_tro_position_composition.py
tests/test_tro_position_composition.py
scripts/run_tro_position_composition_collect.sh
scripts/run_tro_position_composition_hdf5.sh
scripts/submit_tro_position_composition_training.sh
scripts/run_tro_position_composition_smoke.sh
scripts/run_tro_position_composition_rollout.sh
scripts/run_tro_position_composition_merge.sh
scripts/run_tro_position_composition_analyze.sh
```

Pass: existing relevant tests and all new tests pass.

### Gate 3: formal data and HDF5

Collect exactly 20 paired datasets with 30 successes each by consuming each
seed's frozen deterministic candidate stream in order. For each candidate,
accept only one atomic bundle whose four corners all succeeded together.
Archive and inventory every unsuccessful or interrupted bundle. Then create
and strictly validate exactly 20 new HDF5 files. Register them without
modifying old registry records.

Pass: 20/20 datasets and HDF5 files validate; each dataset has exactly 30
accepted rows in deterministic stream order; all candidate indices, seeds and
outcomes are auditable; the full 45-slot reuse map is complete.

### Gate 4: training and checkpoint freeze

Train exactly 20 from-scratch early-stopped policies. After every training job
is terminal, select the highest numeric emitted checkpoint and freeze all 20
new hashes plus the 25 reused hashes before formal rollout.

Pass: 45/45 policy slots validate and no rollout-selected checkpoint exists.

### Gate 5: primary common-absolute formal rollouts

Run exactly 200 new tasks and 5,000 new rows against the frozen original
Stage 2 manifests. Monitor to terminal state and retry rollout jobs only for
infrastructure failures with identical frozen inputs.

### Gate 6: secondary RMAX40 formal rollouts

Run exactly 200 new tasks and 5,000 new rows against the appropriate frozen
Start-family manifests. Do not regenerate accepted states after seeing
results.

### Gate 7: strict merge and frozen analysis

Validate:

```text
new tasks = 400/400
new rows  = 10,000/10,000

full common-absolute matrix = 45 policies and 11,250 rows
full RMAX40 matrix          = 45 policies and 11,250 rows
```

Produce the pre-registered interaction classification, all required secondary
analyses, figures, commands, job ledger, final hashes and storage inventory.

### Gate 8: handoff and stop

Update this PLAN, the composition handoff and `docs/tro_plan.md`. Stop without
launching Stage 3, Rotation, Velocity, compatibility modelling, AR guidance
or human experiments.

## 10. Slurm, retry and storage policy

- Use `sbatch --parsable`; record every job ID, dependency and retry in
  `manifests/jobs.json`.
- Monitor the complete chain through terminal scheduler states. Submission is
  not completion.
- Retry `PREEMPTED`, `TIMEOUT`, node failure, GPU ECC and other
  infrastructure-only failures with identical inputs.
- During collection only, archive a failed scientific candidate's complete
  four-corner bundle and advance to the next deterministic candidate, as
  specified in Section 5.
- Never add an outcome-adaptive latent, retry only one condition from a failed
  bundle, or increase the 30 accepted demonstrations per dataset. Protocol v3
  replacement candidates may only come from the frozen deterministic stream.
- Never retry training or rollout because a condition or policy performs
  poorly.
- Archive partial infrastructure attempts under the new composition namespace
  and exclude them from the formal merge.
- Use only GPU nodes compatible with the frozen environment; avoid known
  `sm_120` incompatibility and documented faulty nodes.
- Disable formal videos.
- Do not copy existing raw data, HDF5 files, checkpoints or rollout rows.
- Do not delete old, intermediate or failed artifacts automatically.
- Report storage and safe cleanup candidates for separate user approval.

## 11. Safety and authority

Once invoked by the user's fresh-agent YOLO/long-goal prompt, the executing
agent is authorised to:

- implement only the composition-specific profile, scripts, tests and
  manifests;
- collect the 20 new corner datasets;
- run deterministic atomic four-corner collection attempts for each frozen
  latent until one complete bundle succeeds;
- create 20 new HDF5 files;
- train 20 new policies;
- run 400 formal rollout tasks and 10,000 new rollout rows;
- submit and monitor Slurm jobs to terminal state;
- retry infrastructure failures using identical frozen inputs;
- analyse and document the complete response surface.

The agent is not authorised to:

- retrain, recollect, overwrite, delete or mutate any completed Stage 2
  artifact;
- change radii, conditions, the deterministic candidate stream, learner,
  accepted demonstration count, checkpoint rule, rollout states, success
  criterion or primary contrasts after outcomes;
- accept condition-specific retries or any incomplete four-corner bundle;
- add `APP4P8` or any other exploratory cell;
- launch Rotation, Velocity, another task, a compatibility model, AR guidance
  or a human study;
- commit, push or open a pull request.

If deterministic candidate provenance, atomic four-corner acceptance or
immutable-anchor integrity cannot be preserved, stop and report the blocker
rather than expanding scope. A failed candidate by itself is not a blocker
under protocol v3; archive it and advance the frozen stream.

## 12. Definition of Done

- [x] All frozen Stage 2 and RMAX40 hashes remain unchanged.
- [x] Protocol, anchor reuse map and expected coverage are frozen.
- [x] All four corners pass the exact 30-latent x five-seed feasibility audit.
- [x] Existing relevant tests and new composition tests pass.
- [x] Collector v2 atomic retry semantics and deterministic attempt-seed
      derivation are tested and frozen before collection resumes.
- [x] Protocol v3 deterministic candidate-stream extension, whole-candidate
      reject/accept, crash/resume, evidence migration and exact-30
      termination are tested and frozen before v3 collection.
- [x] Exactly 20 new datasets contain 30 successful demonstrations each.
- [x] Every failed/interrupted collection attempt is archived and every
      accepted latent has exactly one complete four-corner success bundle.
- [x] Exactly 20 new HDF5 files validate.
- [x] Exactly 20 new policies train from scratch under the frozen learner.
- [x] All 45 selected checkpoint paths and hashes are frozen before rollout.
- [x] Primary common-absolute coverage is 200/200 new tasks and 5,000/5,000
      new rows.
- [x] Secondary RMAX40 coverage is 200/200 new tasks and 5,000/5,000 new rows.
- [x] Both full 45-policy response surfaces strictly validate.
- [x] The four interaction contrasts and classification follow Section 7
      exactly.
- [x] Required secondary analyses, figures, commands, jobs, hashes and storage
      inventory are complete.
- [x] Shared registries are updated without duplicating large artifacts.
- [x] The PLAN, amendments and composition handoff record final v3 execution,
      terminal jobs, results and the exact audit trail.
- [x] No later-stage or out-of-scope experiment is launched.

Definition of Done is **satisfied**. Every submitted scheduler job is terminal,
strict merge and frozen analysis passed, and the experiment stops here without
launching any later-stage or out-of-scope work.
