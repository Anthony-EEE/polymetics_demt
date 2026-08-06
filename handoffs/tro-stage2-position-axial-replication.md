# Handoff: T-RO Stage 2 Position Axial Replication

_Last updated: 2026-07-25 · Branch: hpc-headless-tro @ 2f61da7_

## Goal

Run a balanced five-condition, five-dataset-policy Position replication to
test whether the Stage 1b `START25_APP3P6` candidate and stage-dependent
variation effects reproduce across independent policy realisations, while
maximising reuse of valid Stage 1/1b artifacts and using canonical seed labels
`1..K`.

## Current Progress

- Complete. All Stage 2 jobs and their dependency chain are terminal.
- Frozen Stage 1b and legacy hashes were rechecked and remain unchanged.
- Exact primary coverage is 25/25 dataset-policy slots, 250/250 rollout tasks
  and 6,250/6,250 rollout rows. Strict validation status is `valid`.
- Locked seed1 and seed5 pairing produced persistent scientific failures and
  triggered the PLAN's whole-slot fallback. The active matrix is therefore
  21 new + four reused datasets, 630 new successful demonstrations, and 25 new
  + zero reused policies. The five-condition x five-slot matrix did not change.
- Canonical seed 4 still records actual source seeds `1702/2702`; canonical
  seed 5 records `1701/2701`. Canonical aliases were never represented as
  actual RNG seeds 4 or 5.
- The pre-registered result is `partial`. Candidate-minus-wide passed
  (`mean=+0.2088`, 4/5 positive slots). Candidate-minus-reference did not
  (`mean=-0.0400`, 2/5 positive slots).
- Condition rankings by five-policy mean success rate are:
  - inner: `START25_APP6` 0.5456, `START25_APP3P6` 0.5184,
    `START15_APP6` 0.4720, `START35_APP6` 0.3056,
    `START25_APP8P4` 0.2528;
  - outer: `START25_APP6` 0.4336, `START25_APP3P6` 0.3808,
    `START35_APP6` 0.3616, `START15_APP6` 0.2720,
    `START25_APP8P4` 0.2288;
  - combined primary: `START25_APP6` 0.4896,
    `START25_APP3P6` 0.4496, `START15_APP6` 0.3720,
    `START35_APP6` 0.3336, `START25_APP8P4` 0.2408.
- The fixed interpretation is that widening Approach from 0.060 m to 0.084 m
  is harmful and the 0.036 m candidate reproducibly beats the wide condition,
  but narrowing from 0.060 m to 0.036 m does not reliably improve on the
  reference. A 0.35 m Start radius improves outer deployment relative to
  0.15 m on average (`mean D_start_outer=+0.0896`, 4/5 positive) while losing
  inner performance. This supports an axial response, not a claim that the
  narrowest Approach setting is globally optimal.
- No composition, Rotation, Velocity, cross-task, AR or human-study work was
  started.

## What Worked

- The separate `tro_position_stage2` collection/evaluation profile preserved
  all Stage 1/1b semantics and artifacts.
- Whole-slot candidate rejection/replacement produced exact accepted-latent
  pairing for all five canonical slots, including the seed1/seed5 fallbacks.
- All 25 from-scratch training jobs completed with repository patience 41.
  Selected epochs in condition order were:
  `seed1=[180,40,60,40,40]`, `seed2=[60,40,40,40,40]`,
  `seed3=[80,40,40,40,80]`, `seed4=[40,40,40,40,40]`,
  `seed5=[60,40,60,60,60]`.
- The unified checkpoint manifest was frozen before any Stage 2 rollout and
  has SHA-256
  `240a936999281f429dd1b043b19df5bd9291ed478933305a7c051c5183227580`.
- Rollout manifests paired state IDs/order, initial states, runtime RNG and
  point-cloud RNG across all 25 policies.
- Strict analysis reports every policy's successes/250, nested rollout-seed
  mean and sample std, condition replication, four canonical-seed deltas,
  rankings, discordances, Wilson intervals, cluster bootstrap, validation
  histories, sensitivities and exact pairing assertions.

