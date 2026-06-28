# Handoff: Main Experiments

_Last updated: 2026-06-28 · Branch: hpc-headless-data-collection @ 6a3ad5b_

## Goal
Prepare short-term CoRL rebuttal experiments for the DEMT paper, focusing on cube pick-and-lift spatial corridor and orientation/grasp-cue ablations. The ablation-1 spatial geometry is approved, corrected full datasets have been collected and converted to HDF5, four-condition diffusion-policy training has completed, and policy rollout / video evaluation supports the conclusion that the wide corridor-entry factor is the main source of degradation. The orientation/grasp-cue MVP raw datasets are now collected and validated; HDF5 conversion job `35237839` is running. Keep this file focused on experiment/code execution; paper framing and research logic live in `handoffs/research_thinking.md`.

## Current Progress
- Main ablation generator is `examples/main_abla_1.py`; original `examples/main.py` was intentionally left unchanged.
- HPC helper scripts exist and are uncommitted:
  - `scripts/run_abla1_collect.sh`
  - `scripts/check_abla1_dataset.py`
  - `.gitignore` update for `/logs/`
- Plot helper added and uncommitted:
  - `examples/plot_abla1_ee_trajectories.py`
- Important env path:
  - `/scratch/users/k23114984/conda/envs/polymetis38/bin/python`
  - User first said `/scratch/users/k23114984/conda/env`; actual working path is under `envs/polymetis38`.
- All old dataset contents under `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset` were deleted at user request after the geometry issue was found.
- Previous full/smoke datasets are invalid and gone:
  - old `abla1_smoke`
  - old `abla1_full`
  - old `cube_smoke_test`
