# DEMT Rebuttal Research Workflow

_Last updated: 2026-07-03_

## Purpose

This document defines the 3-agent workflow for the DEMT rebuttal and follow-up experiments.
It incorporates the prior multi-agent history recorded in:

```text
handoffs/multiagent_history_example.md
```

The goal is to make the rebuttal research process controlled, auditable, and claim-driven. The originally desired scientific target was:

```text
The AR guidance parameters are reasonable, human-compatible, and learner-aware
finite candidates for this robot, task family, learner, and N=30 demonstration budget.
```

Strict Agent3 revision on 2026-07-03:

```text
Agent3 should still push Agent1/Agent2 toward a global-optimality-style answer.
The acceptable answer is bounded / constrained optimality: the Table 5 values
are the strongest currently defensible finite candidates under human
compatibility, learner compatibility, and available sensitivity evidence. This
is not a literal proof of global optimality.
```

The workflow must not claim:

```text
The parameters are globally or exactly optimal.
```

Agent2 owns the argument. Agent1 executes. Agent3 critiques. Agent1 and Agent3 do not directly coordinate.

## Current Claim Boundary

The paper already establishes the P/R/V teaching-structure space:

```text
P: spatial path structure
R: contact / grasp orientation structure
V: temporal pacing and phase timing structure
```

The rebuttal gap is not whether P/R/V structures matter. The gap is whether the concrete AR guidance parameters are defensible:

```text
Spatial corridor: r_start = 25 cm, r_middle = 5 cm, r_final = 3 cm
Grasp orientation: 15 deg
Speed cue: [0.5, 2.0] x v_ref
```

The strongest safe framing after strict review is:

```text
The Table 5 values instantiate DEMT-selected structures and are defended as
bounded finite candidates for this robot/task/learner/user-budget setting. They
balance human feasibility and learner-relevant consistency; exhaustive global
threshold optimization is not claimed.
```

For spatial guidance, the key wording is:

```text
25 cm is an outer human guidance / capture envelope. It is not the desired final
demonstration variance, not a claim that uniform 25 cm sampling is optimal, and
not by itself an explanation of why pre-training deployment success is low.
```

## Current Evidence Ledger

### Week 1 Simulation Evidence

Use these results as finite sensitivity evidence, not exact optimality evidence.

```text
Corrected spatial rollout:
  P00/P01/P10/P11 = 8/10, 6/10, 7/10, 6/10

Corrected spatial validation:
  P10 is harder to fit, but rollout is mixed.

Corrected annulus stress, 0.25 <= d <= 0.50 m:
  P00/P01/P10/P11 = 2/10, 1/10, 2/10, 1/10

Orientation rollout:
  R00/R15/R30 = 7/10, 6/10, 4/10

Temporal latest-checkpoint rollout:
  T00/T20/Twide = 10/10, 8/10, 7/10
```

Interpretation:

- Spatial Week 1 is valid but mixed. It supports sensitivity / learner-fit discussion, not a clean monotonic deployment claim.
- Annulus stress is OOD robustness caution, not main evidence for choosing 25 cm.
- Orientation is the cleanest Week 1 story.
- Temporal is usable but should be described carefully because `[0.5, 2.0] x v_ref` is not a fixed metric speed threshold.

### Week 2 Human-Data Evidence

The P1/P2/P6/P7 human keypoint diagnostics are useful but must be placed inside
the broader 25/5/3 funnel argument. They do not prove the 25 cm parameter by
themselves. The paper's stronger spatial evidence is full-trajectory MPCV plus
deployment success improvement.

Corrected definitions:

```text
corridor_crossing:
  CSV key name retained for compatibility
  means each demo's EE point closest to y = 0 plane
  reviewer-facing wording should say nearest-to-corridor-plane early approach keypoint
  analyze x-z spread

pregrasp_keypoint:
  first sustained steep z drop after raw frame >= 70
  analyze x-y spread

coordinate correction:
  collected data are left-handed
  FK output must mirror y = -y
```

Key result:

