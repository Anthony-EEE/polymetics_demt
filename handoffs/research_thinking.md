# Handoff: Research Thinking

_Last updated: 2026-06-28 · Branch: hpc-headless-data-collection @ 6a3ad5b_

## Goal
Maintain the scientific framing for the DEMT CoRL rebuttal separately from the experiment/code handoff. This file should help future agents reason about the paper logic, reviewer-facing claims, and which ablations are worth running next. Keep implementation details in `handoffs/main-experiments.md`.

## Current Progress
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
- Current first guidance ablation result from `main-experiments.md`: wide `corridor_start_radius=0.25` hurts validation and rollout much more than wide `pre_grasp_radius=0.06`, under the current cube pick-and-lift design.
- User decided to pause further corridor guidance experiments because the minimum viable guidance ablation has run through the full pipeline.
- Next research direction is orientation (`orn`) guidance:
  - Original PDF simulation orientation variant: closing orientation alternates between `Rdefault = [-pi, 0, 0]` and `Rtilt = Rxyz(0 deg, -45 deg, 90 deg) Rdefault`, while approach geometry and temporal pacing stay fixed.
  - Original PDF guidance parameter: grasp-orientation tolerance is `15 deg` in Appendix Table 5.
  - The key rebuttal question should be: how much closing-orientation variation can the learner tolerate, and does the `15 deg` guidance threshold sit near a learnable range?

## What Worked
- Clean scientific hierarchy:
  1. Original paper claim: task success is necessary but not sufficient for robot-learnable demonstrations.
  2. Original simulation variants: coarse evidence that spatial, contact-orientation, and temporal structures affect deployment success despite task success.
  3. New rebuttal ablation: fine-grained evidence that the DEMT guidance design is not arbitrary; spatial guidance constraints change learnability.
- Useful rebuttal framing:
  ```text
  The original geometric variant established that spatial variation affects learnability.
  We now add a targeted guidance ablation to localize this effect within the spatial corridor used by DEMT.
  ```
- Safe interpretation of the 25cm value:
  - `r_start=25cm` in the appendix is a human-facing AR guidance tolerance at the broad start of a funnel that narrows to `5cm` and `3cm`.
  - `corridor_start_radius=0.25m` in the new ablation is a sampled waypoint radius used to stress the learned demonstration distribution.
  - These are numerically related but not the same experimental object, so the new result does not contradict the appendix.
- Stronger conceptual claim now available:
  ```text
  DEMT guidance is useful because it constrains demonstration structure, not merely because it helps humans complete the task.
  ```
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

## What Didn't Work
- Do not frame the new result as "the original geometric variant was wrong." The user explicitly clarified that the original logic was correct.
- Do not say "Appendix says 25cm is good, but the new result says 25cm is bad." That conflates AR guidance tolerance with sampled training-data waypoint variability.
- Do not overclaim from validation loss alone. The paper can use validation loss as learner-level diagnostic, but deployment success / rollout success is still the primary metric.
- Do not let the new ablation sprawl into a new paper. For rebuttal, it should be a small missing step that supports the guidance design.
- Do not conflate the original submitted `Rtilt` condition with a `15 deg` threshold sweep. The submitted orientation variant is a large discrete contrast; the new guidance ablation should be an angle-range sweep around the guidance tolerance.
- Current code has a likely orientation-ablation pitfall: `examples/main.py` and `examples/main_abla_1.py` define `_gripper_quat(default|tilt)`, but `move_ee()` defaults to `self.default_orientation_quat` when `target_quat=None`. Future agents must verify whether `--gripper-orientation tilt` actually changes commanded target orientations before collecting data.

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
- Useful PDF text extraction commands:
  ```bash
  pdftotext /scratch/prj/eng_demt_robot_learning/polymetics_demt/DEMT__Deployment_Evaluated_Machine_Teaching_Enhances_Learning_from_Human_Demonstrations.pdf /tmp/demt_paper.txt
  rg -n "Geometric variant|approach region|Spatial corridor|rstart|rmiddle|rfinal|Rollout Setup|Orientation variant|Rdefault|Rtilt|15 deg" /tmp/demt_paper.txt
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
4. Pause additional corridor experiments unless the user reopens that line. The current corridor MVP is enough to show the guidance-ablation pipeline works.
5. Design the next MVP around orientation guidance: fixed spatial path, fixed timing, fixed grasp/lift targets, and only vary closing/contact orientation.
6. Before collecting orientation data, patch or verify the command path so sampled target quaternions are actually passed into `move_ee()` for contact-relevant phases (`pre_grasp`, `grasp`, close/hold, and lift if needed).
7. Prefer a first orientation sweep of `0 deg`, `15 deg`, and `30 deg` with `N=30`, `SEED=1`, `SAMPLE_HZ=8`, then run the same HDF5/train/rollout pipeline as the corridor ablation.
8. Before final rebuttal wording, archive one non-overwritten rollout summary from a final evaluation run and cite only that run.
9. Clean `docs/ablation-1.md` or create a new orientation-specific planning doc so stale corridor assumptions do not bleed into the orientation experiment.

## Open Questions
- Does the rebuttal need the intermediate `corridor_start_radius=0.15` result, or is the completed `2 x 2` guidance ablation enough? Current user direction is to pause corridor for now.
- Should the rebuttal emphasize the surprising result that corridor-entry variation dominated pre-grasp variation in the current ablation, or keep the claim narrower: spatial guidance constraints affect learnability?
- Should the final text explicitly connect appendix `r_start=25cm, r_middle=5cm, r_final=3cm` to the funnel concept, while avoiding a one-to-one comparison with the ablation radius?
- For orientation, should the sweep perturb one physically meaningful axis only (e.g. pitch/tilt around the gripper/object contact axis) or sample uniform axis-angle perturbations within the degree bound?
- Should the first orientation MVP include the submitted-paper `Rtilt` condition, or keep it to the threshold-focused `0/15/30 deg` sweep?

## Changelog
- 2026-06-28: Created separate research handoff for DEMT rebuttal framing, original geometric-variant interpretation, appendix values, and guidance-ablation logic.
- 2026-06-28: Updated with decision to pause corridor after MVP and pivot to orientation guidance ablation, including PDF thresholds, recommended angle levels, and code pitfalls.
