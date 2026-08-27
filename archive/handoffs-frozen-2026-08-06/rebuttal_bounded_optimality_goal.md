# Handoff: Rebuttal Bounded Optimality Goal

_Last updated: 2026-07-03 · Branch: hpc-headless-data-collection @ 73d56df_

## Goal
Start a fresh three-agent goal to redesign the DEMT rebuttal evidence path for
the Table 5 AR guidance parameters. The target is not to claim exact global
optimality, but Agent3 must still push Agent1/Agent2 toward the strongest
possible global-optimality-style explanation: the parameters should be defended
as bounded / constrained / Pareto-optimal finite candidates for this robot, task
family, learner, user-training protocol, and N=30 demonstration budget.

## Current Progress
- 2026-07-03 continuation completed the requested three-agent audit:
  - Agent1 inventoried valid Week1/Week2 evidence and quarantines.
  - Agent2 converted supervisor/user concerns into a minimal experiment queue.
  - Agent3 defined acceptance criteria for bounded / constrained / Pareto
    optimality and accepted the conservative current wording only if exact
    numeric optimality is not claimed.
- New/updated workflow artifacts:
  - `rebuttal_workflow/experiment_queue.md`
  - `rebuttal_workflow/agent1_results/E00_human_percentile_bound_audit.md`
  - `outputs/rebuttal_workflow/human_percentile_bound_audit.csv`
  - `rebuttal_workflow/claim_ledger.md`
  - `research_workflow.md`
  - `rebuttal_workflow/README.md`
- Three-agent convergence:
  ```text
  Current evidence can support bounded finite-candidate wording, not exact
  global optimality.

  Orientation is the strongest existing numeric story.
  Spatial needs a coupled fixed-ratio funnel sweep if a stronger 25 cm claim is
  required.
  Temporal remains a broad pacing-scaffold claim unless a clean ladder is run.
  Human mean/std or percentile statistics define feasible regions only; they do
  not prove learner optimality by themselves.
  ```
- E00 human percentile bound audit was run as a read-only derived analysis:
  ```text
  outputs/rebuttal_workflow/human_percentile_bound_audit.csv
  rows = 36
  P1/P2/P6/P7 n = 120 each, P8 groups n = 30
  ```
  It supports human-compatibility bounds only, not learner optimality.
- The earlier overly optimistic Agent3 acceptance was superseded.
- Current strict framing is in:
  - `rebuttal_workflow/agent3_reviews/R04_global_optimal_pressure_review.md`
  - `rebuttal_workflow/claim_ledger.md`
  - `rebuttal_workflow/rebuttal_fragments/parameter_reasonableness_claim.md`
- R04 states that Agent3 should **not** retreat immediately to "structure-level
  only." Agent3 should demand the best defensible answer to why the Table 5
  settings are near-optimal / best finite candidates.
- Important user correction: temporal ladder is only one example of a broader
  problem. The next goal must evaluate all Week1 follow-up designs, including:
  spatial P00/P01/P10/P11, orientation R00/R15/R30, and temporal T00/T20/Twide.
- The user explicitly questioned the old spatial 2x2 design:
  ```text
  Why P00/P01/P10/P11? Why these independent combinations?
  ```
- Supervisor suggestions to consider, not blindly execute:
  - fixed-ratio spatial funnel sweeps, e.g. corridor:pre_grasp as `25:6`,
    `30:7.2`, etc.
  - use pre-training human P/R/V mean +/- std or percentiles to design sampling
    distributions.
  - one-time-variant experiments: fix R,V first, sweep several P conditions
    with 30 demos each, and use deployment success to identify the best finite
    candidate.
- A key unresolved concern: sampling from pre-training mean/std may merely
  reproduce a weak pre-training distribution, so Agent3 must check whether such
  experiments actually answer guidance optimality or just restate observed
  behaviour.

## What Worked
- The paper's strongest evidence is still the real-robot deployment and Table 9
  structure metrics:
  ```text
  P1 -> P6 EDSR: 14.0% -> 75.0%
  P2 -> P7 EDSR: 22.0% -> 91.0%
  Table 9: MPCV/MCOD/MPSV/validation loss drop for DEMT post-training data.
  ```
- Orientation is the cleanest existing numeric story:
  ```text
  R00/R15/R30 rollout = 7/10, 6/10, 4/10
  post-training human grasp/close p95 ~= 13-14 deg
  ```
- The agents converged that a local orientation bracket (`R10`, `R20`) would be
  useful future work, but is not required before using conservative
  bounded-candidate wording.
- V2 human diagnostics are useful as diagnostics, especially for identifying
  actual post-training tightening, but they must be used carefully.
- E00 gives a compact compatibility table:
  ```text
  P1 pre spatial p95 = 18.28 cm; P2 pre spatial p95 = 26.70 cm
  P6/P7 post spatial p95 = 9.49 / 6.67 cm
  P6/P7 post grasp/close p95 ~= 13-14 deg
  [0.5, 2.0] coverage is high for duration and mean-speed ratios
  ```

## What Didn't Work
- Do not use P1/P2 pre keypoints being mostly inside 25 cm as a proof that
  `r_start = 25 cm` is optimal or necessary. If users are already inside 25 cm,
  that cannot explain low pre-training EDSR.
- Do not use T00/T20/Twide as proof that `[0.5, 2.0] x v_ref` is optimal. The
  conditions are not a rigorous ladder.
- Do not assume the Week1 spatial 2x2 P00/P01/P10/P11 design is scientifically
  adequate. The next goal must audit why those conditions were chosen and
  whether a fixed-ratio funnel sweep is better.