- Previous debug data exists under:
  - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_debug/`
- Debug Slurm jobs submitted and completed:
  - `35224840`
  - `35224841`
  - `35224842`
  - `35224843`
- Debug collection command pattern used:
  ```bash
  for cond in P00 P10 P01 P11; do
    CONDITION=${cond} \
    NUM_DEMOS=1 \
    SEED=7 \
    SAMPLE_HZ=8 \
    OUTPUT_ROOT=/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_debug \
    MAX_COLLECTION_ATTEMPTS=3 \
    sbatch scripts/run_abla1_collect.sh
  done
  ```
- Previous debug datasets passed the then-current checker, but the user said the result was not correct because `corridor_start` had `y=cube_y`, so trajectories went directly toward the object-side `y ~= 0.5` line.
- Debug plot output:
  - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_debug/trajectory_plots/abla1_P00_ee_xyz_trajectories.png`
  - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_debug/trajectory_plots/abla1_P10_ee_xyz_trajectories.png`
  - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_debug/trajectory_plots/abla1_P01_ee_xyz_trajectories.png`
  - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_debug/trajectory_plots/abla1_P11_ee_xyz_trajectories.png`
- Current key metadata from debug:
  ```text
  P00 random_start=[0.2305, 0.0, 0.5120]
      base_pre=[0.5, 0.5, 0.22]
      pre_grasp=[0.5145, 0.4980, 0.22]
      pre_delta=[0.0145, -0.0020, 0.0]
      corr_delta=[-0.0788, 0.0, 0.0321]
  P10 random_start=[0.4004, 0.0, 0.2288]
      base_pre=[0.5, 0.5, 0.22]
      pre_grasp=[0.4923, 0.4838, 0.22]
      pre_delta=[-0.0077, -0.0162, 0.0]
      corr_delta=[-0.0204, 0.0, 0.1756]
  P01 random_start=[0.2305, 0.0, 0.5120]
      base_pre=[0.5, 0.5, 0.22]
      pre_grasp=[0.5436, 0.4939, 0.22]
      pre_delta=[0.0436, -0.0061, 0.0]
      corr_delta=[-0.0788, 0.0, 0.0321]
  P11 random_start=[0.2305, 0.0, 0.5120]
      base_pre=[0.5, 0.5, 0.22]
      pre_grasp=[0.5436, 0.4939, 0.22]
      pre_delta=[0.0436, -0.0061, 0.0]
      corr_delta=[-0.1969, 0.0, 0.0803]
  ```
- Current code state after corrections:
  - `random_start` is back to the user-required `y=0` x-z plane:
    ```text
    [random x, 0, random z]
    ```
  - `pre_grasp` is sampled in x-y around `[cube_x, cube_y, 0.22]` with z fixed:
    ```text
    pre_grasp_delta = [dx, dy, 0]
    ```
  - User clarified `corridor_start` should remain an x-z disk, but its y coordinate must be fixed at world `y=0.15`, not `cube_y`:
    ```text
    base_corridor_start = [cube_x - entry_dx, 0.15, 0.22 + entry_dz]
    corridor_start_delta = [dx, 0, dz]
    corridor_start = base_corridor_start + corridor_start_delta
    ```
  - `examples/main_abla_1.py` now exposes `--corridor-start-y` with default `0.15`; `scripts/run_abla1_collect.sh` forwards `CORRIDOR_START_Y`.
- `scripts/check_abla1_dataset.py` checks `corridor_start_delta[1] == 0` and `base_corridor_start[1] == corridor_start_y`.
- Corrected full dataset has been collected with `SEED=1`, `CORRIDOR_START_Y=0.15`, `SAMPLE_HZ=8`, and `NUM_DEMOS=30` for all four conditions:
  - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full/abla1_P00_d30_seed1`
  - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full/abla1_P10_d30_seed1`
  - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full/abla1_P01_d30_seed1`
  - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full/abla1_P11_d30_seed1`
- Full dataset Slurm jobs completed:
  - `35225029` P00: 30/30 successful demos from 30 attempts.
  - `35225031` P10: 30/30 successful demos from 32 attempts.
  - `35225032` P01: 30/30 successful demos from 32 attempts.
  - `35225033` P11: 30/30 successful demos from 34 attempts.
- All four full datasets passed `scripts/check_abla1_dataset.py`.
- User approved the corrected EE xyz trajectory plots after full collection ("可以!!").
- Full dataset trajectory plots:
  - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full/trajectory_plots/abla1_P00_ee_xyz_trajectories.png`
  - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full/trajectory_plots/abla1_P10_ee_xyz_trajectories.png`
  - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full/trajectory_plots/abla1_P01_ee_xyz_trajectories.png`
  - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full/trajectory_plots/abla1_P11_ee_xyz_trajectories.png`
- HDF5 conversion completed via Slurm job `35225365` using:
  - `STEP1_build_dataset/create_abla1_full_hdf5.py`
  - `STEP1_build_dataset/run_create_abla1_full_hdf5_slurm.sh`
  - source root: `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full`
  - `action_gap = 2`
  - `point_cloud_data = 10000`
- Converted HDF5 files are:
  - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full/abla1_P00_d30_seed1_2gap.hdf5`
  - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full/abla1_P01_d30_seed1_2gap.hdf5`
  - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full/abla1_P10_d30_seed1_2gap.hdf5`
  - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full/abla1_P11_d30_seed1_2gap.hdf5`
- All four HDF5 files were split with `/users/k23114984/code/arcap_policy/STEP2_train_policy/robomimic/scripts/split_train_val.py --ratio 0.1`.
  - Each file has `data=60`, `mask/train=54`, `mask/valid=6`.
- Training configs for the four HDF5 files exist and are uncommitted:
  - `STEP2_train_policy/robomimic/training_config/sim_test_00.json` -> P00 HDF5
  - `STEP2_train_policy/robomimic/training_config/sim_test_01.json` -> P01 HDF5
  - `STEP2_train_policy/robomimic/training_config/sim_test_10.json` -> P10 HDF5
  - `STEP2_train_policy/robomimic/training_config/sim_test_11.json` -> P11 HDF5
- Training Slurm wrapper:
  - `STEP2_train_policy/run_pybullet_dp.sh`
  - uses project dir `/users/k23114984/code/arcap_policy/STEP2_train_policy`
  - default env `/scratch/users/k23114984/conda/arcap`
  - forwards args to `robomimic/scripts/train.py`
  - GPU constraints currently allow `"a100|l40s|h200|h100"` and exclude `erc-hpc-comp040,erc-hpc-comp035`.
- Added uncommitted pipeline submitter:
  - `STEP2_train_policy/submit_abla1_train_pipeline.sh`
  - submits P00 -> P01 -> P10 -> P11 using Slurm `afterok` dependencies.
- Training jobs were submitted sequentially:
  - `35225657` `abla1_P00_dp`
  - `35225658` `abla1_P01_dp`
  - `35225661` `abla1_P10_dp`
  - `35225668` `abla1_P11_dp`
  - Note: P10 submission timed out on the client side, but `squeue` confirmed job `35225661` was created. P11 was submitted manually with `--dependency=afterok:35225661`.
- User reported training is complete and shared loss plot:
  - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full/loss.png`
- Loss interpretation from the plot:
  - All four conditions' train loss quickly drops from about `0.4` to near `0`, so training mechanics and model capacity are not globally broken.
  - `P00` and `P01` have low/stable validation loss, roughly `0.06-0.10`.
  - `P10` and `P11` have high/rising validation loss, roughly `0.25 -> 0.4+`.
  - This pattern isolates the issue to the first bit / wide corridor entry, not the second bit / wider pre-grasp.
- Added uncommitted rollout / visualization script:
  - `examples/eval_abla1_trained_policies.py`
  - loads checkpoints from `/users/k23114984/code/arcap_policy/STEP2_train_policy/trained_models`
  - defaults to `model_epoch_40.pth`
  - samples `random_start` exactly like data collection: reachable x-z plane with fixed `y=0`
  - uses `seed=628`, `num_rollouts=10`, `horizon=80`, `action_gap=2`, `sample_hz=8`, and `action_dt=0.25`
  - success condition matches collection: `final_cube_z >= 0.20`
  - supports `--save-videos` to write one MP4 per condition
