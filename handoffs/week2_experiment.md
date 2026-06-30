# Handoff: Week 2 Experiments

_Last updated: 2026-06-30 · Branch: hpc-headless-data-collection @ 1ab8302_

## Goal
Plan and execute Week 2 DEMT follow-up experiments after the supervisor meeting. The immediate focus is not to run new jobs yet, but to organize the next experimental agenda around real human data diagnostics and cleaner parameter sweeps for spatial corridor guidance and temporal consistency. Week 1 execution details are archived in `handoffs/week1_main-experiments.md`.

## Current Progress
- User explicitly requested no code and no new experiment execution in this handoff turn.
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
- Therefore, Week 2 human-data diagnostics will likely require reconstructing EE pose from Franka/Panda FK using joint trajectories, then deriving phase/contact events from gripper state and path progress.

## What Worked
- `/scratch/users/k23114984/pybullet_data` has a clean enough organization for target/control/ARCap/P8 analysis.
- Manifest files are useful for explaining and auditing the pooled/re-split real-user data construction.
- Target pooled roots provide a direct P1/P2/P6/P7 mapping with 120 demos per phase/skill.
- The existing Week 1 simulation stack can be reused later for spatial and temporal parameter sweeps, but no new jobs have been launched for Week 2 yet.

## What Didn't Work
- Do not use the old Week 1 spatial 2x2 result as the main Week 2 spatial story. It is useful history, but the supervisor meeting shifted the design toward coupled corridor/pre-grasp radius ratios.
- Do not frame a new user study as the short-term solution. Sequential exposure to different radii introduces learning/order effects, and recruitment cost/time is high.
- Do not frame pooled/re-split real-user data as synthetic. The user clarified that all demonstrations are real human data; recombination was a practical response to limited time and budget.
- Do not assume direct EE pose or phase labels are present in the human raw demo directories. Current visible files are joints, gripper state, and point clouds.

## Key Files & Commands
- Week 1 experiment archive:
  - `handoffs/week1_main-experiments.md`
- Week 1 research archive:
  - `handoffs/week1_research_thinking.md`
- Week 2 research plan:
  - `handoffs/week2_research_thinking.md`
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

## Next Steps
1. Write a read-only human-data analysis script only after the user asks for code. It should not modify source data.
2. Reconstruct EE pose from `arm_joints.txt` or `obs/robot0_arm_joints` using the matching Panda/Franka FK setup.
3. Compute real-human spatial envelope statistics for P1/P2/P6/P7/P8: radial percentiles, corridor coverage, pre-grasp/contact spread, and per-phase/path-normalized dispersion.
4. Use human-derived P6/P7/P8 post-training statistics to choose a cleaner spatial sweep. Preferred design from the meeting: keep corridor radius and pre-grasp radius coupled, e.g. `25cm:5cm`, `30cm:6cm`, `35cm:7cm`, approximately a `5:1` funnel ratio.
5. Redesign temporal simulation as a symmetric jitter ladder: `T00`, `T10`, `T20`, `T30`, `T40`, optionally `T50`, instead of mixing `+/-20%` with `[0.5, 2.0]`.
6. Before launching any Slurm jobs, freeze exact candidate names, output roots, and non-overwriting summary paths.

## Open Questions
- Which human-data subset should calibrate spatial radii: P6/P7/P8 target post only, or P1/P2 pre versus P6/P7 post improvement?
- Should spatial parameter levels follow exactly `5:1` corridor:pre-grasp ratio, or compare `2:1` and `5:1` as separate sweep families?
- For temporal analysis, should phase labels be manually defined from gripper/path heuristics or annotated from a smaller validated subset first?
- If the paper is rejected from CoRL, how much of Week 2 should target a September ICRA submission versus a later journal extension?

## Changelog
- 2026-06-30: Created Week 2 experiment handoff after supervisor meeting; recorded human-data roots, pooled/re-split real-user data policy, and planned spatial/temporal sweep direction.
