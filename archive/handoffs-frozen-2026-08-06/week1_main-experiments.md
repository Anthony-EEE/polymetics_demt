# Handoff: Week 1 Main Experiments

_Last updated: 2026-06-30 · Branch: hpc-headless-data-collection @ 1ab8302_

## Goal
Prepare short-term CoRL rebuttal experiments for the DEMT paper, focusing on cube pick-and-lift spatial corridor, orientation/grasp-cue, and temporal consistency ablations. Critical correction on 2026-06-29: the previous ablation-1 spatial dataset/results under `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full` are invalid because data collection used the wrong corridor-start circle center (`[0.3, 0.15, 0.28]` instead of the AR guidance center `[0.3, 0.0, 0.5]`) and included an extra `random_start` segment that is not part of the intended AR guidance distribution. The corrected ablation-1 generator/checker/evaluator now start demos directly at sampled `corridor_start`; the full corrected raw/HDF5/split/train/rollout/video pipeline has completed under `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full_arcenter`. Corrected spatial rollout is mixed (`P00/P01/P10/P11 = 8/10, 6/10, 7/10, 6/10`), while validation loss flags `P10` as clearly worse. Corrected spatial annulus stress rollout has also completed on `abla1_full_arcenter` models with `0.25 <= d <= 0.50m` and low success (`P00/P01/P10/P11 = 2/10, 1/10, 2/10, 1/10`). The orientation/grasp-cue MVP raw datasets are collected, validated, converted to HDF5, split into train/valid masks, trained, and evaluated with rollout/video. The temporal threshold sweep `T00/T20/Twide` has collected, validated, converted, split, plotted, trained, and evaluated with rollout/video; the latest-checkpoint fixed-start evaluation now shows monotonic degradation from `T00` to `Twide`. Keep this file focused on Week 1 experiment/code execution; paper framing and research logic live in `handoffs/week1_research_thinking.md`.

## Current Progress
- 2026-06-30 storage / fresh-context note:
  - User moved the shared training-model storage out of `/users/k23114984` to the project scratch area to avoid the 50GB `/users` quota. Future training outputs should use `/scratch/prj/eng_demt_robot_learning/trained_models` unless a task-specific scratch output root is explicitly required.
  - User also moved Codex SQLite/state under the large scratch area to avoid filling `/users`.
  - Verified `/scratch/prj/eng_demt_robot_learning/trained_models` exists and contains historical `abla1_*`, `orn_mvp_*`, `time_mvp_*`, and partial `abla1_arcenter_*` directories.
  - Important: the corrected ABLA1 rollout summarized below used the successful dataset-local scratch checkpoints under `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full_arcenter/trained_models`, not the top-level `/scratch/prj/eng_demt_robot_learning/trained_models/abla1_arcenter_*` directories. The top-level corrected-arcenter directories currently visible are the earlier partial/failed `20260629173956` run and should not be used as the corrected final checkpoints unless they are replaced or verified.
  - For future jobs, pass `--output /scratch/prj/eng_demt_robot_learning/trained_models` to `/users/k23114984/code/arcap_policy/STEP2_train_policy/run_pybullet_dp.sh` or set submitter `OUTPUT_DIR=/scratch/prj/eng_demt_robot_learning/trained_models`.
  - Last checked Slurm state after the corrected pipeline: no active `k23114984` jobs.
- 2026-06-30 corrected spatial annulus corridor-entry stress rollout completed on the valid `abla1_full_arcenter` models:
  - User asked to test the concern that a tightly clustered demonstration manifold may reduce generalisation / perturbation robustness for a many-starts-to-fixed-grasp task.
  - Slurm job `35289264` ran on `erc-hpc-comp050` and completed normally: `COMPLETED 0:0`, elapsed `00:11:41`.
  - Command used corrected model root and latest-checkpoint fallback:
    - `--model-root /scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full_arcenter/trained_models`
    - `--experiment-template 'abla1_arcenter_{condition}_d30_seed1_2gap'`
    - `--epoch 999999`
    - `STRESS_INNER_RADIUS=0.25`, `STRESS_RADIUS=0.50`
  - Output directory:
    - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full_arcenter/policy_rollouts_seed628_corridor_stress_r025_050/`
  - Summary JSON:
    - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full_arcenter/policy_rollouts_seed628_corridor_stress_r025_050/summary_corridor_stress_r025_050_seed628_n10.json`
  - Checkpoints used:
    ```text
    P00: model_epoch_40.pth
    P01: model_epoch_100.pth
    P10: model_epoch_40.pth
    P11: model_epoch_80.pth
    ```
  - Corrected annulus stress success rates, seed `628`, `10` rollouts each, horizon `80`:
    ```text
    P00: 2/10 = 0.200
    P01: 1/10 = 0.100
    P10: 2/10 = 0.200
    P11: 1/10 = 0.100
    ```
  - Stress distance statistics were identical across conditions because the same sampled starts were reused:
    ```text
    stress_inner_radius = 0.25
    stress_radius       = 0.50
    d_min/mean/max      = 0.2778 / 0.3620 / 0.4917 m
    all_ge_0.25         = True
    all_le_0.50         = True
    ```
  - Verified corrected stress videos with `imageio`; each has `500` frames, `20 fps`, and `320x320` resolution:
    - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full_arcenter/policy_rollouts_seed628_corridor_stress_r025_050/videos/abla1_corridor_stress_P00_r025_050_seed628_n10.mp4`
    - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full_arcenter/policy_rollouts_seed628_corridor_stress_r025_050/videos/abla1_corridor_stress_P01_r025_050_seed628_n10.mp4`
    - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full_arcenter/policy_rollouts_seed628_corridor_stress_r025_050/videos/abla1_corridor_stress_P10_r025_050_seed628_n10.mp4`
    - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full_arcenter/policy_rollouts_seed628_corridor_stress_r025_050/videos/abla1_corridor_stress_P11_r025_050_seed628_n10.mp4`
  - Interpretation boundary: this is a severe OOD entry-perturbation test outside the `0.25m` training corridor. It supports the user's concern that all policies are weak under large entry perturbations, but it does not show that simply training with wider `corridor_start_radius=0.25` improves robustness; P10/P11 are not better than P00/P01 here.
