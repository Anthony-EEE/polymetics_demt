# Handoff: Multiagent Research History

_Last updated: 2026-07-03 · Branch: hpc-headless-data-collection @ 73d56df_

## Goal
Record the DEMT rebuttal / Week 2 research process as a reconstructed three-agent dialogue. This is not a verbatim transcript; it is a structured history distilled from the conversation and the Week 1 / Week 2 handoff files so a fresh agent can understand how the experimental and writing logic evolved.

## Role Definitions
- **Agent1: Experiment Agent / Codex.** The implementation and analysis worker. Reads handoffs and paper/PPT context, edits scripts/docs, runs Slurm jobs, verifies artifacts, and converts research discussion into executable plans or handoff records.
- **Agent2: User / Researcher.** The project owner and paper author. Provides scientific intent, corrects geometry and data assumptions, reports supervisor feedback, chooses priorities, and defines what is acceptable for rebuttal versus ICRA/journal.
- **Agent3: Supervisor / Reviewer Pressure.** A reconstructed role representing the user's supervisor and likely reviewer questions. This role asks why AR parameters are justified, challenges overclaims, points out design flaws, and pushes the work toward defensible framing.

## Current State Snapshot
- Week 1 archived files:
  - `handoffs/week1_main-experiments.md`
  - `handoffs/week1_research_thinking.md`
- Week 2 active files:
  - `handoffs/week2_experiment.md`
  - `handoffs/week2_research_thinking.md`
- Current new history file:
  - `handoffs/multiagent_history.md`
- Key Week 1 result summary:
  ```text
  Spatial corrected rollout: P00/P01/P10/P11 = 8/10, 6/10, 7/10, 6/10
  Spatial corrected annulus stress: P00/P01/P10/P11 = 2/10, 1/10, 2/10, 1/10
  Orientation rollout: R00/R15/R30 = 7/10, 6/10, 4/10
  Temporal latest rollout: T00/T20/Twide = 10/10, 8/10, 7/10
  ```
- Key Week 2 human-data diagnostic summary:
  ```text
  P1 pre skill1 corridor_crossing x-z:
    p90 = 15.83 cm, p95 = 18.28 cm, max = 23.71 cm
    within 10 cm = 65.0%, within 25 cm = 100.0%

  P2 pre skill2 corridor_crossing x-z:
    p90 = 23.63 cm, p95 = 26.70 cm, max = 32.64 cm
    within 10 cm = 32.5%, within 25 cm = 90.8%
  ```

## Dialogue History

### Act 1: Opening The Rebuttal Work

**Agent2:**
Read `handoffs/` and the PPT. We need to start a new week of experiments, thinking, and brainstorming.

**Agent1:**
I read `handoffs/week1_main-experiments.md`, `handoffs/week1_research_thinking.md`, and the generated PPT `outputs/demt_rebuttal_mvp_report.pptx`. I found the core state:
- Spatial corrected result exists but is mixed.
- Orientation and temporal are cleaner.
- The current rebuttal should avoid claiming exact parameter optimality.
- The PPT already frames the MVPs as structure-level sensitivity evidence.

**Agent3:**
The reviewer question is not "can the robot complete the task?" It is "why these AR guidance parameters?" If the paper says `25cm / 15deg / [0.5, 2.0] x v_ref`, the burden is to explain where those numbers came from.

**Agent1:**
The safe rebuttal logic is:
```text
The submitted paper establishes that spatial, contact-orientation, and temporal
structures affect robot learning. The new MVPs do not prove exact numeric
optimality, but they show that relaxing these structures changes learner fit
and/or rollout success under a fixed learner and N=30 budget.
```

**Agent2:**
Good. But I also need a longer-term research direction. If CoRL rejects the paper, we need to have enough material to push toward ICRA or a journal.

### Act 2: Week 1 Spatial Correction And The Geometry Problem

**Agent2:**
The original spatial ablation is not right. The true AR guidance corridor-start center is `[0.3, 0.0, 0.5]`. Also there should be no separate `random_start`: the demo should start directly at sampled `corridor_start`.

