# Handoff: T-RO Stage 2 Position Axial ID/OOD Rerollout

_Last updated: 2026-07-26 · Branch: hpc-headless-tro @ 2f61da7_

## Goal

Rerun only the formal rollouts for the completed 25 Stage 2 Position policies
using condition-relative Start-space ID and OOD banks, so the experiment
measures which 30-demonstration spatial training distribution supports both
in-support learning and out-of-support generalisation.

## Current Progress

- Complete under the user-authorised RMAX40 v2 protocol amendment. The active
  protocol ID is
  `tro_stage2_position_axial_condition_relative_idood_rerollout_rmax40_v2`
  and the frozen global boundary is `R_MAX=0.40 m`.
- The rejected `R_MAX=0.45 m` pilot remains immutable audit evidence. Its 30
  manifests, feasibility audit and failed pre-rollout smoke logs must not be
  overwritten or used for formal evaluation.
- Gate 0 passed. The unified manifest hash and all 25 checkpoint file hashes
  were recomputed successfully. The old Stage 2 `comparison.json` and
  `summary.md` hashes remain unchanged.
- Gate 1 passed. The independent `tro_position_stage2_idood` evaluator
  profile, manifest generator/validator, tests, rollout/smoke/merge/analysis
  entry points and strict analysis implementation are present.
- The RMAX40 implementation and 32 tests pass. Its 30/30 manifests are frozen
  under `manifests/rollout_5seed_rmax40/`, and all rollout output is isolated under
  `dataset/tro_position_stage2_axial_idood_rerollout/rmax40/`.
- The 30/30 RMAX45 pilot manifests remain frozen and registered. Bounds, area
  mappings, state order, same-Start absolute pairing, cross-Start normalized
  pairing and both RNG streams passed for that pilot.
- Whole-triplet feasibility required 179 rejected normalized candidates
  across the ten seed/bank groups. ID directional coverage was balanced
  (`[33,34,34,24]` states by XZ quadrant), but OOD coverage was persistently
  biased (`[5,41,11,68]`) across all five rollout seeds.
- `manifests/feasibility_audit.json` records the rejected RMAX45 decision.
  The RMAX40 PLAN now treats the deterministic reachable-conditioned
  distribution as the target and requires explicit four-quadrant and pooled
  area-quantile coverage rather than angle uniformity after IK conditioning.
- Smoke job `36042451` reached execution before cancellation and all six
  tasks failed before policy rollout because the submitted smoke used
  `horizon=1`, which did not match the frozen `horizon=200` protocol. It
  produced zero rollout rows. The script was corrected but not resubmitted
  because the independent scientific stop already forbids evaluation.
- RMAX40 smoke job `36043096` completed six paths with 25/25 rows each.
- Formal array `36043712` completed 249 tasks. Task 245 was PREEMPTED after
  33 seconds; its one partial row and logs were archived before identical
  input retry `36049746`, which completed. No performance retry occurred.
- Strict merge `36050269` validated 250/250 tasks and 6,250/6,250 rows. Every
  policy has exactly 125 ID and 125 OOD trials; all checkpoint, bound, state,
  same-Start/cross-Start and RNG assertions pass.
- Analysis job `36050433` completed with valid status and three figures.
- Condition-level ID means are: START15_APP6 0.578, START25_APP3P6 0.478,
  START25_APP6 0.478, START35_APP6 0.320 and START25_APP8P4 0.274.
- Condition-level OOD means are: START25_APP6 0.360, START35_APP6 0.328,
  START25_APP3P6 0.317, START15_APP6 0.221 and START25_APP8P4 0.178.
- The ID/OOD Pareto front is `START15_APP6` and `START25_APP6`.
- No data collection or policy training occurred.

## What Worked

- The completed Stage 2 rollout stack already provides checkpoint validation,
  frozen start manifests, exact state/RNG pairing, 250-task arrays, strict
  merging, infrastructure retry handling and policy-level analysis patterns.
- The unified checkpoint manifest is
  `experiments/tro_stage2_position_axial_replication/manifests/checkpoints.json`
  with SHA-256
  `240a936999281f429dd1b043b19df5bd9291ed478933305a7c051c5183227580`.
- The existing evaluator supports XZ disks and annuli with area-uniform
  `sqrt(quantile)` radius sampling and independent runtime/point-cloud RNG
  streams.
- Joint triplet generation successfully produced 25 reachable states for
  every Start-radius/seed/bank manifest in the rejected pilot.
- Existing and new tests pass together: `32 passed`.
- A read-only RMAX40 feasibility diagnostic produced all four quadrants for
  every seed, reduced OOD joint rejections from 167 to 125, and covered pooled
  area quantiles from 0.021 to 0.975.
- The RMAX40 formal array, clean infrastructure retry, strict merge and final
  analysis all reached valid terminal states.

## What Didn't Work

- The old banks were reference-centred deployment regions:
  `[0,0.25]` and `(0.25,0.35]`. For START15, the old inner bank mixed
  in-support and OOD states; for START35, the old outer bank remained
  in-support. Therefore old inner/outer results must not be presented as
  universal ID/OOD results.
