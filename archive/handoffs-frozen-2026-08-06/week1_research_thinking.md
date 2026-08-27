# Handoff: Week 1 Research Thinking

_Last updated: 2026-06-30 · Branch: hpc-headless-data-collection @ 1ab8302_

## Goal
Maintain the scientific framing for the DEMT CoRL rebuttal separately from the experiment/code handoff. This file should help future agents reason about the paper logic, reviewer-facing claims, and which ablations are worth running next. Keep implementation details in `handoffs/week1_main-experiments.md`.

## Current Progress
- 2026-06-29 critical correction and rerun: the old spatial `P00/P01/P10/P11` result under `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full` is invalid for the intended AR-guidance ablation because it used `base_corridor_start ~= [0.3, 0.15, 0.28]` and included an extra `random_start -> corridor_start` segment. The corrected pipeline has now been recollected/retrained/evaluated under `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full_arcenter`, starting directly from sampled `corridor_start` around `[0.3, 0.0, 0.5]` with no `random_start`.
- User clarified the core thesis: the original paper's simulation variants were meant to show that task-successful demonstrations are not necessarily the best demonstrations for robot learning.
- The original paper's geometric variant is not invalid. In the PDF appendix, it is a coarse spatial-geometry variant that enlarges the approach region while holding contact orientation and temporal pacing fixed.
- PDF appendix values checked from `DEMT__Deployment_Evaluated_Machine_Teaching_Enhances_Learning_from_Human_Demonstrations.pdf`:
  - Baseline approach region: `[0.3, 0.5] x [0.3, 0.5] x [0.2, 0.5]`.
  - Geometric variant approach region: `[0.0, 0.5] x [0.0, 0.5] x [0.2, 0.7]`.
  - Appendix Table 5 AR spatial corridor guidance: `r_start = 25cm`, `r_middle = 5cm`, `r_final = 3cm`.
  - Appendix A.9 rollout initial states: `[0.0, 0.6] x [-0.1, 0.1] x [0.0, 0.6] m`.
- The paper-level geometric variant mentions an enlarged `approach region` / `approach-point distribution`; it does not explicitly name the code variable `pre_grasp`.
- User's interpretation: the original geometric variant was effectively sampling around the approach / pre-grasp point. That was appropriate for the original claim.
- The current new ablation should be framed as a guidance-design ablation, not as a replacement or correction of the original paper experiment.
- Corrected spatial MVP result is complete but should be interpreted conservatively. Latest-checkpoint rollout is mixed: `P00/P01/P10/P11 = 8/10, 6/10, 7/10, 6/10`. Validation loss does flag `P10` as clearly worse (`best valid 0.099` versus about `0.029-0.036` for `P00/P01/P11`), but the old claim that wide corridor-entry variation causes a strong rollout collapse should not be reused.
- Corrected spatial annulus stress rollout is also complete on the valid `abla1_full_arcenter` models. It sampled starts from `0.25 <= d <= 0.50m` around the AR corridor-start center and produced low success across all policies: `P00/P01/P10/P11 = 2/10, 1/10, 2/10, 1/10`. This supports the user's robustness concern that all learned policies are weak under large OOD entry perturbations, but it does not show that the wider `0.25m` training corridor improves robustness.
- Orientation (`orn`) guidance direction:
  - Original PDF simulation orientation variant: closing orientation alternates between `Rdefault = [-pi, 0, 0]` and `Rtilt = Rxyz(0 deg, -45 deg, 90 deg) Rdefault`, while approach geometry and temporal pacing stay fixed.
  - Original PDF guidance parameter: grasp-orientation tolerance is `15 deg` in Appendix Table 5.
  - The key rebuttal question should be: how much closing-orientation variation can the learner tolerate, and does the `15 deg` guidance threshold sit near a learnable range?
- Orientation MVP is now complete in `handoffs/main-experiments.md`: `R00/R15/R30` training and rollout show monotonic degradation, supporting the angle-tolerance story.
- User selected the next direction as a fuller temporal threshold sweep, not a two-condition MVP:
  ```text
  T00: fixed phase timing / most consistent baseline
  T20: moderate phase-duration jitter, around +/-20%
  Twide: broad phase-duration variation, tied to the paper's [0.5, 2.0] x v_ref speed-bar tolerance
  ```
- PDF temporal facts checked from `DEMT__Deployment_Evaluated_Machine_Teaching_Enhances_Learning_from_Human_Demonstrations.pdf`:
  - Temporal structure is defined as the speed profile and phase timing around task-relevant events.
  - Table 4 temporal variant uses phase-wise temporal resampling: varying the number of samples assigned to each phase while preserving spatial path and closing orientation.
  - Table 5 speed-bar guidance uses relative speed tolerance `[0.5, 2.0] x v_ref`.
  - Appendix B.1 uses MPSV, the variance of normalized path progress over normalized time, to quantify temporal consistency.