**Agent1:**
I updated the spatial generator and checker logic accordingly:
- `examples/main_abla_1.py` uses `DEFAULT_CORRIDOR_START_CENTER = (0.30, 0.0, 0.50)`.
- `random_start` is removed from Ablation-1 collection/evaluation.
- First frame is saved as phase `corridor_start`.
- Checker rejects any `random_start` metadata or phase.
- Evaluation samples from the matching `corridor_start` distribution.

**Agent3:**
If the previous dataset used the wrong center and extra movement phase, it cannot be used to support a paper claim.

**Agent1:**
Correct. The old `/dataset/abla1_full` spatial artifacts are invalid for the intended AR-guidance ablation. Any HDF5, training loss, rollout, stress rollout, or PPT language using the old wrong-center result must not be cited.

**Agent2:**
Rerun it correctly.

**Agent1:**
The corrected pipeline completed under:
```text
/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full_arcenter
```
For P00/P01/P10/P11, raw collection, checker, HDF5 conversion, train/valid split, scratch training, rollout evaluation, videos, and PPT regeneration all completed.

**Agent1:**
Corrected spatial rollout:
```text
P00: 8/10
P01: 6/10
P10: 7/10
P11: 6/10
```
Corrected validation losses:
```text
P00 best valid = 0.036339
P01 best valid = 0.028998
P10 best valid = 0.099341
P11 best valid = 0.029316
```

**Agent3:**
This is not a clean monotonic deployment story. Do not claim wide corridor causes rollout collapse.

**Agent1:**
Agreed. The defensible statement is:
```text
Corrected spatial evidence is structure-level and learner-fit evidence. It
confirms geometry and flags P10 as harder to fit, but rollout is mixed.
```

### Act 3: Spatial Stress Test And Its Boundary

**Agent2:**
What about robustness? A tightly clustered demonstration manifold might help in-distribution learning but be brittle under large perturbations.

**Agent1:**
I added an annulus corridor-entry stress evaluator:
- Uses corrected `abla1_full_arcenter` models.
- Samples starts with `0.25 <= d <= 0.50m`.
- Same sampled starts reused across conditions.

**Agent1:**
Corrected stress rollout:
```text
P00: 2/10
P01: 1/10
P10: 2/10
P11: 1/10
```
Distance stats:
```text
d_min/mean/max = 0.2778 / 0.3620 / 0.4917 m
all_ge_0.25 = True
all_le_0.50 = True
```

**Agent3:**
This tells us all policies are weak under severe OOD entry perturbation. It does not prove wider training improves robustness.

**Agent1:**
Right. The stress test is backup diagnostics / robustness caution, not main rebuttal evidence.

### Act 4: Orientation MVP

**Agent2:**
Do not use the old P00 spatial baseline for orientation; it only gets around 40-60% rollout. Use a stronger baseline: `corridor_start_radius=0.05`, `pre_grasp_radius=0.0`. Each demo should sample one gripper orientation and use it for the whole trajectory.

**Agent1:**
I implemented orientation MVP:
```text
R00: 0 deg full-trajectory orientation
R15: sampled full-trajectory orientation within +/-15 deg
R30: sampled full-trajectory orientation within +/-30 deg
```
It collected, checked, converted, split, trained, and evaluated.

**Agent1:**
Training validation losses:
```text
R00: best valid 0.030678
R15: best valid 0.056497
R30: best valid 0.090806
```
Rollout:
```text
R00: 7/10
R15: 6/10
R30: 4/10
```

**Agent3:**
This is the strongest Week 1 story. It is plausible because humans cannot realistically hold exact `0 deg`; `15 deg` can be framed as a human-feasible tolerance while `30 deg` degrades more.

**Agent2:**
Yes. This experiment is reasonable and explainable.

### Act 5: Temporal MVP And Its Limitation

**Agent2:**
For temporal, do a fuller threshold sweep rather than a minimal two-condition ablation:
```text
T00: fixed phase timing
T20: +/-20%
Twide: broad variation inspired by [0.5, 2.0] x v_ref
```

