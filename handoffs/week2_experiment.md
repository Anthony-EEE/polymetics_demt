# Handoff: Week 2 Experiments

_Last updated: 2026-07-03 · Branch: hpc-headless-data-collection @ 73d56df_

## Goal
Plan and execute Week 2 DEMT follow-up experiments after the supervisor meeting. The current focus is to build the strongest defensible explanation for the concrete AR guidance parameters under a strict Agent3 who asks for global optimality, while acknowledging that exhaustive global search is practically infeasible. Week 1 execution details are archived in `handoffs/week1_main-experiments.md`.

## Current Progress
- Week 1 handoff files were renamed:
  - `handoffs/week1_main-experiments.md`
  - `handoffs/week1_research_thinking.md`
- Week 2 should treat all data under `/scratch/users/k23114984/pybullet_data` as real human demonstrations. Symlinks, pooling, shuffling, and re-splitting are part of the real-user data organization and must not be framed as fake, synthetic, or cheating.
- Main human-data roots identified:
  ```text
  /scratch/users/k23114984/pybullet_data/target_pooled/pooled_symlinks/target_pre_skill1   -> P1 target prism pre
  /scratch/users/k23114984/pybullet_data/target_pooled/pooled_symlinks/target_pre_skill2   -> P2 target cube pre
  /scratch/users/k23114984/pybullet_data/target_pooled/pooled_symlinks/target_post_skill1  -> P6 target prism post
  /scratch/users/k23114984/pybullet_data/target_pooled/pooled_symlinks/target_post_skill2  -> P7 target cube post
  /scratch/users/k23114984/pybullet_data/phase8/phase8_target/2026-05-03-12-09-56         -> P8 target ordered task
  /scratch/users/k23114984/pybullet_data/phase8/phase8_control/2026-05-02-16-16-44        -> P8 control ordered task
  ```
- Manifest files confirm pooled/re-split real-user structure:
  - `/scratch/users/k23114984/pybullet_data/target_pooled/manifests/target_pooled_manifest.csv`
  - `/scratch/users/k23114984/pybullet_data/control_group/manifests/split_manifest_pre42_post123.csv`
  - `/scratch/users/k23114984/pybullet_data/arcap_group/manifests/split_manifest_arcap_seed42_pre20_post10.csv`
  - `/scratch/users/k23114984/pybullet_data/phase8/phase8_arcap/phase8_arcap_split_manifest.csv`
- Confirmed counts from quick read-only inspection:
  ```text
  P1 target_pre_skill1:  120 demos, frames min/mean/median/max = 109 / 170.7 / 168.0 / 290
  P2 target_pre_skill2:  120 demos, frames min/mean/median/max =  13 / 185.9 / 183.0 / 409
  P6 target_post_skill1: 120 demos, frames min/mean/median/max = 223 / 315.6 / 310.5 / 410
  P7 target_post_skill2: 120 demos, frames min/mean/median/max = 243 / 319.7 / 312.0 / 450
  P8 target:              30 demos, frames min/mean/median/max = 475 / 535.9 / 533.0 / 617
  P8 control:             30 demos, frames min/mean/median/max = 260 / 435.2 / 337.5 / 780
  ```
- Raw human demo directories mainly contain per-frame `arm_joints.txt`, `hand_joints.txt`, and `point_cloud.ply`; pooled HDF5 files contain `actions`, `obs/robot0_arm_joints`, `obs/robot0_hand_joints`, and `obs/pointcloud`. They do not appear to contain direct `ee_pose.txt` or phase labels.
- Implemented a read-only human-data diagnostic script:
  - `scripts/analyze_week2_human_data.py`
  - It reconstructs EE pose from `arm_joints.txt` using PyBullet Panda FK (`franka_panda/panda.urdf`, link 11).
  - Important coordinate correction from the user: collected data are left-handed, so FK output must be mirrored with `y = -y`. The script defaults to `mirror_y=True`; use `--no-mirror-y` only for debugging.
