# CoRL Rebuttal Ablation Plan

_Date: 2026-06-27_

## Context

The submitted CoRL 2026 paper introduces Deployment-Evaluated Machine Teaching
(DEMT) for training novices to provide more robot-learnable visuomotor
demonstrations. The paper defines a teaching-structure space

```text
Z = P x R x V
```

where:

- `P` is spatial/path structure.
- `R` is contact or grasp strategy.
- `V` is temporal or phase-timing structure.

The paper's ideal formulation is:

```text
z* = arg max J(A(D^z)),  z in Z
```

where `J` is measured by downstream robot deployment performance after training
a fixed learner on demonstrations induced by teaching configuration `z`.

However, the submitted experiments only evaluate a small finite candidate set:

```text
C = {z0, zP, zR, zV}
```

This supports the claim that inconsistent successful demonstrations can hurt
learning, but it does not fully explain how the concrete AR guidance parameters
in the appendix were selected. The likely reviewer concern is that the transition
from the DEMT formula to AR guidance appears abrupt.

## Expected Reviewer Concerns

### Concern 1: DEMT Formula to AR Guidance Is Too Abrupt

The paper defines `P`, `R`, and `V`, then introduces corridor guidance, grasp
orientation guidance, and speed-bar guidance. The appendix reports concrete
values such as corridor radius, orientation tolerance, and speed tolerance.

Likely reviewer question:

```text
How were these guidance structures and thresholds selected from the DEMT
formulation?
```

The submitted paper currently gives evidence that `P/R/V` matter, but not a
direct ablation showing that the selected guidance parameters are
deployment-evaluated choices.

### Concern 2: Human Study Scale and Learner/Task Coverage

The paper uses a limited number of participants, a fixed visual-motor learner,
and a limited set of real-robot tasks. These are valid concerns, but they are
too large to fully resolve during rebuttal.

These are better framed as journal-version extensions:

- More participants.
- LIBERO multi-task benchmark validation.
- More visual-motor learners, such as ACT and possibly VLA models.
- More real-robot manipulation tasks.
- Broader structure spaces beyond only `P/R/V`.

## Short-Term Rebuttal Strategy

The best short-term patch is not to solve the full `z*` problem. Instead, add a
small deployment-evaluated ablation showing that the concrete guidance
parameters are not arbitrary.

The rebuttal story should be:

```text
The submitted paper evaluated whether P/R/V structures affect learnability.
To clarify how the DEMT-selected structures are translated into concrete AR
guidance parameters, we add a deployment-evaluated parameter ablation. For each
structure dimension, we vary the consistency constraint while keeping task
success, learner, budget, and deployment protocol fixed. The selected AR
guidance parameters lie in the high-performing region.
```

This directly addresses the formula-to-guidance gap without overclaiming global
optimality.

## Core Experimental Question

For rebuttal, the target question should be:

```text
How consistent must demonstrations be along P, R, and V for best deployment
learning under the fixed learner and finite demonstration budget?
```

This is weaker and safer than:

```text
What is the globally optimal z* over the entire P x R x V space?
```

The rebuttal can present a finite candidate selection:

```text
z_hat = arg max J(A(D^z)),  z in C_ablation
```

where `C_ablation` contains controlled parameter levels for spatial, orientation,
and temporal consistency.

## Proposed Ablation Experiments

### 1. Spatial Structure: Tube / Pre-Grasp Region Ablation

This is the easiest and fastest experiment because the current simulation code
already supports approach noise.

Question:

```text
How large can the approach/pre-grasp region be before deployment learning
degrades?
```

Candidate levels:

| Candidate | Meaning | Example Parameter |
| --- | --- | --- |
| `P0` | Fixed or near-deterministic approach | `0 cm` |
| `P1` | Small approach variation | `1 cm` |
| `P2` | Moderate approach variation | `3 cm` |
| `P3` | Large approach variation | `5 cm` |
| `P4` | Very large approach variation | `8 cm` |

If time is tight, use only three levels:

```text
0 cm, 3 cm, 6 cm
```

Expected rebuttal claim:

```text
Deployment performance is high for fixed/small/moderate approach variation and
drops when the approach region becomes too large. This supports constraining
novice demonstrations with spatial corridor guidance.
```

Important nuance:

