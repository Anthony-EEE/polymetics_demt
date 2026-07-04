# Agent3 Review: Global-Optimality Pressure Review

_Date: 2026-07-03_

## Agent3 Position

Agent3's job is not to immediately concede that global optimality is impossible.
Agent3 should demand:

```text
Explain why these guidance settings are the best defensible settings, not just
why P/R/V structures matter.
```

Agent1/Agent2 are allowed to argue that an exact global search is practically
impossible, but they must replace it with the strongest feasible surrogate:

```text
constrained / Pareto / finite-candidate optimality under this robot, task
family, learner, user-training protocol, and N=30 budget.
```

## What Agent3 Rejects

Agent3 rejects these weak answers:

```text
We cannot do global search, so exact parameters are just implementation choices.
P/R/V matter, therefore Table 5 values are fine.
Pre-training users are inside 25 cm, therefore 25 cm is justified.
T00/T20/Twide proves [0.5, 2.0] is a good temporal threshold.
```

## What Agent3 Can Accept

Agent3 can accept a bounded-optimality argument with four parts:

```text
1. Exact global optimality is infeasible:
   The parameter space is continuous and coupled:
   r_start/r_middle/r_final, orientation tolerance, speed bounds, task phase,
   user adaptation, stochastic policy training, and deployment outcomes.

2. The selected values satisfy human-compatibility constraints:
   The guidance should not reject natural novice behaviour so aggressively that
   users spend training fighting the interface rather than learning the task.

3. The selected values satisfy learner-compatibility constraints:
   After training, unguided demonstrations must become structurally tighter and
   policies trained from them must deploy better.

4. Known looser alternatives hurt or are risky:
   Orientation 30 deg degrades relative to 15 deg.
   Temporal broad variation degrades relative to fixed / smaller variation.
   Uniform broad spatial sampling is not the intended distribution and is mixed.
```

If Agent1/Agent2 provide this, Agent3 can be satisfied that the parameters are
the best currently defensible finite candidates, while still refusing a literal
mathematical global-optimality claim.

## Parameter-by-Parameter Audit

### Spatial: 25 cm / 5 cm / 3 cm Funnel

The old argument was wrong:

```text
P1/P2 pre keypoints mostly inside 25 cm -> therefore 25 cm is justified.
```

This is not enough. If users are already inside 25 cm before training, 25 cm
cannot be the sole explanation for low pre-training EDSR or for why training is
needed.

The stronger explanation is:

```text
r_start = 25 cm is an outer capture / feedback-entry radius, not the final
learner-facing consistency target.

r_middle = 5 cm and r_final = 3 cm define the tightening funnel nearer the
task-critical path and grasp phases.

The training effect is not "get users inside 25 cm"; it is to teach a full
spatio-contact-temporal pattern whose post-training trajectories have much
lower MPCV/MCOD/MPSV and higher EDSR.
```

Evidence:

```text
P1 -> P6 EDSR: 14.0% -> 75.0%
P2 -> P7 EDSR: 22.0% -> 91.0%

Table 9 MPCV:
  P1 pre 0.0046 -> P6 post 0.0007
  P2 pre 0.0083 -> P7 post 0.0005

V2 local diagnostic:
  P6/P7 post nearest-to-corridor-plane p95 = 9.49 / 6.67 cm
```

Agent3 verdict for spatial:

```text
Acceptable as a constrained design explanation:
  25 cm is an outer permissive interface radius in a tightening funnel.

Not acceptable as proven global optimality:
  There is no direct r_start sweep showing 25 cm beats 15/20/30 cm.
```

### Orientation: 15 deg

This is the strongest numeric story.

Evidence:

```text
R00/R15/R30 rollout = 7/10, 6/10, 4/10.
Post-training human grasp/close p95 to group mean ~= 13-14 deg.
Table 9 MCOD improves strongly after DEMT.
```

Agent3 verdict for orientation:

```text
Acceptable as a finite-candidate near-optimal tolerance:
  15 deg is human-achievable and more learner-compatible than 30 deg.

Not exact:
  Missing R05/R10/R20/R45 ladder.
```

### Temporal: [0.5, 2.0] x v_ref

This is the weakest numeric story.

Evidence:

```text
Table 9 MPSV improves after DEMT.
T00/T20/Twide rollout = 10/10, 8/10, 7/10.
```

But supervisor's criticism stands:

```text
0%, +/-20%, and [0.5, 2.0] are not a clean comparable ladder.
```

Agent3 verdict for temporal:

```text
Acceptable only as a broad relative pacing scaffold motivated by temporal
consistency and per-user normalization.

Not acceptable as a proven optimal threshold:
  Need T00/T10/T20/T30/T40/T50 or equivalent.
```

## Rebuttal Wording Agent3 Can Accept

```text
We agree that the continuous AR-parameter space is not exhaustively optimized
in the submitted paper. Instead, DEMT identifies learner-relevant teaching
structures and instantiates them with task-specific guidance parameters chosen
to satisfy both human-compatibility and learner-compatibility constraints under
the fixed learner and N=30 budget. The evidence does not prove literal global
optimality, but it supports these values as bounded, finite-candidate design
choices: the full guidance funnel produces post-training demonstrations with
substantially lower MPCV/MCOD/MPSV and much higher deployment success; the 15
deg orientation tolerance lies near observed post-training human consistency
and remains more learnable than 30 deg; and the speed cue implements a relative
pacing scaffold consistent with the temporal structure that improves after
training. A full threshold sweep over all continuous parameters is left for
future work.
```

## Final Verdict

```text
Agent3 is not satisfied by "exact global optimality is impossible" alone.

Agent3 can be satisfied by a bounded-optimality explanation:
  These are the best currently defensible finite candidates under human
  compatibility, learner compatibility, and available sensitivity evidence.

Agent3 still forbids:
  claiming that every Table 5 value is mathematically or globally optimal.
```
