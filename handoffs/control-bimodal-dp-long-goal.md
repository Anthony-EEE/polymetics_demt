# Handoff: Completed Control-Derived Bimodal Diffusion Policy Experiment

_Last updated: 2026-08-08 · Branch: `hpc-headless-rebuttal` @ `72ca390`_

## Goal

Build and validate the isolated `simulation_control_bimodal_group` experiment:
ten Control-derived bimodal policies `CB01`–`CB10`, exact index matching to
Target-derived `B01`–`B10`, 200 sealed rollouts, route/success statistics, and
an auditable Control-Bimodal versus Target-Bimodal comparison.

## Current Progress

The experiment is **complete**. Pairing, shuffled views, ten physical HDF5
files, training, independent model validation, 200 rollouts, formal analysis,
and the CBxx–Bxx comparison all passed their final readback audits.

- Pairing manifest SHA-256:
  `86cbe45062b32225e4e3233339c4dfd417954f2c7111cb35fd5a7d84c38895e5`.
- Ten epoch-40 policies trained by Slurm array `36382599`; all tasks
  `COMPLETED 0:0`, with no retry or participant-specific tuning.
- Ten real CPU model loads/inference smokes passed. Model validation SHA-256:
  `d48f4726471747c49fae1929bea9cf1bb57a8c877d2871d42e128296577edc5a`.
- Slurm rollout array `36387361` produced 200 result JSONs and 200 complete,
  content-distinct videos; all tasks `COMPLETED 0:0`, with no infrastructure
  failure, retry, replacement, or rerun.
- The final analysis contains exactly 11 required files and independently
  validates ten policies, 200 unique rollout keys/seeds/videos, ten matched
  policy comparisons, and all frozen upstream hashes.
- `validation_report.json` SHA-256:
  `05c6e00329f57bba47b6c145241fc3467cbf01ac8e9d60ed6f99fa2c2bb26cfd`.
- `final_results.json` SHA-256:
  `9692971a7182e9b9e3918f8923f517b7ad72cd6aefc488807f3e3976129cfca5`.
- `bimodal_comparison.json` SHA-256:
  `eb4f353df53bbf6116fce6f3ad7103f5df096006f8e0a4a88c32b74e6d48f463`.

### Frozen pair mapping

| Pair | Control-Bimodal sources | Target-Bimodal sources |
|---|---|---|
| CB01 / B01 | C01 (L) + C07 (R) | T01 (L) + T07 (R) |
| CB02 / B02 | C03 (L) + C06 (R) | T03 (L) + T06 (R) |
| CB03 / B03 | C03 (L) + C07 (R) | T03 (L) + T07 (R) |
| CB04 / B04 | C03 (L) + C10 (R) | T03 (L) + T10 (R) |
| CB05 / B05 | C05 (L) + C10 (R) | T05 (L) + T10 (R) |
| CB06 / B06 | C05 (L) + C09 (R) | T05 (L) + T09 (R) |
| CB07 / B07 | C03 (L) + C09 (R) | T03 (L) + T09 (R) |
| CB08 / B08 | C04 (L) + C06 (R) | T04 (L) + T06 (R) |
| CB09 / B09 | C02 (L) + C10 (R) | T02 (L) + T10 (R) |
| CB10 / B10 | C04 (L) + C08 (R) | T04 (L) + T08 (R) |

### Pooled Control-Bimodal versus Target-Bimodal

`Success/route total` is the route-conditional success rate. Indeterminate
rollouts remain in the overall denominator.

| Metric | Control-Bimodal (CB) | Target-Bimodal (B) | CB − B |
|---|---:|---:|---:|
| Realised L routes | 50/200 (25.0%) | 44/200 (22.0%) | +3.0 pp |
| **L-route total success** | **22/50 (44.0%)** | **20/44 (45.5%)** | **−1.5 pp** |
| Realised R routes | 115/200 (57.5%) | 115/200 (57.5%) | 0.0 pp |
| **R-route total success** | **47/115 (40.9%)** | **53/115 (46.1%)** | **−5.2 pp** |
| Indeterminate routes | 35/200 (17.5%) | 41/200 (20.5%) | −3.0 pp |
| Indeterminate success | 0/35 (0.0%) | 0/41 (0.0%) | 0.0 pp |
| **Overall success** | **69/200 (34.5%)** | **73/200 (36.5%)** | **−2.0 pp** |
| Participant-policy mean ± sample SD | 34.5% ± 10.9% | 36.5% ± 13.3% | matched mean −2.0 pp |