- Implemented an HPC wrapper:
  - `scripts/run_week2_human_diagnostics.sh`
  - Default partition is now `interruptible_cpu`.
  - Default walltime is now `01:00:00`; user preference for non-training jobs is half an hour to one hour.
  - Default output root is `outputs/week2_human_diagnostics_keypoints_quick`.
- Slurm history:
  - First `cpu` job `35366832` was canceled after user corrected partition choice.
  - `interruptible_cpu` job `35366860` ran on `erc-hpc-comp015` and completed successfully.
  - Logs:
    - `outputs/week2_human_diagnostics_keypoints_quick/logs/diag-35366860.out`
    - `outputs/week2_human_diagnostics_keypoints_quick/logs/diag-35366860.err`
  - Stdout reports all groups completed and outputs were written. Stderr only shows PyBullet build time and Matplotlib font-cache messages.
- Generated outputs:
  - `outputs/week2_human_diagnostics_keypoints_quick/demo_metrics.csv`
  - `outputs/week2_human_diagnostics_keypoints_quick/group_summary_long.csv`
  - `outputs/week2_human_diagnostics_keypoints_quick/human_diagnostics_summary.json`
  - `outputs/week2_human_diagnostics_keypoints_quick/keypoint_spread_summary.csv`
  - `outputs/week2_human_diagnostics_keypoints_quick/pre_keypoint_natural_spread_summary.csv`
  - Correct keypoint plots:
    - `corridor_crossing_xz_scatter_by_group.png`
    - `corridor_crossing_xz_center_radius_by_group.png`
    - `pregrasp_keypoint_xy_scatter_by_group.png`
    - `pregrasp_keypoint_xy_center_radius_by_group.png`
- Re-ran the read-only diagnostics without plots after the script gained
  orientation and temporal CSV exports:
  ```text
  python scripts/analyze_week2_human_data.py \
    --frame-stride 10 \
    --output-dir outputs/week2_human_diagnostics_keypoints_v2 \
    --no-plots
  ```
  New V2 outputs:
  ```text
  outputs/week2_human_diagnostics_keypoints_v2/demo_metrics.csv
  outputs/week2_human_diagnostics_keypoints_v2/group_summary_long.csv
  outputs/week2_human_diagnostics_keypoints_v2/keypoint_spread_summary.csv
  outputs/week2_human_diagnostics_keypoints_v2/orientation_event_summary.csv
  outputs/week2_human_diagnostics_keypoints_v2/temporal_human_summary.csv
  outputs/week2_human_diagnostics_keypoints_v2/human_diagnostics_summary.json
  ```
  Verification:
  ```text
  errors = 0
  frame_stride = 10
  mirror_y_applied = true
  n = 120 each for P1/P2/P6/P7, n = 30 each for P8 target/control
  ```
- Correct keypoint definitions:
  - `corridor_crossing`: CSV key name retained for compatibility; it means each demo's EE trajectory point closest to the `y=0` plane. Reviewer-facing text should say "nearest-to-corridor-plane early approach keypoint" unless the term is defined explicitly. Spread/radius must be computed in the x-z plane.
  - `pregrasp_keypoint`: first sustained steep z drop after raw frame 70. Spread/radius must be computed in the x-y plane.
  - Do not use the old reference point `[0.3, 0.0, 0.5]` as a corridor center. That was guidance, not a measured center.
  - Do not use `[0.5, 0.5, 0.22]` as a pre-grasp reference. That was an arbitrary simulation point, not the human-data event definition.
  - Ignore old/wrong pregrasp x-z plots if they exist; pre-grasp is an x-y plane analysis.
- Current git status has two untracked scripts:
  ```text
  ?? scripts/analyze_week2_human_data.py
  ?? scripts/run_week2_human_diagnostics.sh
  ```

## What Worked
- `/scratch/users/k23114984/pybullet_data` has a clean enough organization for target/control/ARCap/P8 analysis.
- Manifest files are useful for explaining and auditing the pooled/re-split real-user data construction.
- Target pooled roots provide a direct P1/P2/P6/P7 mapping with 120 demos per phase/skill.
- The FK-based diagnostic pipeline now runs on HPC and produces group-level CSV/JSON/plots without modifying source data.
- P1/P2 pre-train keypoint stats are useful diagnostics, but they are not a
  valid standalone justification for the 25 cm training parameter. If users are
  already mostly inside 25 cm before training, this cannot explain the low P1/P2
  deployment success.
