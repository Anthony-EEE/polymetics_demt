# Handoff: Bimodal Synthetic-Human Diffusion Policy Long Goal

_Last updated: 2026-08-07 · Branch: `hpc-headless-rebuttal` @ `72ca390`_

## Goal

Build a third, fully isolated experiment named `simulation_bimodal_group` from
the completed Target data. Randomly select ten distinct Left–Right participant
pairs from the 25 possible pairs, create ten shuffled 60-demo synthetic-human
views (`B01`–`B10`, exactly 30 Left + 30 Right), build ten validated HDF5
datasets, train ten uniform Diffusion Policies, run 20 stochastic rollouts per
policy on the frozen ten evaluation starts (200 total), and report Left/Right
route-choice proportions, route-conditional success rates, and overall success
rates. This is a terminal Long Goal: job submission is not completion.

## Current Progress

- The user approved the complete scientific and execution plan in this
  conversation. No bimodal dataset, HDF5, model, Slurm job, rollout, or result
  artifact has been created yet.
- The completed Target raw data are read-only at
  `rebuttal_dataset/simulation_target_group/full_seed20260806/protocol_release_z008_target_tol010_start_replenish/`.
  `T01`–`T05` are Left, `T06`–`T10` are Right, and each has exactly 30
  validated successful demonstrations.
- The ten validated Target HDF5 files are read-only under
  `rebuttal_dataset/simulation_target_group/hdf5/`. The HDF5 validation report
  SHA-256 is
  `44ad0c763badba8e41d56d1093989629fb88186ada225bbb267d35a87df20099`.
- The frozen Target DP training manifest SHA-256 is
  `610caef20d78f441df533aa2b1951029006cdf7b1d5aabf37c8bb1fdde8a5623`.
  Its uniform learner protocol is DP, seed 1, batch 16, 40 epochs x 250 steps,
  exact epoch-40 selection, and no participant-specific tuning or
  performance-based checkpoint selection.
- The frozen paired rollout manifest is read-only at
  `rebuttal_dataset/simulation_target_group/analysis/paired_rollout_specs.json`,
  file SHA-256
  `10dbbe16da06b4013899e350fece05687abc8c45471b584ac5a2473a0e486dad`.
- A reproducible design draw has been frozen below. It was computed from the
  lexicographically ordered 25-pair candidate list with Python stdlib
  `random.Random(20260807).sample(candidates, 10)`. A source participant may
  appear in more than one pair; only the `(Left, Right)` pair must be unique.

| Bimodal participant | Left source | Right source |
|---|---|---|
| B01 | T01 | T07 |
| B02 | T03 | T06 |
| B03 | T03 | T07 |
| B04 | T03 | T10 |
| B05 | T05 | T10 |
| B06 | T05 | T09 |
| B07 | T03 | T09 |
| B08 | T04 | T06 |
| B09 | T02 | T10 |
| B10 | T04 | T08 |

- This random draw is intentionally not balanced: for example, T03 appears in
  four distinct pairs. Do not redraw, rebalance, cherry-pick, or change it in
  response to data, training, or rollout outcomes.
- `simulation_control_group` is a separate live experiment owned by the
  Control Agent. Snapshot at `2026-08-07T17:43:35+01:00`: Slurm array
  `36371239` (`simulation_control_group_collect_r2`, `1-10%3`) remained active;
  C01–C05 were terminal complete, C06–C08 were running, and C09–C10 were
  pending. This is only a snapshot. On every resume, read
  `agents_working/control-simulation.md` and query Slurm read-only before any
  bimodal submission. Never adopt or act on a Control job.

### Ownership and isolation

The Bimodal Agent may create or modify only:

- `examples/rebuttal_bimodal_pipeline/`
- `rebuttal_dataset/simulation_bimodal_group/`
- `agents_working/bimodal-simulation.md`
- `tests/test_rebuttal_bimodal_pipeline.py`

The following are strictly read-only to the Bimodal Agent:

