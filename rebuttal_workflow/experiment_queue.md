# Agent2 Experiment Queue: Bounded Optimality Path

_Last updated: 2026-07-03 · Branch: hpc-headless-data-collection @ 73d56df_

## Three-Agent Convergence

Agent1, Agent2, and Agent3 converged on this decision:

```text
Current evidence can support bounded / constrained finite-candidate wording for
Table 5, but not exact global optimality.

Orientation is the strongest current numeric story.
Spatial needs a coupled funnel sweep if a stronger 25 cm claim is required.
Temporal remains a broad pacing scaffold unless a clean ladder is run.
Human mean/std or percentile statistics define feasible regions only; by
themselves they can merely restate weak pre-training behavior.
```

Agent3 acceptance criteria for any stronger bounded-optimality claim:

```text
1. Include the Table 5 value in a finite candidate set with tighter and looser
   alternatives.
2. Fix all non-tested variables: same robot, task family, learner, N=30,
   training budget, checkpoint rule, and deployment/evaluation starts.
3. Use deployment success as the primary metric. Treat validation loss and
   MPCV/MCOD/MPSV as secondary diagnostics.
4. Evaluate human compatibility separately from learner compatibility.
5. Claim Pareto optimality only if no tested alternative is both more
   human-compatible and at least as learnable, or more learnable and at least as
   human-compatible.
6. If a better finite candidate appears, downgrade or revise the rebuttal claim.
```

## Rebuttal Disposition

Can enter rebuttal now, with conservative wording:

```text
C-BOUNDED-OPTIMALITY:
  Table 5 values are bounded finite candidates under this robot/task/learner/
  user protocol/N=30 setting, not globally optimized thresholds.

C-SPATIAL-25:
  25 cm is a permissive outer feedback-entry radius in a 25/5/3 tightening
  funnel. The main spatial evidence is paper EDSR and Table 9 MPCV, not local
  25 cm pre-coverage.

C-ORIENTATION-15:
  15 deg is human-compatible and learner-aware finite-candidate evidence,
  supported by R00/R15/R30 and post-training human p95 around 13-14 deg.

C-TEMPORAL-SPEED:
  [0.5, 2.0] x v_ref is a broad relative pacing scaffold. Temporal consistency
  is learner-relevant, but the exact interval is not optimized.
```

Must be limitation / future work unless new experiments are run:

```text
Exact or global optimality for any Table 5 value.
Exact spatial threshold optimality for r_start = 25 cm.
Exact temporal threshold optimality for [0.5, 2.0] x v_ref.
Any claim that pre-training mean/std or percentiles prove optimal guidance.
Any claim that P00/P01/P10/P11 is a rigorous coupled-funnel sweep.
```

## E00: Human Percentile Bound Audit

Status:

```text
completed / interpreted / usable as support
```

Reviewer concern:
Are Table 5 values human-compatible, or arbitrary?

Current evidence:
V2 real-user diagnostics already contain spatial keypoints, orientation event
quaternions, and temporal summaries.

Gap:
There was no single auditable table comparing Table 5 values with nearby
tighter/looser alternatives.

This experiment answers:
Which candidate values are plausible human-compatibility bounds.

The claim it can support:
Table 5 sits in a defensible human-compatible range.

The claim it cannot support:
Learner optimality, exact global optimality, or Pareto optimality by itself.

If the result is positive, we will say:
The chosen values avoid over-constraining novices while post-training behavior
tightens inside the outer envelopes.

If the result is negative, we will say:
Human diagnostics support only broad compatibility; threshold choice remains
future work.

Experiment request to Agent1:
Compute P/R/V mean/std, p50/p75/p90/p95, and coverage for spatial
`10/15/20/25/30 cm`, orientation `10/15/20/30 deg`, and temporal `[0.8,1.25]`,
`[0.75,1.5]`, `[0.5,2.0]`.

Expected result that would support us:
Table 5 brackets pre-training behavior while post-training behavior tightens
well inside the envelope.

Expected result that would hurt us:
Adjacent alternatives dominate on coverage with no clear tradeoff.

Resource budget:
Read-only CPU analysis, no training.

Stop condition:
One auditable CSV/table.

Rebuttal deadline relevance:
immediate.

Evidence rating:
usable for human compatibility; weak alone for optimality.

Artifacts:

```text
outputs/rebuttal_workflow/human_percentile_bound_audit.csv
rebuttal_workflow/agent1_results/E00_human_percentile_bound_audit.md
```

## E05: Fixed-Ratio Spatial Funnel Sweep

Status:

```text
planned / highest-value new experiment if compute allows
```

Reviewer concern:
Why `r_start = 25 cm`, and why should the old independent `P00/P01/P10/P11`
design answer that?

Current evidence:
Corrected spatial rollout is mixed:

```text
P00/P01/P10/P11 = 8/10, 6/10, 7/10, 6/10
P10 validation is worse, but rollout does not give a clean monotonic story.
```

Gap:
No local finite-candidate sweep around the submitted spatial funnel.

This experiment answers:
Whether the submitted spatial scale is Pareto-defensible against nearby tighter
and looser funnel candidates.

The claim it can support:
The `25/5/3 cm` spatial funnel is a bounded finite candidate inside a coupled
tightening funnel.

The claim it cannot support:
Exact global spatial optimality.

If the result is positive, we will say:
The submitted-scale funnel is non-dominated: tighter funnels hurt human
feasibility or collection, while looser funnels hurt learner deployment.

If the result is negative, we will say:
The submitted spatial scale is not uniquely supported; spatial evidence should
remain structure-level with threshold optimization as future work.

Experiment request to Agent1:
Fix R and V. Sweep coupled spatial funnel scale with N=30 demos each. Preferred
if the true three-stage funnel is implementable:

```text
S20 = 20 / 4 / 2.4 cm
S25 = 25 / 5 / 3.0 cm
S30 = 30 / 6 / 3.6 cm
optional S15 and S35 if the first three are ambiguous
```

If the current simulator only exposes corridor/pre-grasp radii, use the
matched proxy family:

```text
20:4.8 cm
25:6.0 cm
30:7.2 cm
optional 15:3.6 and 35:8.4 cm
```

Expected result that would support us:
S25 is best or statistically tied on rollout and not worse on validation; S30+
degrades learner fit; S20- is less human-compatible or harder to collect.

Expected result that would hurt us:
S20 or S30 clearly dominates S25, or all conditions are indistinguishable.

Resource budget:
Three core conditions x N=30 collection/HDF5/training/evaluation. Prefer
20-30 paired rollout starts per condition if feasible.

Stop condition:
Stop after the matched-seed sweep; do not chase extra seeds unless ambiguity
would change rebuttal wording.

Rebuttal deadline relevance:
immediate if compute allows; otherwise record as the first future-work item.

Evidence rating:
strong if positive, usable if mixed, weak/do-not-use for numeric threshold if
S25 is dominated.

## E06: Clean Temporal Ladder

Status:

```text
backup / future paper unless reviewer demands exact speed-window support
```

Reviewer concern:
`T00/T20/Twide` is not a clean ladder and does not prove `[0.5, 2.0] x v_ref`.

Current evidence:

```text
T00/T20/Twide latest rollout = 10/10, 8/10, 7/10
human temporal coverage supports broad compatibility, not exact per-user v_ref
```

Gap:
No symmetric or monotonic threshold ladder.

Experiment request to Agent1:
Fix spatial path and orientation; run `T00/T10/T20/T30/T40/T50` or minimal
`T00/T20/T40/T50`, all with matched N=30 and the same evaluation.

Rebuttal deadline relevance:
backup.

Evidence rating:
usable if positive for temporal sensitivity; still weak for exact threshold
optimality.

## E07: Orientation Local Bracket

Status:

```text
backup / future paper
```

Reviewer concern:
Why `15 deg`, not `10 deg` or `20 deg`?

Current evidence:

```text
R00/R15/R30 rollout = 7/10, 6/10, 4/10
post-training grasp/close p95 to group mean is about 13-14 deg
```

Experiment request to Agent1:
Add `R10` and `R20` to the existing `R00/R15/R30`, fixing P/V and using N=30.

Rebuttal deadline relevance:
backup. Current orientation evidence is already usable-to-strong for bounded
finite-candidate wording.

Evidence rating:
strong if positive; current evidence remains usable if not run.

## E08: Human-Derived P/R/V Sampling

Status:

```text
future paper only unless Agent3 rejects E05
```

Reviewer concern:
Could parameters be derived from real users rather than hand-picked?

Current evidence:
V2 diagnostics exist, but direct pre-training mean/std sampling risks
reproducing weak unguided behavior.

Experiment request to Agent1:
Compare pre-derived, post-derived, and Table 5-derived P/R/V distributions with
matched learner training and deployment. Prefer bounded percentiles or
truncated empirical distributions over raw Gaussian mean/std.

Rebuttal deadline relevance:
future paper only.

Evidence rating:
potentially strong for an ICRA/journal extension; weak or misleading if used
alone in the rebuttal.