**Agent1:**
I implemented the temporal MVP:
- Fixed spatial path and orientation to isolate timing.
- `T00`: all phase-duration multipliers `1.0`.
- `T20`: per-demo multipliers sampled from `[0.8, 1.2]`.
- `Twide`: per-demo multipliers sampled from `[0.5, 2.0]`.

**Agent1:**
Latest-checkpoint rollout:
```text
T00:   model_epoch_280.pth, 10/10
T20:   model_epoch_160.pth, 8/10
Twide: model_epoch_220.pth, 7/10
```

**Agent3:**
This supports temporal consistency. But the submitted paper's speed guidance used each person's first trajectory to define `v_ref`; that is weaker than a fixed global number. Also `T00/T20/Twide` is not a symmetric parameter ladder.

**Agent2:**
Exactly. For Week 2, temporal should become `+/-10%`, `+/-20%`, `+/-30%`, `+/-40%`, not a mix of `+/-20%` and `[0.5, 2.0]`.

**Agent1:**
Week 1 temporal can be used as current evidence, but Week 2 should redesign it as a symmetric jitter ladder.

### Act 6: PPT And Rebuttal Framing

**Agent1:**
I generated `outputs/demt_rebuttal_mvp_report.pptx`. It has 13 slides:
- Defines the reviewer question.
- Separates structure-level evidence from exact numeric optimality.
- Reports corrected spatial, orientation, and temporal results.
- Suggests rebuttal wording.

**Agent3:**
The exact AR values should not be claimed as globally optimal. The reviewer may ask "why these values?" not "did you solve global `z*`?"

**Agent1:**
The recommended rebuttal wording:
```text
The exact AR values are task-specific implementation choices for this robot,
learner, and manipulation setting. Our claim is not that these numbers are
globally optimal. Rather, they implement the spatial, contact-orientation, and
temporal structures selected by DEMT. To address the concern, we added
controlled sensitivity ablations showing that relaxing these structures
degrades learner fit and/or rollout success under the same fixed learner and
N=30 budget.
```

**Agent2:**
This is the right boundary. If reviewers ask, we use it. If they do not ask, the same work can become ICRA/journal material.

### Act 7: Supervisor Meeting And Week 2 Reframing

**Agent2:**
I met with my supervisor. We discussed the P/R/V directions:

Spatial:
- More clustered / dense demonstrations clearly help with small `N=30`.
- Current conditions are not enough.
- Instead of independent corridor/pre-grasp factors, we can constrain their ratio: e.g. `25cm:5cm`, `30cm:6cm`.
- A new user study could test user-friendliness and training efficiency, but it is expensive and confounded because users learn over repeated radii.
- I think we can use stored user data: post_train P6/P7/P8 from the paper. Use mean +/- std or distribution to generate data and check which radius matches real human behavior.

Orientation:
- This experiment is reasonable because humans cannot hold exact `0 deg` in reality.

Temporal:
- The paper's current `v_ref` is not ideal; it used each person's first trajectory.
- It would have been better to set a fixed number like the spatial/degree thresholds.
- But since the paper is written that way, use it carefully.
- Future temporal sweep should be consistent: `+/-10%`, `+/-20%`, `+/-30%`, etc.
- My idea: analyze user data and label each phase's frame count, using Pre_train P1/P2 as baseline, then add noise.

Overall:
- Rebuttal should admit we did not originally do full parameter experiments.
- If asked, frame the new work as the missing finite sensitivity analysis.
- If not asked, keep it for journal / next conference.
- If CoRL rejects in early September, use these experiments to strengthen an ICRA submission by mid-September.

**Agent3:**
This is a better research program. It acknowledges limitations without weakening the contribution. It also turns rebuttal work into a future-paper pipeline.

**Agent1:**
I converted this into Week 2 handoffs:
- `handoffs/week2_experiment.md`
- `handoffs/week2_research_thinking.md`

I renamed Week 1 files:
- `handoffs/week1_main-experiments.md`
- `handoffs/week1_research_thinking.md`

Then pushed the handoff and code updates:
```text
108cc88 organize week 2 handoffs
73d56df add rebuttal experiment pipelines
```

### Act 8: Real Human Data Policy

