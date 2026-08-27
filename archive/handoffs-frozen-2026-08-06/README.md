# Frozen Handoffs: DEMT AR-Guidance Work

_Frozen: 2026-08-06_

These files are historical records, not active instructions. Fresh agents must
not read this directory by default. The only active handoff is
`handoffs/handoff_rebuttal.md`; consult this archive only when the user
explicitly requests a historical audit or an older artifact must be traced.

## Final Historical Outcome

The earlier AR-settings anti-cherry-picking experiment was completed and closed.
Under a fixed learner and 30 demonstrations per condition, the final paired N50
deployment results were:

```text
Position S15/S20/S25/S30/S35: 36% / 36% / 36% / 26% / 14%
Contact  R00/R15/R30:         60% / 74% / 64%
Temporal VR1P5/V050_200/VR3/VR4:
                               74% / 74% / 66% / 36%
```

The accepted claim is bounded finite-candidate support for the selected AR
settings under this robot, task, learner, protocol, and data budget. These
experiments do not establish a unique or continuous-space global optimum.

Human P6/P7 diagnostics independently showed post-training tightening in
spatial, orientation, and temporal behavior. In particular, post-training
orientation p95 was about 13--14 degrees, supporting 15 degrees as a
human-compatible candidate.

Authoritative historical result paths:

- `reports/position-rotation-temporal-n50-final.md`
- `dataset/ar_guidance_spatial_S15_S35/policy_rollouts_seed628_shared_r35_paired_n50_h200/summary_seed628_n50.json`
- `dataset/orn_mvp_full/policy_rollouts_seed628_paired_n50_h200/summary_seed628_n50.json`
- `dataset/temporal_vref_reciprocal_spatial_v2/policy_rollouts_seed628_paired_n50_h200/summary_seed628_n50.json`

## Superseded or Invalid Evidence

- `dataset/abla1_full` used invalid legacy spatial geometry and must not be
  cited.
- The old `P00/P01/P10/P11` 2x2 spatial design is history, not the formal
  S15--S35 result.
- N10 results are diagnostics only and must not replace or be combined with
  formal N50 aggregates.
- The 2026-07-18 fixed-point reciprocal temporal run was invalid and its
  dedicated artifacts were deleted; use only the corrected spatially
  distributed reciprocal result.
- Human percentile coverage establishes compatibility, not learner optimality.

## Archived Files

- `ar-guidance-ood-human-logic.md`
- `ar-guidance-spatial-temporal-experiments.md`
- `corl-demt-ar-settings-experiment-closure.md`
- `multiagent_history_example.md`
- `position-contact-n50-rollouts.md`
- `rebuttal_bounded_optimality_goal.md`
- `temporal-vref-experiment-plan.md`
- `temporal-vref-reciprocal-experiment.md`
- `week1_main-experiments.md`
- `week1_research_thinking.md`
- `week2_experiment.md`
- `week2_research_thinking.md`

The individual files are preserved verbatim for provenance and are frozen.