- Corrected P1/P2 pre-train `corridor_crossing` results in x-z:
  ```text
  P1 pre skill1:
    center = (43.19, 17.04) cm
    std_x = 8.32 cm, std_z = 6.19 cm
    radius mean = 8.98 cm
    radius p90 = 15.83 cm, p95 = 18.28 cm, max = 23.71 cm
    within 10cm = 65.0%, within 25cm = 100.0%

  P2 pre skill2:
    center = (44.00, 20.45) cm
    std_x = 12.74 cm, std_z = 8.83 cm
    radius mean = 13.88 cm
    radius p90 = 23.63 cm, p95 = 26.70 cm, max = 32.64 cm
    within 10cm = 32.5%, within 25cm = 90.8%
  ```
- V2 post-training spatial tightening:
  ```text
  P6 post skill1 nearest-to-corridor-plane x-z:
    radius p50 = 4.03 cm, p90 = 7.22 cm, p95 = 9.49 cm, max = 16.80 cm

  P7 post skill2 nearest-to-corridor-plane x-z:
    radius p50 = 3.53 cm, p90 = 6.26 cm, p95 = 6.67 cm, max = 7.54 cm
  ```
  Revised interpretation: these local keypoints show post-training tightening,
  but the main spatial evidence should be the paper's full-trajectory MPCV and
  EDSR improvement. Do not use 25 cm pre-coverage as proof that 25 cm training
  is necessary.
- Corrected P1/P2 pre-train `pregrasp_keypoint` results in x-y:
  ```text
  P1 pre skill1:
    center = (47.85, 47.92) cm
    std_x = 1.29 cm, std_y = 2.49 cm
    radius p95 = 5.37 cm
    within 10cm = 100.0%

  P2 pre skill2:
    center = (48.19, 47.24) cm
    std_x = 1.82 cm, std_y = 4.81 cm
    radius p95 = 6.99 cm
    within 10cm = 96.7%
  ```
- Interpretation: pre-grasp consistency is mostly a sanity check because the target location is fixed. The real useful variability is the early approach/corridor crossing behavior.
- V2 orientation diagnostics:
  ```text
  P6 closest_grasp p95 to group mean = 13.14 deg, coverage_15deg = 100.0%
  P6 first_close   p95 to group mean = 13.47 deg, coverage_15deg = 100.0%
  P7 closest_grasp p95 to group mean = 14.33 deg, coverage_15deg = 99.2%
  P7 first_close   p95 to group mean = 13.59 deg, coverage_15deg = 99.2%
  ```
  Interpretation: this supports 15 deg as a human-compatible tolerance when
  paired with the Week 1 R00/R15/R30 rollout result. It is dispersion-to-group-
  mean evidence, not exact target-frame alignment.
- V2 temporal diagnostics:
  ```text
  duration-ratio coverage in [0.5, 2.0] = 86.7% to 100.0% across groups
  mean-speed-ratio coverage in [0.5, 2.0] = 93.3% to 100.0% across groups
  ```
  Interpretation: this supports human compatibility of a broad relative speed
  window, but it is measured against group median and not exact per-user `v_ref`.
- Added and then strictly revised rebuttal workflow artifacts:
  ```text
  rebuttal_workflow/claim_ledger.md
  rebuttal_workflow/experiment_queue.md
  rebuttal_workflow/rebuttal_fragments/parameter_reasonableness_claim.md
  rebuttal_workflow/agent1_results/E00_human_percentile_bound_audit.md
  rebuttal_workflow/agent1_results/E01_human_spatial_stats_v2.md
  rebuttal_workflow/agent1_results/E03_human_orientation_diagnostics_v2.md
  rebuttal_workflow/agent1_results/E04_human_temporal_diagnostics_v2.md
  rebuttal_workflow/agent3_reviews/R02_full_rebuttal_review.md
  rebuttal_workflow/agent3_reviews/R03_strict_parameter_review.md
  rebuttal_workflow/agent3_reviews/R04_global_optimal_pressure_review.md
  ```
  Current Agent3 verdict is R04: Agent3 still demands a global-optimality-style
  explanation, but can accept a bounded / constrained finite-candidate argument
  if Agent1/Agent2 clearly separate it from literal global optimality.