**Agent2:**
The user data are in `/scratch/users/k23114984`. Do not doubt the symlink or actual directory. Treat all of these as real data. They are all human data. Because there were not enough participants, we shuffled/recombined them. This is not cheating; it was due to time and financial constraints.

**Agent1:**
Understood. I will treat `/scratch/users/k23114984/pybullet_data` as real human demonstrations. Pooled, shuffled, symlinked, or re-split datasets are still real-user data. Safe wording:
```text
pooled and re-split real-user demonstrations
```
Do not call them synthetic or fake.

**Agent1:**
I located the data structure:
```text
/scratch/users/k23114984/pybullet_data/target_pooled/pooled_symlinks/target_pre_skill1   -> P1 target prism pre
/scratch/users/k23114984/pybullet_data/target_pooled/pooled_symlinks/target_pre_skill2   -> P2 target cube pre
/scratch/users/k23114984/pybullet_data/target_pooled/pooled_symlinks/target_post_skill1  -> P6 target prism post
/scratch/users/k23114984/pybullet_data/target_pooled/pooled_symlinks/target_post_skill2  -> P7 target cube post
/scratch/users/k23114984/pybullet_data/phase8/phase8_target/2026-05-03-12-09-56         -> P8 target ordered task
/scratch/users/k23114984/pybullet_data/phase8/phase8_control/2026-05-02-16-16-44        -> P8 control ordered task
```

**Agent1:**
Quick counts:
```text
P1 target_pre_skill1:  120 demos
P2 target_pre_skill2:  120 demos
P6 target_post_skill1: 120 demos
P7 target_post_skill2: 120 demos
P8 target:              30 demos
P8 control:             30 demos
```

**Agent3:**
This enables a stronger argument: the guidance radius can be calibrated against natural human behavior, not just simulation.

### Act 9: Week 2 Human-Data Diagnostics

**Agent1:**
The human demo directories mainly contain:
```text
frame_*/arm_joints.txt
frame_*/hand_joints.txt
frame_*/point_cloud.ply
```
Pooled HDF5 contains:
```text
actions
obs/robot0_arm_joints
obs/robot0_hand_joints
obs/pointcloud
```
There is no direct `ee_pose.txt` or phase label, so we need FK and keypoint detection.

**Agent2:**
Use the data correctly. It is left-handed; mirror y.

**Agent1:**
I implemented a read-only diagnostic pipeline:
- `scripts/analyze_week2_human_data.py`
- `scripts/run_week2_human_diagnostics.sh`

It reconstructs EE pose from `arm_joints.txt` using PyBullet Panda FK and mirrors `y = -y` by default. It runs on `interruptible_cpu`.

**Agent1:**
Successful Slurm job:
```text
35366860 on erc-hpc-comp015
```
Output root:
```text
outputs/week2_human_diagnostics_keypoints_quick
```

**Agent1:**
Correct keypoint definitions:
- `corridor_crossing`: each demo's EE point closest to the `y=0` plane. Analyze spread in x-z.
- `pregrasp_keypoint`: first sustained steep z drop after raw frame 70. Analyze spread in x-y.

**Agent2:**
Do not use `[0.3, 0.0, 0.5]` as a measured corridor center. That was a guidance point, not empirical data. Do not use `[0.5, 0.5, 0.22]` as the pre-grasp metric either.

**Agent1:**
Corrected human diagnostic results:
```text
P1 pre skill1 corridor_crossing:
  center = (43.19, 17.04) cm in x-z
  std_x = 8.32 cm, std_z = 6.19 cm
  radius mean = 8.98 cm
  radius p90 = 15.83 cm
  radius p95 = 18.28 cm
  max = 23.71 cm
  within 10cm = 65.0%
  within 25cm = 100.0%

P2 pre skill2 corridor_crossing:
  center = (44.00, 20.45) cm in x-z
  std_x = 12.74 cm, std_z = 8.83 cm
  radius mean = 13.88 cm
  radius p90 = 23.63 cm
  radius p95 = 26.70 cm
  max = 32.64 cm
  within 10cm = 32.5%
  within 25cm = 90.8%
```

