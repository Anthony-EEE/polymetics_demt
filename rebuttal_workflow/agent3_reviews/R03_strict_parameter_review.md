# Agent3 Review: Strict Parameter Claim Audit

_Date: 2026-07-03_

_Superseded/extended by `R04_global_optimal_pressure_review.md`. R03 correctly
identified the logical flaw in the 25 cm argument, but it was too passive: Agent3
should not simply retreat to "structure-level only". Agent3 should keep pushing
Agent1/Agent2 for the strongest feasible global-optimality-style explanation._

## Main Weakness

The earlier Agent3 review accepted a logically incomplete argument. It treated
P1/P2 pre-training keypoints being mostly within a 25 cm envelope as evidence
for the 25 cm AR parameter. A strict reviewer would reject this:

```text
If users are already mostly inside 25 cm before training, then this does not
explain why pre-training deployment success is low, and it does not show that
25 cm training is necessary.
```

The paper's low pre-training success is robot deployment success after learning
from N=30 demonstrations:

```text
P1 -> P6 trained prism: 14.0% -> 75.0%
P2 -> P7 unseen cube:   22.0% -> 91.0%
```

That failure cannot be reduced to one early spatial radius. It can arise from
full-path inconsistency, contact-orientation inconsistency, timing mismatch,
action distribution complexity, and finite-budget learner fit.

## Most Convincing Evidence

The strongest evidence is already in the paper:

```text
Table 9 structure metrics:
  MPCV, MCOD, MPSV, and validation loss all drop substantially for DEMT P6/P7
  relative to P1/P2 and controls.

Real-robot EDSR:
  Target P1 -> P6: 14.0% -> 75.0%
  Target P2 -> P7: 22.0% -> 91.0%
  Control does not show matched improvement.
```

For the follow-up experiments:

```text
Orientation is the cleanest numeric story:
  R00/R15/R30 = 7/10, 6/10, 4/10.
  Human post-training grasp/close dispersion p95 is about 13-14 deg.

Spatial follow-up is mixed:
  Corrected spatial rollout P00/P01/P10/P11 = 8/10, 6/10, 7/10, 6/10.
  This does not identify 25 cm as a high-performing threshold.

Temporal follow-up is weak for threshold justification:
  T00/T20/Twide = 10/10, 8/10, 7/10.
  But 0%, +/-20%, and [0.5, 2.0] are not a rigorous symmetric ladder.
```

## Reviewer Attack Still Open

The reviewer can still ask:

```text
How exactly were r_start = 25 cm and [0.5, 2.0] x v_ref chosen?
```

Current evidence cannot answer this as exact parameter optimization. It can
only answer that these values implement DEMT-selected structures that are shown
to matter.

## Possible Contradiction

The previous spatial argument was internally unstable:

```text
Claim A: pre-training users mostly fall within 25 cm, so 25 cm is reasonable.
Claim B: 25 cm guidance is needed to train users.
```

If the outer radius is already satisfied by pre-training users, then the training
benefit must come from something else: the full corridor/funnel path, middle and
final constraints, contact orientation, temporal pacing, repeated practice, or
the combination of P/R/V. Therefore, do not cite 25 cm pre-coverage as the main
reason for DEMT's success.

## Required Next Evidence

For a strict parameter claim:

```text
Spatial:
  Hold middle/final/funnel and R/V fixed, vary r_start or corridor family, then
  train/evaluate policies with matched N=30 and deployment protocol.

Temporal:
  Replace T00/T20/Twide with a clean ladder such as
  T00/T10/T20/T30/T40/T50 or matched [0.9,1.1], [0.8,1.2], ...

Orientation:
  Optional R05/R10/R15/R20/R30/R45 would strengthen the already plausible 15 deg
  story.
```

For rebuttal, if time is limited, the authors should not promise this. They
should explicitly state that exact threshold optimization is outside the
submitted scope.

## Suggested Wording

```text
The submitted paper evaluates DEMT at the level of learner-relevant teaching
structures rather than claiming an exhaustive optimization over every AR display
parameter. The Table 5 thresholds are task-specific implementation choices used
to scaffold the selected P/R/V structures. Our deployment and diagnostic results
show that these structures reduce spatial, contact-orientation, and temporal
variability and improve downstream deployment under a fixed learner and N=30
budget. We do not claim that r_start = 25 cm or [0.5, 2.0] x v_ref are uniquely
or globally optimal; a full threshold sweep is future work.
```

## Verdict

```text
Reject the previous R02 "accept argument" verdict.

Accept only the structure-level rebuttal:
  DEMT-selected P/R/V structures are learner-relevant and human-trainable.

Do not accept the stronger numeric-parameter claim:
  all Table 5 values are already proven reasonable learner-aware finite
  candidates.
```

Agent satisfaction:

```text
Agent1: evidence is useful but must be relabeled.
Agent2: must narrow the rebuttal and stop leaning on 25 cm pre-coverage.
Agent3: not satisfied with the old claim; satisfied only with the revised,
        structure-level limitation-aware claim.
```