- 2026-06-29 corrected spatial ABLA1 pipeline completed end-to-end under `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full_arcenter`:
  - Raw collection jobs completed normally: `35264210` P00, `35264211` P10, `35264212` P01, `35264213` P11. Each condition has `30/30` successful demos with `SEED=1`, `SAMPLE_HZ=8`, and no `random_start`.
  - Corrected raw dataset directories:
    - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full_arcenter/abla1_P00_d30_seed1`
    - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full_arcenter/abla1_P10_d30_seed1`
    - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full_arcenter/abla1_P01_d30_seed1`
    - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full_arcenter/abla1_P11_d30_seed1`
  - `scripts/check_abla1_dataset.py` passed for all four corrected raw datasets with expected center `[0.3, 0.0, 0.5]`, expected phase coverage, and no `random_start` metadata/phase. Frame min/mean/max: P00 `95/98.9/103`, P10 `92/100.1/111`, P01 `93/99.0/104`, P11 `90/100.0/111`.
  - Corrected trajectory plots were generated and visually checked:
    - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full_arcenter/trajectory_plots/abla1_P00_ee_xyz_trajectories.png`
    - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full_arcenter/trajectory_plots/abla1_P10_ee_xyz_trajectories.png`
    - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full_arcenter/trajectory_plots/abla1_P01_ee_xyz_trajectories.png`
    - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full_arcenter/trajectory_plots/abla1_P11_ee_xyz_trajectories.png`
  - HDF5 conversion used `scripts/run_abla1_hdf5_slurm.sh` on `interruptible_cpu` as job `35265508`. The files were readable after stdout reached `[INFO] Finished corrected Ablation-1 HDF5 conversion`; the lingering Slurm allocation was canceled after verification. HDF5 outputs:
    - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full_arcenter/abla1_P00_d30_seed1_2gap.hdf5`
    - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full_arcenter/abla1_P01_d30_seed1_2gap.hdf5`
    - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full_arcenter/abla1_P10_d30_seed1_2gap.hdf5`
    - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full_arcenter/abla1_P11_d30_seed1_2gap.hdf5`
  - All four corrected HDF5 files were split with `split_train_val.py --ratio 0.1`; each has `data=60`, `mask/train=54`, `mask/valid=6`, with valid keys `demo_6`, `demo_13`, `demo_18`, `demo_34`, `demo_48`, `demo_59`.
  - First training submission to `/users/k23114984/code/arcap_policy/STEP2_train_policy/trained_models` hit a real `/users` quota failure (`OSError: [Errno 122] Disk quota exceeded`) and was not used. Partial `/users/.../trained_models/abla1_arcenter_*` directories exist but should be treated as failed/partial artifacts.
  - `scripts/submit_abla1_train_pipeline.sh` was updated to default `OUTPUT_DIR` to scratch: `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full_arcenter/trained_models`. `WANDB_DIR`/`WANDB_CACHE_DIR` were also placed under scratch for the successful run.
  - Scratch training jobs `35266567` P00, `35266569` P01, `35266570` P10, and `35266571` P11 completed at Slurm level with `COMPLETED 0:0`. Logs still end with the known `wandb.finish()` / `PrintLogger.isatty` teardown traceback after early stopping and checkpointing.
  - Corrected training run directories:
    - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full_arcenter/trained_models/abla1_arcenter_P00_d30_seed1_2gap/20260629180040`
    - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full_arcenter/trained_models/abla1_arcenter_P01_d30_seed1_2gap/20260629180040`
    - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full_arcenter/trained_models/abla1_arcenter_P10_d30_seed1_2gap/20260629180040`
    - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full_arcenter/trained_models/abla1_arcenter_P11_d30_seed1_2gap/20260629175947`
  - Corrected validation losses parsed from training logs:
    ```text
    P00: stopped epoch 56,  best valid 0.036339 at epoch 15, final 0.044970, latest checkpoint model_epoch_40.pth
    P01: stopped epoch 101, best valid 0.028998 at epoch 60, final 0.041200, latest checkpoint model_epoch_100.pth
    P10: stopped epoch 44,  best valid 0.099341 at epoch 3,  final 0.180095, latest checkpoint model_epoch_40.pth
    P11: stopped epoch 87,  best valid 0.029316 at epoch 46, final 0.047505, latest checkpoint model_epoch_80.pth
    ```
  - Corrected loss plot and summary:
    - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full_arcenter/loss.png`
    - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full_arcenter/training_loss_summary.json`
  - Added `scripts/run_abla1_eval.sh` for corrected latest-checkpoint rollout/video evaluation using `--experiment-template 'abla1_arcenter_{condition}_d30_seed1_2gap'` and `EPOCH=999999` to trigger latest-checkpoint fallback.
  - `examples/eval_abla1_trained_policies.py` was patched so latest-checkpoint fallback sorts `model_epoch_N.pth` numerically instead of lexicographically.
  - Corrected rollout/video eval job `35266572` completed normally. Summary:
    - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full_arcenter/policy_rollouts_seed628_latest/summary_seed628_n10.json`
    ```text
    P00: model_epoch_40.pth,  8/10 = 0.800
    P01: model_epoch_100.pth, 6/10 = 0.600
    P10: model_epoch_40.pth,  7/10 = 0.700
    P11: model_epoch_80.pth,  6/10 = 0.600
    ```
  - Corrected rollout videos were verified readable with `imageio`; each has `500` frames, `20 fps`, and `320x320` resolution:
    - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full_arcenter/policy_rollouts_seed628_latest/videos/abla1_P00_seed628_n10.mp4`
    - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full_arcenter/policy_rollouts_seed628_latest/videos/abla1_P01_seed628_n10.mp4`
    - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full_arcenter/policy_rollouts_seed628_latest/videos/abla1_P10_seed628_n10.mp4`
    - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full_arcenter/policy_rollouts_seed628_latest/videos/abla1_P11_seed628_n10.mp4`
  - `scripts/create_rebuttal_ppt.py` was updated to use corrected spatial summary/plots/loss and to remove the old strong wide-corridor-collapse wording. Regenerated `outputs/demt_rebuttal_mvp_report.pptx`; `python-pptx` check shows `13` slides, and slides 6/7 now report corrected spatial numbers and diagnostics.
  - `squeue -u k23114984` showed no active jobs after the corrected pipeline finished.
- 2026-06-29 critical spatial correction:
  - User identified the true AR guidance `corridor_start` circle center as world `[0.3, 0.0, 0.5]`.
  - User also clarified that there should be no separate `random_start`: the x-z AR corridor-start disk is already on `y=0`, so the demonstration should start directly at sampled `corridor_start`.
  - Existing `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full` raw data used metadata `base_corridor_start ~= [0.3, 0.15, 0.28]` and a `random_start -> corridor_start` motion; therefore its HDF5 files, training losses, rollout videos, corridor-stress runs, and PPT spatial slides must be treated as invalid for the intended spatial ablation.
  - `examples/main_abla_1.py` now uses explicit `DEFAULT_CORRIDOR_START_CENTER = (0.30, 0.0, 0.50)` for the x-z sampling disk.
  - `examples/main_abla_1.py` now resets directly to sampled `corridor_start`, saves the first frame with phase `corridor_start`, then runs `open_gripper -> pre_grasp -> pick_grasp -> close_gripper -> lift`. There is no `random_start` phase or metadata.
  - `scripts/run_abla1_collect.sh` now forwards `CORRIDOR_START_CENTER_X/Y/Z` instead of the deprecated `ENTRY_DX/CORRIDOR_START_Y/ENTRY_DZ`.
  - `scripts/run_abla1_collect.sh` uses Slurm partition `interruptible_cpu`.
  - `scripts/check_abla1_dataset.py` now validates `base_corridor_start == [0.3, 0.0, 0.5]`, `corridor_start_center` if present, `corridor_start == base_corridor_start + corridor_start_delta`, the existing x-z / x-y delta-plane invariants, and rejects any `random_start` metadata or phase.
  - `examples/eval_abla1_trained_policies.py` now evaluates policies from the matching sampled `corridor_start` distribution, not from `random_start`; it supports `--experiment-template` for corrected model names such as `abla1_arcenter_{condition}_d30_seed1_2gap`.
  - Added corrected pipeline helpers:
    - `scripts/create_abla1_hdf5.py`
    - `scripts/run_abla1_hdf5_slurm.sh`
    - `scripts/create_abla1_train_configs.py`
    - `scripts/submit_abla1_train_pipeline.sh`
    - generated configs under `training_config/abla1_arcenter/`
  - Half-run Slurm jobs submitted before removing `random_start` were canceled and must not be used:
    - old pending jobs canceled: `35262203`, `35262204`, `35262205`, `35262206`
    - second half-run jobs canceled: `35262662`, `35262663`, `35262665`, `35262667`
  - The partial data from the second half-run was deleted before the successful corrected recollection above.
  - Local no-random smoke datasets under `/tmp/abla1_norandom_smoke_{P00,P10,P01,P11}` each collected `1/1` successful demo and passed the corrected checker. Frame counts: `P00=99`, `P10=101`, `P01=100`, `P11=102`. Metadata has `base_corridor_start=[0.3,0.0,0.5]`, no `random_start`, and phase order `corridor_start -> open_gripper -> pre_grasp -> pick_grasp -> close_gripper -> lift`.
  - This pending note was superseded by the completed corrected `abla1_full_arcenter` pipeline recorded above.
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
- Current Ablation-1 code state after the 2026-06-29 AR-center/no-random correction:
  - There is no `random_start` for Ablation-1 collection or evaluation.
  - `corridor_start` is sampled as an x-z disk around the AR guidance center:
    ```text
    base_corridor_start = [0.3, 0.0, 0.5]
    corridor_start_delta = [dx, 0, dz]
    corridor_start = base_corridor_start + corridor_start_delta
    ```
  - The simulator resets directly to sampled `corridor_start` before saving the first frame.
  - `pre_grasp` is sampled in x-y around `[cube_x, cube_y, 0.22]` with z fixed:
    ```text
    pre_grasp_delta = [dx, dy, 0]
    ```
  - `examples/main_abla_1.py` exposes `--corridor-start-center-x/y/z`; `scripts/run_abla1_collect.sh` forwards `CORRIDOR_START_CENTER_X/Y/Z`.
- `scripts/check_abla1_dataset.py` checks `corridor_start_delta[1] == 0`, `base_corridor_start == [0.3, 0.0, 0.5]`, and rejects any Ablation-1 `random_start` metadata or phase.
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
  - current corrected version samples initial states from the same `corridor_start` x-z disk used by corrected data collection
  - use `--experiment-template 'abla1_arcenter_{condition}_d30_seed1_2gap'` for corrected retrained models
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
  - No separate `random_start` in Ablation-1.
  - `corridor_start`: x-z disk around AR guidance center `[0.3, 0.0, 0.5]`.
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
  The job completed successfully. `hdf5-35237839.out` ends with `[INFO] Finished orientation MVP HDF5 conversion`; `hdf5-35237839.err` only contains `pybullet build time: Nov 28 2023 23:51:11`.
- Orientation raw-data visualization script was added and run:
  - `examples/plot_orn_mvp_ee_orientation.py`
  - Reads each frame's `ee_pose.txt` as `xyz + quat_xyzw`, plus demo metadata fields such as `orientation_angle_degrees`, `default_quat_xyzw`, and `contact_quat_xyzw`.
  - Plots EE 3D xyz, x-y view, x-z view, EE angle from default quaternion, EE angle error to demo target/contact quaternion, and sampled orientation-angle histogram.
  - Generated plots:
    - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/orn_mvp_full/orientation_plots/orn_mvp_R00_ee_xyz_orientation.png`
    - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/orn_mvp_full/orientation_plots/orn_mvp_R15_ee_xyz_orientation.png`
    - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/orn_mvp_full/orientation_plots/orn_mvp_R30_ee_xyz_orientation.png`
  - `R30` plot was visually inspected and looked sane.
