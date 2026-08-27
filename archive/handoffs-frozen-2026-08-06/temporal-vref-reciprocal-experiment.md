# Handoff: Temporal Vref Reciprocal Experiment — Spatially Distributed Rerun

_Last updated: 2026-07-19 · Branch: hpc-headless-data-collection @ de6d7de_

## Goal
Rerun the reciprocal P6/P7 `v_ref` experiment from scratch with the originally
requested strong R00 spatial baseline distribution. Compare `VR1P5`,
`V050_200`, `VR3`, and `VR4` while holding the spatial distribution,
orientation, data budget, learner, and evaluation protocol constant. The
2026-07-18 fixed-path experiment is invalid and must never be cited.

## Current Progress
- 2026-07-19 fresh-session cleanup gate revalidated before any new work:
  all three invalid roots remain absent. No deletion was needed and no unrelated
  path was touched. The Ceph checkout and
  `/scratch/prj/eng_demt_robot_learning/polymetics_demt` resolve to the same
  device/inode (`46:5504333212695`). Branch/commit remain
  `hpc-headless-data-collection @ de6d7de`; the initial user Slurm queue was
  empty. The dirty tree was recorded and preserved without reset/checkout.
- The real R00 metadata was re-audited empirically across all 30 demos:
  30 distinct reachable random starts, 30 distinct corridor deltas, corridor
  XZ norm max `0.0491131 m`, nonzero x/z variance, and exactly zero pre-grasp
  deltas. This is the spatial behavior the corrected manifest must reproduce.
- Initial code audit found fixed-start/zero-delta collection and checker defects,
  plus a 10-rollout fixed-start evaluator with an old V050 override. Those
  defects are now corrected in the manifest-driven implementation described
  below; no old checkpoint override remains.
- Implemented the corrected manifest-driven collection/check/HDF5/split/eval
  paths and passed the first static gate (4 unit tests, `py_compile`, `bash -n`,
  and `git diff --check`). Generated the shared 48-candidate pool at
  `dataset/temporal_vref_reciprocal_spatial_v2/shared_collection_manifest_seed1.json`
  (SHA-256 `54a0d5b66429e65151620020c33b12a74d9efde6d4b489073d3a37714dc84c03`).
  All 48 starts are distinct and IK-valid; all 48 corridor deltas are distinct,
  max XZ norm is `0.0497571 m`, x/z variances are nonzero, pre-grasp deltas are
  exactly zero, P6/P7 streams differ, and all four exact reciprocal mappings
  validate.
- Four compute-node one-candidate smoke jobs completed `0:0`:
  `35880300` VR1P5 (79 frames), `35880301` V050_200 (83), `35880302`
  VR3 (101), and `35880303` VR4 (122). All lifted the cube to about `0.2947 m`,
  passed individual and four-condition smoke checks, and used identical
  `candidate_0000` spatial arrays/common U values. Manual inspection of real
  VR4 metadata confirmed exact `['1/4','4']`, a nonzero corridor delta, fixed
  pre-grasp, independently mapped P6/P7 multipliers, and the manifest SHA.
  Spatial-audit and trajectory/timing plots under
  `dataset/temporal_vref_reciprocal_spatial_v2/smoke_plots` were visually
  inspected and are sane. Read-only compute visibility job `35880298` also
  confirmed branch/commit/manifest identity and write access.
- Formal shared-pool collection jobs were submitted independently on
  `interruptible_cpu`: VR1P5 `35880320`, V050_200 `35880321`, VR3 `35880322`,
  and VR4 `35880323`. Each traverses candidates 0-47 and retains successful
  candidate IDs; the finalizer will take the first 30 IDs in the four-way
  success intersection so a condition-specific failure cannot misalign the
  spatial sets. All four reached `COMPLETED 0:0`, with 48/48 successful
  candidates: VR1P5 in `00:07:45`, V050_200 in `00:10:15`, VR3 in
  `00:11:20`, and VR4 in `00:17:25`. Their stderr files contain only the
  PyBullet build banner.
- Because every candidate succeeded in every condition, the finalizer selected
  `candidate_0000` through `candidate_0029` and wrote
  `selected_candidates.json`; the four final raw groups are
  `temporal_{condition}_d30_seed1`. The full frame-level group checker passed:
  exactly 30 distinct starts and 30 distinct corridor deltas, maximum selected
  delta radius `0.0496274 m`, nonzero delta X/Z variance, all-zero pre-grasp
  deltas, candidate-wise spatial equality, exact rational bounds, and correct
  shared-U P6/P7 mappings.