**Agent3:**
This answers "why 25 cm, why not 10 cm" better than the Week 1 spatial simulation:
```text
10 cm would exclude many natural pre-training corridor crossings, especially
for P2. 25 cm covers most natural approach behavior.
```

**Agent1:**
Important framing:
```text
25 cm is not the desired final demonstration variance. It is a permissive
guidance/capture envelope around natural human approach variability. Human
movement priors and guidance regularize behavior into a tighter learnable
distribution.
```

**Agent2:**
This resolves the apparent contradiction that uniform 25 cm simulation may be hard to learn, while 25 cm AR guidance can still be reasonable. Humans do not uniformly fill the 25 cm disk.

### Act 10: Current Writing Logic

**Agent3:**
The paper/rebuttal must avoid the trap:
```text
25 cm is optimal because simulation says so.
```
The actual logic should be:
```text
25 cm is a human-facing capture envelope. It covers natural unguided approach
variability. The learner still benefits when actual demonstrated trajectories
are clustered by human priors and guidance.
```

**Agent1:**
The revised spatial argument is:
1. Week 1 uniform spatial sampling showed learner sensitivity but not a clean optimality result.
2. Week 2 human data shows 10 cm is too tight for natural human approach behavior.
3. 25 cm is plausible as an outer AR guidance envelope because it covers most P1/P2 natural corridor crossings.
4. The next simulation should use human-prior sampling or percentile truncation, not uniform disk sampling alone.

**Agent2:**
Future candidate simulations:
```text
U10_P03   uniform 10 cm corridor, tight pre-grasp
U25_P03   uniform 25 cm corridor, tight pre-grasp
Hpre_P03  empirical P1/P2 pre crossing prior, tight pre-grasp
H90_P03   truncated human-prior crossing radius at natural p90, tight pre-grasp
```
Also consider percentile levels `90/80/70/60/50`.

**Agent3:**
This becomes a stronger ICRA/journal story:
```text
DEMT does not just hand-pick thresholds. It links robot-learnability,
human-achievable behavior, and AR guidance envelopes.
```

## Work Logic By Role

### Agent1 Work Logic
1. Read existing handoffs, paper/PDF facts, and PPT before acting.
2. Translate Agent2's conceptual corrections into concrete code or analysis tasks.
3. Run minimal smoke checks before full Slurm jobs.
4. Verify every output: JSON summaries, videos, plots, HDF5 split masks, logs, and job states.
5. Keep failed or invalid artifacts documented so future agents do not cite them.
6. Separate implementation facts from research framing:
   - Experiment details in `week*_experiment` / `week1_main-experiments`.
   - Scientific interpretation in `week*_research_thinking`.
7. Avoid overclaiming from validation loss alone.
8. Treat user-provided data policy as authoritative: `/scratch/users/k23114984/pybullet_data` contains real human demonstrations even if pooled/re-split.

### Agent2 Work Logic
1. Drives the scientific direction and knows the paper's true intent.
2. Corrects implementation assumptions when they deviate from AR/user-study reality.
3. Keeps the work connected to CoRL rebuttal, ICRA contingency, and journal extension.
4. Pushes for explanations that are defensible to a supervisor/reviewer:
   - Why 25 cm?
   - Why 15 deg?
   - Why temporal thresholds?
5. Distinguishes practical constraints from methodological weakness:
   - Pooled/re-split real-user data is acceptable given time/finance constraints.
   - New user studies are expensive and confounded.
6. Rejects misleading metrics:
   - Do not use guidance center as empirical center.
   - Do not analyze pre-grasp in the wrong plane.
   - Do not pretend uniform simulation radius equals real human AR behavior.

### Agent3 Work Logic
1. Challenges unsupported parameter claims.
2. Pushes the project away from "global optimality" language.
3. Forces separation of:
   - task-successful demonstration,
   - robot-learnable demonstration,
   - human-achievable guidance,
   - exact numeric threshold optimality.
4. Identifies limitations:
   - small participant count,
   - fixed learner,
   - temporal `v_ref` defined per person,
   - lack of full parameter sweep in submitted version.