- `agents_working/README.md`
- `agents_working/control-simulation.md` and every Control prompt/review file
- `agents_working/target-simulation.md` and every Target prompt/review file
- `handoffs/handoff_rebuttal.md` and this handoff
- `examples/rebuttal_target_pipeline/`
- `examples/rebuttal_control_pipeline/`
- `rebuttal_dataset/simulation_target_group/`
- `rebuttal_dataset/simulation_control_group/`
- shared task/evaluation files, including
  `examples/main_obstacle_transport.py` and
  `examples/eval_obstacle_transport_trained_policy.py`

Use the exact group label `simulation_bimodal_group` in every new manifest,
HDF5 attribute, job name, log, checkpoint, rollout, plot, and result. Do not
commit, reset, clean, rename, delete, overwrite, cancel, hold, release, requeue,
or otherwise modify any Target or Control artifact or job. Implement all
adapters in the Bimodal-owned helper directory.

## What Worked

- The Target pipeline already provides immutable, validated raw trajectories,
  participant-level HDF5 files, a frozen DP protocol, a validated evaluator,
  and ten paired evaluation starts. Reuse these read-only instead of collecting
  new simulator demonstrations or inventing a different learner.
- Relative symbolic links provide the requested auditable 60-demo folder view
  without duplicating the large raw frame trees. A manifest must remain the
  authoritative mapping from shuffled Bimodal demo index to Target source.
- Copying the already validated Target HDF5 trajectory groups into new physical
  Bimodal HDF5 files preserves the exact observations/actions and avoids a new
  point-cloud resampling pass. The symlink view is provenance; the new HDF5 is
  the standalone training input.
- Target's existing `route_behavior()` definition is already auditable: use the
  box positions inside the obstacle y-band, classify by median x relative to
  obstacle x, and return `indeterminate` if the trace never reaches the band.
- Conservative, group-specific Slurm arrays and exact pre-submit duplicate-job
  audits are required while Control is concurrently active.

## What Didn't Work

- The earlier draft proposed balancing source usage so each Target participant
  appeared twice. The user rejected that constraint. The authorised design is
  a true no-replacement random sample of ten unique pairs from all 25 pairs;
  source-person reuse is allowed and is not balanced after the draw.
- Ten pairings cannot be constructed without source-person reuse from only five
  Left and five Right participants. `cannot repeat` means the exact `(L, R)`
  pair cannot repeat; it does not mean each source person can be used only once.
- Do not force exactly ten Left and ten Right rollout choices. The scientific
  question is whether each stochastic DP naturally approaches 10/10 across 20
  draws. Observe and report the route distribution; never resample a scientific
  outcome to improve balance or success.
- Random folder ordering does not create 600 independent demonstrations. The
  experiment contains 600 trajectory memberships across the ten B datasets but
  only the 300 completed Target trajectories as underlying unique data, with
  unequal multiplicity induced by the frozen random pairing. Report this
  dependency explicitly.
- `python` is not on the default shell `PATH` in this workspace. Use the frozen
  runtime `/scratch/users/k23114984/conda/arcap/bin/python` or an explicitly
  validated equivalent; do not silently switch environments.
- Do not edit the shared evaluator to add repeat/route support. Build a
  Bimodal-only evaluator by adapting the validated Target logic read-only.

## Key Files & Commands

### Required startup read order

1. `agents_working/README.md` (read-only coordination contract).
2. `handoffs/handoff_rebuttal.md` (Target completion and active Control facts).
3. This file, `handoffs/bimodal-dp-long-goal.md`.
4. Full current `agents_working/control-simulation.md`, read-only, solely to
   avoid job/path/resource interference.
5. Full `agents_working/target-simulation.md`, read-only, for frozen Target
   provenance.
6. Target HDF5 validation/training/checkpoint/rollout manifests listed below.
7. Create `agents_working/bimodal-simulation.md`, mark `IN_PROGRESS`, and record
   the current stage, timestamp, output roots, process/job IDs, and logs before
   taking a write action.

### Read-only frozen inputs

- Target raw root:
  `rebuttal_dataset/simulation_target_group/full_seed20260806/protocol_release_z008_target_tol010_start_replenish/`
- Target HDF5 root: `rebuttal_dataset/simulation_target_group/hdf5/`
- Target HDF5 validation:
  `rebuttal_dataset/simulation_target_group/hdf5/validation_report.json`