- The audit concluded that P00/P01/P10/P11 is valid history but a weak spatial
  answer: it uses independent corridor/pre-grasp factors and mixed rollout
  results, so it should not be the main bounded-optimality evidence for 25 cm.
- Do not substitute pre-training mean/std sampling for a learner-evaluated
  finite-candidate experiment. Agent3 flagged this as likely to restate weak
  pre-training behavior.
- Do not let Agent3 accept "global optimality is impossible" as a sufficient
  answer. Agent3 should force Agent1/Agent2 to produce the best feasible
  bounded-optimality argument.

## Key Files & Commands
- Workflow and current framing:
  - `research_workflow.md`
  - `rebuttal_workflow/experiment_queue.md`
  - `rebuttal_workflow/agent3_reviews/R04_global_optimal_pressure_review.md`
  - `rebuttal_workflow/claim_ledger.md`
  - `rebuttal_workflow/rebuttal_fragments/parameter_reasonableness_claim.md`
  - `rebuttal_workflow/agent1_results/E00_human_percentile_bound_audit.md`
- Prior experiment history:
  - `handoffs/week1_main-experiments.md`
  - `handoffs/week1_research_thinking.md`
  - `handoffs/week2_experiment.md`
  - `handoffs/week2_research_thinking.md`
  - `handoffs/multiagent_history_example.md`
- Paper and supervisor discussion artifact:
  - `DEMT__Deployment_Evaluated_Machine_Teaching_Enhances_Learning_from_Human_Demonstrations.pdf`
  - `outputs/demt_rebuttal_mvp_report.pptx`
- Human diagnostics:
  - `outputs/rebuttal_workflow/human_percentile_bound_audit.csv`
  - `outputs/week2_human_diagnostics_keypoints_v2/keypoint_spread_summary.csv`
  - `outputs/week2_human_diagnostics_keypoints_v2/orientation_event_summary.csv`
  - `outputs/week2_human_diagnostics_keypoints_v2/temporal_human_summary.csv`
- Useful PDF extraction:
  ```bash
  pdftotext DEMT__Deployment_Evaluated_Machine_Teaching_Enhances_Learning_from_Human_Demonstrations.pdf /tmp/demt_paper.txt
  rg -n "Table 5|Table 9|P1|P2|P6|P7|MPCV|MCOD|MPSV|vref|25|15" /tmp/demt_paper.txt
  ```

## Next Steps
1. Use current rebuttal wording only with the strict boundary:
   ```text
   Table 5 values are bounded finite candidates for this robot/task/learner/
   user protocol/N=30 setting, not globally optimized thresholds.
   ```
2. If a stronger spatial parameter claim is needed and compute allows, run E05
   from `rebuttal_workflow/experiment_queue.md`: fixed-ratio spatial funnel
   sweep, fixed R/V, matched N=30, same learner, paired deployment starts, and
   deployment success as primary metric.
3. Prefer true three-stage scaled Table 5 funnels if implementable:
   ```text
   S20 = 20 / 4 / 2.4 cm
   S25 = 25 / 5 / 3.0 cm
   S30 = 30 / 6 / 3.6 cm
   optional S15/S35 if the first three are ambiguous
   ```
   If the simulator only exposes corridor/pre-grasp radii, use the matched
   proxy family:
   ```text
   20:4.8, 25:6.0, 30:7.2 cm
   optional 15:3.6, 35:8.4 cm
   ```
4. Treat E06 temporal ladder, E07 orientation bracket, and E08 human-derived
   P/R/V sampling as backup/future-paper work unless Agent3 rejects the current
   conservative rebuttal.
5. If E05 is not run or is negative, keep spatial wording at "25 cm is a
   permissive outer radius in a tightening funnel" and list exact threshold
   optimization as future work.

## Open Questions
- Does current compute/time allow E05 before the rebuttal deadline?
- Can the current simulator implement the true three-stage `25/5/3` funnel, or
  only the corridor/pre-grasp proxy family?
- Should E05 include only the three core conditions (`S20/S25/S30`) or also
  `S15/S35` from the start?
- How much compute/time is available for new N=30 collection + training +
  deployment evaluations?

## Suggested New-Chat Goal Prompt
```text
开启 goal：基于 research_workflow.md、handoffs/、rebuttal_workflow/、论文 PDF 和 outputs/demt_rebuttal_mvp_report.pptx，使用三 agent 工作流全面重审 Week1/Week2 rebuttal 参数实验。不要只修 temporal；要系统检查 spatial P00/P01/P10/P11、orientation R00/R15/R30、temporal T00/T20/Twide 是否科学，哪些证据可用/必须降级。Agent3 必须逼近 global optimality，不能直接退守 structure-only；Agent1/Agent2 必须设计最强 bounded/constrained/Pareto optimality 证据路径。参考但不要盲从 supervisor 的 fixed-ratio funnel sweep、pre_train P/R/V mean±std sampling、one-time-variant 等建议，由 agents 自主设计最合理的 rebuttal 实验矩阵。最终更新 claim ledger / experiment queue / handoff，并明确哪些 claim 可以进 rebuttal，哪些必须作为 limitation/future work。只有当 Agent3 接受新的实验设计和 bounded-optimality 证据路径时，goal 才算完成。
```

## Changelog
- 2026-07-03: Continued the goal with the requested three-agent workflow,
  completed E00 human percentile bound audit, created
  `rebuttal_workflow/experiment_queue.md`, and updated the claim ledger with
  the converged bounded-optimality path.
- 2026-07-03: Created fresh-context handoff for the next goal: full Week1/Week2 rebuttal experiment audit and bounded-optimality experiment design.