5. Encourages conservative, credible writing:
   ```text
   finite candidate sensitivity analysis
   task-specific guidance values
   human-achievable consistency range
   deployment-evaluated structure selection
   ```

## Key Decisions
- Old wrong-center spatial results under `dataset/abla1_full` are invalid for the intended AR-center ablation.
- Corrected spatial result is valid but mixed; use it conservatively.
- Corrected spatial stress result is OOD robustness caution, not main evidence.
- Orientation MVP is the cleanest Week 1 evidence.
- Temporal MVP supports consistency but needs a future symmetric jitter ladder.
- New user study is not the short-term solution.
- Real human data under `/scratch/users/k23114984/pybullet_data` is authoritative.
- Pooled/re-split human data must be framed as real-user data organization, not synthetic generation.
- `25 cm` should be framed as a permissive human-facing AR capture envelope, not desired final variance or proven optimal radius.
- Future spatial simulation should compare uniform sampling against human-prior / percentile-truncated sampling.

## Things Not To Say
- Do not say "the original geometric variant was wrong."
- Do not say "25 cm is globally optimal."
- Do not say "Appendix says 25 cm is good but simulation says 25 cm is bad."
- Do not say pooled/re-split user data is fake or cheating.
- Do not claim Week 1 spatial rollout proves a monotonic degradation.
- Do not claim annulus stress proves tighter guidance improves OOD robustness.
- Do not describe `[0.5, 2.0] x v_ref` as fixed metric speed.
- Do not use `[0.3, 0.0, 0.5]` as measured human corridor center.
- Do not use `[0.5, 0.5, 0.22]` as measured human pre-grasp center.

## Useful Rebuttal Paragraph
```text
The submitted version did not claim global optimality of these numeric
thresholds. They are task-specific AR guidance values implementing
DEMT-selected spatial, contact-orientation, and temporal structures. We added
finite candidate sensitivity analyses and real-user diagnostics to show that
these structures correspond to learnable and human-achievable consistency
ranges. In particular, pre-training user data show that a 10 cm spatial
envelope would exclude many natural corridor-crossing behaviors, whereas the
25 cm envelope covers most natural approach variability. This 25 cm value is
therefore best interpreted as a permissive human-facing guidance envelope, not
as the desired final demonstration variance or a globally optimal radius.
```

## Useful Future-Paper Paragraph
```text
Beyond the rebuttal, the project can be reframed as a method for connecting
deployment-evaluated robot learning sensitivity with human-achievable teaching
behavior. Week 1 established that spatial, contact-orientation, and temporal
structures affect learner fit and rollout success. Week 2 begins to connect
those structures to real user behavior by measuring the natural distribution
of unguided and post-training demonstrations. This opens a path toward an ICRA
or journal version where AR guidance parameters are not only task-specific
implementation choices, but are calibrated against both robot learnability and
human movement distributions.
```

## Key Files
- `handoffs/week1_main-experiments.md`
- `handoffs/week1_research_thinking.md`
- `handoffs/week2_experiment.md`
- `handoffs/week2_research_thinking.md`
- `scripts/analyze_week2_human_data.py`
- `scripts/run_week2_human_diagnostics.sh`
- `outputs/week2_human_diagnostics_keypoints_quick/keypoint_spread_summary.csv`
- `outputs/week2_human_diagnostics_keypoints_quick/pre_keypoint_natural_spread_summary.csv`
- `DEMT__Deployment_Evaluated_Machine_Teaching_Enhances_Learning_from_Human_Demonstrations.pdf`

## Open Questions
- Should the next simulation use P1 only, P2 only, or pooled P1/P2 human-prior sampling?
- Should the spatial prior be empirical resampling, elliptical Gaussian, radial percentile truncation, or all three?
- Should Week 2 update `week2_research_thinking.md` with the 2026-07-02 human diagnostic interpretation, since it is currently older than `week2_experiment.md`?
- Should orientation human-data diagnostics be run next, or should spatial be stabilized first for rebuttal?
- Should temporal be redesigned around human phase frame statistics before any new rollout jobs?

## Changelog
- 2026-07-03: Created reconstructed three-agent dialogue history from conversation plus Week 1 and Week 2 handoff records.