- Target training manifest:
  `rebuttal_dataset/simulation_target_group/models/training_experiment_manifest.json`
- Target selected-checkpoint manifest:
  `rebuttal_dataset/simulation_target_group/models/selected_checkpoints_manifest.json`
  (SHA-256
  `a06b1784234ef4f6e07f23b16fc82781e95c29a83553474b8bccf15ba870ea93`)
- Target rollout spec:
  `rebuttal_dataset/simulation_target_group/analysis/paired_rollout_specs.json`
- Target evaluator and route classifier:
  `examples/rebuttal_target_pipeline/evaluate_target_policy.py`
- Target analysis logic:
  `examples/rebuttal_target_pipeline/analyze_target_results.py`
- Target conversion/schema reference:
  `examples/rebuttal_target_pipeline/convert_target_hdf5.py`
- Target training preparation/reference:
  `examples/rebuttal_target_pipeline/prepare_target_training.py`

Verify frozen hashes before writing:

```bash
sha256sum \
  rebuttal_dataset/simulation_target_group/hdf5/validation_report.json \
  rebuttal_dataset/simulation_target_group/models/training_experiment_manifest.json \
  rebuttal_dataset/simulation_target_group/models/selected_checkpoints_manifest.json \
  rebuttal_dataset/simulation_target_group/analysis/paired_rollout_specs.json
```

Expected SHA-256 values, in order:

```text
44ad0c763badba8e41d56d1093989629fb88186ada225bbb267d35a87df20099
610caef20d78f441df533aa2b1951029006cdf7b1d5aabf37c8bb1fdde8a5623
a06b1784234ef4f6e07f23b16fc82781e95c29a83553474b8bccf15ba870ea93
10dbbe16da06b4013899e350fece05687abc8c45471b584ac5a2473a0e486dad
```

### Reserved Bimodal outputs

- Pairing manifest:
  `rebuttal_dataset/simulation_bimodal_group/pairing_manifest.json`
- Shuffled symlink views:
  `rebuttal_dataset/simulation_bimodal_group/mixed_raw/B01/` through `B10/`
- HDF5 root: `rebuttal_dataset/simulation_bimodal_group/hdf5/`
- Model root: `rebuttal_dataset/simulation_bimodal_group/models/`
- Rollout root:
  `rebuttal_dataset/simulation_bimodal_group/policy_rollouts/`
- Analysis root: `rebuttal_dataset/simulation_bimodal_group/analysis/`
- Live ledger: `agents_working/bimodal-simulation.md`

Before every Bimodal `sbatch`, perform an exact ownership/duplicate audit:

```bash
squeue -u k23114984 -o '%.18i %.32j %.2t %.10M %.10l %R'
sacct -S 2026-08-07 --format=JobIDRaw,JobName%40,State,ExitCode,Elapsed,NodeList -n -P
```

Adopt an existing Bimodal-owned job if its exact name, command, workdir, log
paths, and output root prove ownership. Never interact with job `36371239` or
any current/future job whose name, command, ledger, log, or output points to
Target or Control.

### Planned Bimodal-owned helpers

These files do not exist yet and should be implemented under
`examples/rebuttal_bimodal_pipeline/`:

- `create_bimodal_pairing.py`
- `create_mixed_symlink_views.py`
- `validate_mixed_symlink_views.py`
- `build_bimodal_hdf5.py`
- `validate_bimodal_hdf5.py`
- `prepare_bimodal_training.py`
- `train_bimodal_one.py`
- `train_bimodal_array.sbatch`
- `validate_bimodal_models.py`
- `evaluate_bimodal_policy.py`
- `evaluate_bimodal_array.sbatch`
- `analyze_bimodal_results.py`

All creators must refuse to overwrite existing formal output, use temporary
`.inprogress.<pid>` artifacts followed by atomic rename where appropriate, and
write hashes/provenance. Validators must re-open the actual payloads rather
than trusting creator summaries.

## Next Steps