- Policy rollout implementation details:
  - model observations are `robot0_arm_joints`, `robot0_hand_joints`, `pointcloud`
  - action is absolute joint target: 7 arm joints plus 1 gripper scalar, matching HDF5 conversion where actions are current frame plus `action_gap=2`
  - diffusion policy requires observation history, not a single frame; the script maintains `observation_horizon=7` by repeating the initial observation and then appending new observations
  - `torch.manual_seed` and `torch.cuda.manual_seed_all` are set in addition to Python / NumPy seeds, but diffusion rollouts may still show small run-to-run variation
- First pure rollout evaluation job:
  - Slurm job `35235693`, GPU node `erc-hpc-comp036`, completed
  - command used:
    ```bash
    /scratch/users/k23114984/conda/arcap/bin/python -u examples/eval_abla1_trained_policies.py \
      --conditions P00 P01 P10 P11 \
      --num-rollouts 10 \
      --seed 628 \
      --horizon 80 \
      --playback-speed 100 \
      --cuda \
      --output-dir /scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full/policy_rollouts_seed628
    ```
  - pure rollout success rates:
    ```text
    P00: 6/10 = 0.600
    P01: 5/10 = 0.500
    P10: 0/10 = 0.000
    P11: 0/10 = 0.000
    ```
  - output summary:
    `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full/policy_rollouts_seed628/summary_seed628_n10.json`
- Video rollout job:
  - Slurm job `35236243`, GPU node `erc-hpc-comp037`, completed
  - command used:
    ```bash
    /scratch/users/k23114984/conda/arcap/bin/python -u examples/eval_abla1_trained_policies.py \
      --conditions P00 P01 P10 P11 \
      --num-rollouts 10 \
      --seed 628 \
      --horizon 80 \
      --playback-speed 100 \
      --cuda \
      --save-videos \
      --video-fps 20 \
      --video-every-n-actions 2 \
      --video-width 320 \
      --video-height 320 \
      --output-dir /scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full/policy_rollouts_seed628 \
      --video-dir /scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full/policy_rollouts_seed628/videos
    ```
  - video job success rates:
    ```text
    P00: 4/10 = 0.400
    P01: 5/10 = 0.500
    P10: 1/10 = 0.100
    P11: 2/10 = 0.200
    ```
  - video files were verified readable with `imageio`; each has `500` frames, `20 fps`, and `320x320` resolution:
    - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full/policy_rollouts_seed628/videos/abla1_P00_seed628_n10.mp4`
    - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full/policy_rollouts_seed628/videos/abla1_P01_seed628_n10.mp4`
    - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full/policy_rollouts_seed628/videos/abla1_P10_seed628_n10.mp4`
    - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full/policy_rollouts_seed628/videos/abla1_P11_seed628_n10.mp4`
  - note: video job reran inference, so its success rates overwrote `summary_seed628_n10.json` and differ from the earlier pure rollout job.
- Confirmed ablation condition definitions from `examples/main_abla_1.py` and `scripts/check_abla1_dataset.py`:
  ```text
  P00: corridor_start_radius=0.10, pre_grasp_radius=0.02
  P10: corridor_start_radius=0.25, pre_grasp_radius=0.02
  P01: corridor_start_radius=0.10, pre_grasp_radius=0.06
  P11: corridor_start_radius=0.25, pre_grasp_radius=0.06
  ```
- Sampling geometry to preserve:
  - `random_start`: sampled on the `y=0` x-z plane, common to all four conditions.
  - `corridor_start`: x-z disk around the nominal entry, fixed world `y=0.15`.
  - `pre_grasp`: x-y disk above cube, fixed `z=0.22`.
  - `grasp` and `lift`: fixed object-relative targets.
- HDF5 split detail:
  - Each condition has `data=60`, `mask/train=54`, `mask/valid=6`.
  - The same HDF5 valid keys were used across all four conditions: `demo_6`, `demo_13`, `demo_18`, `demo_34`, `demo_48`, `demo_59`.
  - Because `action_gap=2`, those correspond to original raw demos `[3, 6, 9, 17, 24, 29]`.
  - Quick metadata statistics did not show the valid raw demos as obviously more extreme than train, so the `P10/P11` validation loss increase is more likely a real learnability issue from wide `corridor_start_radius=0.25` than a simple bad split.
- Orientation/grasp-cue MVP has started after user decided not to use `P00` as baseline because policy rollout success was only about `40-60%`.
- User-specified orientation MVP spatial baseline:
  ```text
  corridor_start_radius = 0.05
  pre_grasp_radius = 0.0
  corridor_start_y = 0.15
  random_start remains on world y=0 x-z plane
  ```
- User revised the orientation execution rule: each demo samples one gripper orientation and uses it for the entire trajectory, from `random_start` through `lift`. Do not revert to the earlier plan where only `pre_grasp/pick_grasp/lift` used the sampled orientation.
- Added uncommitted orientation MVP files in this repo:
  - `examples/main_orn_mvp.py`
  - `examples/plot_orn_mvp_ee_orientation.py`
  - `scripts/run_orn_mvp_collect.sh`
  - `scripts/check_orn_mvp_dataset.py`
  - `scripts/create_orn_mvp_hdf5.py`
  - `scripts/run_orn_mvp_hdf5_slurm.sh`
  - `scripts/create_orn_mvp_train_configs.py`
  - `scripts/submit_orn_mvp_train_pipeline.sh`
  - generated configs under `training_config/orn_mvp/`