The sample SD of the ten matched policy-level overall-success differences is
17.8 percentage points (`n=10`, `ddof=1`). CB has 12 more primary cylinder
topples and 8 fewer primary target misses than B.

### Detailed per-policy comparison

| Pair | CB L/R/I | B L/R/I | CB overall | B overall | CB − B |
|---|---:|---:|---:|---:|---:|
| CB01 / B01 | 6/11/3 | 4/10/6 | 10/20 (50%) | 6/20 (30%) | +20 pp |
| CB02 / B02 | 7/9/4 | 2/15/3 | 7/20 (35%) | 11/20 (55%) | −20 pp |
| CB03 / B03 | 5/13/2 | 1/15/4 | 8/20 (40%) | 11/20 (55%) | −15 pp |
| CB04 / B04 | 3/14/3 | 1/15/4 | 5/20 (25%) | 5/20 (25%) | 0 pp |
| CB05 / B05 | 5/11/4 | 7/9/4 | 8/20 (40%) | 6/20 (30%) | +10 pp |
| CB06 / B06 | 1/15/4 | 4/11/5 | 8/20 (40%) | 4/20 (20%) | +20 pp |
| CB07 / B07 | 6/11/3 | 8/7/5 | 2/20 (10%) | 7/20 (35%) | −25 pp |
| CB08 / B08 | 7/9/4 | 5/13/2 | 7/20 (35%) | 6/20 (30%) | +5 pp |
| CB09 / B09 | 6/10/4 | 5/11/4 | 6/20 (30%) | 11/20 (55%) | −25 pp |
| CB10 / B10 | 4/12/4 | 7/9/4 | 8/20 (40%) | 6/20 (30%) | +10 pp |

### Per-policy L/R success

Each cell is `successes / realised route count (conditional success rate)`.

| Pair | CB L success | B L success | CB R success | B R success |
|---|---:|---:|---:|---:|
| CB01 / B01 | 2/6 (33.3%) | 1/4 (25.0%) | 8/11 (72.7%) | 5/10 (50.0%) |
| CB02 / B02 | 7/7 (100.0%) | 0/2 (0.0%) | 0/9 (0.0%) | 11/15 (73.3%) |
| CB03 / B03 | 1/5 (20.0%) | 0/1 (0.0%) | 7/13 (53.8%) | 11/15 (73.3%) |
| CB04 / B04 | 0/3 (0.0%) | 0/1 (0.0%) | 5/14 (35.7%) | 5/15 (33.3%) |
| CB05 / B05 | 1/5 (20.0%) | 2/7 (28.6%) | 7/11 (63.6%) | 4/9 (44.4%) |
| CB06 / B06 | 0/1 (0.0%) | 2/4 (50.0%) | 8/15 (53.3%) | 2/11 (18.2%) |
| CB07 / B07 | 1/6 (16.7%) | 6/8 (75.0%) | 1/11 (9.1%) | 1/7 (14.3%) |
| CB08 / B08 | 5/7 (71.4%) | 2/5 (40.0%) | 2/9 (22.2%) | 4/13 (30.8%) |
| CB09 / B09 | 3/6 (50.0%) | 4/5 (80.0%) | 3/10 (30.0%) | 7/11 (63.6%) |
| CB10 / B10 | 2/4 (50.0%) | 3/7 (42.9%) | 6/12 (50.0%) | 3/9 (33.3%) |

### Route classification and B01 clarification

`indeterminate` is an observed route category, not uncertainty about a
completed left/right pass. Route is recomputed from the policy-step box trace:

- Inside the obstacle y-band, whose half-width is
  `OBSTACLE_RADIUS + BOX_HALF_EXTENT = 0.075 m`, compare the median box x with
  obstacle x. Smaller is L; otherwise it is R.
- If the box trace never enters that y-band, the rollout is `indeterminate`.
  Typical causes are dropping the box early, moving away, remaining near the
  start, or timing out before reaching the obstacle. Such outcomes stay in the
  overall denominator and are never forced into L or R.

B01 has 20 rollouts: 4 L, 10 R, and 6 indeterminate. It succeeds on 1/4 L,
5/10 R, and 0/6 indeterminate outcomes, for 6 successes and 14 failures
overall (30%). Its 14 primary failures are ten cylinder topples and four
target misses.

The specifically inspected video
`B01/videos/case_00_repeat_0_execution_0.mp4` is a valid scientific failure:
`policy_timeout`, `target_xy_error=4.354202415652407 m`, cylinder tilt about
90 degrees, and route `indeterminate`. It is not a corrupt video or an
infrastructure failure.