- Generated the formal plot set under `temporal_plots/` and visually inspected
  the shared spatial audit, P6/P7 histograms, and VR4 trajectory/timing plot.
  Starts cover the requested square, all corridor points are inside the 5 cm
  disk, pre-grasp is a true point mass, cross-condition spatial error is zero,
  the exact fraction labels are present, and the trajectories are coherent.
- After repeating the branch/commit, checkout identity, writable-root, dirty
  tree, unit/static, absent-output, and empty-queue gates, submitted four
  independent HDF5 conversions: VR1P5 `35881103`, V050_200 `35881111`, VR3
  `35881112`, and VR4 `35881113`. All completed `0:0`; output sizes are about
  1.3, 1.4, 1.9, and 2.4 GB respectively.
- Shared candidate-level split job `35881632` completed `0:0`, writing the same
  raw `27/3` and augmented `54/6` train/valid split to all four files. Full HDF5
  validation passed: 60 demos per condition, disjoint full-coverage masks,
  identical cross-file source split, two augmentations per raw candidate,
  correct source-frame accounting, finite arrays, 8-D actions, and 10,000x6
  point clouds. Total samples are VR1P5 `2722`, V050_200 `3092`, VR3 `4069`,
  and VR4 `5150`.
- Generated and audited four training configs under
  `training_config/temporal_vref_reciprocal_spatial_v2`. Compute visibility job
  `35881800` completed and confirmed the live branch/commit, new config, HDF5,
  and training submit code on `erc-hpc-comp230`. Submitted four new GPU
  trainings with W&B disabled: VR1P5 `35881838`, V050_200 `35881844`, VR3
  `35881848`, and VR4 `35881849`. Their effective outcomes, retries, logs,
  checkpoints, and load tests are recorded in the following bullets.
- VR1P5 `35881838` was cluster-preempted after `00:01:22`. V050_200
  `35881844` was misleadingly marked `COMPLETED 0:0`, but log inspection caught
  a hardware `CUDA error: uncorrectable ECC error encountered`; the external
  trainer catches exceptions and therefore returned zero without a valid
  completion. Preserved both failure records and resubmitted only the affected
  conditions as VR1P5 `35882051` and V050_200 `35882052`. VR3/VR4 continue in
  their original jobs.
- Retry `35882051` landed on the same faulty comp223 node and hit the same ECC
  error. Retry `35882052` correctly refused to overwrite the prior same-name
  output, but the external trainer converted its noninteractive EOF to exit
  zero. Neither produced a checkpoint. To preserve rather than delete evidence,
  moved only these failed experiment directories to
  `VR1P5/failed_attempt_35882051_ecc` and
  `V050_200/failed_attempt_35881844_ecc`. Added an explicit submit-time node
  exclusion and resubmitted only VR1P5 `35882393` and V050_200 `35882394`,
  excluding comp223 (plus the pre-existing comp040/comp035 exclusions).
- The four effective trainings all completed after validation early stopping:
  VR1P5 `35882393` epoch 52 (best valid `0.0709466`), V050_200 `35882394`
  epoch 47 (`0.0705535`), VR3 `35881848` epoch 50 (`0.0665663`), and VR4
  `35881849` epoch 47 (`0.0551551`). Each has 290 MB epoch-20 and epoch-40
  checkpoints; all selected epoch-40 checkpoints were actually loaded on CPU
  as 72.4M-parameter RolloutPolicy objects. Each external run emits a W&B
  `PrintLogger.isatty` cleanup exception only after early stopping and
  checkpoint persistence; model load tests distinguish this from the earlier
  ECC failures.
- Wrote and manually inspected `training_loss_summary.json` and `loss.png`.
  Wrote explicit checkpoint manifest SHA-256
  `61cb091e8ba666ceb43e77b2727324754b1969fede34ce1fb5d12ab86b922972`,
  recording effective training job IDs and four paths exclusively under the
  corrected `temporal_vref_reciprocal_spatial_v2` model root; old fixed-point
  checkpoint reuse is explicitly false.