- Orientation HDF5 conversion created:
  - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/orn_mvp_full/orn_mvp_R00_d30_seed1_2gap.hdf5`
  - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/orn_mvp_full/orn_mvp_R15_d30_seed1_2gap.hdf5`
  - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/orn_mvp_full/orn_mvp_R30_d30_seed1_2gap.hdf5`
- All three orientation HDF5 files were split with `/users/k23114984/code/arcap_policy/STEP2_train_policy/robomimic/scripts/split_train_val.py --ratio 0.1`.
  - Each file has `data=60`, `mask/train=54`, `mask/valid=6`.
  - The same HDF5 valid keys were used across all three conditions: `demo_6`, `demo_13`, `demo_18`, `demo_34`, `demo_48`, `demo_59`.
- Training configs were generated locally:
  - `training_config/orn_mvp/orn_mvp_R00.json`
  - `training_config/orn_mvp/orn_mvp_R15.json`
  - `training_config/orn_mvp/orn_mvp_R30.json`
  These point to the expected orientation HDF5 files above and use the existing `/users/k23114984/code/arcap_policy/STEP2_train_policy/robomimic/training_config/sim_test_00.json` as template.
- Orientation training pipeline was submitted with `scripts/submit_orn_mvp_train_pipeline.sh`:
  - `35238575` `orn_R00_dp`
  - `35238576` `orn_R15_dp`
  - `35238577` `orn_R30_dp`
  - Initial queue check showed `R00` running on `erc-hpc-vm043`; `R15` and `R30` were pending on Slurm dependencies.
- User reported orientation training is complete. This was verified from `/users/k23114984/code/arcap_policy/STEP2_train_policy/trained_models` rather than Slurm, because `squeue`/`sacct` were unavailable inside the sandbox.
- Orientation trained model directories:
  - `/users/k23114984/code/arcap_policy/STEP2_train_policy/trained_models/orn_mvp_R00_d30_seed1_2gap/20260628162610`
  - `/users/k23114984/code/arcap_policy/STEP2_train_policy/trained_models/orn_mvp_R15_d30_seed1_2gap/20260628165021`
  - `/users/k23114984/code/arcap_policy/STEP2_train_policy/trained_models/orn_mvp_R30_d30_seed1_2gap/20260628170849`
- Orientation training logs show validation early stopping, not normal max-epoch completion:
  ```text
  R00: stopped at epoch 81, best valid loss 0.030678, final valid loss 0.037462
  R15: stopped at epoch 64, best valid loss 0.056497, final valid loss 0.077684
  R30: stopped at epoch 47, best valid loss 0.090806, final valid loss 0.133987
  ```
- Available orientation checkpoints:
  ```text
  R00: model_epoch_20.pth, model_epoch_40.pth, model_epoch_60.pth, model_epoch_80.pth
  R15: model_epoch_20.pth, model_epoch_40.pth, model_epoch_60.pth
  R30: model_epoch_20.pth, model_epoch_40.pth
  ```
- Each run ended after early stopping with a `wandb.finish()` cleanup error:
  ```text
  AttributeError: 'PrintLogger' object has no attribute 'isatty'
  ```
  Treat this as a logging teardown issue after training/checkpointing, not as evidence that the training itself failed.
- Added uncommitted orientation rollout evaluator and Slurm wrapper:
  - `examples/eval_orn_mvp_trained_policies.py`
  - `scripts/run_orn_mvp_eval.sh`
- Orientation rollout/video evaluation completed as Slurm job `35239777` on `erc-hpc-comp248`:
  ```bash
  sbatch --parsable scripts/run_orn_mvp_eval.sh
  ```
  It uses matching train-condition evaluation distributions:
  - `R00`: fixed 0 deg.
  - `R15`: each rollout samples one full-trajectory orientation within +/-15 deg.
  - `R30`: each rollout samples one full-trajectory orientation within +/-30 deg.
  It evaluates the common checkpoint `model_epoch_40.pth` for all three conditions.
- Orientation rollout success rates, seed `628`, `10` rollouts each, horizon `80`, action gap `2`, CUDA, videos enabled:
  ```text
  R00: 7/10 = 0.700
  R15: 6/10 = 0.600
  R30: 4/10 = 0.400
  ```
- Orientation rollout output summary:
  - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/orn_mvp_full/policy_rollouts_seed628/summary_seed628_n10.json`
  - per-condition JSON files in the same directory.
- Orientation rollout videos were verified readable with `imageio`; each has `500` frames, `20 fps`, and `320x320` resolution:
  - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/orn_mvp_full/policy_rollouts_seed628/videos/orn_mvp_R00_seed628_n10.mp4`
  - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/orn_mvp_full/policy_rollouts_seed628/videos/orn_mvp_R15_seed628_n10.mp4`
  - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/orn_mvp_full/policy_rollouts_seed628/videos/orn_mvp_R30_seed628_n10.mp4`
- Current git status in `/scratch/prj/eng_demt_robot_learning/polymetics_demt` includes:
  ```text
   M handoffs/main-experiments.md
   M handoffs/research_thinking.md
  ?? examples/eval_orn_mvp_trained_policies.py
  ?? examples/eval_time_mvp_trained_policies.py
  ?? examples/main_time_mvp.py
  ?? examples/plot_time_mvp_temporal.py
  ?? scripts/check_time_mvp_dataset.py
  ?? scripts/create_time_mvp_hdf5.py
  ?? scripts/create_time_mvp_train_configs.py
  ?? scripts/run_orn_mvp_eval.sh
  ?? scripts/run_time_mvp_collect.sh
  ?? scripts/run_time_mvp_eval.sh
  ?? scripts/run_time_mvp_hdf5_slurm.sh
  ?? scripts/submit_time_mvp_train_pipeline.sh
  ?? training_config/time_mvp/
  ```
- User approved the next experiment direction as a fuller temporal threshold sweep, not a minimal two-condition timing ablation:
  ```text
  T00: fixed phase timing / most consistent temporal baseline
  T20: moderate phase-duration jitter around +/-20%
  Twide: broad phase-duration variation, preferably tied to [0.5, 2.0] x baseline duration / v_ref
  ```
- PDF facts used for the temporal design:
  - Temporal structure is speed profile and phase timing around task-relevant events.
  - The paper's temporal simulation variant uses phase-wise temporal resampling while preserving spatial path and closing orientation.
  - Appendix Table 5 speed-bar guidance uses relative speed tolerance `[0.5, 2.0] x v_ref`.
  - Appendix B.1 MPSV measures normalized path-progress synchronisation variance; lower MPSV means more consistent speed and phase timing.
- Existing orientation full datasets show that natural frame-count variation is dominated by `random_start -> corridor_start` distance, so a temporal ablation should control path geometry more tightly than the current R00 data if the goal is to isolate timing:
  ```text
  R00 frame counts, 30 demos:
  TOTAL:          min/mean/max/std = 94 / 105.03 / 114 / 5.96
  random_start:   1 / 1.00 / 1 / 0.00
  open_gripper:   6 / 6.00 / 6 / 0.00
  corridor_start: 12 / 22.10 / 31 / 5.93
  pre_grasp:      30 / 31.93 / 34 / 1.00
  pick_grasp:     14 / 14.00 / 14 / 0.00
  close_gripper:  10 / 10.00 / 10 / 0.00
  lift:           20 / 20.00 / 20 / 0.00
  ```
- Added uncommitted Temporal MVP files:
  - `examples/main_time_mvp.py`
  - `examples/plot_time_mvp_temporal.py`
  - `examples/eval_time_mvp_trained_policies.py`
  - `scripts/run_time_mvp_collect.sh`
  - `scripts/check_time_mvp_dataset.py`
  - `scripts/create_time_mvp_hdf5.py`
  - `scripts/run_time_mvp_hdf5_slurm.sh`
  - `scripts/create_time_mvp_train_configs.py`
  - `scripts/submit_time_mvp_train_pipeline.sh`
  - `scripts/run_time_mvp_eval.sh`
  - generated configs under `training_config/time_mvp/`
- Temporal implementation choices:
  - fixed default orientation for all phases.
  - fixed spatial path to isolate timing: `random_start ~= [0.40, 0.0, 0.40]`, `corridor_start_delta=[0,0,0]`, `pre_grasp_delta=[0,0,0]`.
  - `T00`: all phase-duration multipliers exactly `1.0`.
  - `T20`: per-demo phase-duration multipliers sampled uniformly from `[0.8, 1.2]`.
  - `Twide`: per-demo phase-duration multipliers sampled uniformly from `[0.5, 2.0]`.
- Local smoke collection passed for all three Temporal conditions under `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/time_mvp_debug`:
  - `T00`: 1/1, `95` frames, checker passed.
  - `T20`: 1/1, `96` frames, checker passed.
  - `Twide`: 1/1, `130` frames, checker passed.
- Full raw Temporal collection completed with `NUM_DEMOS=30`, `SEED=1`, `SAMPLE_HZ=8`, `MAX_COLLECTION_ATTEMPTS=80`:
  - `35240986` T00: 30/30 successful demos from 30 attempts.
  - `35241005` T20: 30/30 successful demos from 30 attempts.
  - `35241008` Twide: 30/30 successful demos from 30 attempts.
- Full raw Temporal dataset directories:
  - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/time_mvp_full/time_mvp_T00_d30_seed1`
  - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/time_mvp_full/time_mvp_T20_d30_seed1`
  - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/time_mvp_full/time_mvp_Twide_d30_seed1`
