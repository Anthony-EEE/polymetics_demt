# Handoff: T-RO Stage 2c Position Composition

_Last updated: 2026-07-27 · Branch: hpc-headless-tro @ 2f61da7_

## Goal

Complete the four missing cells in the existing 3 x 3 Position
Start x Approach factorial while keeping the 25 Stage 2 axial slots
immutable, then execute the pre-registered common-absolute interaction
analysis and condition-relative RMAX40 ID/OOD diagnostics.

## Current Progress

The job is complete. All Gates 0--8 and every item in
`experiments/tro_stage2_position_composition/PLAN.md` Definition of Done
passed.

- Protocol v3 candidate-stream collection is implemented, tested and frozen.
  A failed candidate archives its entire four-corner bundle and advances the
  deterministic stream; only infrastructure interruption retries the
  identical candidate.
- Collection job `36055938` completed 5/5. There are exactly 20 new raw
  datasets with 30 accepted demonstrations each.
- Accepted candidate IDs by canonical seed are:
  - seed1:
    `1,2,4,6,8,10,13,16,17,20,21,22,23,25,27,30,34,36,37,39,44,46,47,48,49,50,52,53,55,57`;
  - seed2:
    `0,1,3,5,6,8,10,11,12,14,15,16,17,18,19,20,21,23,24,26,27,31,32,35,36,38,40,43,44,45`;
  - seed3:
    `2,4,5,6,8,11,12,15,16,17,19,20,22,24,25,27,29,30,31,32,33,37,39,40,41,42,43,44,45,46`;
  - seed4:
    `0,2,5,6,10,11,12,14,21,22,23,27,30,33,34,36,38,39,43,44,47,48,49,50,52,54,56,57,59,60`;
  - seed5:
    `0,3,5,6,7,8,9,11,12,13,14,15,16,18,20,21,24,25,26,28,30,31,32,33,34,35,36,37,38,41`.
- Old-anchor-paired accepted counts are `28,28,24,24,29` by seed, for
  133 total. The 17 later-stream replacements are paired exactly across the
  four new corners only and are not represented as paired to old anchors.
- The v3 ledgers contain 25 rejected candidate identities: five migrated v2
  frontier candidates plus 20 newly executed v3 rejections. The preserved
  v1/v2 ledgers contain 92 failed simulator attempt executions, including the
  original seed4 candidate4 and seed5 candidate1 evidence. Thus 112 actual
  failed executions are preserved without double-counting migrated candidate
  identities.
- HDF5 job `36056459` completed 5/5. Exactly 20 new HDF5 files validate, each
  with 60 episodes and frozen 54/6 train/valid masks.
- The first training submission `36057059`--`36057078` failed/cancelled before
  learner entry because `PROJECT_DIR` selected the wrong code root; it created
  zero checkpoints. Identical-config retries `36057105`--`36057124` completed
  20/20 from-scratch policies.
- All 45 selected checkpoint paths and hashes were frozen before formal
  rollout outcome inspection. The unified checkpoint manifest SHA-256 is
  `91e47d35b5f621f49dc4aba3b3a1d316131b6a080645e5089f62575bfa5fb326`.
- Primary job `36059233` stopped before policy loading because the
  composition loader rejected the immutable Stage 2 five-condition metadata
  order. It created zero rows. A profile-scoped compatibility correction
  passed tests; identical-input retry `36059244` completed 200/200 tasks and
  5,000/5,000 rows.
- Secondary job `36061752` completed 188 tasks and had 12 tasks
  `PREEMPTED` on `erc-hpc-comp054`. Their 40 partial rows were archived by
  task ownership. Identical-input retry `36062210` completed 12/12, yielding
  200/200 tasks and 5,000/5,000 rows.
- Strict merge passed:
  - 400/400 new tasks and 10,000/10,000 new rows;
  - common absolute: 45 policies, 450 tasks, 11,250 rows;
  - RMAX40: 45 policies, 450 tasks, 11,250 rows.
- Final relevant tests passed 52/52.

The frozen interaction classification is `interaction`. Primary contrast
results are:

| Contrast | Five canonical-seed values | Mean | SD | Bootstrap 95% | Sign | Signal |
|---|---|---:|---:|---|---:|---|
| `I_tight_15` | -0.556, 0.044, 0.388, 0.648, 0.288 | 0.1624 | 0.4562 | [-0.2184, 0.4752] | 4/5 | yes |
| `I_tight_35` | -0.572, 0.140, 0.088, 0.264, 0.048 | -0.0064 | 0.3265 | [-0.3056, 0.1896] | 1/5 | no |
| `I_wide_15` | -0.200, -0.012, 0.024, 0.280, 0.712 | 0.1608 | 0.3524 | [-0.0800, 0.4432] | 3/5 | no |
| `I_wide_35` | 0.064, -0.076, 0.396, 0.156, 0.112 | 0.1304 | 0.1722 | [0.0080, 0.2816] | 4/5 | yes |