## What Didn't Work

- Legacy seed1 candidate 2 was not waypoint-IK reachable for
  `START35_APP6`. Block-0/seed5 candidate 2 persistently failed the reference
  lift criterion. Neither locked slot could remain in the exact primary
  comparison, so both used the pre-registered full-slot fallback.
- Parallel HDF5 jobs raced while updating the shared dataset manifest. The
  files themselves were valid. The ledger was repaired by sequential
  per-seed validation followed by a full independent 25-slot hash audit; no
  HDF5 bytes were rebuilt or modified.
- Three formal rollout tasks were preempted: array indices `24`, `28`, `244`.
  Their 17, 7 and 9 partial rows were archived under
  `dataset/tro_position_stage2_axial/infrastructure_retries/`. Clean retries
  `36036368` and `36036894` completed with identical frozen inputs.
- The candidate did not replicate against the reference across all five
  policies. Seed1-3 sensitivity was more favorable than the all-five result,
  while seed4-5 were negative for candidate-minus-reference; both are reported
  without excluding aliases or changing the decision rule.

## Key Files & Commands

- Authority: `experiments/tro_stage2_position_axial_replication/PLAN.md`
- Reproducible command log:
  `experiments/tro_stage2_position_axial_replication/commands.md`
- Protocol, fallback, datasets, policies, checkpoints and jobs:
  `experiments/tro_stage2_position_axial_replication/manifests/`
- Strict result:
  `experiments/tro_stage2_position_axial_replication/analysis/comparison.json`
  (SHA-256
  `c70020fe70ab5aae9959ea990e66a2e2f3c4af4c05f24557a79d64c973ef9113`)
- Human-readable result:
  `experiments/tro_stage2_position_axial_replication/analysis/summary.md`
  (SHA-256
  `825a13e358b01e8707c99e1f19673b01d46df62edbacecce12bff6bbc6684370`)
- Figures:
  `experiments/tro_stage2_position_axial_replication/analysis/figures/`
- Formal raw/HDF5/rollouts/logs:
  `dataset/tro_position_stage2_axial/`
- Models:
  `/scratch/prj/eng_demt_robot_learning/trained_models/tro_position_stage2_axial/`
- Shared registries:
  `experiments/shared_artifacts/dataset_policy_registry.json` and
  `experiments/shared_artifacts/rollout_manifest_registry.json`
- All Stage 1, Stage 1b and Stage 2 tests passed: `25 passed`.

## Next Steps

1. Stop. Stage 2 is complete.
2. Do not launch Position composition or Stage 3 without a new explicit
   authorization and protocol.
3. If storage cleanup is later authorised, safe candidates are the Stage 2
   smoke outputs, archived preemption partials, and non-selected emitted
   checkpoints. Do not delete them automatically; selected checkpoints,
   formal data, manifests and analysis are not cleanup candidates.

## Open Questions

None for Stage 2. The `partial` classification and sensitivity split should be
treated as the fixed experimental result, not as permission to alter
`delta_min` or select a more favorable bank.

## Changelog

- 2026-07-25: Added the frozen inner, outer and combined condition rankings
  and the bounded scientific interpretation: Approach 0.084 m is harmful,
  Approach 0.036 m does not beat the 0.060 m reference reliably, and wider
  Start coverage helps outer deployment with an inner-performance tradeoff.
- 2026-07-25: Completed all gates. Recorded seed1/seed5 whole-slot fallbacks,
  21 new + four reused datasets, 25 new policies, frozen checkpoints, three
  clean infrastructure retries, 250/250 tasks, 6,250/6,250 rows, strict
  `partial` classification, registries, storage inventory and stop boundary.
- 2026-07-25: Created the authorised five-condition, five-dataset-policy Stage
  2 handoff with canonical seed aliases, exact artifact reuse, 16 new datasets,
  20 new policies and 6,250 formal rollouts.
