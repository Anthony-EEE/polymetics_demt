# Agent2 Claim Ledger

_Revised after strict Agent3/user challenge on 2026-07-03._

## Revision Summary

The earlier ledger overclaimed. In particular, the P1/P2 pre-training
nearest-to-corridor-plane statistics do **not** justify the 25 cm training
parameter by themselves. If many pre-training demonstrations are already within
the 25 cm outer envelope, then that fact cannot explain why training with a
25 cm outer envelope is necessary, nor why pre-training deployment success is
low. Pre-training failure in the paper is deployment failure under the fixed
learner, not a simple violation of one spatial radius.

The safer rebuttal position is:

```text
Agent3 should still push toward a global-optimality-style explanation. Agent1
and Agent2 should answer with bounded / constrained optimality: the Table 5
values are the strongest currently defensible finite candidates under
human-compatibility, learner-compatibility, and available sensitivity evidence.
This is not a proof of literal global optimality.
```

## Three-Agent Convergence: 2026-07-03

Agent1, Agent2, and Agent3 independently converged on the same boundary:

```text
Current evidence supports bounded finite-candidate wording, not exact global
optimality.

Orientation is the strongest current numeric story.
Spatial requires a coupled fixed-ratio funnel sweep if the rebuttal needs a
stronger claim about 25 cm.
Temporal remains a broad pacing-scaffold claim unless a clean ladder is run.
Human percentile / mean-std audits are compatibility evidence only; they do not
prove learner optimality and can merely restate weak pre-training behavior.
```

The actionable queue is now:

```text
rebuttal_workflow/experiment_queue.md
```

## C-BOUNDED-OPTIMALITY

Claim ID:
C-BOUNDED-OPTIMALITY

Reviewer attack:
Why should we believe the submitted AR guidance settings are close to optimal,
rather than arbitrary implementation constants?

Claim:
Exact global optimization over all AR parameters is practically infeasible, but
the settings can be defended as bounded / constrained finite candidates because
they jointly satisfy:

```text
human compatibility:
  Users can interact with the guidance without being over-constrained at the
  start of training.

learner compatibility:
  Post-training unguided demonstrations show lower MPCV/MCOD/MPSV, lower
  validation loss, and higher EDSR.

negative sensitivity:
  Looser orientation and broader temporal variation hurt deployment in finite
  sensitivity checks.

parameter role separation:
  r_start is an outer feedback-entry radius; r_middle/r_final and R/V cues are
  the tighter learner-facing constraints.
```

Evidence rating:
acceptable for rebuttal if phrased as bounded optimality / finite-candidate
reasonableness. Not acceptable as mathematical global optimality.

Allowed wording:
The guidance values are the best currently defensible constrained candidates
under this robot/task/learner/user-budget setting.

Forbidden wording:
The guidance values are proven global optima.

## C-SPATIAL-25

Claim ID:
C-SPATIAL-25

Reviewer attack:
If pre-training users are mostly already inside the 25 cm outer envelope, why
does pre-training deployment success remain low, and why would 25 cm training be
necessary?

Revised claim:
The 25 cm value should **not** be used as a central proof of spatial training
necessity. It can only be described as a permissive outer AR feedback/capture
radius. The main paper's spatial evidence is instead that DEMT post-training
demonstrations have much lower full-trajectory spatial variability and much
higher deployment success than pre-training/control data.

Evidence:

```text
Paper EDSR:
  Target P1 -> P6 trained prism: 14.0% -> 75.0%
  Target P2 -> P7 unseen cube:   22.0% -> 91.0%
  Control does not improve comparably.

Paper Table 9 full-trajectory spatial consistency (MPCV):
  Target P1 prism pre  = 0.0046 +/- 0.0016
  DEMT P6 prism post   = 0.0007 +/- 0.0004
  Target P2 cube pre   = 0.0083 +/- 0.0014
  DEMT P7 cube post    = 0.0005 +/- 0.0003

E01 V2 local keypoint compatibility diagnostic:
  P1 pre 25 cm coverage = 100.0%
  P2 pre 25 cm coverage = 90.8%
  P6/P7 post nearest-to-corridor-plane p95 = 9.49 / 6.67 cm
```

Evidence rating:
usable for structure-level spatial consistency and post-training tightening;
weak / do-not-use for proving that the exact 25 cm value is necessary in
isolation. Use 25 cm only as part of the 25/5/3 funnel design explanation.

Limitations:

- The V2 keypoint diagnostic is one local early-approach point, not the
  full-path MPCV used in the paper.
- Being inside 25 cm does not imply robot learnability. The learner can still
  fail because of full trajectory shape, contact orientation, timing, action
  multimodality, visual observations, and finite-data policy fitting.
- If the rebuttal says "25 cm is justified because pre-training users fit
  within 25 cm", a strict reviewer can ask why training is needed at all.

Allowed wording:
The 25 cm value is a permissive outer feedback radius, while the learner-relevant
spatial improvement is better supported by the reduction in full-trajectory
MPCV and the deployment improvement from P1/P2 to P6/P7. We do not claim that
25 cm alone is an optimized threshold; the more defensible design claim is that
the 25/5/3 funnel balances permissive entry with tighter task-critical guidance.

Forbidden wording:
25 cm is necessary because pre-training users are within 25 cm. 25 cm explains
the P1/P2 deployment failure. Uniform 25 cm sampling is optimal. The current
data prove exact spatial radius optimality.

Next action:
If exact spatial parameter justification is required, prioritize E05 from
`rebuttal_workflow/experiment_queue.md`: a fixed-ratio funnel sweep that includes
the Table 5 scale and tighter/looser candidates while fixing R/V, N=30, learner,
checkpoint rule, and paired deployment starts. If E05 is not run or is negative,
keep the spatial claim at role-separated funnel / structure-level consistency.