- Repeated the full eval pre-submit gate and passed compute-node compilation /
  manifest visibility job `35884279` on comp230. Submitted paired primary eval
  array `35884281_[0-3]`, with the faulty comp223 node excluded. Tasks map in
  fixed order to VR1P5, V050_200, VR3, VR4; each was required to produce 50
  per-rollout JSONs and one readable video before the four-condition merge.
- Eval array `35884281_[0-3]` completed `0:0` in `00:08:17`, `00:08:59`,
  `00:11:11`, and `00:14:15`. It produced exactly 50 per-rollout JSONs and one
  MP4 per condition. Strict merge job `35884542` completed `0:0`, validating
  condition set, protocol, manifest hashes, checkpoint paths, paired specs,
  realised starts/IK details, and success rule. Aggregate results:
  - VR1P5 `37/50 = 0.74`, Wilson 95% `[0.6045, 0.8413]`, median successful
    time `5.75 s`;
  - V050_200 `37/50 = 0.74`, Wilson 95% `[0.6045, 0.8413]`, median `7.00 s`;
  - VR3 `33/50 = 0.66`, Wilson 95% `[0.5215, 0.7756]`, median `10.75 s`;
  - VR4 `18/50 = 0.36`, Wilson 95% `[0.2414, 0.4986]`, median `11.50 s`.
  Pairwise success-only discordances (left/right) are VR1P5-V050 `10/10`,
  VR1P5-VR3 `11/7`, VR1P5-VR4 `25/6`, V050-VR3 `10/6`, V050-VR4 `23/4`,
  and VR3-VR4 `19/4`; all six tables sum to 50.
- OpenCV decoded every video frame without error: VR1P5 `2239`, V050_200
  `2327`, VR3 `2891`, VR4 `4089`, all 320x320 at 20 fps. Manually inspected
  preview frames show the expected labelled simulation scene rather than black
  or corrupt output. Final aggregate SHA-256 is
  `3c84bdecc4bb1113a7d84f0b8ed0ac8e116f98c1008d0eeaa8cca36f20f3e9ed`.
- Repeated the final raw group checker and four-file full HDF5 validator after
  all execution; both passed again. Unit tests, all changed-file `py_compile`,
  all changed-shell `bash -n`, `git diff --check`, checkpoint loads, paired
  merge, video decode, and empty final Slurm queue all pass. No commit/push was
  made, and unrelated dirty/untracked files were preserved.
- A post-submit audit found that the evaluator's condition-summary return block
  had been displaced during editing. It was restored before any evaluation was
  submitted; `py_compile`, all four reciprocal unit tests, shell syntax checks,
  and `git diff --check` pass after the repair.
- Generated the primary seed-628 paired rollout start manifest (no model
  evaluation was started) at
  `dataset/temporal_vref_reciprocal_spatial_v2/policy_rollouts_seed628_paired_n50_h200/paired_manifest_seed628_n50_h200.json`
  (SHA-256 `1bb280bdf63aca2da0b261f89be3541eb1b7e91dd5833eea43d0469030d95e1b`).
  It has exactly 50 distinct IK-validated starts, nonzero X/Z variance, full
  `[0.2,0.6]` bounds compliance, horizon 200, `action_dt=0.25`, and
  terminate-on-success enabled.
- The initial scientific defect was confirmed before correction. The pre-fix
  temporal collection code recorded `corridor_start_radius=0.05` but set
  `corridor_start_delta=[0,0,0]`; it also fixed
  `random_start=[0.4,0,0.4]`. The pre-fix checker validated configured radius
  fields instead of the empirical spatial distribution. None of that code or
  data was used in the completed result above.
- The intended temporal baseline was to reuse the strong orientation R00
  geometry, not a point mass:
  - reachable `random_start`: `y=0`, with `x,z` sampled from `[0.2,0.6]`;
  - `corridor_start`: base `[cube_x-0.2, 0.15, 0.28]` plus a uniform-area XZ
    disk sample of radius `0.05 m`;
  - `pre_grasp`: fixed at `[cube_x,cube_y,0.22]`, radius `0.0`;
  - default gripper orientation for the entire trajectory.
- This interpretation is supported by
  `handoffs/week1_main-experiments.md`, the working implementation in
  `examples/main_orn_mvp.py`, and the actual 30-demo R00 raw dataset. In R00,
  all 30 random starts and all 30 corridor deltas are distinct; pre-grasp is
  fixed.
