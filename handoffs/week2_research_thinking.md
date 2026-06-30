# Handoff: Week 2 Research Thinking

_Last updated: 2026-06-30 · Branch: hpc-headless-data-collection @ 1ab8302_

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
1. When coding resumes, first analyze real human data, not new simulation rollouts. Use it to calibrate likely spatial radius, orientation tolerance, and temporal variation ranges.
2. For spatial, report human-derived envelope percentiles and then run a coupled funnel-ratio sweep if needed:
   ```text
   S20_4, S25_5, S30_6, S35_7, optional S40_8
   ```
3. For orientation, keep the current R00/R15/R30 result unless a stronger result is needed. Optional additions are `R45` or human-derived orientation-distribution sampling.
4. For temporal, redesign around a symmetric jitter ladder:
   ```text
   T00, T10, T20, T30, T40, optional T50
   ```
   If possible, base nominal phase frames on P1/P2 or P6/P7 human phase statistics.
5. Rebuttal wording should be conservative:
   ```text
   The submitted version did not claim global optimality of these numeric thresholds. They are task-specific AR guidance values implementing DEMT-selected spatial, contact-orientation, and temporal structures. We added finite candidate sensitivity analyses and real-user diagnostics to show that these structures correspond to learnable and human-achievable consistency ranges.
   ```

## Open Questions
- Should the rebuttal mention human-data diagnostics if the analysis is ready in time, or reserve them for ICRA/journal?
- Should the spatial sweep focus on `5:1` only, or include `2:1` as a competing design family?
- Should temporal `v_ref` be reframed as a limitation in rebuttal, or only in the future paper?
- If CoRL is accepted, which Week 2 experiments still belong in the journal version?

## Changelog
- 2026-06-30: Created Week 2 research handoff after supervisor meeting; recorded revised spatial/orientation/temporal framing, human-data policy, and rebuttal-vs-ICRA/journal strategy.