## C-ORIENTATION-15

Claim ID:
C-ORIENTATION-15

Reviewer attack:
Why 15 deg orientation tolerance?

Revised claim:
This is the strongest numeric-parameter story, but still finite-candidate
reasonableness rather than exact optimality. The paper and follow-up evidence
support that contact-orientation consistency matters, and 15 deg is a plausible
human-achievable tolerance that remains more learnable than larger dispersion.

Evidence:

```text
Week 1 orientation rollout:
  R00/R15/R30 = 7/10, 6/10, 4/10

E03 V2 post closest_grasp / first_close dispersion to group mean:
  P6 p95 = 13.14 / 13.47 deg, coverage_15deg = 100.0% / 100.0%
  P7 p95 = 14.33 / 13.59 deg, coverage_15deg = 99.2% / 99.2%

Paper Table 9 contact-orientation consistency (MCOD):
  Target P1 prism pre = 0.3342 rad
  DEMT P6 prism post  = 0.0749 rad
  Target P2 cube pre  = 0.6582 rad
  DEMT P7 cube post   = 0.1668 rad
```

Evidence rating:
usable to strong for finite-candidate reasonableness; not exact optimality.

Limitations:
Only a small candidate set was tested. Human orientation diagnostics measure
dispersion to group mean, not exact alignment to the AR target frame.

Allowed wording:
15 deg is consistent with observed post-training orientation consistency and
with a finite sensitivity check where 30 deg degrades more.

Forbidden wording:
15 deg is exactly optimal or globally selected by DEMT.

Next action:
Optional backup/future sweep: add a local bracket R10/R20 around the existing
R00/R15/R30 with matched collection, training, and deployment protocol. Current
evidence is already usable-to-strong for bounded finite-candidate wording.

## C-TEMPORAL-SPEED

Claim ID:
C-TEMPORAL-SPEED

Reviewer attack:
Why `[0.5, 2.0] x v_ref`? The current temporal MVP compares 0%, +/-20%, and a
broad asymmetric `[-50%, +100%]`-style window, which is not a rigorous parameter
ladder.

Revised claim:
Current evidence supports temporal consistency as a DEMT structure, but does
not rigorously justify the exact `[0.5, 2.0] x v_ref` threshold.

Evidence:

```text
Paper Table 9 temporal synchronisation (MPSV):
  Target P1 prism pre = 0.0026
  DEMT P6 prism post  = 0.0013
  Target P2 cube pre  = 0.0056
  DEMT P7 cube post   = 0.0010

Week 1 temporal rollout:
  T00/T20/Twide = 10/10, 8/10, 7/10

E04 V2 human timing diagnostic:
  duration-ratio coverage in [0.5, 2.0] = 86.7% to 100.0%
  mean-speed-ratio coverage in [0.5, 2.0] = 93.3% to 100.0%
```

Evidence rating:
usable for temporal-structure relevance; weak for exact threshold
justification.

Limitations:

- The temporal MVP levels are not a clean symmetric ladder.
- The V2 diagnostic uses group-median ratios, not each person's first-trajectory
  `v_ref` from Table 5.
- The current evidence cannot distinguish whether `[0.5, 2.0]`, `[0.75, 1.5]`,
  or another interval is best.

Allowed wording:
Temporal consistency is learner-relevant, and the speed cue implements a broad
relative pacing scaffold. The exact interval is an implementation parameter and
future work should evaluate a clean temporal ladder.

Forbidden wording:
`[0.5, 2.0] x v_ref` is optimally selected or rigorously supported by the
current temporal MVP.

Next action:
If threshold justification is required, run T00/T10/T20/T30/T40/T50 or an
equivalent symmetric phase-ratio ladder with matched protocol. This is backup /
future-paper work unless the rebuttal must defend the exact speed-window
threshold.

## C-FULL-PARAMETER-CLAIM

Claim ID:
C-FULL-PARAMETER-CLAIM

Reviewer attack:
The paper jumps from DEMT's ideal `z*` formulation to concrete AR parameters.

Revised claim:
The current evidence can defend **bounded optimality / finite-candidate
reasonableness** for the Table 5 guidance design, but not exact numeric
optimality of all parameters. The rebuttal should explicitly separate these:

```text
Supported:
  DEMT-selected P/R/V structures are learner-relevant and trainable.
  Post-training unguided demonstrations have lower MPCV/MCOD/MPSV and higher
  deployment success.
  The 25/5/3 spatial funnel has a defensible role separation: permissive entry
  plus task-critical tightening.
  15 deg has reasonable finite sensitivity support.
  [0.5, 2.0] x v_ref is a broad relative pacing scaffold, but weakly supported
  as an exact threshold.

Not supported:
  r_start = 25 cm is exactly optimal.
  [0.5, 2.0] x v_ref is exactly optimal.
  The current MVPs are rigorous per-parameter sweeps for all thresholds.
```

Evidence rating:
accepted for bounded finite-candidate framing. Not accepted for literal global
optimality.

Allowed wording:
The Table 5 values are task-specific implementation choices for scaffolding the
DEMT-selected structures and can be defended as the best currently supported
constrained candidates; exact threshold optimization remains a limitation and
future work.

Forbidden wording:
The Table 5 parameters are fully justified by the current follow-up experiments.
All three numeric thresholds are learner-aware optimal candidates.

Next action:
Use `rebuttal_fragments/parameter_reasonableness_claim.md` only after its
2026-07-03 revision. Do not use the superseded R02 acceptance language. If a
stronger spatial parameter claim is needed, use E05 fixed-ratio funnel sweep as
the first new experiment; do not substitute raw pre-training mean/std sampling
for learner-evaluated finite candidates.