- On 2026-07-19 the user explicitly ordered deletion of every artifact from the
  invalid 2026-07-18 reciprocal run. The following dedicated roots were
  resolved, measured, deleted, and verified absent:
  ```text
  dataset/temporal_vref_reciprocal_n15_n3_n4                         6.1 GB
  training_config/temporal_vref_reciprocal                           21 KB
  /scratch/prj/eng_demt_robot_learning/trained_models/
    temporal_vref_reciprocal_n15_n3_n4                              11 GB
  ```
  The deletion is irreversible and removed raw demos, HDF5 files, plots,
  Slurm logs, rollout JSON/video, three trained variants, and generated configs.
- The historical 2026-07-05 `V050_200` raw data/model was not created yesterday
  and was therefore not deleted. It is nevertheless trained on the same invalid
  fixed-point geometry and is forbidden as the corrected baseline checkpoint.
  The corrected rerun must recollect and retrain `V050_200` along with the other
  three conditions.
- All corrected collection, conversion, training, rollout, and merge jobs are
  terminal and recorded above. No commit or push was made.

## What Worked
- Preserve the exact reciprocal temporal definitions:
  ```text
  VR1P5    n=3/2  multiplier range [2/3, 3/2]
  V050_200 n=2    multiplier range [1/2, 2]
  VR3      n=3    multiplier range [1/3, 3]
  VR4      n=4    multiplier range [1/4, 4]
  ```
  Use `fractions.Fraction`; do not encode `2/3` or `1/3` as `0.67` or `0.33`.
- The explicit paired manifest, per-rollout RNG reset, strict four-condition
  merge, time-to-success reporting, and horizon-200 evaluator from the deleted
  run are useful infrastructure after replacing their fixed-start assumptions.
- Reuse the validated human timing source:
  ```text
  outputs/week2_human_phase_reference_p6p7_v2/v_ref_phase_reference.json
  v_ref_group = P6P7_post_valid_order
  ```
- Reuse the established learner/data constants unless a real failure requires a
  documented change: 8 Hz collection, 10,000-point observations, action gap 2,
  30 successful raw demos per condition, and 10% validation.

## What Didn't Work
- Treating “same spatial path distribution across temporal conditions” as “one
  fixed path” destroyed the intended baseline coverage and made fixed-start
  rollout a ceiling test.
- Do not set `delta_start=np.zeros(3)`. A nonzero configured radius in metadata
  is not evidence that sampling occurred.
- Do not fix all rollout starts to `[0.4,0,0.4]` and call the run spatially
  distributed or robust.
- Do not reuse the old `V050_200` checkpoint, even through an explicit override.
  It is valid as a file but invalid for this corrected scientific comparison.
- Do not cite any output or success/efficiency number from invalid jobs
  `35870393`–`35872331`. Their dedicated artifacts have been deleted.
- Do not use `V075_150` or `V025_250`; both remain superseded.
- The checker must never accept a dataset merely because every demo says
  `corridor_start_radius=0.05`. It must inspect actual deltas and cross-demo
  variation.

## Corrected Experimental Design

### 1. Shared collection manifest
Before smoke or full collection, generate a versioned JSON manifest using
separate deterministic RNG streams for spatial and temporal latent variables.
Each candidate ID contains:

- sampled `random_start_x` and `random_start_z` in `[0.2,0.6]`, `y=0`;
- sampled corridor disk latent values and resolved XZ offset, using
  `r=0.05*sqrt(U)` and `theta=2*pi*U`;
- `pre_grasp_delta=[0,0,0]`;
- independent common uniforms `u_P6` and `u_P7`.

For condition `n`, map each phase latent by
`multiplier = 1/n + u * (n - 1/n)`. This gives the required marginal uniform
distribution while pairing spatial points and temporal ranks across all four
conditions. Use distinct RNG streams so changes in timing code cannot alter
spatial samples.

All four conditions must use the same 30 accepted candidate IDs. If any
candidate fails in any condition, replace that candidate for all four with the
next deterministic candidate; do not silently create different spatial sets.

### 2. Raw collection
Collect and train all four conditions from scratch:

```text
VR1P5, V050_200, VR3, VR4
30 shared successful demos each, seed 1, 8 Hz
```

Keep default orientation. Only P6 and P7 independently receive the reciprocal
`v_ref` multipliers; all other timing rules remain identical across conditions.
Store manifest ID, raw latent values, exact rational bounds, resolved waypoints,
and realised IK error in every demo metadata file.