```text
P1 pre skill1 corridor_crossing x-z:
  center = (43.19, 17.04) cm
  std_x = 8.32 cm, std_z = 6.19 cm
  radius mean = 8.98 cm
  radius p90 = 15.83 cm
  radius p95 = 18.28 cm
  radius max = 23.71 cm
  within 10 cm = 65.0%
  within 25 cm = 100.0%

P2 pre skill2 corridor_crossing x-z:
  center = (44.00, 20.45) cm
  std_x = 12.74 cm, std_z = 8.83 cm
  radius mean = 13.88 cm
  radius p90 = 23.63 cm
  radius p95 = 26.70 cm
  radius max = 32.64 cm
  within 10 cm = 32.5%
  within 25 cm = 90.8%

P6 post skill1 nearest-to-corridor-plane x-z:
  radius p50 = 4.03 cm
  radius p90 = 7.22 cm
  radius p95 = 9.49 cm
  radius max = 16.80 cm

P7 post skill2 nearest-to-corridor-plane x-z:
  radius p50 = 3.53 cm
  radius p90 = 6.26 cm
  radius p95 = 6.67 cm
  radius max = 7.54 cm
```

Interpretation:

```text
These local keypoint numbers show that 25 cm is permissive, but they do not
justify why 25 cm training is necessary in isolation. The stronger explanation
is that 25 cm is only the outer feedback-entry radius in a 25/5/3 tightening
funnel. Since many pre-training keypoints are already inside 25 cm, pre-training
deployment failure must be explained by full-trajectory path consistency,
contact orientation, timing, visual/action distribution, and finite-budget
learner fit.
```

Paper-level structure evidence to prioritize:

```text
Real-robot EDSR:
  Target P1 -> P6 trained prism = 14.0% -> 75.0%
  Target P2 -> P7 unseen cube   = 22.0% -> 91.0%

Table 9 MPCV:
  Target P1 prism pre = 0.0046 +/- 0.0016
  DEMT P6 prism post  = 0.0007 +/- 0.0004
  Target P2 cube pre  = 0.0083 +/- 0.0014
  DEMT P7 cube post   = 0.0005 +/- 0.0003
```

Do not present pre-grasp concentration as a major discovery. Because the target is fixed, pre-grasp should naturally be concentrated. It is mainly a sanity check.

### Week 2 Orientation / Temporal Human Diagnostics

Use these as compatibility diagnostics. The learner-aware evidence still comes
from Week 1 finite simulation sweeps.

```text
Orientation post-training, angle to group mean:
  P6 closest_grasp p95 = 13.14 deg, coverage_15deg = 100.0%
  P6 first_close   p95 = 13.47 deg, coverage_15deg = 100.0%
  P7 closest_grasp p95 = 14.33 deg, coverage_15deg = 99.2%
  P7 first_close   p95 = 13.59 deg, coverage_15deg = 99.2%

Temporal human diagnostics, ratio to group median:
  duration coverage in [0.5, 2.0] = 86.7% to 100.0% across groups
  mean-speed coverage in [0.5, 2.0] = 93.3% to 100.0% across groups
```

Interpretation:

```text
15 deg is consistent with post-training human grasp-orientation dispersion and
the R00/R15/R30 learner sensitivity. The temporal human diagnostics support
human compatibility of a broad relative speed window, but not exact validation
of per-user v_ref.
```

## Evidence Quarantine

These artifacts or analyses must not be used for rebuttal claims:

```text
dataset/abla1_full old spatial results
old wrong-center spatial HDF5 / training / rollout artifacts
old spatial analysis that treats [0.3, 0.0, 0.5] as an empirical human center
old pregrasp analysis that treats [0.5, 0.5, 0.22] as the human pre-grasp reference
old pregrasp x-z plots
any claim that corrected Week 1 spatial rollout proves monotonic degradation
any claim that annulus stress proves tighter guidance improves OOD robustness
any claim that P1/P2 pre keypoints being inside 25 cm justifies 25 cm training
any claim that 25 cm pre-coverage explains low pre-training EDSR
R02_full_rebuttal_review.md as current Agent3 verdict; it is superseded by R03
```

The valid corrected spatial root is:

```text
/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full_arcenter
```

## Agent Roles

### Agent1: Research Engineer

Agent1 executes tasks issued by Agent2. Agent1 is the implementation and analysis worker.

Responsibilities:

- Read relevant handoffs, paper excerpts, scripts, logs, and prior outputs before acting.
- Inspect implementation details in the codebase.
- Prepare data collection, conversion, training, rollout, plotting, and diagnostic jobs.
- Run nontrivial compute through Slurm.
- Verify artifacts: JSON summaries, CSVs, videos, HDF5 masks, logs, plots, and job states.
- Report implementation facts separately from scientific interpretation.
- Maintain result cards that can be consumed by Agent2.
- Document failed or invalid artifacts so they are not cited later.