- Full raw Temporal checker results:
  ```text
  T00:   frames min/mean/max = 95 / 95.0 / 95, checker passed
  T20:   frames min/mean/max = 81 / 92.8 / 103, checker passed
  Twide: frames min/mean/max = 75 / 115.6 / 151, checker passed
  ```
- Temporal HDF5 conversion completed via Slurm job `35241095`.
  - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/time_mvp_full/time_mvp_T00_d30_seed1_2gap.hdf5`
  - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/time_mvp_full/time_mvp_T20_d30_seed1_2gap.hdf5`
  - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/time_mvp_full/time_mvp_Twide_d30_seed1_2gap.hdf5`
- All three Temporal HDF5 files were split with `/users/k23114984/code/arcap_policy/STEP2_train_policy/robomimic/scripts/split_train_val.py --ratio 0.1`.
  - Each file has `data=60`, `mask/train=54`, `mask/valid=6`.
  - Valid keys are identical across conditions: `demo_6`, `demo_13`, `demo_18`, `demo_34`, `demo_48`, `demo_59`.
- Temporal training configs:
  - `training_config/time_mvp/time_mvp_T00.json`
  - `training_config/time_mvp/time_mvp_T20.json`
  - `training_config/time_mvp/time_mvp_Twide.json`
- Initial Temporal training submitter incorrectly used sequential Slurm dependencies. User explicitly objected and asked to use parallel GPUs. Old pending dependency jobs were canceled:
  - canceled `35241288` T20 dependency job.
  - canceled `35241294` Twide dependency job.
  - `scripts/submit_time_mvp_train_pipeline.sh` was updated to submit all three conditions independently with no dependency.
- Temporal training completed for all three conditions:
  - `35241285` T00 ran on `erc-hpc-comp248`, early-stopped at epoch `287`, best valid loss `0.001597`, final valid loss `0.001774`, then logged the known `wandb.finish()` / `PrintLogger.isatty` teardown traceback after checkpointing.
  - `35241808` T20 ran on `erc-hpc-comp031`, early-stopped at epoch `163`, best valid loss `0.006668`, final valid loss `0.007382`, then logged the same known wandb teardown traceback.
  - `35241809` Twide ran on `erc-hpc-comp036`, early-stopped at epoch `227`, best valid loss `0.007672`, final valid loss `0.008700`, then logged the same known wandb teardown traceback.
- Temporal rollout/video evaluation ran as Slurm job `35242042` with dependency `afterany:35241808:35241809`:
  ```bash
  sbatch --parsable --dependency=afterany:35241808:35241809 scripts/run_time_mvp_eval.sh
  ```
  It used `model_epoch_40.pth` for all three conditions, `seed=628`, `10` rollouts, `horizon=80`, CUDA, videos enabled, and common fixed-start evaluation. It wrote logs to `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/time_mvp_full/logs/eval-35242042.{out,err}` and rollout/video outputs under `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/time_mvp_full/policy_rollouts_seed628/`.
- Temporal rollout success rates from `summary_seed628_n10.json`:
  ```text
  T00:   5/10 = 0.500
  T20:   7/10 = 0.700
  Twide: 7/10 = 0.700
  ```
- Temporal rollout output summary and per-condition JSON files:
  - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/time_mvp_full/policy_rollouts_seed628/summary_seed628_n10.json`
  - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/time_mvp_full/policy_rollouts_seed628/time_mvp_T00_seed628_n10.json`
  - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/time_mvp_full/policy_rollouts_seed628/time_mvp_T20_seed628_n10.json`
  - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/time_mvp_full/policy_rollouts_seed628/time_mvp_Twide_seed628_n10.json`
- Temporal rollout videos were verified readable with `imageio`; each has `500` frames, `20 fps`, and `320x320` resolution:
  - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/time_mvp_full/policy_rollouts_seed628/videos/time_mvp_T00_seed628_n10.mp4`
  - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/time_mvp_full/policy_rollouts_seed628/videos/time_mvp_T20_seed628_n10.mp4`
  - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/time_mvp_full/policy_rollouts_seed628/videos/time_mvp_Twide_seed628_n10.mp4`
- `35242042` stdout reached `Wrote .../summary_seed628_n10.json`, but the Slurm job stayed in `RUNNING` with no new output after all summary/video files were complete and verified. It was canceled manually to release the GPU; `sacct` reported `CANCELLED by 827643` with `ExitCode 0:0`. Treat the cancellation as cleanup after successful output generation, not as failed evaluation.
- Morning re-check on `2026-06-29` confirmed:
  - `squeue -u k23114984` has no active jobs.
  - `summary_seed628_n10.json` is still present and reports `T00=5/10`, `T20=7/10`, `Twide=7/10`.
  - The three Temporal MP4 files are still readable with `imageio` and still report `500` frames, `20 fps`, `320x320`.
- User reran Temporal fixed-start rollout/video evaluation on `2026-06-29` with each condition's latest visible checkpoint instead of the common `model_epoch_40.pth`. The latest-output directory is separate from the old epoch-40 output:
  - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/time_mvp_full/policy_rollouts_seed628_latest/`
  - Slurm job `35251222` (`time_mvp_eval`) completed normally on `erc-hpc-comp038` with `ExitCode 0:0` and elapsed time `00:12:13`.
  - `squeue -u k23114984` showed no active jobs after this check.
  - The eval log records `device=cpu` for all three policies, despite running on a GPU node.
- Latest Temporal fixed-start rollout success rates from `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/time_mvp_full/policy_rollouts_seed628_latest/summary_seed628_n10.json`:
  ```text
  T00:   model_epoch_280.pth, 10/10 = 1.000
  T20:   model_epoch_160.pth,  8/10 = 0.800
  Twide: model_epoch_220.pth,  7/10 = 0.700
  ```
  This is the current Temporal rollout result and is monotonic with increasing timing variation. The older `/policy_rollouts_seed628/` directory still contains the `model_epoch_40.pth` run with `T00=5/10`, `T20=7/10`, `Twide=7/10`.
- Latest Temporal rollout videos were verified readable with `imageio`; each has `500` frames, `20 fps`, and `320x320` resolution:
  - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/time_mvp_full/policy_rollouts_seed628_latest/videos/time_mvp_T00_seed628_n10.mp4`
  - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/time_mvp_full/policy_rollouts_seed628_latest/videos/time_mvp_T20_seed628_n10.mp4`
  - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/time_mvp_full/policy_rollouts_seed628_latest/videos/time_mvp_Twide_seed628_n10.mp4`