Use new roots so no stale path can be mistaken for a corrected artifact:

```text
dataset/temporal_vref_reciprocal_spatial_v2
training_config/temporal_vref_reciprocal_spatial_v2
/scratch/prj/eng_demt_robot_learning/trained_models/
  temporal_vref_reciprocal_spatial_v2
```

### 3. Required raw validation and plots
The checker must validate both each demo and the four-condition group:

- 30 successful demos and identical candidate-ID set/order per condition;
- `random_start_y=0`, `x,z` within `[0.2,0.6]`, and 30 distinct starts;
- `corridor_delta_y=0`, every XZ radius `<=0.05`, and 30 distinct corridor
  deltas with nonzero x/z variance;
- `corridor_start=base_corridor_start+corridor_start_delta` numerically;
- every pre-grasp delta exactly zero and radius exactly zero;
- empirical spatial arrays match across all four conditions candidate by
  candidate;
- P6/P7 bounds are exact reciprocal fractions, phase samples are in bounds,
  P6 and P7 are independently generated, and the stored common uniforms map
  back to the multipliers;
- successful final lift and required phase/frame coverage.

Plots must include random-start XZ scatter, corridor-offset XZ scatter with the
5 cm boundary, pre-grasp point mass, candidate-wise cross-condition equality,
phase multiplier histograms, phase duration/frame distributions, and trajectory
plots. Visually inspect them before HDF5 conversion.

### 4. HDF5, split, and training
- Convert four datasets, not three.
- Preserve manifest/candidate IDs into HDF5 attributes or an adjacent auditable
  manifest.
- Apply the same train/valid candidate split across all four conditions
  (`27/3` raw source demos for a 0.1 validation ratio; account explicitly for
  any converter augmentation when validating HDF5 demo counts).
- Validate disjoint masks, full coverage, shapes, finite values, source-ID
  pairing, point counts, and action timing.
- Train four new models in parallel where resources permit. `V050_200` is a new
  corrected baseline, not an override. Load-test every selected checkpoint.

### 5. Paired rollout
Primary evaluation must use 50 spatially varied paired rollouts, seed 628:

```text
random_start: shared reachable draws with y=0, x,z in [0.2,0.6]
horizon: 200
action_dt: 0.25
terminate_on_success: true
success threshold: cube z >= 0.2
same start, simulator seed, Python/NumPy/Torch/CUDA RNG, point-cloud RNG,
observation history, action timing, and success protocol for all four models
```

The evaluator must reject a manifest containing a repeated fixed point. Save
videos and per-rollout JSON. Aggregate exactly `VR1P5`, `V050_200`, `VR3`, and
`VR4`; report success rate with uncertainty, paired success discordances,
steps/time-to-success for successful trials, failures, checkpoints, videos, and
job IDs. A fixed-center rollout may be retained only as a clearly labelled
secondary diagnostic, never as the primary result.

## Key Files & Commands
- Required context and baseline evidence:
  ```text
  handoffs/week1_main-experiments.md
  handoffs/temporal-vref-experiment-plan.md          # historical pipeline only
  handoffs/ar-guidance-spatial-temporal-experiments.md
  examples/main_orn_mvp.py
  examples/main_abla_1.py                            # sample_xz_disk
  dataset/orn_mvp_full/orn_mvp_R00_d30_seed1
  outputs/week2_human_phase_reference_p6p7_v2/v_ref_phase_reference.json
  ```
- Files requiring correction or audit:
  ```text
  examples/main_time_mvp.py
  scripts/check_time_mvp_dataset.py
  scripts/run_time_mvp_collect.sh
  examples/plot_time_mvp_temporal.py
  scripts/create_time_mvp_hdf5.py
  scripts/run_time_mvp_hdf5_slurm.sh
  scripts/split_ar_guidance_hdf5.py
  scripts/run_ar_guidance_split_slurm.sh
  scripts/create_time_mvp_train_configs.py
  scripts/submit_time_mvp_train_pipeline.sh
  scripts/summarize_ar_guidance_training.py
  examples/eval_time_mvp_trained_policies.py
  scripts/create_time_mvp_eval_manifest.py
  scripts/run_time_mvp_eval.sh
  scripts/run_time_mvp_eval_merge.sh
  scripts/validate_time_mvp_hdf5.py
  tests/test_temporal_vref_reciprocal.py
  ```
