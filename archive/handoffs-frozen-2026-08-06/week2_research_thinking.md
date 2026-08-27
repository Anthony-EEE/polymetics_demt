# Handoff: Week 2 Research Thinking

_Last updated: 2026-07-03 · Branch: hpc-headless-data-collection @ 73d56df_

## Goal
Maintain the Week 2 scientific framing after the supervisor meeting. The aim is to turn the Week 1 rebuttal MVPs into a cleaner research program: answer potential CoRL reviewer questions conservatively, prepare stronger ICRA-ready experiments by mid-September if needed, and keep journal extensions aligned with real human behavior.

## Current Progress
- Supervisor meeting reframed the work around `P/R/V`:
  - Spatial: dense/clustered demonstrations are expected to help a fixed learner under the small `N=30` budget.
  - Orientation: a tolerance sweep is scientifically reasonable because humans cannot realistically maintain exact `0 deg` gripper orientation.
  - Temporal: the submitted paper used each person's first trajectory to set `v_ref`; this is not ideal because the temporal threshold is not a fixed global number like radius or degree, but the current paper can still be defended with careful wording.
- Rebuttal strategy:
  - Admit the submitted paper did not fully run these parameter experiments.
  - If reviewers ask, frame Week 1/Week 2 evidence as finite candidate sensitivity analysis, not global parameter optimization.
  - If reviewers do not ask, keep this work for ICRA/journal expansion.
- Longer-term strategy:
  - If CoRL is rejected in early September, use the new parameter experiments and human-data diagnostics to strengthen a next submission for ICRA by mid-September.
  - Journal version can include redesigned AR guidance and possibly new human training/data collection with updated parameters.
- Human-data policy:
  - All data under `/scratch/users/k23114984/pybullet_data` should be treated as real human demonstrations.
  - Pooled, shuffled, symlinked, or re-split datasets are still real-user data. Do not question them as fake or cheating.
  - Safe wording: `pooled and re-split real-user demonstrations`.
- PDF/human protocol facts checked:
  - P1: prism, no guidance, trained-task pre-test.
  - P2: cube, no guidance, unseen-object pre-test.
  - P6: prism, no guidance, trained-task post-test.
  - P7: cube, no guidance, unseen-object post-test.
  - P8: ordered pick-and-place, no guidance, unseen-task test.
  - Only unguided phases P1, P2, P6, P7, and P8 are used for robot learning.
- 2026-07-03 strict rebuttal claim status:
  - The earlier "finite-candidate parameter reasonableness" claim was too
    loose, but pure structure-level retreat is also too weak.
  - Current Agent3-style verdict is recorded in:
    - `rebuttal_workflow/agent3_reviews/R04_global_optimal_pressure_review.md`
  - Agent3 still asks for global optimality. Agent1/Agent2 must provide the
    strongest feasible bounded-optimality explanation.
  - The central claim ledger is:
    - `rebuttal_workflow/claim_ledger.md`
  - The concise rebuttal fragment is:
    - `rebuttal_workflow/rebuttal_fragments/parameter_reasonableness_claim.md`
- 2026-07-03 three-agent continuation completed the full Week1/Week2 audit.
  The converged queue is:
  - `rebuttal_workflow/experiment_queue.md`
  The read-only human compatibility audit is:
  - `rebuttal_workflow/agent1_results/E00_human_percentile_bound_audit.md`
  - `outputs/rebuttal_workflow/human_percentile_bound_audit.csv`
  Current decision: E05 fixed-ratio spatial funnel sweep is the highest-value
  new experiment if a stronger `25 cm` claim is needed; temporal ladder,
  orientation bracket, and human-derived P/R/V sampling are backup/future-paper
  work unless the rebuttal explicitly needs them.

## What Worked
- Week 1 orientation story is the cleanest:
  ```text
  R00/R15/R30 rollout = 7/10, 6/10, 4/10
  ```
  This supports the idea that `15 deg` is a plausible human-feasible tolerance while `30 deg` degrades more.
- Week 1 latest temporal result is usable but should be improved:
  ```text
  T00/T20/Twide rollout = 10/10, 8/10, 7/10
  ```
  It supports temporal consistency, but the condition levels are not a clean symmetric parameter ladder.
- Real human data offers a stronger bridge from AR parameter values to human behavior:
  - Use post-training P6/P7/P8 to estimate what DEMT-trained users actually do.
  - Use pre-training P1/P2 to show how unguided behavior is broader or less consistent.
  - Use percentiles rather than only mean ± std when translating behavior into radius/tolerance choices.
- V2 human diagnostics are useful but **do not** solve the spatial parameter
  rebuttal:
  ```text
  P1 pre nearest-to-corridor-plane radius:
    p90/p95/max = 15.83 / 18.28 / 23.71 cm
    10 cm coverage = 65.0%, 25 cm coverage = 100.0%

  P2 pre nearest-to-corridor-plane radius:
    p90/p95/max = 23.63 / 26.70 / 32.64 cm
    10 cm coverage = 32.5%, 25 cm coverage = 90.8%

  P6 post nearest-to-corridor-plane radius:
    p90/p95 = 7.22 / 9.49 cm

  P7 post nearest-to-corridor-plane radius:
    p90/p95 = 6.26 / 6.67 cm
  ```
  Revised interpretation: these local keypoints show that post-training
  demonstrations are tighter, but they do not prove that `r_start = 25 cm` is
  necessary. If pre-training users are already mostly inside 25 cm, then low
  pre-training deployment success must be explained by full-path MPCV, contact
  orientation, temporal synchronisation, and learner fit rather than this one
  radius.
