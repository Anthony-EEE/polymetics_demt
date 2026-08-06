# T-RO Stage 2 Position condition-relative ID/OOD rerollout notes

## Active RMAX40 v2 amendment

The user authorised `R_MAX=0.40 m` and continuation through Definition of
Done. The rejected RMAX45 pilot below remains immutable. Active artifacts use
protocol ID
`tro_stage2_position_axial_condition_relative_idood_rerollout_rmax40_v2`,
manifest directory `manifests/rollout_5seed_rmax40/` and rollout directory
`dataset/tro_position_stage2_axial_idood_rerollout/rmax40/`.

The active reachable-conditioned distribution passed its explicit Gate 2
criteria: 30/30 manifests, 25 jointly reachable states per manifest, every
manifest containing all four XZ quadrants, pooled ID area quantiles
`[0.0288,0.9883]`, pooled OOD area quantiles `[0.0213,0.9753]`, and exact
same-Start/cross-Start/RNG pairing. All 32 tests passed.

RMAX40 smoke job `36043096` completed all six paths with 25/25 rows and exact
manifest/checkpoint hashes. Formal array `36043712` was then submitted with
250 tasks and `%40` throttle. It completed 249 tasks; task 245 was preempted
after 33 seconds. Its one partial row and logs were archived before identical
input retry job `36049746`, which completed. No performance-dependent retry
occurred.

Strict merge job `36050269` validated 250/250 summaries and 6,250/6,250 rows,
including 125 ID and 125 OOD rows per policy, all 25 checkpoint hashes,
condition-specific bounds, state order, same-Start absolute pairing,
cross-Start normalized pairing and runtime/point-cloud RNG. An earlier merge
attempt `36050142` exposed an aggregate-only field assumption in the
validator; the validator was corrected without changing rollout artifacts.

Analysis job `36050433` completed. The condition-level means are:

| Condition | ID | OOD | OOD − ID |
|---|---:|---:|---:|
| `START15_APP6` | 0.578 | 0.221 | -0.357 |
| `START35_APP6` | 0.320 | 0.328 | +0.008 |
| `START25_APP3P6` | 0.478 | 0.317 | -0.162 |
| `START25_APP6` | 0.478 | 0.360 | -0.118 |
| `START25_APP8P4` | 0.274 | 0.178 | -0.096 |

The primary ID/OOD Pareto front is `START15_APP6` and `START25_APP6`.
Balanced scores remain descriptive only because the absolute ID/OOD intervals
differ across Start families.

## Implemented

- Added the independent evaluator profile `tro_position_stage2_idood`; the
  completed `tro_position_stage2` profile and its manifests remain unchanged.
- Added Gate 0 checkpoint and old-analysis revalidation in
  `scripts/tro_position_stage2_idood.py`.
- Frozen 30 formal manifests under `manifests/rollout_5seed/`.
- Enforced whole-triplet candidate rejection across Start radii 0.15, 0.25
  and 0.35 m.
- Enforced shared normalized area quantile, XZ direction, state index,
  runtime RNG and point-cloud RNG across Start families.
- The three `START25_*` conditions reference the same Start25 manifest and
  therefore share absolute states and state IDs exactly.
- Added strict merge/analysis, Slurm rollout/smoke/merge/analysis entry
  points, and condition-relative tests.

## Rejected RMAX45 Gate 2 pilot

Manifest feasibility produced valid radii and 25 jointly reachable states for
every seed/bank group, but the reachable-conditioned OOD direction
distribution was persistently biased. Across the 125 unique normalized OOD
states, XZ quadrant counts were `[5, 41, 11, 68]`, compared with
`[33, 34, 34, 24]` for ID. Every OOD rollout seed showed the same directional
depletion, and joint-triplet rejection counts were 21, 34, 33, 55 and 24.

Per PLAN section 4, this triggers a mandatory stop. `R_MAX` remains 0.45 m;
no bounds or sampling distribution were altered. No formal rerollout was
submitted.

The first six-path smoke array, job `36042451`, reached execution before the
stop/cancel command and failed immediately because the smoke script used
`horizon=1`, which did not exactly match the frozen manifest protocol. No
policy rollout row was produced. The script has been corrected to
`horizon=200`, but it was deliberately not resubmitted because the independent
scientific feasibility stop already prevents policy evaluation.

## Validation

- Unified checkpoint manifest:
  `240a936999281f429dd1b043b19df5bd9291ed478933305a7c051c5183227580`.
- All 25 checkpoint file hashes were recomputed successfully.
- Old Stage 2 analysis hashes remained:
  - `comparison.json`:
    `c70020fe70ab5aae9959ea990e66a2e2f3c4af4c05f24557a79d64c973ef9113`
  - `summary.md`:
    `825a13e358b01e8707c99e1f19673b01d46df62edbacecce12bff6bbc6684370`
- Existing Stage 1/confirmation/Stage 2 tests plus the new ID/OOD tests:
  `32 passed`.
- The manifest validator reports 30/30 valid manifests, exact same-Start
  absolute pairing and exact cross-Start normalized/RNG pairing.