## What Worked

- Exact index matching preserved the same pair order, mixture positions,
  train/valid split stream, evaluation cases, repeats, and policy-sampling
  seeds between `CBxx` and `Bxx`.
- Ten standalone 60-trajectory HDF5 files passed flush/close/reopen and
  dataset-by-dataset Control-source equality checks. They contain 600
  memberships and 300 unique Control trajectories.
- Uniform training matched the frozen Target-Bimodal protocol hash
  `6c309f4330939e5dede194de669bae3ea167e2978262de906ff970f5a18fd77d`.
- Atomic creators, exclusive output refusal, independent model loading,
  200-video content hashing, route recomputation, and success recomputation all
  caught partial or inconsistent output before publication.
- The final plot was visually inspected and the complete 11-file analysis set
  passed an independent hash/readback audit.

## What Didn't Work

- The original repeat-pose gate of 10 micrometres / 0.01 degrees was too
  strict for contact dynamics. It rejected CB01 case 0 and CB09 case 5, whose
  largest box-position delta was 1.715 mm and largest box-orientation delta was
  2.522 degrees.
- The analyzer initially failed closed and published no analysis, as required
  by the original plan. The user then explicitly judged millimetre-scale
  repeat variation realistic and authorized a post-rollout engineering
  envelope of 2 mm / 3 degrees. All 100 repeat pairs pass that envelope.
- The final artifacts transparently retain both facts:
  `original_gate_passed=false`, `original_gate_violating_pair_count=2`,
  `amended_gate_passed=true`, and `amended_gate_violating_pair_count=0`.
  No rollout was rerun or replaced, and the amendment is not presented as
  preregistered.
- The 600 HDF5 memberships are not 600 independent demonstrations; they reuse
  300 unique Control trajectories with intentionally unequal source
  multiplicity.
- The 200 matched rollout keys are useful descriptive common-random-number
  pairs, but the inferential unit remains the ten participant-level policies.

## Key Files & Commands

- Live ledger: `agents_working/control-bimodal-simulation.md`.
- Formal result:
  `rebuttal_dataset/simulation_control_bimodal_group/analysis/final_results.json`.
- Formal comparison:
  `rebuttal_dataset/simulation_control_bimodal_group/analysis/bimodal_comparison.json`.
- Detailed comparison CSV:
  `rebuttal_dataset/simulation_control_bimodal_group/analysis/bimodal_comparison.csv`.
- Per-policy rates:
  `rebuttal_dataset/simulation_control_bimodal_group/analysis/participant_success_rates.csv`.
- All-rollout table:
  `rebuttal_dataset/simulation_control_bimodal_group/analysis/rollout_results.csv`.
- Validation report:
  `rebuttal_dataset/simulation_control_bimodal_group/analysis/validation_report.json`.
- Plot:
  `rebuttal_dataset/simulation_control_bimodal_group/analysis/route_success_summary.png`.
- Analyzer:
  `examples/rebuttal_control_bimodal_pipeline/analyze_control_bimodal_results.py`.

Regression command:

```bash
/scratch/users/k23114984/conda/arcap/bin/python -m pytest -q \
  tests/test_rebuttal_control_bimodal_pipeline.py \
  tests/test_rebuttal_bimodal_pipeline.py
```

The last run passed `21/21`. Do not rerun the final analyzer in-place: its
exclusive publication contract correctly refuses to overwrite the existing
`analysis/` root.

## Next Steps

1. No experiment or Slurm work remains; both arrays are terminal and have no
   active tasks.
2. Use `final_results.json` and `bimodal_comparison.json` as the authoritative
   paper/report inputs. Use the CSVs for plotting or further descriptive
   tables.
3. When reporting repeat equivalence, state both the original-gate result and
   the user-authorized 2 mm / 3 degree engineering interpretation.
4. Preserve Control, Target, existing Target-Bimodal, and all sealed rollout
   artifacts as read-only.

## Changelog

- 2026-08-08: Created the planning-only Control-derived Bimodal long-goal
  handoff; no experiment task had started.
- 2026-08-08: Updated the handoff after full completion with jobs, validation
  evidence, protocol-amendment disclosure, pooled and per-policy CB-versus-B
  tables, and separate L/R total success rates.
- 2026-08-08: Added the exact `indeterminate` route definition, B01's
  success/failure breakdown, and the inspected B01 case-00 repeat-0 outcome.