- Minimum pre-submit/final checks:
  ```bash
  python -m unittest -v tests.test_temporal_vref_reciprocal
  python -m py_compile <all changed Python files>
  bash -n <all changed shell files>
  git diff --check
  ```
- Before any `sbatch`, verify branch/commit, dirty files, Ceph/scratch path
  identity, compute-node visibility of the modified code, writable roots,
  available checkpoints, and the user's current Slurm queue. Never cancel a job
  unless its ID is recorded as belonging to this corrected experiment.

## Next Steps
No required experiment stage remains. Treat the corrected aggregate and its
manifests as the primary result. If downstream analysis is requested, read this
handoff and use the exact paths/hashes below; never substitute the deleted
fixed-point run or the archived failed training attempts. Do not commit or push
unless the user explicitly requests it.

## Changelog
- 2026-07-18: The reciprocal fixed-path pipeline was run; this entire run was
  later rejected because its spatial metadata did not reflect real sampling.
- 2026-07-19: Confirmed the point-mass defect in raw data and code. Deleted and
  verified absence of all dedicated 2026-07-18 reciprocal data, HDF5, plots,
  logs, configs, trained variants, rollout JSONs, and videos (about 17.1 GB).
- 2026-07-19: Replaced the completed-run narrative with the spatially
  distributed four-model rerun design and prohibited reuse of the old fixed-path
  `V050_200` checkpoint.
- 2026-07-19: Revalidated the three-path cleanup and Ceph/scratch checkout
  identity, recorded the empty Slurm baseline, empirically rechecked all 30 R00
  metadata files, and documented the remaining fixed-point/checker/eval defects.
- 2026-07-19: Implemented and statically validated the manifest-driven spatial
  rerun pipeline, then generated and empirically validated the shared 48-candidate
  collection manifest (SHA-256 `54a0d5b6...c84c03`).
- 2026-07-19: Completed and manually inspected all four HPC smoke collections
  (`35880300`-`35880303`); individual/group checkers and smoke plots passed.
- 2026-07-19: Submitted four formal 48-candidate shared-pool collection jobs
  (`35880320`-`35880323`) and began 2-5 minute `squeue`/`sacct` monitoring.
- 2026-07-19: Restored the evaluator's displaced per-condition summary return
  before evaluation and repeated the unit/static validation gate successfully.
- 2026-07-19: Generated and empirically checked the seed-628 50-start primary
  paired rollout manifest; no checkpoint evaluation has been run yet.
- 2026-07-19: All four formal collection jobs completed 48/48; selected the
  common first 30 candidates, passed the full raw group checker, generated the
  formal plots, and manually inspected spatial, multiplier, and VR4 trajectory
  plots before HDF5 conversion.
- 2026-07-19: Submitted four parallel per-condition HDF5 conversion jobs
  (`35881103`, `35881111`-`35881113`) after a fresh pre-submit gate.
- 2026-07-19: All HDF5 jobs completed; shared split job `35881632` and the full
  four-file HDF5 validator passed. Generated/audited configs, passed compute
  visibility job `35881800`, and submitted four corrected training jobs
  (`35881838`, `35881844`, `35881848`, `35881849`).
- 2026-07-19: Detected VR1P5 preemption and a masked V050_200 GPU ECC failure by
  reading logs rather than trusting `0:0`; resubmitted only those conditions as
  `35882051` and `35882052`.
- 2026-07-19: The first retries hit comp223 ECC / noninteractive existing-run
  protection. Archived the two checkpoint-free failed directories without
  deletion, added submit node exclusion support, and resubmitted the two
  affected conditions as `35882393`/`35882394` away from comp223.
- 2026-07-19: All four effective trainings early-stopped successfully, produced
  load-tested epoch-40 checkpoints, and yielded an inspected loss summary plus
  explicit new-checkpoint manifest; post-training W&B cleanup exceptions are
  documented separately from model validity.
- 2026-07-19: Eval compute visibility job `35884279` passed; submitted paired
  50-rollout GPU array `35884281_[0-3]` with comp223 excluded.
- 2026-07-19: All four 50-rollout eval tasks and strict merge job `35884542`
  completed; validated aggregate rates are 0.74/0.74/0.66/0.36 in reciprocal
  condition order. Fully decoded and manually inspected all four videos, then
  repeated raw, HDF5, unit/static, checkpoint, paired-merge, video, diff, and
  empty-queue final gates successfully. Experiment is complete.
