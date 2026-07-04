# DEMT Rebuttal Workflow Artifacts

This directory stores claim-driven rebuttal artifacts produced from the current
workflow.

Current reviewed claim after strict revision:

```text
DEMT-selected P/R/V structures are learner-relevant and human-trainable under
the fixed learner and N=30 budget. The concrete Table 5 AR thresholds should be
defended as bounded / constrained finite candidates, not literal global optima.
```

Key current files:

- `claim_ledger.md`: Agent2 claim ledger and allowed wording.
- `experiment_queue.md`: Agent2 queue after the three-agent bounded-optimality
  audit; E05 fixed-ratio spatial funnel sweep is the main new experiment if a
  stronger spatial parameter claim is needed.
- `agent1_results/E00_human_percentile_bound_audit.md`: compact
  human-compatibility bound table for P/R/V candidate values.
- `agent1_results/E01_human_spatial_stats_v2.md`: read-only human spatial
  diagnostics result card.
- `agent1_results/E03_human_orientation_diagnostics_v2.md`: human orientation
  diagnostics plus Week 1 learner evidence result card.
- `agent1_results/E04_human_temporal_diagnostics_v2.md`: human temporal
  diagnostics plus Week 1 learner evidence result card.
- `agent3_reviews/R04_global_optimal_pressure_review.md`: current strict
  reviewer / PI critique and verdict.
- `agent3_reviews/R03_strict_parameter_review.md`: identifies the 25 cm logic
  flaw but is superseded by R04's bounded-optimality framing.
- `agent3_reviews/R02_full_rebuttal_review.md`: superseded; do not cite as the
  current verdict.
- `rebuttal_fragments/parameter_reasonableness_claim.md`: concise rebuttal
  wording.

Do not use these artifacts to claim exact global optimality or full numeric
threshold justification for every Table 5 value.