- Current rebuttal MVP status:
  - Spatial: corrected arcenter/no-random rerun complete; rollout is mixed (`8/10`, `6/10`, `7/10`, `6/10`) and validation mainly flags `P10`. Corrected `0.25-0.50m` annulus stress rollout is low for all policies (`2/10`, `1/10`, `2/10`, `1/10`), so use it as OOD robustness caution rather than as evidence that wider training corridors help.
  - Orientation: `R00/R15/R30` shows monotonic degradation, with rollout `7/10`, `6/10`, `4/10`.
  - Temporal: latest-checkpoint fixed-start evaluation shows `T00/T20/Twide = 10/10`, `8/10`, `7/10`.
- A supervisor-meeting PPT was generated:
  - `outputs/demt_rebuttal_mvp_report.pptx`
  - source: `scripts/create_rebuttal_ppt.py`
  - Current version was regenerated after the corrected spatial rerun and now uses `abla1_full_arcenter` spatial summary/plots/loss.
- Important revised rebuttal boundary:
  ```text
  The parameters implement DEMT-selected structures.
  The MVPs support the need for these spatial, orientation, and temporal constraints.
  They do not prove exact numeric optimality of 25cm / 15deg / [0.5, 2.0] x v_ref.
  ```

## What Worked
- Clean scientific hierarchy:
  1. Original paper claim: task success is necessary but not sufficient for robot-learnable demonstrations.
  2. Original simulation variants: coarse evidence that spatial, contact-orientation, and temporal structures affect deployment success despite task success.
  3. New rebuttal ablation: fine-grained evidence that the DEMT guidance design is not arbitrary; spatial guidance constraints affect learner fit, though corrected rollout evidence is mixed.
- Useful rebuttal framing:
  ```text
  The original geometric variant established that spatial variation affects learnability.
  We now add a targeted guidance ablation to check sensitivity within the spatial corridor used by DEMT.
  ```
- Safe interpretation of the 25cm value:
  - `r_start=25cm` in the appendix is a human-facing AR guidance tolerance at the broad start of a funnel that narrows to `5cm` and `3cm`.
  - `corridor_start_radius=0.25m` in the new ablation is a sampled waypoint radius used to stress the learned demonstration distribution.
  - These are numerically related but not the same experimental object, so the new result does not contradict the appendix.
- Stronger conceptual claim now available:
  ```text
  DEMT guidance is useful because it constrains demonstration structure, not merely because it helps humans complete the task.
  ```
- Corrected spatial interpretation:
  ```text
  The corrected spatial run should be used as cautious structure-level evidence. It confirms the geometry and flags a learner-fit issue for P10, but it does not reproduce the old strong rollout degradation story. The corrected annulus stress run shows broad OOD entry perturbations remain difficult for all four policies, and wider corridor training did not rescue robustness in this small n=10 probe.
  ```
- Useful stress-failure diagnostics if the user wants to mine the weak annulus result:
  - Tube / corridor occupancy: portion of rollout frames inside a DEMT corridor tube, first exit time, max/mean distance to tube, outside-tube AUC, and re-entry count.
  - Progress-aligned error: DTW or path-progress-aligned EE RMSE rather than raw time-index RMSE, with phase-wise errors for approach, pre-grasp, grasp, and lift.
  - Task-relevant proximity: minimum distance to pre-grasp, minimum distance to cube / grasp region, time to enter a 5cm grasp neighborhood, and whether the policy remains stable after entering.
  - Smoothness / stability: joint or EE velocity, acceleration, jerk, action-delta norm, high-frequency oscillation score, and gripper open-close switching count.
  - Paired-start analysis: because all policies used the same annulus starts, compare each start across P00/P01/P10/P11 and group failures by start geometry (`0.25-0.35` vs `0.35-0.50`, high/low z, left/right/front/back).
  - Failure taxonomy: never approaches cube, approaches but misses pre-grasp, bad cube contact, closes too early/late, lifts without grasp, grasps then drops, or unstable oscillation.
- Orientation ablation framing:
  ```text
  The submitted paper already showed that a large contact-orientation variant can hurt deployment.
  A targeted guidance ablation should now test whether the 15 deg grasp-orientation threshold is a reasonable boundary for learnable demonstrations.
  ```
- Recommended MVP orientation levels:
  ```text
  R00: fixed orientation, 0 deg
  R15: orientation variation within +/-15 deg
  R30: orientation variation beyond threshold, +/-30 deg
  ```
  If time allows, add either `R05` for a small-variation condition or `Rtilt` to directly reproduce the submitted paper's large orientation contrast.