Agent1 must not:

- Decide the final rebuttal claim.
- Expand experimental scope without Agent2 approval.
- Interact with Agent3 directly.
- Treat validation loss as deployment success.
- Use quarantined evidence.
- Modify raw human data.

#### Agent1 Read Permissions

Agent1 may read:

```text
/scratch/prj/eng_demt_robot_learning/polymetics_demt
/scratch/prj/eng_demt_robot_learning/polymetics_demt/handoffs
/scratch/prj/eng_demt_robot_learning/polymetics_demt/outputs
/scratch/prj/eng_demt_robot_learning/polymetics_demt/docs
/scratch/prj/eng_demt_robot_learning/polymetics_demt/scripts
/scratch/prj/eng_demt_robot_learning/polymetics_demt/examples
/scratch/prj/eng_demt_robot_learning/polymetics_demt/training_config
/scratch/prj/eng_demt_robot_learning/trained_models
~/code/arcap
/scratch/users/k23114984/pybullet_data
```

Human data policy:

```text
/scratch/users/k23114984/pybullet_data contains real human demonstrations.
Pooled, shuffled, symlinked, or re-split data are still real-user data.
Safe wording: pooled and re-split real-user demonstrations.
```

Agent1 must not call these data fake, synthetic, or cheating.

#### Agent1 Write Permissions

Agent1 may write experiment outputs under:

```text
/scratch/prj/eng_demt_robot_learning/polymetics_demt/outputs/rebuttal_workflow/
/scratch/prj/eng_demt_robot_learning/polymetics_demt/outputs/week2_human_diagnostics_keypoints_quick/
/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/new_rebuttal_experiment_roots/
/scratch/prj/eng_demt_robot_learning/polymetics_demt/training_config/rebuttal_*/
/scratch/prj/eng_demt_robot_learning/trained_models/rebuttal_*/
```

Agent1 may write result cards only in:

```text
rebuttal_workflow/agent1_results/
```

Agent1 may modify code only when Agent2 explicitly requests code changes. Preferred locations:

```text
scripts/rebuttal_*
examples/rebuttal_*
training_config/rebuttal_*
```

Agent1 must not modify:

```text
/scratch/users/k23114984/pybullet_data
the submitted PDF
rebuttal_workflow/agent3_reviews/
Agent2 decision logs except by appending requested result-card links
```

#### Agent1 Compute Rules

Agent1 should use:

```text
CPU preprocessing / plotting / diagnostics:
  partition = interruptible_cpu
  walltime = 00:30:00 to 01:00:00 for non-training jobs

GPU training:
  use existing training scripts and project scratch output paths

Rollout / evaluation:
  prefer sbatch when runtime is nontrivial
```

Avoid writing large model outputs to `/users`. Prefer:

```text
/scratch/prj/eng_demt_robot_learning/trained_models
```

#### Agent1 Result Card

Every Agent1 result must use:

```text
Experiment ID:
Purpose:
Agent2 request:
Code changes:
Commands / Slurm jobs:
Data generated:
Models generated:
Primary metric:
Secondary metrics:
Plots / summaries:
Verification performed:
Failures / warnings:
Can this support the requested claim? yes / no / partial
Reason:
Next engineering action if requested:
```

### Agent2: DEMT First Author and Coordinator

Agent2 owns the scientific argument, reviewer strategy, and experiment queue.

Responsibilities:

- Assume the strongest reviewer criticism.
- Convert criticism into explicit claims.
- Decide whether existing evidence is enough.
- Issue minimal, precise Agent1 tasks.
- Interpret Agent1 results and assign evidence strength.
- Draft rebuttal fragments, figure plans, and table plans.
- Summarize only the relevant evidence for Agent3.
- Iterate based on Agent3 criticism.
- Keep CoRL rebuttal needs separate from ICRA / journal extension ideas.

Agent2 is the only agent allowed to coordinate both Agent1 and Agent3.

#### Agent2 Read Permissions

Agent2 may read:

```text
DEMT paper PDF
handoffs/
outputs/
docs/
scripts/
examples/
training_config/
Slurm logs under outputs/ or dataset experiment roots
rebuttal_workflow/agent1_results/
rebuttal_workflow/agent3_reviews/
rebuttal_workflow/rebuttal_fragments/
research_workflow.md
```