- 2026-07-03 three-agent bounded-optimality continuation completed. The
  converged experiment queue is now `rebuttal_workflow/experiment_queue.md`.
  E00 generated the read-only compatibility table:
  ```text
  outputs/rebuttal_workflow/human_percentile_bound_audit.csv
  ```
  The highest-value new experiment, if a stronger spatial claim is required, is
  E05 fixed-ratio spatial funnel sweep. Human-derived mean/std or percentile
  sampling is future-paper work unless paired with learner training/evaluation.

## What Didn't Work
- Do not use the old Week 1 spatial 2x2 result as the main Week 2 spatial story. It is useful history, but the supervisor meeting shifted the design toward coupled corridor/pre-grasp radius ratios.
- Do not frame a new user study as the short-term solution. Sequential exposure to different radii introduces learning/order effects, and recruitment cost/time is high.
- Do not frame pooled/re-split real-user data as synthetic. The user clarified that all demonstrations are real human data; recombination was a practical response to limited time and budget.
- Do not assume direct EE pose or phase labels are present in the human raw demo directories. Current visible files are joints, gripper state, and point clouds.
- Do not say the 25 cm value is directly proven by post-training learning performance. That is the reviewer trap: if uniform 25 cm simulation learns poorly, claiming "25 cm is optimal because humans prefer it" is contradictory.
- Do not interpret the guidance radius as the desired final demonstration variance. It should be framed as a permissive capture/guidance envelope around natural human approach variability.
- Do not use the old "first-frame EE to AR corridor center `[0.3, 0.0, 0.5]`" metric; the user rejected it because `[0.3, 0.0, 0.5]` is a guidance point, not an empirical corridor center.
- Do not use the old "minimum distance to `[0.5, 0.5, 0.22]`" pre-grasp metric; the user rejected it because pre-grasp should be detected from the steep z drop after frame 70.
- Do not analyze pre-grasp in x-z. The corrected pre-grasp spread plane is x-y.
- Do not use orientation human diagnostics as exact AR target-frame alignment;
  they measure dispersion to group mean.
- Do not use temporal human diagnostics as exact validation of per-user `v_ref`;
  they are group-median ratio diagnostics.
- Do not say P1/P2 pre keypoints being mostly inside 25 cm justifies 25 cm
  training. That creates the contradiction: if users already satisfy the outer
  envelope, why is pre-training EDSR low?
- Do not use `T00/T20/Twide` as a rigorous temporal threshold sweep; the levels
  are not comparable as a clean ladder.

## Key Files & Commands
- Week 1 experiment archive:
  - `handoffs/week1_main-experiments.md`
- Week 1 research archive:
  - `handoffs/week1_research_thinking.md`
- Week 2 research plan:
  - `handoffs/week2_research_thinking.md`
- Human diagnostic script:
  - `scripts/analyze_week2_human_data.py`
- Slurm wrapper:
  - `scripts/run_week2_human_diagnostics.sh`
- Latest no-plot diagnostics output root:
  - `outputs/week2_human_diagnostics_keypoints_v2`
- Earlier Slurm diagnostics output root with plots:
  - `outputs/week2_human_diagnostics_keypoints_quick`
- Main summary files:
  - `outputs/week2_human_diagnostics_keypoints_v2/human_diagnostics_summary.json`
  - `outputs/week2_human_diagnostics_keypoints_v2/keypoint_spread_summary.csv`
  - `outputs/week2_human_diagnostics_keypoints_v2/orientation_event_summary.csv`
  - `outputs/week2_human_diagnostics_keypoints_v2/temporal_human_summary.csv`
- Human data root:
  - `/scratch/users/k23114984/pybullet_data`
- Pooled HDF5 files:
  - `/scratch/users/k23114984/pybullet_data/pool_pre_skill1_2gap.hdf5`
  - `/scratch/users/k23114984/pybullet_data/pool_post_skill1_2gap.hdf5`