- Temporal trained model directories currently visible:
  - `/users/k23114984/code/arcap_policy/STEP2_train_policy/trained_models/time_mvp_T00_d30_seed1_2gap/20260628194339`
  - `/users/k23114984/code/arcap_policy/STEP2_train_policy/trained_models/time_mvp_T20_d30_seed1_2gap/20260628204435`
  - `/users/k23114984/code/arcap_policy/STEP2_train_policy/trained_models/time_mvp_Twide_d30_seed1_2gap/20260628204435`
- Temporal plots were generated and the summary image was visually checked:
  - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/time_mvp_full/temporal_plots/time_mvp_T00_temporal_xyz_phase.png`
  - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/time_mvp_full/temporal_plots/time_mvp_T20_temporal_xyz_phase.png`
  - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/time_mvp_full/temporal_plots/time_mvp_Twide_temporal_xyz_phase.png`
  - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/time_mvp_full/temporal_plots/time_mvp_temporal_summary.png`
  - Detailed plots show `x(t)`, `y(t)`, `z(t)`, phase frame-count distributions, duration multipliers, total frame histograms, and 3D/XY/XZ paths.
- Rebuttal/supervisor-meeting PPT was generated on `2026-06-29`:
  - `outputs/demt_rebuttal_mvp_report.pptx`
  - source generator: `scripts/create_rebuttal_ppt.py`
  - It has `13` slides and embeds the spatial/orientation/temporal rollout summaries and plots.
  - `python-pptx` was installed into `/scratch/users/k23114984/conda/envs/polymetis38` with:
    ```bash
    /scratch/users/k23114984/conda/envs/polymetis38/bin/python -m pip install python-pptx
    ```
  - Local copy command for the user's laptop:
    ```bash
    scp k23114984@erc-hpc-login1.create.kcl.ac.uk:/scratch/prj/eng_demt_robot_learning/polymetics_demt/outputs/demt_rebuttal_mvp_report.pptx .
    ```
- Important rebuttal wording clarification after user questioned the PPT:
  - Do **not** say the MVPs prove `25cm / 15deg / [0.5, 2.0] x v_ref` are exact optimal values.
  - Say the AR parameters implement DEMT-selected structures; the MVPs support the need for these spatial, orientation, and temporal constraints.
  - The MVPs provide structure-level sensitivity evidence, not global threshold optimality.
  - For temporal, `[0.5, 2.0] x v_ref` is a unitless relative speed tolerance around a reference speed; `v_ref` itself has metric speed units. The Temporal MVP's `[0.5, 2.0]` duration multiplier is inspired by broad speed/phase-timing variation, but is not identical to the real AR speed-bar feedback.
- Added and ran a quick ablation-1 corridor-entry stress rollout to test the user's concern that tighter path guidance may improve in-distribution learning but reduce perturbation robustness:
  - Added uncommitted files:
    - `examples/eval_abla1_corridor_stress.py`
    - `scripts/run_abla1_corridor_stress_eval.sh`
  - Slurm job `35257787` completed normally on `erc-hpc-vm048` with `ExitCode 0:0` and elapsed time `00:09:18`.
  - Evaluation starts each rollout by placing the EE at `base_corridor_start + sample_xz_disk(0.50)` on the same corridor-start x-z plane, with fixed `y=0.15`, open gripper, default orientation, fixed cube, and then runs the trained policy closed loop.
  - The sampler rejects physically unhelpful starts below `z=0.04`, above `z=0.70`, or with IK error above `0.025`; all four policies use the same 10 sampled stress starts for fair paired comparison.
  - Output directory:
    - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full/policy_rollouts_seed628_corridor_stress_r050/`
  - Summary JSON:
    - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full/policy_rollouts_seed628_corridor_stress_r050/summary_corridor_stress_r050_seed628_n10.json`
  - Corridor-entry stress success rates, seed `628`, `10` rollouts each, horizon `80`, radius `0.50`, checkpoint `model_epoch_40.pth`:
    ```text
    P00: 2/10 = 0.200
    P01: 4/10 = 0.400
    P10: 0/10 = 0.000
    P11: 1/10 = 0.100
    ```
  - Stress distance statistics were identical across conditions because the same sampled starts were reused:
    ```text
    d_min/mean/max = 0.1398 / 0.3155 / 0.4833 m
    ```
  - Verified stress rollout videos with `imageio`; each has `500` frames, `20 fps`, and `320x320` resolution:
    - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full/policy_rollouts_seed628_corridor_stress_r050/videos/abla1_corridor_stress_P00_r050_seed628_n10.mp4`
    - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full/policy_rollouts_seed628_corridor_stress_r050/videos/abla1_corridor_stress_P01_r050_seed628_n10.mp4`
    - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full/policy_rollouts_seed628_corridor_stress_r050/videos/abla1_corridor_stress_P10_r050_seed628_n10.mp4`
    - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full/policy_rollouts_seed628_corridor_stress_r050/videos/abla1_corridor_stress_P11_r050_seed628_n10.mp4`
  - Interpretation boundary: this is a severe OOD corridor-entry perturbation test, not evidence that `0.50m` should be used for data collection. It supports the user's concern that very tight guidance can be brittle under large entry perturbations, while also showing that simply widening the training corridor to `0.25m` did not improve robustness here because those policies already learned worse.