#### Agent2 Write Permissions

Agent2 may write or modify:

```text
research_workflow.md
rebuttal_workflow/README.md
rebuttal_workflow/agent2_master_plan.md
rebuttal_workflow/reviewer_attacks.md
rebuttal_workflow/experiment_queue.md
rebuttal_workflow/decision_log.md
rebuttal_workflow/rebuttal_fragments/
handoffs/week2_experiment.md
handoffs/week2_research_thinking.md
```

Agent2 may request that Agent1 modify code, run Slurm jobs, or regenerate outputs. Agent2 should not personally run long training or rollout jobs unless explicitly acting as Agent1 for that task.

Agent2 must not:

- Overclaim exact optimality.
- Hide mixed or negative results.
- Treat validation loss as the primary deployment metric.
- Conflate AR guidance tolerance with uniform simulation sampling.
- Use quarantined evidence.
- Let an experiment start without a written claim and stop condition.

#### Agent2 Planning Gate

Before issuing any Agent1 task, Agent2 must fill:

```text
Reviewer concern:
Current evidence:
Gap:
This experiment answers:
The claim it can support:
The claim it cannot support:
If the result is positive, we will say:
If the result is negative, we will say:
Experiment request to Agent1:
Expected result that would support us:
Expected result that would hurt us:
Resource budget:
Stop condition:
Rebuttal deadline relevance: immediate / backup / future paper only
```

If these fields cannot be filled, the task is not ready.

#### Agent2 Evidence Rating

Agent2 must rate every result:

```text
strong:
  Can be used centrally in rebuttal.

usable:
  Can be used as supporting evidence with conservative wording.

weak:
  Keep in internal report or appendix only.

do not use:
  Invalid, misleading, or likely to create a stronger reviewer attack.
```

#### Agent2 Claim Ledger

Agent2 should maintain claims in this form:

```text
Claim ID:
Reviewer attack:
Claim:
Evidence:
Evidence rating:
Limitations:
Allowed wording:
Forbidden wording:
Next action:
```

### Agent3: Senior Reviewer / PI Critic

Agent3 is the strict reviewer / PI pressure role. Agent3 only evaluates Agent2's summaries.

Responsibilities:

- Identify the sharpest weakness in the argument.
- Check whether evidence actually answers the reviewer concern.
- Identify overclaims and hidden contradictions.
- Decide whether more evidence is required.
- Suggest tighter wording.

Agent3 must not run experiments, inspect raw code by default, or direct Agent1.

#### Agent3 Read Permissions

Agent3 may read:

```text
Agent2 summaries
Agent2-selected result cards
Agent2-selected figures and tables
Agent2-selected rebuttal fragments
Agent2-selected paper excerpts
research_workflow.md
```

Agent3 should not independently browse raw experiment directories unless Agent2 asks for a targeted audit.

#### Agent3 Write Permissions

Agent3 may write:

```text
rebuttal_workflow/agent3_reviews/
```

Agent3 must not modify:

```text
code
datasets
Slurm scripts
Agent1 result cards
raw outputs
Agent2 decision logs except through clearly marked review feedback
```

#### Agent3 Review Gate

Agent3 should review with:

```text
Main weakness:
Most convincing evidence:
Reviewer attack still open:
Possible contradiction:
Required next evidence:
Suggested wording:
Verdict: accept argument / needs one more experiment / too weak / future paper only
```

## Workflow State Machine

Every experiment should move through these states:

```text
proposed:
  Agent2 has a reviewer concern but no approved task yet.

planned:
  Agent2 filled the planning gate and issued an Agent1 task.

running:
  Agent1 has submitted or started the job.

completed:
  Agent1 has produced outputs and a result card.

interpreted:
  Agent2 assigned evidence rating and wrote allowed / forbidden wording.

reviewed:
  Agent3 reviewed Agent2's summary.

accepted:
  Agent2 decided it can enter rebuttal or internal report.

quarantined:
  Result is invalid, misleading, or unsafe to cite.
```

No result should be used in rebuttal before it reaches `interpreted`. Central claims should reach `reviewed`.

## Workflow Loop

Use this loop:

```text
1. Agent2 defines reviewer concern and claim.
2. Agent2 fills the planning gate.
3. Agent2 issues the minimal Agent1 task.
4. Agent1 executes with smoke checks and Slurm jobs where appropriate.
5. Agent1 returns a result card.
6. Agent2 updates the claim ledger and drafts wording.
7. Agent2 sends a concise summary to Agent3.
8. Agent3 critiques.
9. Agent2 decides: stop, revise wording, quarantine, or request another experiment.
```

