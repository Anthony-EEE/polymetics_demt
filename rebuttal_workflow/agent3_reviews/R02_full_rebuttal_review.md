# Agent3 Review: Full Parameter Reasonableness Claim

_Superseded on 2026-07-03 by `R03_strict_parameter_review.md` after the user
identified a missing contradiction: if pre-training users are already mostly
inside the 25 cm outer envelope, that fact cannot explain low pre-training
deployment success or justify why 25 cm training is needed. Do not cite this
file as the current Agent3 verdict._

Main weakness:
The original paper's ideal DEMT formulation can be read as an optimization over
`P x R x V`, while the available evidence is finite and task-specific. Any
claim that the exact numeric thresholds are optimal would be indefensible.

Most convincing evidence:

```text
Spatial:
  P1/P2 pre data show 10 cm is too restrictive for natural approach behavior.
  P6/P7 post data show actual learned demonstrations are much tighter than the
  25 cm outer envelope.

Orientation:
  R00/R15/R30 rollout = 7/10, 6/10, 4/10.
  P6/P7 post grasp/close dispersion p95 is about 13-14 deg, with about
  99-100% coverage inside 15 deg.

Temporal:
  T00/T20/Twide rollout = 10/10, 8/10, 7/10.
  Human duration and mean-speed ratios are mostly covered by [0.5, 2.0], but
  this is supporting evidence only.
```

Reviewer attack still open:
If the rebuttal tries to say "we found the optimal parameters", the attack is
still open. If the rebuttal says "these are reasonable finite candidates
supported by sensitivity checks and human diagnostics", the attack is
adequately answered.

Possible contradiction:
Uniform 25 cm simulation is not the same as 25 cm AR guidance. This is only a
contradiction if the paper claims the guided data are uniformly distributed in
the 25 cm disk. The new wording avoids that by treating 25 cm as an outer
capture envelope and citing post-training tightness.

Required next evidence:
No additional evidence is required for the narrowed rebuttal claim. E02
human-prior simulation would strengthen a future-paper argument but is not
necessary for the current rebuttal unless the authors want to claim learner
superiority of a human-prior distribution.

Suggested wording:

```text
The submitted version does not claim global optimality of these thresholds.
They are task-specific AR guidance values implementing the DEMT-selected
structures. We added finite candidate sensitivity analyses and real-user
diagnostics showing that the values correspond to human-achievable and
learner-relevant consistency ranges under the fixed learner and N=30 budget.
```

Verdict:
accept argument, conditional on the conservative wording in
`rebuttal_workflow/claim_ledger.md` and
`rebuttal_workflow/rebuttal_fragments/parameter_reasonableness_claim.md`.

Agent satisfaction:

```text
Agent1: satisfied. Current evidence is auditable and documented.
Agent2: satisfied. The claim is narrowed to finite-candidate reasonableness.
Agent3: satisfied. No exact-optimality claim remains, and the main reviewer
        contradiction has a defensible answer.
```