- User pointed out the full `r=0.50` disk includes samples inside the `0.25m` training radius. The corridor stress evaluator was updated to support annulus sampling via `--stress-inner-radius`; it samples area-uniformly with `r = sqrt(U(r_inner^2, r_outer^2))`.
  - `scripts/run_abla1_corridor_stress_eval.sh` now defaults to `STRESS_INNER_RADIUS=0.25`, `STRESS_RADIUS=0.50`, output directory `policy_rollouts_seed628_corridor_stress_r025_050`, and `interruptible_gpu` with `time=0:30:00`.
  - Attempted partition name `interruptable_gpu` was invalid; actual Slurm partition is `interruptible_gpu`.
  - Old pending GPU job `35258848` was canceled after it sat in `Priority`.
  - Annulus Slurm job `35258966` completed normally on `erc-hpc-comp222` with `ExitCode 0:0` and elapsed time `00:08:15`.
  - Summary JSON:
    - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full/policy_rollouts_seed628_corridor_stress_r025_050/summary_corridor_stress_r025_050_seed628_n10.json`
  - Verified the sampled stress distances are all outside the `0.25m` region:
    ```text
    stress_inner_radius = 0.25
    stress_radius       = 0.50
    d_min/mean/max      = 0.2778 / 0.3587 / 0.4876 m
    all_ge_0.25         = True
    ```
  - Annulus corridor-entry stress success rates, seed `628`, `10` rollouts each, horizon `80`, checkpoint `model_epoch_40.pth`:
    ```text
    P00: 3/10 = 0.300
    P01: 2/10 = 0.200
    P10: 0/10 = 0.000
    P11: 0/10 = 0.000
    ```
  - Verified annulus stress videos with `imageio`; each has `500` frames, `20 fps`, and `320x320` resolution:
    - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full/policy_rollouts_seed628_corridor_stress_r025_050/videos/abla1_corridor_stress_P00_r025_050_seed628_n10.mp4`
    - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full/policy_rollouts_seed628_corridor_stress_r025_050/videos/abla1_corridor_stress_P01_r025_050_seed628_n10.mp4`
    - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full/policy_rollouts_seed628_corridor_stress_r025_050/videos/abla1_corridor_stress_P10_r025_050_seed628_n10.mp4`
    - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full/policy_rollouts_seed628_corridor_stress_r025_050/videos/abla1_corridor_stress_P11_r025_050_seed628_n10.mp4`
  - Current interpretation: even when evaluating only outside the `0.25m` corridor, the policies trained with `corridor_start_radius=0.25` do not show improved OOD robustness; both `P10` and `P11` are `0/10`. This strengthens the conclusion that simply widening the successful-demo approach distribution degrades learnability and does not automatically create recovery behavior.

## What Worked
- The corrected `abla1_full_arcenter` pipeline now works end-to-end when model outputs and wandb cache are kept under scratch instead of `/users`.
- The corrected checker is doing useful protection work: it rejects any `random_start` metadata/phase and validates the AR center `[0.3, 0.0, 0.5]`.
- `scripts/run_abla1_eval.sh` successfully evaluates the corrected scratch-trained models and writes latest-checkpoint rollout summaries/videos to `dataset/abla1_full_arcenter/policy_rollouts_seed628_latest/`.
- Numeric checkpoint sorting in `examples/eval_abla1_trained_policies.py` is necessary for latest-checkpoint fallback; otherwise `model_epoch_80.pth` can sort after/before the wrong epoch lexicographically.
- Corrected spatial PPT regeneration works with `scripts/create_rebuttal_ppt.py`; the current deck has 13 slides and uses `abla1_full_arcenter` for spatial result files.
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
- `scripts/check_abla1_dataset.py` now checks corrected ABLA1 invariants:
  - no `random_start` metadata or phase
  - `base_corridor_start == [0.3, 0.0, 0.5]`
  - `corridor_start == base_corridor_start + corridor_start_delta`
  - `corridor_start_delta[1] == 0`
  - `pre_grasp_delta[2] == 0`
- Historical only: old HDF5 conversion job `35225365` finished successfully for the now-invalid `/dataset/abla1_full` run. Do not cite those old HDF5/loss/rollout outputs.
- `split_train_val.py` worked directly with `/scratch/users/k23114984/conda/arcap/bin/python`; no Slurm job was needed for splitting.
- The training script supports `--name`, `--dataset`, and `--output` overrides, so the four condition jobs can share base configs while using unique experiment names.
- The corrected loss plot no longer supports the old strong clean-factorial rollout story. It does show `P10` validation loss is much worse, while `P00/P01/P11` have similar low best validation loss.
- `examples/eval_abla1_trained_policies.py` can evaluate all four trained policies directly in PyBullet using robomimic `policy_from_checkpoint`.
- For this robomimic diffusion-policy fork, rollout observations must include the time dimension `[T, ...]`; with `observation_horizon=7`, the script maintains a 7-frame observation history.
- Video capture works by writing PyBullet RGB frames with `imageio.get_writer(...).append_data(...)`, similar to `/scratch/prj/eng_demt_robot_learning/libero_demt/scripts/visualize_dataset_demo.py`.
- Keep the policy point-cloud camera at the original `200x200` dimensions / intrinsics and render videos separately at `320x320`; changing `sim.image_width` / `sim.image_height` after init can break pointcloud cropping.
- Corrected rollout/video results are mixed (`P00/P01/P10/P11 = 8/10, 6/10, 7/10, 6/10`), so use corrected spatial evidence conservatively.
- Orientation MVP raw collection works locally and on HPC with the stricter baseline `corridor_start_radius=0.05`, `pre_grasp_radius=0.0`.
- `examples/main_orn_mvp.py` correctly samples one quaternion per demo and uses it for full-trajectory IK / motion, including `random_start`, `corridor_start`, `pre_grasp`, `pick_grasp`, and `lift`.
- `scripts/check_orn_mvp_dataset.py` verifies orientation conditions, full-phase orientation metadata, `corridor_start_radius=0.05`, `pre_grasp_radius=0.0`, `random_start y=0`, `corridor_start_y=0.15`, phase coverage, and successful final cube lift.
- `examples/plot_orn_mvp_ee_orientation.py` successfully generated per-condition orientation plots for `R00/R15/R30`. It computes quaternion angular distance using `abs(dot(q1, q2))`, so `q` and `-q` are treated as the same rotation.
- Orientation training produced the expected monotonic validation-loss ordering: `R00` best, `R15` intermediate, `R30` worst. This supports the angle-tolerance hypothesis at the training-loss level, pending rollout evaluation.
- Orientation rollout success also follows the expected monotonic ordering under matching train-condition evaluation: `R00` best, `R15` intermediate, `R30` worst.
- The next temporal sweep should reuse the stronger orientation baseline geometry (`corridor_start_radius=0.05`, `pre_grasp_radius=0.0`, default orientation) rather than old `P00`, because old `P00` policy rollout was only around `40-60%`.
- `examples/main_abla_1.py` already supports explicit `duration` in `move_ee()`, so a temporal generator can vary phase timing without changing the IK target path.
- Temporal data collection, checking, HDF5 conversion, split, and plotting all worked with the fixed-path design. The resulting frame-count spread is clean: `T00` fixed at 95 frames, `T20` moderately variable, and `Twide` visibly broad.
- `examples/plot_time_mvp_temporal.py` produces useful Temporal diagnostics: `x(t)`, `y(t)`, `z(t)`, phase frame counts, duration multipliers, total frames, 3D/XY/XZ paths, and a cross-condition summary including normalized path progress.
- For Temporal training, submit conditions in parallel. The user explicitly rejected sequential dependencies because the school GPU cluster has enough nodes.
- Temporal training finished cleanly at the training/checkpoint level for `T00/T20/Twide` via validation early stopping; the repeated `wandb.finish()` / `PrintLogger.isatty` traceback is a teardown issue after checkpointing.
- Temporal rollout/video evaluation ran end-to-end and produced readable videos plus JSON summaries. The initial fixed-start `model_epoch_40` evaluation produced `T00=0.500`, `T20=0.700`, `Twide=0.700`; the later latest-checkpoint fixed-start evaluation produced the cleaner monotonic result `T00=1.000`, `T20=0.800`, `Twide=0.700`.

## What Didn't Work
- Writing corrected ABLA1 training runs to `/users/k23114984/code/arcap_policy/STEP2_train_policy/trained_models` failed with a real `OSError: [Errno 122] Disk quota exceeded`. Keep future high-volume training outputs, wandb cache, and generated artifacts on `/scratch/prj/...`.
- Do not assume `/scratch/prj/eng_demt_robot_learning/trained_models/abla1_arcenter_*` is the corrected final ABLA1 model root just because it exists. As of 2026-06-30, those top-level corrected-arcenter directories are the earlier partial `20260629173956` attempt; the corrected rollout used the dataset-local scratch checkpoints under `polymetics_demt/dataset/abla1_full_arcenter/trained_models`.
- Login shells now often print `/users/k23114984` quota-cache `OSError: [Errno 122] Disk quota exceeded` tracebacks. These are noisy and most scratch/Slurm commands still work, but they should not be ignored for any workflow that writes under `/users`.
- Corrected HDF5 job `35265508` wrote readable complete HDF5 files but left the Slurm allocation running after stdout reached the finished message; it was canceled only after verifying all four HDF5 files with `h5py`.
- Do not use the partial `/users/.../trained_models/abla1_arcenter_*` runs from the failed quota attempt; use scratch trained models under `dataset/abla1_full_arcenter/trained_models`.
- The original ablation plan/code used x-z sampling for both `corridor_start` and `pre_grasp`. This made `pre_grasp` z vary and was wrong for the user's intended geometry.
- A previous assistant correction mistakenly changed `random_start` to x-y/fixed-z. The user rejected this during the older geometry design; for corrected ABLA1 there is no `random_start` at all.
- The old `N=30, seed=1` datasets passed the old checker but were invalid for training; the user reported val loss explosion and then requested deleting all dataset contents.
- The latest completed old debug collection passed the old checker, but the user said "还是不对" because `corridor_start` used `y=cube_y`. That intermediate `corridor_start_y=0.15` fix was later superseded by the true AR center `[0.3, 0.0, 0.5]` and no-random-start design.
- `conda run -n polymetis38` can fail due to env lookup/location issues. Prefer the absolute python:
  ```bash
  /scratch/users/k23114984/conda/envs/polymetis38/bin/python
  ```
- Running `sbatch`/`squeue` inside the default sandbox fails or is unreliable; use escalation.
- HPC shell startup prints quota/slurm credit tracebacks in command output. Some are noisy, but the `/users` disk quota error is real for writes under `/users`; prefer scratch for generated outputs.
- `sbatch` can create a job even if the client-side command times out while waiting for a response. Always check `squeue` before retrying, to avoid duplicate submissions.
- Do not infer final deployment performance from validation loss alone. The current loss plot is useful for diagnosis, but rollout success rate should be checked before writing the final rebuttal claim.
- The current `docs/ablation-1.md` still contains stale planned assumptions in places, including fixed-height x-y random-start wording and `corridor_start` y tied to object/cube y. Treat the implemented code and approved plots as authoritative until the doc is cleaned up.
- Early rollout script attempt passed a single-frame observation and failed with `AssertionError` because the diffusion policy expected `[B, T, ...]` observations.
- A second rollout attempt used `T=1` and failed with `RuntimeError: mat1 and mat2 shapes cannot be multiplied (1x328 and 760x512)`; the model requires the full `observation_horizon=7`.
- First video attempt changed `sim.image_width` / `sim.image_height` to `320`, but `camera_intrinsic` remained from `200x200`; pointcloud cropping later became empty and raised `RuntimeError: Cropped point cloud is empty.` The fix was to render video frames via a separate `pb.getCameraImage(width, height, ...)` path without changing the policy pointcloud camera dimensions.
- Video rollouts can produce slightly different success counts from pure rollouts because inference is rerun; do not mix success-rate numbers without noting which run produced them.
- Do not use the old `P00` spatial condition as the orientation baseline. The user rejected it because trained policy rollout success was only around `40-60%`. Use `corridor_start_radius=0.05` and `pre_grasp_radius=0.0`.
- Do not switch orientation only near grasp/contact unless the user changes direction again. The current accepted MVP is one sampled gripper orientation per demo, applied for the whole trajectory.
- HDF5 job `35237839` was briefly considered for cancellation after staying pending, but the user interrupted and explicitly said to let it continue. It later completed successfully.
- All three orientation training runs ended with a `wandb.finish()` cleanup traceback after validation early stopping. Do not confuse this with a failed training run; checkpoints and logs were already written.
- Do not implement the temporal ablation by simply changing `sample_hz`; that changes observation density globally, not phase timing structure.
- Do not let random-start distance dominate the temporal condition. For `T00/T20/Twide`, keep spatial path and orientation fixed or tightly controlled, then vary only phase durations / phase sample counts.
- Do not submit Temporal training as a dependency chain. An earlier version of `scripts/submit_time_mvp_train_pipeline.sh` did that, creating pending jobs `35241288` and `35241294`; those were canceled and resubmitted in parallel as `35241808` and `35241809`.
- T00 Temporal training also ended with the same `wandb.finish()` / `PrintLogger.isatty` traceback seen in orientation training. Treat this as logging teardown after training/checkpointing unless checkpoints are missing.
- Temporal evaluation job `35242042` remained running after writing the summary and all videos. After verifying JSON and MP4 files, it was canceled to release the GPU; do not interpret the final Slurm `CANCELLED` state as a failed rollout run.
- Do not cite `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/time_mvp_full/policy_rollouts_seed628/` as the current Temporal latest-checkpoint result. That directory is the older `model_epoch_40.pth` run. Use `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/time_mvp_full/policy_rollouts_seed628_latest/` for the current latest-checkpoint rollout/videos.

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
- Corrected ABLA1 rollout Slurm wrapper:
  - `scripts/run_abla1_eval.sh`
- Slurm wrapper:
  - `scripts/run_abla1_collect.sh`
- HDF5 converter:
  - `scripts/create_abla1_hdf5.py`
- HDF5 conversion Slurm wrapper:
  - `scripts/run_abla1_hdf5_slurm.sh`
- Training configs:
  - `training_config/abla1_arcenter/abla1_arcenter_P00.json`
  - `training_config/abla1_arcenter/abla1_arcenter_P01.json`
  - `training_config/abla1_arcenter/abla1_arcenter_P10.json`
  - `training_config/abla1_arcenter/abla1_arcenter_P11.json`
- Training Slurm wrapper:
  - `STEP2_train_policy/run_pybullet_dp.sh`
- Training pipeline submitter:
  - `scripts/submit_abla1_train_pipeline.sh`
- Corrected ABLA1 output root and current artifacts:
  - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full_arcenter/`
  - raw data: `abla1_{P00,P01,P10,P11}_d30_seed1`
  - HDF5: `abla1_{P00,P01,P10,P11}_d30_seed1_2gap.hdf5`
  - scratch trained models: `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full_arcenter/trained_models/abla1_arcenter_{P00,P01,P10,P11}_d30_seed1_2gap/`
  - corrected rollout summary: `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full_arcenter/policy_rollouts_seed628_latest/summary_seed628_n10.json`
  - corrected rollout videos: `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full_arcenter/policy_rollouts_seed628_latest/videos/`
  - corrected validation-loss plot: `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full_arcenter/loss.png`
  - corrected trajectory plots: `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full_arcenter/trajectory_plots/`