1. **Adopt isolated coordination.** Complete the startup read order, audit the
   dirty worktree without cleaning it, query the active Control jobs read-only,
   confirm all reserved Bimodal roots are absent, then create only
   `agents_working/bimodal-simulation.md`. Record stage statuses for Pairing,
   Mixed Views, HDF5, Training, Model Validation, Rollout, and Analysis.

2. **Freeze and validate the ten-pair design.** Generate the candidate list in
   left-major order from `T01`–`T05` x `T06`–`T10`. Use exactly
   `random.Random(20260807).sample(candidates, 10)` and require the output to
   equal the frozen table in this handoff. Write `pairing_manifest.json` with
   the algorithm, seed, candidate order, selected order, source participant
   routes/centres, source HDF5/raw hashes, and multiplicity counts. Require ten
   unique pairs, valid L/R membership, and no outcome-dependent redraw.

3. **Create ten completely shuffled symlink views.** For each B participant,
   construct the deterministic item list `Left demo 0..29` followed by `Right
   demo 0..29`; shuffle once with Python stdlib seed
   `20260807 + 1000 + B_index` (`B_index` is 1..10). Create relative symlinks
   named `demo_0`..`demo_59` for raw directories and
   `demo_00.json`..`demo_59.json` for result JSONs. Do not copy or modify Target
   raw data. Write a per-B `mixture_manifest.json` mapping every shuffled index
   to route, source participant, source demo index, resolved path, and hashes.
   Runs of consecutive L or R are valid; do not impose alternation.

4. **Validate the views before HDF5.** For each B require exactly 60 resolvable
   raw-directory links and 60 resolvable result-JSON links, exactly 30 L + 30 R,
   all 30 source demos from each selected source, no duplicated source demo
   within B, successful Target result metadata, no broken/absolute/out-of-root
   symlink, exact frozen shuffle replay, and no zero-byte or partial manifest.
   Validate all ten together against `pairing_manifest.json`.

5. **Build ten standalone 60-trajectory HDF5 files.** Follow each mixture
   manifest and physically copy the corresponding `data/demo_<source_index>`
   group from the validated Target participant HDF5 into shuffled Bimodal
   `data/demo_0`..`data/demo_59`. Preserve arrays exactly. Set new attrs for
   `group=simulation_bimodal_group`, `participant_id=Bxx`, `route`,
   `source_group`, `source_participant_id`, `source_demo_index`, and all source
   hashes; recompute file-level totals and mean initial states. Do not use HDF5
   external links for the formal learner input. Preflight disk space; the
   filesystem had ample shared capacity at planning time, but current quota
   remains an execution-time check.

6. **Make a deterministic route-stratified split.** Each B HDF5 must have 54
   training trajectories (`27 L + 27 R`) and 6 validation trajectories (`3 L
   + 3 R`). Use one frozen, recorded split seed and algorithm for all B files.
   The HDF5 demo numbering remains the fully shuffled order; masks select the
   stratified members. Do not reorder into L-then-R for training.

7. **Validate HDF5 as a hard gate.** Require ten files, 60 trajectories per
   file, 600 trajectory memberships total, exact 30/30 modes, exact source
   hashes, correct route/provenance attrs, Target-identical datasets/dtypes/
   shapes/action-gap/point count, finite learner observations/actions, valid
   54/6 masks, no duplicated source trajectory within a B file, no partial or
   zero-byte outputs, and 20 real loader smokes (train + valid for every B).
   Record underlying unique-trajectory and multiplicity counts truthfully.

8. **Freeze ten uniform DP configs.** Adapt the Target preparation logic in the
   Bimodal-owned helper directory. The only participant-specific config fields
   are the B dataset path and experiment name. Keep seed 1, batch 16, 40 epochs
   x 250 training steps, 50 validation steps per epoch, identical observation/
   action schema and DP horizons, and exact `model_epoch_40.pth` selection.
   Disable training rollouts and all best-loss/best-rollout checkpoint choices.
   Freeze a canonical protocol hash before submission.