## Recommended Directory Layout

Create only when needed:

```text
rebuttal_workflow/
  README.md
  agent2_master_plan.md
  reviewer_attacks.md
  experiment_queue.md
  decision_log.md
  claim_ledger.md

  agent1_results/
    E01_human_spatial_stats.md
    E02_human_prior_sampling.md
    E03_orientation_threshold.md
    E04_temporal_threshold.md

  agent3_reviews/
    R01_spatial_25cm_review.md
    R02_full_rebuttal_review.md
    R03_strict_parameter_review.md
    R04_global_optimal_pressure_review.md

  rebuttal_fragments/
    spatial_25cm_argument.md
    orientation_15deg_argument.md
    temporal_speedcue_argument.md
```

## Current Experiment Queue

Detailed queue after the 2026-07-03 three-agent bounded-optimality audit is in:

```text
rebuttal_workflow/experiment_queue.md
```

That queue supersedes the old idea that E02 human-prior sampling is the main
spatial rebuttal path. The current Agent2/Agent3 convergence is:

```text
E00 human percentile bound audit:
  completed; usable as human-compatibility support only.

E05 fixed-ratio spatial funnel sweep:
  highest-value new experiment if a stronger 25 cm claim is required.

E06 clean temporal ladder:
  backup / future paper unless exact speed-window support is required.

E07 orientation bracket:
  backup / future paper; current R00/R15/R30 plus human p95 evidence is already
  usable for bounded finite-candidate wording.

E08 human-derived P/R/V sampling:
  future paper only unless paired with learner training/evaluation.
```

### E01: Human Spatial Statistics

Status:

```text
completed / interpreted / re-reviewed
```

Main outputs:

```text
outputs/week2_human_diagnostics_keypoints_v2/keypoint_spread_summary.csv
outputs/week2_human_diagnostics_keypoints_v2/human_diagnostics_summary.json
rebuttal_workflow/agent1_results/E01_human_spatial_stats_v2.md
```

Use to support:

```text
25 cm is permissive as an outer local feedback radius.
Post-training local early-approach keypoints are tighter than pre-training.
```

Do not use to claim:

```text
25 cm is globally optimal.
Uniform 25 cm sampling is ideal for learning.
25 cm pre-coverage explains low pre-training deployment success.
25 cm pre-coverage proves 25 cm training is necessary.
```

### E02: Human-Prior Simulation Sampling

Status:

```text
proposed
```

Reviewer concern:

```text
If uniform 25 cm sampling learns poorly, why use 25 cm guidance?
```

Experiment purpose:

```text
Future-paper test of whether a non-uniform human-shaped outer-envelope
distribution is more learnable than a broad uniform disk. This would not by
itself prove that r_start = 25 cm is optimal.
```

Candidate conditions:

```text
U10_P03   uniform 10 cm corridor + tight pregrasp
U25_P03   uniform 25 cm corridor + tight pregrasp
Hpre_P03  empirical P1/P2 human crossing prior + tight pregrasp
H90_P03   human-prior truncated at p90 + tight pregrasp
```

Optional percentile ladder:

```text
H50_P03
H60_P03
H70_P03
H80_P03
H90_P03
```

Primary metric:

```text
rollout success
```

Secondary metrics:

```text
validation loss
trajectory spread
distance to corridor tube
failure type
```

Expected useful result:

```text
Human-shaped sampling is more learnable than broad uniform 25 cm sampling under
matched N=30, supporting the idea that AR tolerance is not the same as the
effective demonstration distribution.
```

Safe wording if positive:

```text
The effective demonstration distribution under an outer spatial envelope is not
uniform; human priors and downstream constraints can make it tighter and more
learnable. This supports the envelope-vs-distribution distinction, not exact
25 cm optimality.
```

Safe wording if negative:

```text
The simulation does not establish a learner advantage for the human-prior
approximation. Keep the rebuttal limited to structure-level DEMT evidence and
do not use E02 for spatial threshold justification.
```

Current decision:

```text
required only if the rebuttal insists on a spatial threshold claim. If the
rebuttal stays at structure-level DEMT, E02 can be future work.
```

### E03: Orientation 15 Deg Argument

Status:

```text
completed / usable / reviewed
```

Known result:

```text
R00/R15/R30 rollout = 7/10, 6/10, 4/10
P6/P7 post grasp/close p95 to group mean = about 13-14 deg
```

Use to support:

```text
15 deg is a plausible human-feasible tolerance near a learnable range,
while 30 deg is looser and degrades more.
```

Do not use to claim:

```text
15 deg is exactly optimal.
```

### E04: Temporal Speed Cue Argument

Status:

```text
completed / usable for structure-level timing only / weak for exact threshold
```

Known result:

```text
T00/T20/Twide rollout = 10/10, 8/10, 7/10
human duration/speed coverage in [0.5, 2.0] is mostly high, but measured
against group median rather than exact per-user v_ref
```

Use to support:

```text
Temporal consistency matters for the fixed learner and N=30 budget.
```

Do not use to claim:

```text
[0.5, 2.0] x v_ref is globally optimal.
```

Limitation:

```text
v_ref is normalized from a reference trajectory, not a fixed metric speed threshold.
T00/T20/Twide is not a clean symmetric ladder.
```

Future-paper improvement:

```text
T00, T10, T20, T30, T40, optional T50
```

## Reviewer Attacks To Keep Active

Agent2 and Agent3 should repeatedly test the plan against:

```text
Why 25 cm rather than 10 cm?
If uniform 25 cm sampling learns poorly, why use 25 cm guidance?
Are you confusing AR guidance tolerance with the training-data distribution?
Are you proving exact optimality or finite-candidate reasonableness?
Are the human diagnostics from pre-training or post-training?
Does pregrasp concentration just reflect the fixed target?
Does validation loss actually predict deployment success?
Are the new experiments small enough for rebuttal, or are they becoming a new paper?
Is pooled / re-split user data being framed honestly as real-user data organization?
Does the temporal speed cue rely on per-user v_ref rather than a fixed threshold?
```

## Things Not To Say

```text
The original geometric variant was wrong.
25 cm is globally optimal.
Appendix says 25 cm is good but simulation says 25 cm is bad.
Pooled/re-split user data is fake or cheating.
Week 1 spatial rollout proves monotonic degradation.
Annulus stress proves tighter guidance improves OOD robustness.
[0.5, 2.0] x v_ref is a fixed metric speed.
[0.3, 0.0, 0.5] is the measured human corridor center.
[0.5, 0.5, 0.22] is the measured human pre-grasp center.
Pre-grasp concentration is surprising evidence for guidance.
```

## Allowed Rebuttal Wording

Current safe wording:

```text
We agree that the continuous AR-parameter space is not exhaustively optimized in
the submitted paper. However, the Table 5 values are not arbitrary constants:
they instantiate DEMT-selected P/R/V structures under the fixed robot, task
family, learner, and N=30 budget. Our claim is bounded rather than absolute:
these values are the best currently defensible finite candidates under
human-compatibility and learner-compatibility constraints, not mathematically
proven global optima.
```

Future paper:

```text
The follow-up direction is to connect deployment-evaluated robot learning
sensitivity with human-achievable teaching behavior, so that AR guidance
parameters are calibrated against both learner constraints and real human
movement distributions.
```

## Key Source Files

```text
handoffs/multiagent_history_example.md
handoffs/week1_main-experiments.md
handoffs/week1_research_thinking.md
handoffs/week2_experiment.md
handoffs/week2_research_thinking.md
scripts/analyze_week2_human_data.py
scripts/run_week2_human_diagnostics.sh
outputs/week2_human_diagnostics_keypoints_v2/keypoint_spread_summary.csv
outputs/week2_human_diagnostics_keypoints_v2/orientation_event_summary.csv
outputs/week2_human_diagnostics_keypoints_v2/temporal_human_summary.csv
rebuttal_workflow/claim_ledger.md
rebuttal_workflow/agent3_reviews/R04_global_optimal_pressure_review.md
DEMT__Deployment_Evaluated_Machine_Teaching_Enhances_Learning_from_Human_Demonstrations.pdf
```

## Open Questions

```text
If exact spatial threshold justification is required, what controlled r_start /
funnel-family sweep is feasible?
Should E02 use P1 only, P2 only, or pooled P1/P2 human-prior sampling for a
future-paper envelope-vs-distribution test?
Should temporal be redesigned around a clean T00/T10/T20/T30/T40 ladder before
any more threshold claims?
```