- Preferred shared model root for future training:
  - `/scratch/prj/eng_demt_robot_learning/trained_models`
  - For corrected ABLA1, copy or rerun into this root before using it as the rollout `--model-root`; the current final corrected ABLA1 rollout used dataset-local checkpoints under `dataset/abla1_full_arcenter/trained_models`.
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
- Orientation MVP trained-policy evaluator and Slurm wrapper:
  - `examples/eval_orn_mvp_trained_policies.py`
  - `scripts/run_orn_mvp_eval.sh`
- Temporal MVP files:
  - `examples/main_time_mvp.py`
  - `examples/plot_time_mvp_temporal.py`
  - `scripts/run_time_mvp_collect.sh`
  - `scripts/check_time_mvp_dataset.py`
  - `scripts/create_time_mvp_hdf5.py`
  - `scripts/run_time_mvp_hdf5_slurm.sh`
  - `scripts/create_time_mvp_train_configs.py`
  - `scripts/submit_time_mvp_train_pipeline.sh`
  - `examples/eval_time_mvp_trained_policies.py`
  - `scripts/run_time_mvp_eval.sh`
- Temporal MVP training configs:
  - `training_config/time_mvp/time_mvp_T00.json`
  - `training_config/time_mvp/time_mvp_T20.json`
  - `training_config/time_mvp/time_mvp_Twide.json`
- Latest Temporal rollout summary and videos:
  - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/time_mvp_full/policy_rollouts_seed628_latest/summary_seed628_n10.json`
  - `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/time_mvp_full/policy_rollouts_seed628_latest/videos/`
  - Slurm logs: `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/time_mvp_full/logs/eval-35251222.out` and `.err`
- Rebuttal meeting PPT:
  - `outputs/demt_rebuttal_mvp_report.pptx`
  - generator: `scripts/create_rebuttal_ppt.py`
  - regenerate with:
    ```bash
    /scratch/users/k23114984/conda/envs/polymetis38/bin/python scripts/create_rebuttal_ppt.py
    ```
  - copy to local machine with:
    ```bash
    scp k23114984@erc-hpc-login1.create.kcl.ac.uk:/scratch/prj/eng_demt_robot_learning/polymetics_demt/outputs/demt_rebuttal_mvp_report.pptx .
    ```
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
    OUTPUT_ROOT=/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full_arcenter_debug \
    MAX_COLLECTION_ATTEMPTS=3 \
    sbatch scripts/run_abla1_collect.sh
  done
  ```
- Submit corrected full raw collection:
  ```bash
  for cond in P00 P10 P01 P11; do
    CONDITION=${cond} \
    NUM_DEMOS=30 \
    SEED=1 \
    SAMPLE_HZ=8 \
    OUTPUT_ROOT=/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full_arcenter \
    MAX_COLLECTION_ATTEMPTS=80 \
    sbatch scripts/run_abla1_collect.sh
  done
  ```
- Check converted HDF5 split masks:
  ```bash
  /scratch/users/k23114984/conda/arcap/bin/python - <<'PY'
  import h5py
  from pathlib import Path
  root = Path('/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full_arcenter')
  for name in ['P00', 'P01', 'P10', 'P11']:
      path = root / f'abla1_{name}_d30_seed1_2gap.hdf5'
      with h5py.File(path, 'r') as f:
          print(path.name, len(f['data']), len(f['mask/train']), len(f['mask/valid']))
  PY
  ```
- Submit training pipeline:
  ```bash
  WANDB_MODE=disabled \
  WANDB_DIR=/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full_arcenter/wandb \
  WANDB_CACHE_DIR=/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full_arcenter/wandb/cache \
  scripts/submit_abla1_train_pipeline.sh
  ```
- Check current training queue:
  ```bash
  squeue -u k23114984 -o "%.18i %.16P %.30j %.8u %.2t %.10M %.6D %R"
  ```
- Inspect the completed training loss plot:
  ```bash
  python - <<'PY'
  from pathlib import Path
  print(Path('/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full_arcenter/loss.png'))
  PY
  ```
- Re-check HDF5 valid keys:
  ```bash
  /scratch/users/k23114984/conda/arcap/bin/python - <<'PY'
  import h5py
  from pathlib import Path
  root = Path('/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full_arcenter')
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
  root = Path('/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full_arcenter')
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
  sbatch --job-name=abla1c_P00_dp \
    /users/k23114984/code/arcap_policy/STEP2_train_policy/run_pybullet_dp.sh \
    --config /scratch/prj/eng_demt_robot_learning/polymetics_demt/training_config/abla1_arcenter/abla1_arcenter_P00.json \
    --name abla1_arcenter_P00_d30_seed1_2gap \
    --output /scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full_arcenter/trained_models
  ```
- Run corrected latest-checkpoint rollout/video evaluation via Slurm:
  ```bash
  sbatch --parsable scripts/run_abla1_eval.sh
  ```