Common-absolute combined means are:

| Condition | Rate |
|---|---:|
| `START15_APP3P6` | 0.4944 |
| `START15_APP6` | 0.3720 |
| `START15_APP8P4` | 0.2840 |
| `START25_APP3P6` | 0.4496 |
| `START25_APP6` | 0.4896 |
| `START25_APP8P4` | 0.2408 |
| `START35_APP3P6` | 0.2872 |
| `START35_APP6` | 0.3336 |
| `START35_APP8P4` | 0.2152 |

RMAX40 ID/OOD means are:

| Condition | ID | OOD | ID-OOD |
|---|---:|---:|---:|
| `START15_APP3P6` | 0.7584 | 0.2688 | 0.4896 |
| `START15_APP6` | 0.5776 | 0.2208 | 0.3568 |
| `START15_APP8P4` | 0.4176 | 0.1488 | 0.2688 |
| `START25_APP3P6` | 0.4784 | 0.3168 | 0.1616 |
| `START25_APP6` | 0.4784 | 0.3600 | 0.1184 |
| `START25_APP8P4` | 0.2736 | 0.1776 | 0.0960 |
| `START35_APP3P6` | 0.2800 | 0.2512 | 0.0288 |
| `START35_APP6` | 0.3200 | 0.3280 | -0.0080 |
| `START35_APP8P4` | 0.1792 | 0.1632 | 0.0160 |

All five frozen 3 x 3 leaderboards, ordered by success rate, are:

1. Primary common-absolute combined:
   `START15_APP3P6` 0.4944 >
   `START25_APP6` 0.4896 >
   `START25_APP3P6` 0.4496 >
   `START15_APP6` 0.3720 >
   `START35_APP6` 0.3336 >
   `START35_APP3P6` 0.2872 >
   `START15_APP8P4` 0.2840 >
   `START25_APP8P4` 0.2408 >
   `START35_APP8P4` 0.2152.
2. Common-inner:
   `START15_APP3P6` 0.6512 >
   `START25_APP6` 0.5456 >
   `START25_APP3P6` 0.5184 >
   `START15_APP6` 0.4720 >
   `START15_APP8P4` 0.3872 >
   `START35_APP3P6` 0.3056 =
   `START35_APP6` 0.3056 >
   `START25_APP8P4` 0.2528 >
   `START35_APP8P4` 0.2256.
3. Common-outer:
   `START25_APP6` 0.4336 >
   `START25_APP3P6` 0.3808 >
   `START35_APP6` 0.3616 >
   `START15_APP3P6` 0.3376 >
   `START15_APP6` 0.2720 >
   `START35_APP3P6` 0.2688 >
   `START25_APP8P4` 0.2288 >
   `START35_APP8P4` 0.2048 >
   `START15_APP8P4` 0.1808.
4. Condition-relative RMAX40 ID:
   `START15_APP3P6` 0.7584 >
   `START15_APP6` 0.5776 >
   `START25_APP3P6` 0.4784 =
   `START25_APP6` 0.4784 >
   `START15_APP8P4` 0.4176 >
   `START35_APP6` 0.3200 >
   `START35_APP3P6` 0.2800 >
   `START25_APP8P4` 0.2736 >
   `START35_APP8P4` 0.1792.
5. Condition-relative RMAX40 OOD:
   `START25_APP6` 0.3600 >
   `START35_APP6` 0.3280 >
   `START25_APP3P6` 0.3168 >
   `START15_APP3P6` 0.2688 >
   `START35_APP3P6` 0.2512 >
   `START15_APP6` 0.2208 >
   `START25_APP8P4` 0.1776 >
   `START35_APP8P4` 0.1632 >
   `START15_APP8P4` 0.1488.

Primary combined within-row Approach rankings are
`APP3P6 > APP6 > APP8P4` at START15 and
`APP6 > APP3P6 > APP8P4` at both START25 and START35. Within-column Start
rankings are `START15 > START25 > START35` for APP3P6 and APP8P4, and
`START25 > START15 > START35` for APP6.

The RMAX40 Pareto front is `START15_APP3P6` and `START25_APP6`. It remains a
condition-relative secondary view; cross-Start banks are not one common
absolute deployment distribution.

## What Worked

- Deterministically continuing candidate 31, 32, 33, and so on resolved
  dynamic candidate failures without adding accepted samples, adding a
  physical perturbation, or condition-specific cherry-picking.
- Atomic four-corner staging, failure archival and crash/resume semantics
  preserved exact four-corner pairing and final exact-30 datasets.
- Common-absolute reuse supplied exact nine-condition state/runtime-RNG/PCD-RNG
  pairing for the primary interaction contrasts.