- Orientation conditions:
  ```text
  R00: 0 deg, full-trajectory default orientation
  R15: one sampled full-trajectory orientation within +/-15 deg
  R30: one sampled full-trajectory orientation within +/-30 deg
  ```
- Local smoke tests passed:
  - `/tmp/orn_mvp_smoke_R00`: `1/1`, checker passed, angle `0.0 deg`.
  - `/tmp/orn_mvp_smoke_R30`: `1/1`, checker passed, sampled angle `0.0672 deg` for seed 7.
- HPC one-demo debug collection completed and all datasets passed `scripts/check_orn_mvp_dataset.py`:
  - `35237190` R00 -> `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/orn_mvp_debug/orn_mvp_R00_d1_seed7`
  - `35237193` R15 -> `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/orn_mvp_debug/orn_mvp_R15_d1_seed7`
  - `35237194` R30 -> `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/orn_mvp_debug/orn_mvp_R30_d1_seed7`
- HPC full raw orientation datasets completed with `NUM_DEMOS=30`, `SEED=1`, `SAMPLE_HZ=8`, `MAX_COLLECTION_ATTEMPTS=80`, `corridor_start_radius=0.05`, `pre_grasp_radius=0.0`:
  - `35237327` R00: 30/30 successful demos from 30 attempts.
  - `35237329` R15: 30/30 successful demos from 30 attempts.
  - `35237328` R30: 30/30 successful demos from 33 attempts.
- Full raw orientation dataset directories:
  - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/orn_mvp_full/orn_mvp_R00_d30_seed1`
  - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/orn_mvp_full/orn_mvp_R15_d30_seed1`
  - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/orn_mvp_full/orn_mvp_R30_d30_seed1`
- Full raw orientation checker results:
  - R00: 30 demos, frames min/mean/max `94/105.0/114`, angle range `0.0..0.0`, passed.
  - R15: 30 demos, frames min/mean/max `94/104.6/117`, angle range `-12.8408..13.7367`, passed.
  - R30: 30 demos, frames min/mean/max `94/103.9/117`, angle range `-25.9074..27.4734`, passed.
- HDF5 conversion for orientation MVP was submitted as Slurm job `35237839` with:
  ```bash
  sbatch scripts/run_orn_mvp_hdf5_slurm.sh
  ```
  Current status at handoff time: `R`, running on `erc-hpc-comp004` for about `2:13`. The user explicitly said to wait and resume later; do not cancel it.
- Orientation raw-data visualization script was added and run:
  - `examples/plot_orn_mvp_ee_orientation.py`
  - Reads each frame's `ee_pose.txt` as `xyz + quat_xyzw`, plus demo metadata fields such as `orientation_angle_degrees`, `default_quat_xyzw`, and `contact_quat_xyzw`.
  - Plots EE 3D xyz, x-y view, x-z view, EE angle from default quaternion, EE angle error to demo target/contact quaternion, and sampled orientation-angle histogram.
  - Generated plots:
    - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/orn_mvp_full/orientation_plots/orn_mvp_R00_ee_xyz_orientation.png`
    - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/orn_mvp_full/orientation_plots/orn_mvp_R15_ee_xyz_orientation.png`
    - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/orn_mvp_full/orientation_plots/orn_mvp_R30_ee_xyz_orientation.png`
  - `R30` plot was visually inspected and looked sane.