- Exact absolute states cannot be shared across START15, START25 and START35
  when each uses its own support boundary. The new PLAN instead requires exact
  absolute pairing within a Start family and normalized quantile/direction/RNG
  pairing across Start families.
- A single cross-condition combined leaderboard is not a common-distribution
  comparison under condition-relative banks. The new primary presentation is
  separate ID and OOD performance plus generalisation gap; balanced combined
  performance is descriptive only.
- The rejected RMAX45 jointly reachable-conditioned OOD sample is
  directionally non-uniform:
  `R_MAX=0.45`. Per rollout seed, OOD quadrant counts are
  `[1,8,3,13]`, `[2,4,1,18]`, `[0,10,2,13]`, `[1,8,3,13]` and
  `[1,11,2,11]`. This prompted the explicit RMAX40 protocol amendment; it is
  preserved as pilot evidence rather than silently replaced.
- The initial smoke script's `horizon=1` did not match the frozen manifest
  protocol. Exact protocol validation correctly rejected it before policy
  execution. The corrected script now uses `horizon=200`.
- The first strict merge attempt `36050142` incorrectly expected an
  aggregate-only `checkpoint_manifest_sha256` field in single-condition
  summaries. The validator was corrected to compare the recorded manifest
  path while retaining independent checkpoint hash validation; no rollout
  artifact changed.

## Key Files & Commands

- New sole authority:
  `experiments/tro_stage2_position_axial_idood_rerollout/PLAN.md`
- Completed Stage 2 handoff:
  `handoffs/tro-stage2-position-axial-replication.md`
- Frozen checkpoints:
  `experiments/tro_stage2_position_axial_replication/manifests/checkpoints.json`
- Existing implementation starting points:
  `examples/eval_abla1_trained_policies.py`,
  `scripts/tro_position_stage2.py`,
  `scripts/run_tro_position_stage2_rollout.sh`,
  `scripts/run_tro_position_stage2_merge.sh`,
  `scripts/analyze_tro_position_stage2.py`, and
  `tests/test_tro_position_stage2.py`.
- Old rollout manifests, read-only:
  `experiments/tro_stage2_position_axial_replication/manifests/rollout_5seed/`
- New artifact root:
  `experiments/tro_stage2_position_axial_idood_rerollout/`
- New large-output root:
  `dataset/tro_position_stage2_axial_idood_rerollout/`
- Implementation:
  `scripts/tro_position_stage2_idood.py`,
  `scripts/analyze_tro_position_stage2_idood.py`,
  `scripts/run_tro_position_stage2_idood_{smoke,rollout,merge,analyze}.sh`,
  and `tests/test_tro_position_stage2_idood.py`.
- Frozen protocol and checkpoint reuse:
  `experiments/tro_stage2_position_axial_idood_rerollout/manifests/protocol.json`
  and `checkpoint_reuse.json`.
- Active RMAX40 protocol and checkpoint reuse will be:
  `manifests/protocol_rmax40.json` and
  `manifests/checkpoint_reuse_rmax40.json`.
- Scientific stop evidence:
  `experiments/tro_stage2_position_axial_idood_rerollout/manifests/feasibility_audit.json`.
- Commands, job record, hashes and storage:
  `commands.md`, `manifests/jobs.json`, `manifests/final_hashes.json` and
  `manifests/storage_inventory.json`.
- Final result:
  `experiments/tro_stage2_position_axial_idood_rerollout/analysis/comparison.json`
  and `analysis/summary.md`.
- Figures:
  `analysis/figures/condition_id_ood_tradeoff.png`,
  `analysis/figures/id_ood_pareto.png`, and
  `analysis/figures/realised_radial_distributions.png`.
- Full job/retry history is in `manifests/jobs.json`.

## Next Steps

1. Stop. The RMAX40 rerollout is complete.
2. Do not launch any further experiment without a new explicit PLAN.
3. Treat balanced scores as descriptive only; the separate ID/OOD table and
   Pareto front are the primary result.

## Changelog

- 2026-07-26: Completed RMAX40 v2 through Definition of Done: six-path smoke,
  249 original + one clean preemption retry, 250/250 valid tasks,
  6,250/6,250 rows, strict pairing/hash/RNG validation, final ID/OOD analysis,
  Pareto figures and complete job/storage records.
- 2026-07-25: User authorised the RMAX40 v2 amendment and continuation through
  Definition of Done. Updated the PLAN, implementation, tests and isolated
  artifact namespaces while preserving all rejected RMAX45 pilot evidence.
- 2026-07-25: Completed Gates 0–1 and manifest generation, froze and
  registered 30 valid paired manifests, recorded 32 passing tests, and stopped
  at Gate 2 because all five OOD seed banks showed persistent directional
  reachability bias. Recorded failed pre-rollout smoke job 36042451, zero
  formal submissions/rows, and the prohibition on silent protocol changes.
- 2026-07-25: Created the dedicated rerollout handoff and authoritative PLAN
  with `R_MAX=0.45`, condition-relative Start ID/OOD banks, 30 frozen
  manifests, 250 tasks, 6,250 rows, checkpoint reuse and no retraining.