- V2 human orientation diagnostics can now support the 15 deg claim:
  ```text
  P6/P7 post closest_grasp and first_close p95 to group mean = about 13-14 deg
  coverage_15deg = 99.2% to 100.0%
  ```
  Pair this with Week 1 R00/R15/R30 = 7/10, 6/10, 4/10. Use it to say
  15 deg is human-compatible and learner-aware, not exactly optimal.
- V2 temporal diagnostics are usable but weaker:
  ```text
  duration-ratio coverage in [0.5, 2.0] = 86.7% to 100.0%
  mean-speed-ratio coverage in [0.5, 2.0] = 93.3% to 100.0%
  ```
  These ratios are against group median, not exact per-user `v_ref`, so use
  only as human-compatibility support. Learner-aware evidence remains the Week 1
  T00/T20/Twide rollout.
- The supervisor's spatial ratio idea gives a cleaner simulation design than the Week 1 independent 2x2 sweep:
  ```text
  25cm:5cm, 30cm:6cm, 35cm:7cm, ...
  ```
  This matches a funnel interpretation and avoids ambiguous independent-factor effects.

## What Didn't Work
- Do not claim the current evidence proves exact optimality of `25cm / 15deg / [0.5, 2.0] x v_ref`.
- Do not overuse Week 1 corrected spatial rollout as the main spatial result. It is mixed:
  ```text
  P00/P01/P10/P11 = 8/10, 6/10, 7/10, 6/10
  ```
  Validation loss flags P10, but rollout does not give a clean monotonic spatial story.
- Do not make a new user study the near-term answer. Radius-order effects and participant learning make within-subject radius comparisons problematic, and recruitment costs are high.
- Do not mix temporal condition scales in the next sweep. `T00/T20/Twide` combined fixed, `+/-20%`, and `[0.5, 2.0]`; Week 2 should use a symmetric ladder such as `+/-10%`, `+/-20%`, `+/-30%`, `+/-40%`.
- Do not describe `v_ref` as a fixed metric speed in the submitted paper. It was computed from each person's first trajectory, which is a limitation to acknowledge carefully.
- Do not use the CSV key name `corridor_crossing` literally unless defining it.
  The metric is the observed trajectory point closest to the y=0 corridor
  plane; reviewer-facing wording should say "nearest-to-corridor-plane early
  approach keypoint."
- Do not treat orientation dispersion to group mean as exact AR target-frame
  alignment.

## Key Files & Commands
- Week 2 experiment execution handoff:
  - `handoffs/week2_experiment.md`
- Week 1 research archive:
  - `handoffs/week1_research_thinking.md`
- Rebuttal/supervisor PPT from Week 1:
  - `outputs/demt_rebuttal_mvp_report.pptx`
- Human data root:
  - `/scratch/users/k23114984/pybullet_data`
- PDF:
  - `DEMT__Deployment_Evaluated_Machine_Teaching_Enhances_Learning_from_Human_Demonstrations.pdf`
- Useful PDF text search:
  ```bash
  pdftotext DEMT__Deployment_Evaluated_Machine_Teaching_Enhances_Learning_from_Human_Demonstrations.pdf /tmp/demt_paper.txt
  rg -n "P1|P2|P6|P7|P8|Table 6|MPCV|MCOD|MPSV|vref|speed cue|15 deg|r_start" /tmp/demt_paper.txt
  ```

## Next Steps
1. For rebuttal, use the revised bounded-optimality claim:
   ```text
   The Table 5 AR thresholds are defended as bounded finite candidates under
   human-compatibility and learner-compatibility constraints. They are not
   literal global optima over the continuous AR-parameter space.
   ```
2. For spatial, lead with the paper's EDSR and Table 9 MPCV reduction, not the
   local 25 cm coverage diagnostic.
3. For orientation, combine the current R00/R15/R30 result with V2 human
   post-training dispersion. Optional additions are `R05`, `R45`, or
   target-frame-aligned human orientation analysis.
4. For temporal, if future work is needed, redesign around a symmetric jitter ladder:
   ```text
   T00, T10, T20, T30, T40, optional T50
   ```
   If possible, base nominal phase frames on P1/P2 or P6/P7 human phase statistics.
5. Rebuttal wording should be conservative:
   ```text
   The submitted paper does not exhaustively optimize the continuous AR
   parameter space. Instead, the Table 5 values instantiate DEMT-selected
   structures and are defended as the best currently supported constrained
   candidates for this robot, task family, learner, and N=30 budget.
   ```
6. If stronger spatial evidence is required, use E05 from
   `rebuttal_workflow/experiment_queue.md`: fixed-ratio spatial funnel sweep,
   fixed R/V, matched N=30, same learner/checkpoint rule, paired deployment
   starts, and deployment success as the primary metric.

## Open Questions
- Which subset of the human-data diagnostics should fit into rebuttal length:
  spatial only, or spatial plus a compact orientation sentence?
- Should the spatial sweep focus on `5:1` only, or include `2:1` as a competing design family?
- Should temporal `v_ref` be reframed as a limitation in rebuttal, or only in the future paper?
- If CoRL is accepted, which Week 2 experiments still belong in the journal version?

## Changelog
- 2026-07-03: Added the three-agent bounded-optimality continuation result,
  E00 human percentile audit, and E05 fixed-ratio spatial funnel sweep as the
  next defensible spatial experiment.
- 2026-07-03: Added R04 bounded-optimality framing. Agent3 should keep pressuring Agent1/Agent2 toward a global-optimality-style answer; the acceptable rebuttal is constrained finite-candidate optimality, not literal global optimality and not structure-only retreat.
- 2026-06-30: Created Week 2 research handoff after supervisor meeting; recorded revised spatial/orientation/temporal framing, human-data policy, and rebuttal-vs-ICRA/journal strategy.