- Run corrected latest-checkpoint rollout/video evaluation directly:
  ```bash
  /scratch/users/k23114984/conda/arcap/bin/python -u examples/eval_abla1_trained_policies.py \
    --model-root /scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full_arcenter/trained_models \
    --conditions P00 P01 P10 P11 \
    --experiment-template 'abla1_arcenter_{condition}_d30_seed1_2gap' \
    --epoch 999999 \
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
    --output-dir /scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full_arcenter/policy_rollouts_seed628_latest \
    --video-dir /scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full_arcenter/policy_rollouts_seed628_latest/videos
  ```
- Verify video files:
  ```bash
  /scratch/users/k23114984/conda/arcap/bin/python - <<'PY'
  from pathlib import Path
  import imageio.v2 as imageio
  root = Path('/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/abla1_full_arcenter/policy_rollouts_seed628_latest/videos')
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
- Inspect orientation training logs:
  ```bash
  tail -n 80 /users/k23114984/code/arcap_policy/STEP2_train_policy/trained_models/orn_mvp_R00_d30_seed1_2gap/20260628162610/logs/log.txt
  tail -n 80 /users/k23114984/code/arcap_policy/STEP2_train_policy/trained_models/orn_mvp_R15_d30_seed1_2gap/20260628165021/logs/log.txt
  tail -n 80 /users/k23114984/code/arcap_policy/STEP2_train_policy/trained_models/orn_mvp_R30_d30_seed1_2gap/20260628170849/logs/log.txt
  ```
- Run orientation rollout evaluation with videos:
  ```bash
  sbatch --parsable scripts/run_orn_mvp_eval.sh
  ```
- Re-run orientation rollout evaluation directly:
  ```bash
  /scratch/users/k23114984/conda/arcap/bin/python -u examples/eval_orn_mvp_trained_policies.py \
    --conditions R00 R15 R30 \
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
    --output-dir /scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/orn_mvp_full/policy_rollouts_seed628 \
    --video-dir /scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/orn_mvp_full/policy_rollouts_seed628/videos
  ```
- Verify orientation rollout videos:
  ```bash
  /scratch/users/k23114984/conda/arcap/bin/python - <<'PY'
  from pathlib import Path
  import imageio.v2 as imageio
  root = Path('/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/orn_mvp_full/policy_rollouts_seed628/videos')
  for p in sorted(root.glob('orn_mvp_R*_seed628_n10.mp4')):
      reader = imageio.get_reader(str(p))
      meta = reader.get_meta_data()
      n = reader.count_frames()
      reader.close()
      print(p.name, p.stat().st_size, n, meta.get('fps'), meta.get('size'))
  PY
  ```

## Next Steps
1. Review the regenerated PPT `outputs/demt_rebuttal_mvp_report.pptx`; spatial slides now use corrected `abla1_full_arcenter` results and avoid the old strong wide-corridor-collapse claim.
2. Corrected-arcenter corridor-stress rollout is now complete under `dataset/abla1_full_arcenter/policy_rollouts_seed628_corridor_stress_r025_050/`. The older corridor-stress results under `dataset/abla1_full/` are tied to the invalid old spatial run and should not be cited.
3. If a stronger spatial story is needed, consider an intermediate `corridor_start_radius=0.15` or a larger-rollout-count rerun; do not overinterpret the current `n=10` mixed rollout result.
4. If centralizing model outputs, move/copy the successful corrected ABLA1 dataset-local checkpoints into `/scratch/prj/eng_demt_robot_learning/trained_models` and verify rollout `--model-root` before reusing them.
5. Clean up or archive partial `/users/.../trained_models/abla1_arcenter_*` and partial top-level `trained_models/abla1_arcenter_*` runs from the failed quota attempt if disk pressure or ambiguous checkpoint selection blocks later work.
6. Update `docs/ablation-1.md` if it will be used externally; it may still contain stale geometry assumptions from earlier iterations.

## Open Questions
- Should the next experiment add `corridor_start_radius=0.15` to locate the degradation threshold between `0.10` and `0.25`?
- Should `P10/P11` be rerun with more than 30 raw demos if rollout confirms poor performance?
- Should the plotter show sampled waypoints (`random_start`, `corridor_start`, `pre_grasp`, `grasp`, `lift`) explicitly overlaid, instead of only the EE trajectory?
- Should final reported rollout success rates use one deterministic rerun after the torch seed patch, and should that rerun be saved to a non-overwriting output directory?
- Should corridor-stress evaluation use more than `n=10` rollouts or additional stress radii if this robustness story becomes central? The corrected `0.25-0.50m` annulus run is complete but small.
- For orientation rollout evaluation, should deployment initial orientation be fixed/default for all policies, sampled from the matching train condition, or evaluated under a common stress distribution?
- Should Temporal rollout evaluation add a stress distribution, or is the latest fixed-start checkpoint comparison (`T00=1.000`, `T20=0.800`, `Twide=0.700`) sufficient for the rebuttal?
- What exact rebuttal wording does the supervisor prefer: "task-specific implementation choices with sensitivity evidence" vs. a stronger claim about parameter motivation?

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
- 2026-06-28: Updated handoff after orientation HDF5 conversion completed, splitting all R00/R15/R30 HDF5 files into 54 train / 6 valid demos, and submitting sequential training jobs `35238575 -> 35238576 -> 35238577`.
- 2026-06-28: Updated handoff to reflect the user's instruction to stop active work and wait while the orientation training jobs run.
- 2026-06-28: Updated handoff after user reported orientation training completion; verified trained model directories/checkpoints/logs and recorded early-stopping validation losses for R00/R15/R30.
- 2026-06-28: Updated handoff after adding orientation trained-policy rollout/video evaluator, running Slurm job `35239777`, recording R00/R15/R30 success rates, and verifying generated MP4 videos.
- 2026-06-28: Updated next direction to the user-approved temporal threshold sweep `T00/T20/Twide`, including PDF temporal rationale, baseline phase-count stats, planned files, and execution steps.
- 2026-06-28: Updated handoff after implementing and running the Temporal MVP pipeline through raw collection, validation, HDF5 conversion, train/valid split, temporal plots, and parallel training submission; T20/Twide remain running.
- 2026-06-28: Updated handoff after checking T20/Twide were still running and pre-submitting Temporal rollout/video evaluation job `35242042` with `afterany` dependency on both remaining training jobs.
- 2026-06-28: Updated handoff with latest Temporal training progress: T20 around epoch 97 and Twide around epoch 104, both still running, with eval job `35242042` still pending on dependency.
- 2026-06-28: Updated handoff with latest Temporal training progress: T20 around epoch 118 and still improving, Twide around epoch 127 with 24 no-improvement epochs, and eval job `35242042` still pending on dependency.
- 2026-06-28: Updated handoff after T20/Twide training completed, Temporal rollout/video evaluation produced `T00=5/10`, `T20=7/10`, `Twide=7/10`, MP4 videos were verified, and eval job `35242042` was canceled only after outputs were complete to release the GPU.
- 2026-06-29: Updated handoff after morning verification that no Slurm jobs remain, Temporal summary JSON still reports `T00=5/10`, `T20=7/10`, `Twide=7/10`, and all three MP4 videos remain readable.
- 2026-06-29: Updated handoff after checking the user's latest Temporal checkpoint rollout/video rerun: job `35251222` completed normally, `policy_rollouts_seed628_latest` reports `T00=10/10`, `T20=8/10`, `Twide=7/10`, and all three latest MP4 files are readable.
- 2026-06-29: Updated handoff after creating the supervisor-meeting rebuttal PPT, installing `python-pptx` in `polymetis38`, documenting the local `scp` command, and clarifying that MVPs support structure-level constraints rather than exact numeric parameter optimality.
- 2026-06-29: Updated handoff after canceling/deleting partial corrected spatial data, removing the extra `random_start` segment from Ablation-1 collection/evaluation, validating no-random smokes for P00/P10/P01/P11, and recording the corrected no-random spatial pipeline.
- 2026-06-29: Updated handoff after completing corrected `abla1_full_arcenter` raw collection, checks, plots, HDF5 conversion, split, scratch training, latest-checkpoint rollout/video evaluation, corrected loss plot, and regenerated PPT.
- 2026-06-30: Updated handoff for fresh-context restart after the user moved shared `trained_models` and Codex state to scratch; recorded the distinction between final dataset-local corrected ABLA1 checkpoints and partial top-level corrected-arcenter runs.
- 2026-06-30: Updated handoff after running corrected `abla1_full_arcenter` annulus corridor-entry stress evaluation with `0.25 <= d <= 0.50m`, recording low success rates, verified stress distances, videos, and Slurm completion.