- Orientation HDF5 conversion should create:
  - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/orn_mvp_full/orn_mvp_R00_d30_seed1_2gap.hdf5`
  - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/orn_mvp_full/orn_mvp_R15_d30_seed1_2gap.hdf5`
  - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/orn_mvp_full/orn_mvp_R30_d30_seed1_2gap.hdf5`
- Training configs were generated locally:
  - `training_config/orn_mvp/orn_mvp_R00.json`
  - `training_config/orn_mvp/orn_mvp_R15.json`
  - `training_config/orn_mvp/orn_mvp_R30.json`
  These point to the expected orientation HDF5 files above and use the existing `/users/k23114984/code/arcap_policy/STEP2_train_policy/robomimic/training_config/sim_test_00.json` as template.
- Current git status in `/scratch/prj/eng_demt_robot_learning/polymetics_demt` includes:
  ```text
   M .gitignore
   M docs/ablation-1.md
   M examples/main_abla_1.py
   M handoffs/main-experiments.md
  ?? examples/eval_abla1_trained_policies.py
  ?? examples/main_orn_mvp.py
  ?? examples/plot_abla1_ee_trajectories.py
  ?? examples/plot_orn_mvp_ee_orientation.py
  ?? handoffs/research_thinking.md
  ?? scripts/check_abla1_dataset.py
  ?? scripts/check_orn_mvp_dataset.py
  ?? scripts/create_orn_mvp_hdf5.py
  ?? scripts/create_orn_mvp_train_configs.py
  ?? scripts/run_abla1_collect.sh
  ?? scripts/run_orn_mvp_collect.sh
  ?? scripts/run_orn_mvp_hdf5_slurm.sh
  ?? scripts/submit_orn_mvp_train_pipeline.sh
  ?? training_config/
  ```

## What Worked
- Slurm submission works when `sbatch`/`squeue` are run with escalation/outside sandbox.
- `scripts/run_abla1_collect.sh` already points to the correct conda env path:
  ```bash
  CONDA_ENV=${CONDA_ENV:-"/scratch/users/k23114984/conda/envs/polymetis38"}
  ```
- `examples/plot_abla1_ee_trajectories.py` can plot arbitrary condition directory names via:
  ```bash
  python examples/plot_abla1_ee_trajectories.py \
    --dataset-root /scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_debug \
    --dataset-template 'abla1_{condition}_d1_seed7' \
    --output-dir /scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_debug/trajectory_plots \
    --stride 1
  ```
- `scripts/check_abla1_dataset.py` now checks mixed-plane invariants:
  - `random_start y == 0`
  - `corridor_start_delta[1] == 0`
  - `base_corridor_start[1] == corridor_start_y` (default `0.15`)
  - `pre_grasp_delta[2] == 0`
- HDF5 conversion job `35225365` finished successfully. Its stdout ended with `[INFO] Finished HDF5 conversion`; stderr only contained `pybullet build time: Nov 28 2023 23:51:11`.
- `split_train_val.py` worked directly with `/scratch/users/k23114984/conda/arcap/bin/python`; no Slurm job was needed for splitting.
- The training script supports `--name`, `--dataset`, and `--output` overrides, so the four condition jobs can share base configs while using unique experiment names.
- The completed loss plot gives a clean factorial pattern: `P00/P01` good, `P10/P11` bad. This supports the current conclusion that increasing `corridor_start_radius` from `0.10` to `0.25` hurts validation much more than increasing `pre_grasp_radius` from `0.02` to `0.06`.
- `examples/eval_abla1_trained_policies.py` can evaluate all four trained policies directly in PyBullet using robomimic `policy_from_checkpoint`.
- For this robomimic diffusion-policy fork, rollout observations must include the time dimension `[T, ...]`; with `observation_horizon=7`, the script maintains a 7-frame observation history.
- Video capture works by writing PyBullet RGB frames with `imageio.get_writer(...).append_data(...)`, similar to `/scratch/prj/eng_demt_robot_learning/libero_demt/scripts/visualize_dataset_demo.py`.
- Keep the policy point-cloud camera at the original `200x200` dimensions / intrinsics and render videos separately at `320x320`; changing `sim.image_width` / `sim.image_height` after init can break pointcloud cropping.
- Rollout/video results agree qualitatively with validation losses: `P00/P01` are partially successful, while wide corridor-entry conditions `P10/P11` are much worse.
- Orientation MVP raw collection works locally and on HPC with the stricter baseline `corridor_start_radius=0.05`, `pre_grasp_radius=0.0`.
- `examples/main_orn_mvp.py` correctly samples one quaternion per demo and uses it for full-trajectory IK / motion, including `random_start`, `corridor_start`, `pre_grasp`, `pick_grasp`, and `lift`.
- `scripts/check_orn_mvp_dataset.py` verifies orientation conditions, full-phase orientation metadata, `corridor_start_radius=0.05`, `pre_grasp_radius=0.0`, `random_start y=0`, `corridor_start_y=0.15`, phase coverage, and successful final cube lift.
- `examples/plot_orn_mvp_ee_orientation.py` successfully generated per-condition orientation plots for `R00/R15/R30`. It computes quaternion angular distance using `abs(dot(q1, q2))`, so `q` and `-q` are treated as the same rotation.

## What Didn't Work
- The original ablation plan/code used x-z sampling for both `corridor_start` and `pre_grasp`. This made `pre_grasp` z vary and was wrong for the user's intended geometry.
- A previous assistant correction mistakenly changed `random_start` to x-y/fixed-z. The user rejected this. `random_start` must remain on the `y=0` x-z plane.
- The old `N=30, seed=1` datasets passed the old checker but were invalid for training; the user reported val loss explosion and then requested deleting all dataset contents.
- The latest completed old debug collection passed the old checker, but the user said "还是不对" because `corridor_start` used `y=cube_y`. This was addressed by fixing `corridor_start_y=0.15`; corrected smoke and full trajectory plots were approved.
- `conda run -n polymetis38` can fail due to env lookup/location issues. Prefer the absolute python:
  ```bash
  /scratch/users/k23114984/conda/envs/polymetis38/bin/python
  ```
- Running `sbatch`/`squeue` inside the default sandbox fails or is unreliable; use escalation.
- HPC shell startup prints quota/slurm credit tracebacks in command output. These are noisy but did not prevent Slurm debug jobs from completing.
- `sbatch` can create a job even if the client-side command times out while waiting for a response. Always check `squeue` before retrying, to avoid duplicate submissions.
- Do not infer final deployment performance from validation loss alone. The current loss plot is useful for diagnosis, but rollout success rate should be checked before writing the final rebuttal claim.
- The current `docs/ablation-1.md` still contains stale planned assumptions in places, including fixed-height x-y random-start wording and `corridor_start` y tied to object/cube y. Treat the implemented code and approved plots as authoritative until the doc is cleaned up.
- Early rollout script attempt passed a single-frame observation and failed with `AssertionError` because the diffusion policy expected `[B, T, ...]` observations.
- A second rollout attempt used `T=1` and failed with `RuntimeError: mat1 and mat2 shapes cannot be multiplied (1x328 and 760x512)`; the model requires the full `observation_horizon=7`.
- First video attempt changed `sim.image_width` / `sim.image_height` to `320`, but `camera_intrinsic` remained from `200x200`; pointcloud cropping later became empty and raised `RuntimeError: Cropped point cloud is empty.` The fix was to render video frames via a separate `pb.getCameraImage(width, height, ...)` path without changing the policy pointcloud camera dimensions.
- Video rollouts can produce slightly different success counts from pure rollouts because inference is rerun; do not mix success-rate numbers without noting which run produced them.
- Do not use the old `P00` spatial condition as the orientation baseline. The user rejected it because trained policy rollout success was only around `40-60%`. Use `corridor_start_radius=0.05` and `pre_grasp_radius=0.0`.
- Do not switch orientation only near grasp/contact unless the user changes direction again. The current accepted MVP is one sampled gripper orientation per demo, applied for the whole trajectory.
- HDF5 job `35237839` was briefly considered for cancellation after staying pending, but the user interrupted and explicitly said to let it continue. At this handoff it is now running; do not cancel it.

## Key Files & Commands
- Main generator:
  - `examples/main_abla_1.py`
- Current planning doc, partially edited and may still contain wrong geometry assumptions:
  - `docs/ablation-1.md`
- Checker:
  - `scripts/check_abla1_dataset.py`
- Plotter:
  - `examples/plot_abla1_ee_trajectories.py`
- Policy rollout / video evaluator:
  - `examples/eval_abla1_trained_policies.py`
- Slurm wrapper:
  - `scripts/run_abla1_collect.sh`
- HDF5 converter:
  - `STEP1_build_dataset/create_abla1_full_hdf5.py`
- HDF5 conversion Slurm wrapper:
  - `STEP1_build_dataset/run_create_abla1_full_hdf5_slurm.sh`
- Training configs:
  - `STEP2_train_policy/robomimic/training_config/sim_test_00.json`
  - `STEP2_train_policy/robomimic/training_config/sim_test_01.json`
  - `STEP2_train_policy/robomimic/training_config/sim_test_10.json`
  - `STEP2_train_policy/robomimic/training_config/sim_test_11.json`
- Training Slurm wrapper:
  - `STEP2_train_policy/run_pybullet_dp.sh`
- Training pipeline submitter:
  - `STEP2_train_policy/submit_abla1_train_pipeline.sh`
- Orientation MVP generator:
  - `examples/main_orn_mvp.py`
- Orientation MVP xyz/orientation plotter:
  - `examples/plot_orn_mvp_ee_orientation.py`
- Orientation MVP raw-data Slurm wrapper:
  - `scripts/run_orn_mvp_collect.sh`
- Orientation MVP checker:
  - `scripts/check_orn_mvp_dataset.py`
- Orientation MVP HDF5 converter and Slurm wrapper:
  - `scripts/create_orn_mvp_hdf5.py`
  - `scripts/run_orn_mvp_hdf5_slurm.sh`
- Orientation MVP training config generator and submitter:
  - `scripts/create_orn_mvp_train_configs.py`
  - `scripts/submit_orn_mvp_train_pipeline.sh`
- Orientation MVP training configs:
  - `training_config/orn_mvp/orn_mvp_R00.json`
  - `training_config/orn_mvp/orn_mvp_R15.json`
  - `training_config/orn_mvp/orn_mvp_R30.json`
- Check debug data:
  ```bash
  for cond in P00 P10 P01 P11; do
    python scripts/check_abla1_dataset.py \
      /scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_debug/abla1_${cond}_d1_seed7 \
      --expected-demos 1 \
      --expected-condition ${cond}
  done
  ```
- Plot debug data:
  ```bash
  python examples/plot_abla1_ee_trajectories.py \
    --dataset-root /scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_debug \
    --dataset-template 'abla1_{condition}_d1_seed7' \
    --output-dir /scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_debug/trajectory_plots \
    --stride 1
  ```
- Submit one-demo debug jobs:
  ```bash
  for cond in P00 P10 P01 P11; do
    CONDITION=${cond} \
    NUM_DEMOS=1 \
    SEED=7 \
    SAMPLE_HZ=8 \
    OUTPUT_ROOT=/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_debug \
    CORRIDOR_START_Y=0.15 \
    MAX_COLLECTION_ATTEMPTS=3 \
    sbatch scripts/run_abla1_collect.sh
  done
  ```
- Check converted HDF5 split masks:
  ```bash
  /scratch/users/k23114984/conda/arcap/bin/python - <<'PY'
  import h5py
  from pathlib import Path
  root = Path('/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full')
  for name in ['P00', 'P01', 'P10', 'P11']:
      path = root / f'abla1_{name}_d30_seed1_2gap.hdf5'
      with h5py.File(path, 'r') as f:
          print(path.name, len(f['data']), len(f['mask/train']), len(f['mask/valid']))
  PY
  ```
- Submit training pipeline:
  ```bash
  STEP2_train_policy/submit_abla1_train_pipeline.sh
  ```
- Check current training queue:
  ```bash
  squeue -j 35225657,35225658,35225661,35225668 \
    -o "%.18i %.9P %.30j %.8u %.2t %.10M %.6D %R"
  ```
- Inspect the completed training loss plot:
  ```bash
  python - <<'PY'
  from pathlib import Path
  print(Path('/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full/loss.png'))
  PY
  ```
- Re-check HDF5 valid keys:
  ```bash
  /scratch/users/k23114984/conda/arcap/bin/python - <<'PY'
  import h5py
  from pathlib import Path
  root = Path('/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full')
  for cond in ['P00', 'P01', 'P10', 'P11']:
      with h5py.File(root / f'abla1_{cond}_d30_seed1_2gap.hdf5', 'r') as f:
          valid = [x.decode() if isinstance(x, bytes) else str(x) for x in f['mask/valid'][()]]
          print(cond, valid)
  PY
  ```
- Recompute raw train/valid waypoint statistics:
  ```bash
  /scratch/users/k23114984/conda/arcap/bin/python - <<'PY'
  import json, math, statistics
  from pathlib import Path
  root = Path('/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full')
  valid_raw = [3, 6, 9, 17, 24, 29]
  for cond in ['P00', 'P01', 'P10', 'P11']:
      droot = root / f'abla1_{cond}_d30_seed1'
      rows = []
      for i in range(30):
          m = json.loads((droot / f'demo_{i}' / 'metadata.json').read_text())
          cn = math.sqrt(sum(float(x) ** 2 for x in m['corridor_start_delta']))
          pn = math.sqrt(sum(float(x) ** 2 for x in m['pre_grasp_delta']))
          rows.append((i, cn, pn))
      print(cond)
      for name, ids in [('train', [i for i in range(30) if i not in valid_raw]), ('valid', valid_raw)]:
          sub = [r for r in rows if r[0] in ids]
          print(name, 'corr_mean', statistics.mean(r[1] for r in sub), 'pre_mean', statistics.mean(r[2] for r in sub))
  PY
  ```
- Individual training command pattern:
  ```bash
  sbatch --job-name=abla1_P00_dp \
    /users/k23114984/code/arcap_policy/STEP2_train_policy/run_pybullet_dp.sh \
    --config /users/k23114984/code/arcap_policy/STEP2_train_policy/robomimic/training_config/sim_test_00.json \
    --name abla1_P00_d30_seed1_2gap \
    --output /users/k23114984/code/arcap_policy/STEP2_train_policy/trained_models
  ```
- Run pure policy rollouts:
  ```bash
  /scratch/users/k23114984/conda/arcap/bin/python -u examples/eval_abla1_trained_policies.py \
    --conditions P00 P01 P10 P11 \
    --num-rollouts 10 \
    --seed 628 \
    --horizon 80 \
    --playback-speed 100 \
    --cuda \
    --output-dir /scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full/policy_rollouts_seed628
  ```
- Run policy rollouts with videos:
  ```bash
  /scratch/users/k23114984/conda/arcap/bin/python -u examples/eval_abla1_trained_policies.py \
    --conditions P00 P01 P10 P11 \
    --num-rollouts 10 \
    --seed 628 \
    --horizon 80 \
    --playback-speed 100 \
    --cuda \
    --save-videos \
    --video-fps 20 \
    --video-every-n-actions 2 \
    --video-width 320 \
    --video-height 320 \
    --output-dir /scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full/policy_rollouts_seed628 \
    --video-dir /scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full/policy_rollouts_seed628/videos
  ```
- Verify video files:
  ```bash
  /scratch/users/k23114984/conda/arcap/bin/python - <<'PY'
  from pathlib import Path
  import imageio.v2 as imageio
  root = Path('/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full/policy_rollouts_seed628/videos')
  for p in sorted(root.glob('abla1_P*_seed628_n10.mp4')):
      reader = imageio.get_reader(str(p))
      meta = reader.get_meta_data()
      n = reader.count_frames()
      reader.close()
      print(p.name, p.stat().st_size, n, meta.get('fps'), meta.get('size'))
  PY
  ```
- Check orientation MVP raw full datasets:
  ```bash
  for cond in R00 R15 R30; do
    scripts/check_orn_mvp_dataset.py \
      /scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/orn_mvp_full/orn_mvp_${cond}_d30_seed1 \
      --expected-demos 30 \
      --expected-condition ${cond}
  done
  ```
- Check queued/running orientation HDF5 job:
  ```bash
  squeue -j 35237839 -o "%.18i %.30j %.2t %.10M %R"
  ```
- Recreate orientation raw-data visualization plots:
  ```bash
  /scratch/users/k23114984/conda/envs/polymetis38/bin/python examples/plot_orn_mvp_ee_orientation.py \
    --dataset-root /scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/orn_mvp_full \
    --conditions R00 R15 R30 \
    --stride 3
  ```
- Inspect orientation HDF5 conversion logs after job starts/completes:
  ```bash
  tail -n 80 /scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/orn_mvp_full/logs/hdf5-35237839.out
  tail -n 80 /scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/orn_mvp_full/logs/hdf5-35237839.err
  ```
- Split orientation HDF5 files after conversion:
  ```bash
  for cond in R00 R15 R30; do
    /scratch/users/k23114984/conda/arcap/bin/python \
      /users/k23114984/code/arcap_policy/STEP2_train_policy/robomimic/scripts/split_train_val.py \
      --dataset /scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/orn_mvp_full/orn_mvp_${cond}_d30_seed1_2gap.hdf5 \
      --ratio 0.1
  done
  ```
- Submit orientation training pipeline after HDF5 split:
  ```bash
  scripts/submit_orn_mvp_train_pipeline.sh
  ```

## Next Steps
1. Let HDF5 conversion job `35237839` finish unless the user explicitly says otherwise. At handoff time it is running on `erc-hpc-comp004`; monitor it with `squeue`, then inspect logs under `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/orn_mvp_full/logs/`.
2. Verify the three expected orientation HDF5 files exist and contain converted demos.
3. Run `split_train_val.py --ratio 0.1` on each orientation HDF5 file and verify `data`, `mask/train`, and `mask/valid` counts.
4. Submit `scripts/submit_orn_mvp_train_pipeline.sh` to train `R00 -> R15 -> R30` sequentially through `/users/k23114984/code/arcap_policy/STEP2_train_policy/run_pybullet_dp.sh`.
5. After training completes, adapt `examples/eval_abla1_trained_policies.py` or add an orientation-specific evaluator so rollout initial orientation matches each condition's policy/data convention.
6. Decide which spatial rollout run to cite in the rebuttal materials separately from the orientation MVP.
7. Update `docs/ablation-1.md` or create a new orientation-specific doc so stale corridor assumptions do not bleed into final writing.

## Open Questions
- Should the next experiment add `corridor_start_radius=0.15` to locate the degradation threshold between `0.10` and `0.25`?
- Should `P10/P11` be rerun with more than 30 raw demos if rollout confirms poor performance?
- Should the plotter show sampled waypoints (`random_start`, `corridor_start`, `pre_grasp`, `grasp`, `lift`) explicitly overlaid, instead of only the EE trajectory?
- Should final reported rollout success rates use one deterministic rerun after the torch seed patch, and should that rerun be saved to a non-overwriting output directory?
- For orientation rollout evaluation, should deployment initial orientation be fixed/default for all policies, sampled from the matching train condition, or evaluated under a common stress distribution?

## Changelog
- 2026-06-27: Created handoff for detailed `examples/main.py` experiments and documented phase/data/noise behavior.
- 2026-06-27: Updated handoff with DEMT paper/rebuttal context, created planning docs, and recorded agreed Spatial corridor ablation design with random EE initialization on the reachable `y = 0` x-z plane.
- 2026-06-27: Updated handoff after implementing `examples/main_abla_1.py`, smoke testing all four 2 x 2 conditions, and pushing commits `d9821ec` and `27a2d53` to GitHub.
- 2026-06-27: Updated handoff after adding ablation-1 Slurm/checker scripts and completing validated HPC collection for four `N=30, seed=1` conditions.
- 2026-06-27: Rewrote handoff after discovering the previous datasets were geometrically invalid, deleting all dataset contents, correcting `pre_grasp` to x-y/fixed-z sampling, collecting one-demo debug Slurm data, and recording that the user still considers the debug result incorrect.
- 2026-06-27: Updated handoff after user clarified `corridor_start` should remain x-z sampled with fixed world `y=0.15`, and code/checker/Slurm wrapper were updated for `--corridor-start-y`.
- 2026-06-27: Updated handoff after collecting corrected full `abla1_full` datasets for P00/P10/P01/P11 with 30 demos each, all using seed 1 and passing checker.
- 2026-06-27: Updated handoff after the user approved the full EE xyz trajectory plots and cleared the way for docs cleanup and downstream training/evaluation.
- 2026-06-27: Updated handoff after converting the corrected full datasets to four split HDF5 files and submitting the sequential four-condition diffusion-policy Slurm training pipeline.
- 2026-06-28: Updated handoff after training completed and loss analysis showed low validation loss for P00/P01 but high/rising validation loss for P10/P11, implicating wide corridor-entry sampling.
- 2026-06-28: Updated handoff after adding trained-policy rollout/video evaluation, recording pure rollout and video-run success rates, and documenting the four generated MP4 outputs.
- 2026-06-28: Split research framing into `handoffs/research_thinking.md`; this file should remain focused on experiment/code state.
- 2026-06-28: Updated handoff after implementing orientation/grasp-cue MVP, collecting and validating R00/R15/R30 raw full datasets, generating training configs, and submitting queued HDF5 conversion job `35237839`.
- 2026-06-28: Updated handoff after adding orientation raw-data xyz/quaternion visualization, generating R00/R15/R30 plots, and confirming HDF5 job `35237839` is now running.
