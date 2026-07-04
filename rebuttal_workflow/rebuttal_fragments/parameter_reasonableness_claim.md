# Rebuttal Fragment: Bounded Parameter Optimality

We agree that the continuous AR-parameter space is not exhaustively optimized
in the submitted paper. However, the thresholds in Table 5 are not arbitrary
constants: they instantiate the DEMT-selected P/R/V structures under a fixed
robot setup, task family, learner, and N=30 demonstration budget. Our claim is
therefore bounded rather than absolute: these values are the best currently
defensible finite candidates under human-compatibility and learner-compatibility
constraints, not mathematically proven global optima.

For spatial guidance, the key point is that the `25/5/3 cm` values form a
tightening funnel rather than a single desired demonstration variance.
`r_start = 25 cm` is a permissive outer feedback-entry radius; it should not be
interpreted as the final learner-facing consistency target. The lower radii
near the middle and final task-critical regions provide the tighter spatial
scaffold. This is consistent with the paper's outcome: after guidance removal,
DEMT users produce unguided demonstrations with much lower full-trajectory
spatial variability (MPCV) and much higher deployment success (P1 to P6:
14.0% to 75.0%; P2 to P7: 22.0% to 91.0%). The low pre-training success cannot
be explained by a single early keypoint being inside or outside 25 cm; the
learner-relevant signal is the full spatio-contact-temporal trajectory.

For orientation guidance, the 15 deg value has the cleanest finite sensitivity
support. In controlled candidates, 30 deg orientation variation degrades rollout
relative to 15 deg, and post-training human grasp/close orientations concentrate
within roughly 13-14 deg of a consistent group orientation. We therefore treat
15 deg as a human-achievable and learner-compatible finite candidate, not as an
exact optimum.

For temporal guidance, `[0.5, 2.0] x v_ref` is best framed as a broad relative
pacing scaffold. The paper shows temporal synchronisation improves after DEMT,
and the follow-up temporal MVP supports that larger timing variation hurts
deployment. But the current temporal follow-up is not a clean threshold ladder,
so we do not claim exact optimality of the interval.

Overall, DEMT supports a constrained design claim: the selected guidance values
are defensible finite candidates for the evaluated setting because they balance
human feasibility with learner-relevant consistency, while exhaustive global
optimization over all coupled AR parameters remains future work.
