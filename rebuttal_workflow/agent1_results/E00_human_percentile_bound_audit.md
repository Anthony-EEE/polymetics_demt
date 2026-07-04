# Agent1 Result Card: E00 Human Percentile Bound Audit

Experiment ID:
E00_human_percentile_bound_audit

Purpose:
Create a compact human-compatibility table for Table 5 parameter alternatives
before any expensive finite-candidate training sweep.

Agent2 request:
Compute P/R/V mean, standard deviation, percentiles, and coverage for nearby
candidate thresholds. Use this only as compatibility evidence, not as learner
optimality evidence.

Code changes:
None. This was a read-only derived analysis over existing V2 diagnostics.

Commands / Slurm jobs:

```bash
mkdir -p outputs/rebuttal_workflow
python - <<'PY'
# One-off CSV aggregation over outputs/week2_human_diagnostics_keypoints_v2.
# See shell history for the exact aggregation body.
PY
```

Data generated:

```text
outputs/rebuttal_workflow/human_percentile_bound_audit.csv
```

Models generated:
None.

Primary metric:
Coverage of candidate spatial radii, orientation tolerances, and temporal ratio
windows against real-user diagnostic distributions.

Secondary metrics:
Mean, standard deviation, p50, p75, p90, p95, and max for each group and metric.

Verification performed:

```text
Input demo_metrics.csv V2 diagnostics:
  frame_stride = 10
  mirror_y_applied = true
  P1/P2/P6/P7 each have n = 120 demos
  P8 target/control each have n = 30 demos

Output CSV rows = 36
```

Primary facts:

```text
Spatial nearest-to-corridor-plane x-z radius to group mean:
  P1 pre p95 = 18.28 cm; coverage 10/15/20/25/30 cm =
    65.0 / 86.7 / 95.0 / 100.0 / 100.0%
  P2 pre p95 = 26.70 cm; coverage 10/15/20/25/30 cm =
    32.5 / 60.0 / 80.8 / 90.8 / 98.3%
  P6 post p95 = 9.49 cm; P7 post p95 = 6.67 cm

Orientation angle to group mean at grasp-relevant events:
  P6 post closest_grasp p95 = 13.14 deg; coverage 15 deg = 100.0%
  P6 post first_close   p95 = 13.47 deg; coverage 15 deg = 100.0%
  P7 post closest_grasp p95 = 14.33 deg; coverage 15 deg = 99.2%
  P7 post first_close   p95 = 13.59 deg; coverage 15 deg = 99.2%

Temporal ratios to group median:
  duration coverage [0.5, 2.0] = 86.7% to 100.0% across groups
  mean-speed coverage [0.5, 2.0] = 93.3% to 100.0% across groups
  tighter [0.8, 1.25] coverage is lower, especially for P1/P2/P8 control.
```

Failures / warnings:

- This audit is observational human-compatibility evidence only.
- Pre-training mean/std or percentiles can restate weak unguided behavior if
  used as a direct sampling distribution.
- The spatial metric is a local nearest-to-corridor-plane keypoint, not
  full-trajectory MPCV.
- Temporal ratios are to group medians, not the submitted paper's per-user
  `v_ref`.

Can this support the requested claim? partial

Reason:
The audit supports that Table 5 values sit in plausible human-compatible
regions: 25 cm is a permissive outer spatial envelope, 15 deg matches
post-training grasp consistency, and `[0.5, 2.0]` is a broad pacing window. It
does not prove learner optimality or bounded Pareto optimality by itself.

Next engineering action if requested:
Use this table to choose finite candidates for E05 fixed-ratio spatial funnel
sweep. Do not start human-derived P/R/V sampling from raw pre-training
mean/std without a learner-evaluation plan.