- Useful read-only inspection commands:
  ```bash
  find -L /scratch/users/k23114984/pybullet_data -maxdepth 3 -type d | sort
  find -L /scratch/users/k23114984/pybullet_data/target_pooled/pooled_symlinks/target_pre_skill1 -mindepth 1 -maxdepth 1 -type d | wc -l
  sed -n '1,8p' /scratch/users/k23114984/pybullet_data/target_pooled/manifests/target_pooled_manifest.csv
  ```
- Run diagnostics on HPC:
  ```bash
  sbatch scripts/run_week2_human_diagnostics.sh
  ```
- Direct local/interactive command pattern used by wrapper:
  ```bash
  python scripts/analyze_week2_human_data.py \
    --output-dir outputs/week2_human_diagnostics_keypoints_quick \
    --frame-stride 10
  ```

## Next Steps
1. Use the paper's structure-level evidence as the primary rebuttal evidence:
   - EDSR: P1 -> P6 = 14.0% -> 75.0%; P2 -> P7 = 22.0% -> 91.0%.
   - Table 9: MPCV/MCOD/MPSV/validation loss drop for DEMT post-training data.
2. Treat V2 local human diagnostics as secondary diagnostics only:
   - spatial keypoints: compatibility / tightening, not 25 cm parameter proof.
   - orientation: useful support for 15 deg finite-candidate reasonableness.
   - temporal: broad compatibility only, not exact `[0.5, 2.0]` proof.
3. Reviewer-facing framing:
   ```text
   The Table 5 values instantiate DEMT-selected P/R/V structures under the
   fixed robot, task family, learner, and N=30 budget. We defend them as
   bounded finite candidates satisfying human-compatibility and
   learner-compatibility constraints, not as mathematically proven global
   optima.
   ```
4. Use the revised strict wording from:
   - `rebuttal_workflow/claim_ledger.md`
   - `rebuttal_workflow/rebuttal_fragments/parameter_reasonableness_claim.md`
5. Use `rebuttal_workflow/experiment_queue.md` for next experiments:
   - E05 fixed-ratio spatial funnel sweep is the first new experiment if a
     stronger 25 cm claim is required.
   - E06 temporal ladder is backup/future-paper unless exact speed-window
     support is required.
   - E07 orientation bracket is backup/future-paper because the current
     orientation story is already usable.

## Open Questions
- Should the 25 cm argument report P1 and P2 separately, pooled across both, or both?
- If future E02 is run, should the simulation sampling distribution be empirical resampling from P1/P2 points, radial percentile truncation, Gaussian/elliptical sampling from mean/std, or all three?
- Which percentile levels should be finalized: user mentioned 90/80/70/60/50, but exact p50/p60/p70/p80 values should be computed from `outputs/week2_human_diagnostics_keypoints_v2/demo_metrics.csv` or `keypoint_spread_summary.csv`.
- Should the future simulation use P1 skill1 only, P2 skill2 only, or a pooled P1/P2 prior?
- For temporal analysis, should phase labels be manually defined from gripper/path heuristics or annotated from a smaller validated subset first?
- If the paper is rejected from CoRL, how much of Week 2 should target a September ICRA submission versus a later journal extension?

## Changelog
- 2026-07-03: Cross-linked the three-agent bounded-optimality queue, E00 human
  percentile audit, and E05 fixed-ratio spatial funnel sweep as the next
  experiment if stronger spatial evidence is required.
- 2026-07-03: Added R04 global-optimality pressure review. Agent3 should keep pushing for the best possible parameter explanation; Agent1/Agent2 should answer with bounded/constrained finite-candidate optimality, not a retreat to structure-only wording.
- 2026-07-02: Added Week 2 human keypoint diagnostics, corrected left-handed y mirror and keypoint plane definitions, recorded successful Slurm run, and captured natural-pretrain rationale for the 25 cm guidance envelope.
- 2026-06-30: Created Week 2 experiment handoff after supervisor meeting; recorded human-data roots, pooled/re-split real-user data policy, and planned spatial/temporal sweep direction.