9. **Train and monitor ten policies.** Use a uniquely named Bimodal Slurm array
   with group-owned logs/output roots, conservative GPU concurrency (no more
   than `%2`), and exclusion of known bad GPU node `erc-hpc-comp223`. Check
   Control's current GPU jobs before submission but never alter them. Monitor
   every task to terminal state and inspect exit code, stderr, OOM/TIMEOUT/
   PREEMPTED/CANCELLED, run-completion metadata, exact epoch-40 checkpoint, and
   prompt behavior. Only proven infrastructure failures may be deterministically
   retried; no extra budget or tuning per B.

10. **Validate all models.** Re-hash configs/HDF5/checkpoints, load all ten
    exact epoch-40 checkpoints using the real policy loader, and run finite
    inference smokes on their own HDF5 observations. Freeze a selected-
    checkpoint manifest before any formal rollout.

11. **Run 20 stochastic rollouts per policy, 200 total.** Consume the exact
    read-only Target ten-case rollout manifest and hash. For each B policy and
    each eval case `0..9`, run repeat `0` and repeat `1`: identical box start,
    setup, environment, point-cloud protocol, success criterion, horizon, and
    evaluator settings, but a distinct deterministic policy diffusion-sampling
    seed recorded in the result. Do not generate replacement starts and do not
    force route choice. Use a Bimodal-only evaluator and preserve the frozen
    success criterion `target_xy_error<=0.10 and box_settled and
    cylinder_tilt<=10deg`; contacts remain diagnostic. Save 200 unique result
    JSONs and 200 videos. Scientific failures are final; only reviewed pre-
    result infrastructure failures may resume the identical spec/repeat.

12. **Classify realised route without forcing a label.** Copy the validated
    Target `route_behavior()` semantics into the Bimodal helper: over policy
    box positions within the obstacle y-band of half-width
    `OBSTACLE_RADIUS + BOX_HALF_EXTENT`, take median x; classify L when x is
    left of obstacle x and R otherwise. If the policy trace never reaches the
    band, report `indeterminate`. Never use final success to infer route and
    never discard indeterminate outcomes.

13. **Compute success and mode statistics.** For every B policy report
    `n_L`, `n_R`, `n_indeterminate` (summing to 20), selection proportions over
    all 20, `success_L/n_L`, `success_R/n_R`, and overall `success_total/20`.
    If a conditional denominator is zero, emit `null`/`NA`, not zero. Across
    all 200 outcomes report pooled L/R/indeterminate counts and proportions,
    pooled L-conditional and R-conditional success, raw total success/200,
    failure taxonomy, and participant-policy overall success mean +/- sample
    SD (`ddof=1`, n=10). Report deviation from 50/50 and mode collapse
    factually; do not expect or enforce exactly ten L and ten R per policy.

14. **Write and independently validate final artifacts.** At minimum produce
    `analysis/final_results.json`, `participant_success_rates.csv`,
    `route_choice_summary.csv`, `rollout_results.csv`,
    `validation_report.json`, `experiment_manifest.json`, a route/success plot,
    and a 200-video index. Final validation must prove 10 x 20 unique outcomes,
    two repeats for every B/case pair, exact spec/checkpoint/config hashes,
    valid route classification, complete videos, correct recomputed statistics,
    no outcome replacement, and no Target/Control writes.

15. **Finish the Long Goal.** Mark every row in
    `agents_working/bimodal-simulation.md` complete only after its validator
    passes. Final response must lead with the ten Left/Right choice counts,
    conditional success rates, per-policy overall rates, pooled 200-rollout
    rate, and participant-level mean +/- SD; then list pairings, hashes, jobs,
    artifacts, infrastructure retries, indeterminate cases, data-reuse limits,
    and confirmation that the concurrent Control pipeline was untouched.

## Open Questions

None. The user has approved the unique-pair sampling semantics, shuffled
relative-symlink views, 60-trajectory HDF5 files, Target-matched DP protocol,
20 stochastic rollouts per policy, observed rather than forced route choice,
and all requested success-rate statistics.

## Changelog

- 2026-08-07: Created the executable Bimodal DP Long Goal plan with frozen
  random pairings, isolated ownership alongside the live Control R2 pipeline,
  shuffled 30L+30R symlink/HDF5 stages, ten-policy training, 200 stochastic
  rollouts, and route-conditional/overall success analysis.