The goal is not to prove one universal best radius. The goal is to show that
spatial consistency has a deployment-sensitive range, and the AR corridor
parameters are chosen to keep demonstrations within that range.

### 2. Contact Structure: Gripper Orientation Constraint Ablation

This is probably the most persuasive ablation because the submitted simulation
already shows orientation inconsistency causes a severe deployment drop.

Question:

```text
How much closing-orientation variation can the learner tolerate?
```

Candidate levels:

| Candidate | Meaning | Example Parameter |
| --- | --- | --- |
| `R0` | Fixed closing orientation | `0 deg` |
| `R1` | Tight orientation variation | `±5 deg` |
| `R2` | Moderate orientation variation | `±15 deg` |
| `R3` | Large orientation variation | `±30 deg` |
| `R4` | Very large or mixed orientation | `±45 deg` or submitted `Rtilt` |

Expected rebuttal claim:

```text
Deployment remains high under tight-to-moderate orientation variation but
degrades under large closing-orientation dispersion. This supports the use of
gripper-orientation guidance and explains the 15 degree tolerance in the
appendix.
```

This ablation can connect directly to the appendix parameter:

```text
Grasp orientation tolerance = 15 deg
```

### 3. Temporal Structure: Phase-Ratio / Timing Consistency Ablation

This is conceptually important but should be kept simple. Avoid a large temporal
grid during rebuttal.

Question:

```text
How similar must phase timing be across demonstrations for stable learning?
```

Represent each trajectory by a phase-ratio vector:

```text
q = [start, approach, descend, grasp, lift] / total_time
```

Then vary the amount of phase-ratio jitter across demonstrations.

Candidate levels:

| Candidate | Meaning | Example Parameter |
| --- | --- | --- |
| `V0` | Fixed phase ratio | `0% jitter` |
| `V1` | Small timing variation | `±10%` |
| `V2` | Moderate timing variation | `±25%` |
| `V3` | Large timing variation | `±50%` |

Expected rebuttal claim:

```text
Policies trained from demonstrations with consistent phase timing deploy more
reliably. Large phase-ratio variation reduces deployment success even when
scripted demonstrations remain task-successful.
```

This can connect to the appendix speed-bar parameter:

```text
relative speed tolerance = [0.5, 2.0] x v_ref
```

For rebuttal, it is enough to show that temporal inconsistency matters and that
the guidance encourages trajectories to stay within a high-performing timing
range. A full search over every phase ratio should be left for the journal
version.

## Minimal Experiment Matrix

The smallest useful rebuttal experiment is:

| Dimension | Levels | Number of Conditions |
| --- | --- | ---: |
| `P` spatial approach variation | `0, 3, 6 cm` | 3 |
| `R` orientation variation | `0, 15, 45 deg` | 3 |
| `V` phase-ratio jitter | `0, 25, 50%` | 3 |
| Shared baseline | fixed `P/R/V` | 1 |

This gives about 10 conditions if the baseline is shared.

For each condition:

- Collect `N = 30` task-successful demonstrations.
- Train the same fixed visuomotor learner.
- Evaluate with the same deployment protocol.
- Report empirical deployment success rate, `EDSR`.

First-pass smoke test:

- 1 dataset seed per condition.
- 10 deployment rollouts per trained policy.

Rebuttal-strength version:

- 3 dataset seeds per condition.
- 10 deployment rollouts per trained policy.
- Report mean ± std.

If compute allows, use 4 seeds to match the submitted simulation table. If not,
3 seeds is still defensible as an additional ablation.

## Suggested Result Table

The rebuttal table could look like:

| Structure | Candidate | Dispersion Parameter | EDSR (%) |
| --- | --- | --- | ---: |
| Spatial `P` | Fixed | `0 cm` | TBD |
| Spatial `P` | Moderate | `3 cm` | TBD |
| Spatial `P` | Large | `6 cm` | TBD |
| Contact `R` | Fixed | `0 deg` | TBD |
| Contact `R` | Moderate | `15 deg` | TBD |
| Contact `R` | Large | `45 deg` | TBD |
| Temporal `V` | Fixed | `0% jitter` | TBD |
| Temporal `V` | Moderate | `25% jitter` | TBD |
| Temporal `V` | Large | `50% jitter` | TBD |

The figure should preferably show three small line plots:

- EDSR vs spatial radius.
- EDSR vs orientation variation.
- EDSR vs temporal jitter.