- Same-Start RMAX40 reuse preserved the correct condition-relative pairing
  scope without pretending cross-Start states were identical.
- Checkpoint selection remained highest numeric emitted epoch and was frozen
  before rollout.
- Scoped infrastructure retries reused identical configs, checkpoints,
  manifests, states and seeds.
- The 25 old checkpoints, 25 old HDF5 files and five frozen top-level anchor
  hashes all revalidated with zero mismatch.

## What Didn't Work

- Protocol v1 stopped on the first scientific corner failure. Its job
  `36053381` recorded seed4 candidate4 and seed5 candidate1
  `START35_APP8P4` failures; this evidence remains immutable.
- Protocol v2 derived new runtime seeds but the paired-latent simulator path
  had no seed-coupled physics draw. Its 92 failed attempts were
  content-identical apart from provenance metadata. Job `36054403` was
  cancelled after the causal audit. Do not resume this obsolete loop.
- The first HDF5 parallel tasks concurrently wrote `datasets.json`, causing
  lost small-manifest fields. All HDF5 files were valid; sequential
  consolidation restored the manifest without rebuilding a file.
- The initial training export pointed to the wrong code root. It failed before
  training and created no checkpoint.
- The initial primary loader required nine-condition metadata even for the
  immutable original five-condition manifests. The fix accepts only the exact
  legacy Stage 2 order and only under the composition profile.
- Twelve RMAX40 tasks were preempted on `erc-hpc-comp054`. Partial outputs
  were excluded and archived; the retry also excludes that node.
- The first local analysis pass produced a NumPy `int64` sign count that was
  not JSON serializable. It stopped before writing the frozen report. The
  count is now a built-in `int` with a regression test; no scientific input
  or rule changed.
- The rejected RMAX45 pilot remains audit evidence only. No `APP4P8`, physical
  perturbation, Stage 3 or other exploratory condition was launched.

## Key Files & Commands

Authority and final results:

```text
experiments/tro_stage2_position_composition/PLAN.md
experiments/tro_stage2_position_composition/commands.md
experiments/tro_stage2_position_composition/analysis/comparison.json
experiments/tro_stage2_position_composition/analysis/summary.md
experiments/tro_stage2_position_composition/manifests/merge_validation.json
experiments/tro_stage2_position_composition/manifests/jobs.json
experiments/tro_stage2_position_composition/manifests/storage_inventory_v3.json
experiments/tro_stage2_position_composition/manifests/final_hashes_v3.json
```

Frozen protocol and checkpoint hashes:

```text
protocol_v3.json
  be77da99fb84195506f7fdf3bdd51feddcfa938047bad116fa40951a11d9c487
candidate_stream_v3.json
  7852a6cd23efb6e8a1bf4a8eb8e9359b6711787013f07428ec3e75ab4b67a7af
checkpoints.json
  91e47d35b5f621f49dc4aba3b3a1d316131b6a080645e5089f62575bfa5fb326
analysis/comparison.json
  8c44a3dd42752353f4dc48c5b240d9198ca2fcc5030e1aa552761b5c1e96f0c5
```

Validation commands:

```bash
/scratch/users/k23114984/conda/arcap/bin/python \
  scripts/tro_position_composition.py strict-merge
/scratch/users/k23114984/conda/arcap/bin/python \
  scripts/analyze_tro_position_composition.py
/scratch/users/k23114984/conda/arcap/bin/python -m pytest -q \
  tests/test_tro_position_mvp0.py \
  tests/test_tro_position_confirmation.py \
  tests/test_tro_position_stage2.py \
  tests/test_tro_position_stage2_idood.py \
  tests/test_tro_position_composition.py
```

Storage:

- dataset namespace: 32,703,499,054 bytes;
- new model namespace: 15,683,479,273 bytes;
- no automatic cleanup was performed;
- user-approval-only candidates are smoke output (59,675,769 bytes) and
  34 unselected checkpoints (9,863,628,940 bytes).

The worktree remains intentionally dirty. Protected untracked files `[`,
`count=0`, `done` and `fi` remain present. No commit, push or PR was made.

## Next Steps

None for Stage 2c execution. Review the frozen analysis and storage cleanup
candidates. Any cleanup, Stage 3, Rotation, Velocity, compatibility modelling,
AR guidance or human study requires a separate user decision and authority.

## Open Questions

None.

## Changelog

- 2026-07-26: Created after GO-to-composition and recorded v1 scientific
  failures, v2 amendment, v2 runtime-RNG blocker and v3 candidate-stream
  authority.
- 2026-07-27: Replaced blocker-era status with the complete Gate 0--8
  execution, terminal scheduler ledger, strict surfaces, frozen interaction
  result, ID/OOD diagnostics, hashes, storage inventory and stop boundary.
- 2026-07-27: Added all five complete 3 x 3 leaderboards plus the primary
  within-row and within-column rankings.