- Temporal ablation framing:
  ```text
  The submitted paper showed that temporal pacing variation can hurt deployment.
  The rebuttal sweep should now ask how much phase-timing variation is tolerable under the same fixed learner and N=30 budget.
  ```
- Safe interpretation of the temporal sweep:
  - `T00` should represent intentionally aligned event timing, not merely the current script's natural timing.
  - `T20` is the middle threshold condition for a more complete sweep.
  - `Twide` should be framed as broad timing/speed variation inspired by the paper's speed-bar tolerance range, not as an exact reproduction of human AR speed-bar feedback.
- Safe rebuttal wording after the three MVPs:
  ```text
  The exact AR values are task-specific implementation choices for this robot, learner, and manipulation setting. Our claim is not that these numbers are globally optimal. Rather, they implement the spatial, contact-orientation, and temporal structures selected by DEMT. To address the concern, we added controlled sensitivity ablations showing that relaxing these structures degrades learner fit and/or rollout success under the same fixed learner and N=30 budget.
  ```

## What Didn't Work
- Do not frame the new result as "the original geometric variant was wrong." The user explicitly clarified that the original logic was correct.
- Do not say "Appendix says 25cm is good, but the new result says 25cm is bad." That conflates AR guidance tolerance with sampled training-data waypoint variability.
- Do not overclaim from validation loss alone. The paper can use validation loss as learner-level diagnostic, but deployment success / rollout success is still the primary metric.
- Do not cite old spatial results from `dataset/abla1_full`, including old loss plots, rollout videos, corridor-stress outputs, or PPT wording. Use `dataset/abla1_full_arcenter` only.
- Do not claim the corrected spatial rollout proves wide corridor-entry variation is the dominant degradation. The corrected rollout is mixed; the safe claim is sensitivity/learner-fit evidence plus a need for corridor constraints at the structure level.
- Do not make the corrected annulus stress success rate a main rebuttal result. It is generally weak across all policies and is more useful as a diagnostic / robustness caution than as clean evidence for one spatial guidance setting.
- Do not interpret the corrected stress result as evidence that tighter guidance improves OOD robustness. It only shows that wider training (`corridor_start_radius=0.25`) did not improve robustness in this small annulus probe.
- Do not let the new ablation sprawl into a new paper. For rebuttal, it should be a small missing step that supports the guidance design.
- Do not conflate the original submitted `Rtilt` condition with a `15 deg` threshold sweep. The submitted orientation variant is a large discrete contrast; the new guidance ablation should be an angle-range sweep around the guidance tolerance.
- Current code has a likely orientation-ablation pitfall: `examples/main.py` and `examples/main_abla_1.py` define `_gripper_quat(default|tilt)`, but `move_ee()` defaults to `self.default_orientation_quat` when `target_quat=None`. Future agents must verify whether `--gripper-orientation tilt` actually changes commanded target orientations before collecting data.
- Do not use the current natural `R00` phase-count variability as the temporal baseline without thought: most existing variation comes from random-start-to-corridor distance, which mixes spatial variation with timing variation.
- Do not change spatial path or orientation in the temporal sweep. The PDF temporal variant explicitly preserves spatial path and closing orientation while resampling phase timing.
- Do not say the MVPs empirically prove the exact AR numbers are optimal. The user explicitly questioned this wording; use "structure-level sensitivity evidence" instead.
- For temporal, `[0.5, 2.0] x v_ref` is a unitless relative speed tolerance, not a fixed `m/s` value. The new Temporal MVP uses duration multipliers to induce broad phase-timing variation inspired by the paper's speed-bar tolerance, but it is not an exact reproduction of real AR speed-bar feedback.