This is easier for reviewers to understand than a large multi-factor table.

## Rebuttal Wording

Suggested wording:

```text
We agree that the submitted version did not sufficiently detail how the
deployment-evaluated structure selection is translated into concrete AR guidance
parameters. To address this, we added a parameter ablation in simulation. For
each structure dimension P, R, and V, we constructed task-successful
demonstration datasets with controlled spatial dispersion, closing-orientation
dispersion, and phase-timing dispersion, respectively. The learner, embodiment,
budget, and rollout evaluation were kept fixed. Results show that deployment
performance remains high only within bounded consistency ranges and drops under
large spatial, contact, or temporal variation. The AR corridor, grasp-orientation
tolerance, and speed-bar thresholds used in Appendix A.5 were selected to keep
novice demonstrations within these high-performing ranges.
```

Important language constraint:

Avoid claiming:

```text
We solved for the global z* over P x R x V.
```

Instead claim:

```text
We performed deployment-evaluated finite candidate selection over practical
guidance parameters.
```

This is accurate and defensible.

## What Not to Do for Rebuttal

Avoid these for the short-term CoRL rebuttal:

- Do not run LIBERO as the main patch.
- Do not add ACT or VLA training as the main patch.
- Do not recruit many more participants unless data collection is already ready.
- Do not attempt a full factorial `P x R x V` search.
- Do not claim universal optimal thresholds.

These are valuable for the journal version, but they are too risky for a
rebuttal window.

## Journal-Version Direction

For the journal extension, the broader research direction can be:

```text
From hand-designed P/R/V structures to deployment-discovered teaching structures.
```

Possible extensions:

- Define a larger structure space beyond only `P/R/V`.
- Use simulation benchmarks such as LIBERO to evaluate many tasks.
- Test multiple learners: 3D Diffusion Policy, ACT, and possibly VLA models.
- Add more real-robot tasks with different manipulation bottlenecks.
- Recruit more participants for stronger human-study power.
- Study whether different learners prefer different teaching structures.
- Learn or search for structure dimensions automatically from deployment
  sensitivity, rather than manually defining them.

The journal story can be:

```text
CoRL version: DEMT shows that deployment-selected P/R/V structures can train
novices to provide more learnable demonstrations.

Journal version: DEMT becomes a general methodology for discovering which
human-controllable demonstration structures matter for different learners,
tasks, and embodiments.
```

## Recommended Timeline

### Days 1-2: Finalise Candidate Sets

Decide the exact levels for:

- Spatial approach radius.
- Closing-orientation variation.
- Temporal phase-ratio jitter.

Keep the candidate set small. The priority is a clean rebuttal story, not a
complete search.

### Days 3-5: Implement and Validate Data Generation

For each condition:

- Generate one demo dataset.
- Check that all demonstrations are task-successful.
- Check metadata records the condition parameters.
- Check phase labels and frame counts.
- Confirm point clouds and poses are valid in headless mode.

### Days 6-8: Smoke Experiment

Run:

- 1 seed per condition.
- 10 deployment rollouts per policy.

Goal:

- Verify that trends are visible.
- Increase perturbation magnitudes if the effect is too small.
- Reduce perturbation magnitudes if too many demonstrations fail before policy
  training.

### Days 9-14: Rebuttal-Strength Ablation

Run:

- 3 seeds per condition.
- 10 deployment rollouts per trained policy.

Produce:

- EDSR table.
- Three line plots.
- Optional secondary diagnostics: MPCV, MCOD, MPSV, validation loss.

### Days 15-18: Write Rebuttal and Appendix Patch

Write:

- A concise rebuttal paragraph.
- A small table or figure.
- A short appendix addition explaining candidate construction.

The text should frame the experiment as clarifying the DEMT-to-guidance
translation, not as a new main contribution.

## Personal Recommendation

If time is limited, start with the spatial ablation because the existing code is
closest to it. Then do the orientation ablation because it is likely to be the
most persuasive. Do the temporal ablation last, and keep it coarse.

The strongest minimal patch is:

```text
P/R/V each with three levels, fixed learner, fixed budget, fixed deployment
protocol, EDSR reported across three seeds.
```

That is enough to answer the immediate reviewer concern:

```text
The AR guidance parameters were not arbitrary; they were chosen to keep
demonstrations within deployment-validated consistency ranges.
```