## Key Files & Commands
- Scientific source PDF:
  - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/DEMT__Deployment_Evaluated_Machine_Teaching_Enhances_Learning_from_Human_Demonstrations.pdf`
- Experiment/code handoff:
  - `handoffs/main-experiments.md`
- Current planning doc, may contain stale geometry assumptions and should be cleaned before final writing:
  - `docs/ablation-1.md`
- Existing orientation implementation references:
  - `examples/main.py`
  - `examples/main_abla_1.py`
  - `scripts/run_demt_collect.sh`
  - `docs/corl-rebuttal-ablation-plan.md`
- Rebuttal meeting PPT:
  - `outputs/demt_rebuttal_mvp_report.pptx`
  - `scripts/create_rebuttal_ppt.py`
- Useful PDF text extraction commands:
  ```bash
  pdftotext /scratch/prj/eng_demt_robot_learning/polymetics_demt/DEMT__Deployment_Evaluated_Machine_Teaching_Enhances_Learning_from_Human_Demonstrations.pdf /tmp/demt_paper.txt
  rg -n "Geometric variant|approach region|Spatial corridor|rstart|rmiddle|rfinal|Rollout Setup|Orientation variant|Rdefault|Rtilt|15 deg|Temporal variant|phase-wise|speed bar|MPSV|relative speed tolerance" /tmp/demt_paper.txt
  ```
- Key appendix locations found by text search:
  - Table 4: simulation variant construction and approach-region values.
  - Table 5: DEMT-derived AR guidance parameters.
  - A.9: rollout setup.
- Current code references for orientation:
  ```text
  examples/main.py:
    _gripper_quat("tilt") uses Rxyz(0, -pi/4, pi/2) * Rdefault.
    CLI supports --gripper-orientation default|tilt.
    move_ee() currently defaults to self.default_orientation_quat unless target_quat is passed.

  examples/main_abla_1.py:
    Same orientation helper pattern.
  ```

## Next Steps
1. Keep `handoffs/main-experiments.md` focused on pipeline execution, code, job IDs, datasets, HDF5, training, rollout, and exact commands.
2. Use this file for high-level research decisions, including rebuttal framing and whether an extra ablation is scientifically worth the cost.
3. In rebuttal writing, state that the original geometric variant was a coarse spatial-structure test, and the new experiment is a guidance-design ablation that localizes the spatial effect.
4. Treat corrected spatial as complete for now unless the user asks for a stronger spatial story; old corridor-stress outputs under `dataset/abla1_full` remain invalid, while the corrected annulus stress output under `dataset/abla1_full_arcenter` can be cited only with the OOD robustness boundary above.
5. Treat orientation MVP as completed unless the user asks for checkpoint or stress-distribution follow-up.
6. Treat the temporal threshold sweep `T00 / T20 / Twide` as completed for the current MVP evidence package.
7. If the user asks to analyze the stress rollout further, prioritize no-new-rollout diagnostics first: tube occupancy, progress-aligned RMSE, task-region entry metrics, smoothness/jerk, and paired-start failure taxonomy. Do not start by changing code or rerunning policies unless the user explicitly requests it.
8. In the supervisor meeting, decide whether the current evidence package is enough for rebuttal or whether more seeds / stress radii are needed before making a robustness claim central.
9. Before final rebuttal wording, archive/cite one non-overwritten rollout summary for each MVP and name the evaluation setting.
10. Clean `docs/ablation-1.md` or create a rebuttal-specific doc so stale corridor/orientation assumptions and old Temporal epoch-40 numbers do not bleed into final writing.

## Open Questions
- Does the rebuttal need an intermediate `corridor_start_radius=0.15` result or more rollout seeds to strengthen the corrected spatial story?
- Should corrected spatial evidence be framed only as validation/learner-fit sensitivity, with rollout reported as mixed?
- Should the final text explicitly connect appendix `r_start=25cm, r_middle=5cm, r_final=3cm` to the funnel concept, while avoiding a one-to-one comparison with the ablation radius?
- Does the supervisor accept the revised wording that exact AR values are task-specific implementation choices, while the MVPs support the need for the corresponding structural constraints?
- Is the corrected-arcenter corridor-stress result (`0.25-0.50m`, n=10) sufficient as a robustness caution, or does this need more rollout seeds / stress radii before being mentioned in rebuttal?
- If stress failure analysis continues, which diagnostic should be implemented first: tube occupancy / distance-to-corridor, progress-aligned RMSE, smoothness / jerk, or paired-start failure taxonomy?

## Changelog
- 2026-06-28: Created separate research handoff for DEMT rebuttal framing, original geometric-variant interpretation, appendix values, and guidance-ablation logic.
- 2026-06-28: Updated with decision to pause corridor after MVP and pivot to orientation guidance ablation, including PDF thresholds, recommended angle levels, and code pitfalls.
- 2026-06-28: Updated direction after orientation MVP completion; next experiment should be a temporal threshold sweep `T00/T20/Twide` grounded in PDF phase-wise resampling, speed-bar tolerance, and MPSV framing.
- 2026-06-29: Updated after all three MVPs completed and the supervisor-meeting PPT was generated; clarified that the rebuttal should claim structure-level sensitivity evidence, not exact numeric parameter optimality.
- 2026-06-29: Recorded the pre-rerun spatial correction that removed the extra `random_start` segment.
- 2026-06-29: Updated after corrected `abla1_full_arcenter` spatial rerun completed; spatial evidence is now valid but mixed, so the rebuttal framing should be conservative.
- 2026-06-30: Updated after corrected `abla1_full_arcenter` annulus stress rollout completed; all policies were weak under `0.25-0.50m` OOD entry perturbations, and wider corridor training did not show a robustness advantage in this small probe.
- 2026-06-30: Added post-stress brainstorming: treat stress success as low-value main evidence, and if needed mine failures with tube occupancy, progress-aligned RMSE, smoothness/stability, and paired-start diagnostics.
