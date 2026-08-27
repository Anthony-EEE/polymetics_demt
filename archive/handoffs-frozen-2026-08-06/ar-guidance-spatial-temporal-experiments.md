# Handoff: AR Guidance Spatial and Temporal Experiments

_Last updated: 2026-07-04 12:55 BST · Branch: hpc-headless-data-collection @ 73d56df_

## Goal
Start a fresh engineering run for the new AR-guidance experiments. This handoff
is standalone. The next agent should follow the original Week 1 engineering
pipeline end to end:

```text
collect raw demos -> visualize trajectories -> convert to HDF5 -> split
train/valid -> train diffusion-policy models on GPU -> rollout compare
```

Run two new experiment tracks:

```text
Spatial:  S15 / S20 / S25 / S30 / S35
Temporal: T00 / T25 / T50 / T75 / T100
```

Do not run a new orientation/degree experiment now. Week 1 `R00/R15/R30` is
enough for the current decision.

## Current Progress
- Latest user-requested spatial shared-r35 rerollout is complete.
  `examples/eval_abla1_trained_policies.py` now supports a shared start
  manifest path and all S conditions read the exact same absolute
  `corridor_start` points sampled with `--shared-start-radius 0.35`. The
  recorded eval distribution is:
  ```text
  paired_shared_absolute_corridor_starts_r35
  ```
- Final shared-r35 output root:
  ```text
  /scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/ar_guidance_spatial_S15_S35/policy_rollouts_seed628_shared_r35_parallel
  ```
  It contains five per-condition JSON files, five videos, the shared start
  manifest, and `summary_seed628_n10.json`. Final success rates:
  ```text
  S15: 6/10 = 0.600
  S20: 3/10 = 0.300
  S25: 4/10 = 0.400
  S30: 1/10 = 0.100
  S35: 2/10 = 0.200
  ```
  Verification passed: all per-condition JSONs have
  `paired_shared_absolute_corridor_starts_r35`, all five conditions have
  identical absolute `corridor_start` lists, and the aggregate summary records
  `shared_start_radius = 0.35` with 10 starts.
- Completed shared-r35 Slurm chain:
  ```text
  manifest generation: 35403550
  rollout array:       35403922 (tasks 0-4 = S15/S20/S25/S30/S35)
  merge summary:       35403923
  ```
  `35403922_0` wrote S15, `35403922_1` wrote S20, `35403922_2` wrote S25,
  `35403922_3` wrote S30, and `35403922_4` wrote S35. `35403923` loaded the
  shared manifest and wrote the final aggregate summary.
- Earlier shared-r35 rerollout attempt `35403050` was submitted with:
  ```bash
  OUTPUT_DIR=/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/ar_guidance_spatial_S15_S35/policy_rollouts_seed628_shared_r35 \
  VIDEO_DIR=/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/ar_guidance_spatial_S15_S35/policy_rollouts_seed628_shared_r35/videos \
  sbatch scripts/run_abla1_eval.sh --shared-start-radius 0.35
  ```
  That job was a single sequential eval job: `scripts/run_abla1_eval.sh`
  requests `--ntasks=1`, `--gres=gpu:1`, and runs one Python process that loops
  over `S15 S20 S25 S30 S35`. It was not a Slurm array and did not parallelize
  the five conditions.
- Job `35403050` used `#SBATCH --partition=gpu`, not `interruptible_gpu`. Per
  user preference, future rollout and data-collection submissions should use
  `interruptible_gpu` or `interruptible_cpu` rather than plain `gpu` or `cpu`.
- Per user request, job `35403050` was cancelled. Verified Slurm state:
  ```text
  35403050|abla1_eval|CANCELLED by 827643|0:0|00:03:15|2026-07-04T12:02:10|2026-07-04T12:05:25
  ```
  `squeue -u k23114984` was empty after cancellation. The cancelled job ran
  briefly and produced only this partial file:
  ```text
  /scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/ar_guidance_spatial_S15_S35/policy_rollouts_seed628_shared_r35/videos/spatial_S15_seed628_n10.mp4
  ```
  No complete JSON or aggregate summary was produced for the shared-r35 rerun.
- During the completed rerun, an intermediate plain-`gpu` probe was tried and
  then cancelled after it remained pending while the restored interruptible
  main chain was already running. Cancelled duplicate/probe jobs:
  ```text
  35403562, 35403563, 35403812, 35403832, 35403931, 35403934
  ```
  Do not treat any output under `policy_rollouts_seed628_shared_r35_parallel_gpu`
  as final; it was only a probe path.
- Code plumbing is patched for the new condition names and roots. Key changed
  files include `examples/main_abla_1.py`, `examples/main_time_mvp.py`,
  `scripts/run_*collect.sh`, HDF5/config/eval scripts, checkers, plotters, and
  generated configs under:
  ```text
  training_config/ar_guidance_spatial_S15_S35
  training_config/ar_guidance_temporal_T00_T100
  ```
- Temporal T100 now records a positive duration rule in metadata:
  ```text
  min_phase_duration_frames = 1
  min_phase_duration_seconds = 1 / sample_hz
  phase_duration_clamp_rule = target_phase_duration_seconds = max(raw_duration_seconds, min_phase_duration_frames / sample_hz)
  ```
- Smoke collection passed for all S and T conditions. The first temporal smoke
  attempt failed because `TimeMvpSim` called missing
  `sample_reachable_random_start`; fixed by adding the helper to `PandaSim`,
  then reran temporal smoke as `*_smoke_retry1`.
- Full raw collection completed successfully:
  ```text
  spatial jobs:  35393088 S15, 35393089 S20, 35393090 S25, 35393091 S30, 35393092 S35
  temporal jobs: 35393093 T00, 35393094 T25, 35393095 T50, 35393096 T75, 35393097 T100
  ```
  Each full raw group has 30 demos.
- Full dataset checks and plots completed through dependent jobs:
  ```text
  spatial postcheck:  35393215
  temporal postcheck: 35393216
  ```
  Plot outputs:
  ```text
  dataset/ar_guidance_spatial_S15_S35/trajectory_plots
  dataset/ar_guidance_temporal_T00_T100/temporal_plots
  ```
- HDF5 conversion and train/valid split completed:
  ```text
  spatial HDF5:  35393217
  temporal HDF5: 35393218
  split:         35393219
  ```
  All 10 HDF5 files have `train` and `valid` masks. HDF5 conversion produced
  60 robomimic demos per condition from 30 raw demos.
- GPU training has been submitted with model output under scratch:
  ```text
  /scratch/prj/eng_demt_robot_learning/trained_models/ar_guidance_spatial_S15_S35
  /scratch/prj/eng_demt_robot_learning/trained_models/ar_guidance_temporal_T00_T100
  ```
  Training jobs:
  ```text
  spatial:  35393220 S15, 35393221 S20, 35393222 S25, 35393223 S30, 35393224 S35
  temporal: 35393236 T00, 35393254 T25, 35393255 T50, 35393256 T75, 35393257 T100
  ```
  S15 job `35393220` completed successfully at 2026-07-04 00:17 BST after
  validation early stopping at epoch 56. It wrote:
  ```text
  /scratch/prj/eng_demt_robot_learning/trained_models/ar_guidance_spatial_S15_S35/S15/spatial_S15_d30_seed1_2gap/20260703234546
  ```
  Checkpoints: `models/model_epoch_20.pth`, `models/model_epoch_40.pth`.
  The Slurm state is `COMPLETED 0:0`; the wandb `PrintLogger.isatty` finish
  error appeared after early stopping but did not make the job fail. S20 job
  `35393221` also completed successfully at 2026-07-04 00:40 BST after early
  stopping at epoch 44, latest checkpoint `model_epoch_40.pth`. S25 job
  `35393222` completed successfully at 2026-07-04 01:31 BST after early
  stopping at epoch 87, latest checkpoint `model_epoch_80.pth`. S30 job
  `35393223` completed successfully at 2026-07-04 02:02 BST after early
  stopping at epoch 44, latest checkpoint `model_epoch_40.pth`. As of
  2026-07-04 02:03 BST, S35 job `35393224` is running, with latest checkpoint
  `model_epoch_20.pth`, and T00 job `35393236` has started under the temporal
  scratch model root. As of 2026-07-04 02:23 BST, all five spatial training
  jobs are `COMPLETED 0:0`; S35 early-stopped at epoch 44 with latest
  checkpoint `model_epoch_40.pth`. Spatial eval job `35393258` is no longer
  dependency-blocked and is pending GPU resources. As of 2026-07-04 02:45 BST,
  T00 and T25 temporal training are running with latest checkpoints
  `model_epoch_60.pth` and `model_epoch_80.pth`, respectively; T50/T75/T100
  remain pending. As of 2026-07-04 03:06 BST, T00 has reached epoch 96 with
  latest checkpoint `model_epoch_80.pth`, T25 has reached epoch 135 with latest
  checkpoint `model_epoch_120.pth`, and T50 is running. T75/T100 and spatial
  eval remain pending on GPU priority. As of 2026-07-04 03:28 BST,
  T00/T25/T50 are all still running and writing checkpoints: T00 latest
  `model_epoch_120.pth`, T25 latest `model_epoch_200.pth`, T50 latest
  `model_epoch_40.pth`. T75/T100 and spatial eval remain pending on GPU
  priority. As of 2026-07-04 03:50 BST, T25 completed successfully after early
  stopping at epoch 238, latest checkpoint `model_epoch_220.pth`. T75 has
  started; T00 and T50 are still running; T100 and spatial eval remain pending
  on GPU priority. As of 2026-07-04 04:10 BST, T00/T50/T75 are still running
  with latest checkpoints `model_epoch_200.pth`, `model_epoch_80.pth`, and
  `model_epoch_20.pth`; T100 and spatial eval remain pending. As of
  2026-07-04 04:54 BST, T100 has started and all remaining temporal jobs are
  running. Latest checkpoints: T00 `model_epoch_260.pth`, T50
  `model_epoch_120.pth`, T75 `model_epoch_100.pth`, T100
  `model_epoch_20.pth`. Spatial eval remains pending. As of
  2026-07-04 05:25 BST, T00 completed successfully after early stopping at
  epoch 287, latest checkpoint `model_epoch_280.pth`. T50/T75/T100 are still
  running with latest checkpoints `model_epoch_180.pth`,
  `model_epoch_200.pth`, and `model_epoch_120.pth`; spatial eval remains
  pending. As of 2026-07-04 05:56 BST, T100 completed successfully after early
  stopping at epoch 159, latest checkpoint `model_epoch_140.pth`. T50/T75 are
  still running. Spatial eval job `35393258` failed after S35 sampled an
  unreachable `corridor_start`; S15-S30 JSONs and all five videos were written
  but S35 JSON and aggregate summary were missing. The eval script was patched
  to pre-sample paired normalized x-z offsets that are IK-reachable for all S
  conditions, preserving paired starts while avoiding unreachable S35 samples.
  Spatial eval was resubmitted as job `35400911`. T50 completed successfully
  at 2026-07-04 05:57 BST after early stopping at epoch 242, latest checkpoint
  `model_epoch_240.pth`; T75 is the only remaining running training job.
  As of 2026-07-04 07:31 BST, temporal eval `35393259` completed successfully
  and wrote T00-T100 JSONs, all five videos, and `summary_seed628_n10.json`.
  Temporal success rates: T00 10/10, T25 9/10, T50 9/10, T75 7/10, T100 7/10.
  As of 2026-07-04 06:10 BST, T75 is still running at epoch 267 with latest
  checkpoint `model_epoch_260.pth`. Resubmitted spatial eval job `35400911`
  is pending on GPU priority. As of 2026-07-04 06:37 BST, T75 completed
  successfully after early stopping at epoch 284, latest checkpoint
  `model_epoch_280.pth`, so all 10 training jobs are complete. Loss summary
  job `35395079` completed and wrote both tracks' `training_loss_summary.json`
  and `loss.png`. Spatial eval `35400911` and temporal eval `35393259` are
  pending on GPU priority. As of 2026-07-04 07:19 BST, spatial eval
  `35400911` completed successfully and wrote S15-S35 JSONs, all five videos,
  and `summary_seed628_n10.json`. Spatial success rates: S15 9/10, S20 3/10,
  S25 4/10, S30 1/10, S35 4/10. Temporal eval `35393259` is running.
- Training loss summary job `35395079` is submitted and depends on all 10
  training jobs. It will run `scripts/summarize_ar_guidance_training.py` and
  write `training_loss_summary.json` plus `loss.png` under each dataset root.
- Rollout eval jobs are submitted and pending on successful training:
  ```text
  spatial eval:  35393258
  temporal eval: 35393259
  ```

### Spatial Conditions

Run all five:

```text
S15: corridor_start_radius = 0.15 m
S20: corridor_start_radius = 0.20 m
S25: corridor_start_radius = 0.25 m
S30: corridor_start_radius = 0.30 m
S35: corridor_start_radius = 0.35 m
```

Current corrected Ablation-1 simulator exposes two spatial radii:

```text
corridor_start_radius
pre_grasp_radius
```

If using the existing two-radius proxy, keep a fixed `25:6` ratio:

```text
S15: corridor_start_radius = 0.15 m, pre_grasp_radius = 0.036 m
S20: corridor_start_radius = 0.20 m, pre_grasp_radius = 0.048 m
S25: corridor_start_radius = 0.25 m, pre_grasp_radius = 0.060 m
S30: corridor_start_radius = 0.30 m, pre_grasp_radius = 0.072 m
S35: corridor_start_radius = 0.35 m, pre_grasp_radius = 0.084 m
```

Preferred alternative if feasible: implement true three-stage
`r_start/r_middle/r_final` funnel scaling instead of the two-radius proxy.

### Output Roots

Use new dataset roots so old corrected data is preserved:

```text
/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/ar_guidance_spatial_S15_S35
/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/ar_guidance_temporal_T00_T100
```

Use scratch model storage, not `/users`, to avoid quota failures:

```text
/scratch/prj/eng_demt_robot_learning/trained_models/ar_guidance_spatial_S15_S35
/scratch/prj/eng_demt_robot_learning/trained_models/ar_guidance_temporal_T00_T100
```

## What Worked
- Corrected Week 1 spatial collection starts directly at sampled
  `corridor_start`; there is no `random_start`.
- Correct AR corridor-start center is:
  ```text
  [0.3, 0.0, 0.5]
  ```
- `examples/main_abla_1.py` supports spatial radius overrides:
  ```text
  --corridor-start-radius
  --pre-grasp-radius
  ```
- `scripts/run_abla1_collect.sh` forwards:
  ```text
  CORRIDOR_START_RADIUS
  PRE_GRASP_RADIUS
  ```
- `examples/main_time_mvp.py` already has a temporal-condition table
  `TIME_CONDITIONS` and samples per-phase duration multipliers. This is the
  right place to replace `T00/T20/Twide` with `T00/T25/T50/T75/T100`.
- HDF5 conversion scripts worked with:
  ```text
  action_gap = 2
  point_cloud_data = 10000
  ```
- Full new HDF5 conversion worked with:
  ```text
  scripts/run_abla1_hdf5_slurm.sh
  scripts/run_time_mvp_hdf5_slurm.sh
  ```
- Train/valid split with the ARCap robomimic splitter worked:
  ```bash
  /users/k23114984/code/arcap_policy/STEP2_train_policy/robomimic/scripts/split_train_val.py \
    --dataset <hdf5> --ratio 0.1
  ```
- `scripts/split_ar_guidance_hdf5.py` and
  `scripts/run_ar_guidance_split_slurm.sh` worked for splitting all 10 new
  HDF5 files.
- GPU training through:
  ```text
  /users/k23114984/code/arcap_policy/STEP2_train_policy/run_pybullet_dp.sh
  ```
  worked when output was placed on scratch.
- Latest-checkpoint rollout fallback worked for prior experiments. Preserve or
  re-add numeric checkpoint sorting where needed.
- The new shared-r35 code path reached start generation before cancellation.
  The `35403050` log printed:
  ```text
  Generated 10 shared reachable corridor starts with radius=0.35 for conditions=['S15', 'S20', 'S25', 'S30', 'S35'].
  ```

## What Didn't Work
- Do not use old spatial root `dataset/abla1_full`; it had wrong geometry and
  an extra `random_start`.
- Do not use old `P00/P01/P10/P11` as the new spatial answer. Those were an
  independent 2x2 design:
  ```text
  P00: 0.10 / 0.02
  P01: 0.10 / 0.06
  P10: 0.25 / 0.02
  P11: 0.25 / 0.06
  ```
- Do not leave metadata as `P00` while overriding radii. Raw demo metadata,
  HDF5 names, training configs, model names, rollout summaries, and plots must
  use real S condition names.
- Do not use old temporal `T00/T20/Twide` as the new temporal answer. The
  corrected temporal ladder is `T00/T25/T50/T75/T100`.
- Do not call temporal a fixed metric-speed threshold experiment. It is a
  controlled phase-duration/pacing jitter experiment, with paper context that
  speed feedback is relative to an initial reference trajectory speed.
- Do not run a new orientation/degree sweep now. Week 1 `R00/R15/R30` is
  enough.
- Do not evaluate policies on different rollout-start distributions within an
  experiment track. Spatial S conditions should share paired rollout starts;
  temporal T conditions should share the same fixed temporal-eval starts.
- Do not write model outputs under `/users/k23114984`; prior training hit quota.
- Temporal smoke failed before adding `sample_reachable_random_start` to
  `PandaSim`. If this helper is removed, temporal collection and temporal eval
  will fail.
- The `cpu` partition queued slowly for these jobs. Collection/postcheck/HDF5
  wrappers were moved to `interruptible_cpu`; future rollout and data
  collection should also use the appropriate `interruptible_*` partition
  (`interruptible_cpu` or `interruptible_gpu`) instead of plain `cpu` or
  `gpu`. GPU training is a separate concern unless the user changes that rule.
- Do not treat
  `/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/ar_guidance_spatial_S15_S35/policy_rollouts_seed628_shared_r35`
  as valid shared-r35 rollout results yet. Job `35403050` was cancelled after a
  short partial S15 video and before per-condition JSON or aggregate summary.
- Avoid future spatial/temporal rollout submissions as one sequential
  all-condition job when parallel resources are available. Prefer a Slurm array
  or one job per condition, while preserving identical paired starts through a
  shared manifest or strictly identical deterministic start generation.

## Key Files & Commands

### Spatial Files

- Collection generator:
  - `examples/main_abla_1.py`
  - Patch `--ablation-condition` choices to accept
    `S15/S20/S25/S30/S35`, or add a new spatial-funnel mode/table.
- Collection wrapper:
  - `scripts/run_abla1_collect.sh`
  - Patch allowed `CONDITION` values to include `S15/S20/S25/S30/S35`.
- Dataset checker:
  - `scripts/check_abla1_dataset.py`
  - Patch only if it assumes old `P` names; keep geometry checks.
- Plot helper:
  - `examples/plot_abla1_ee_trajectories.py`
- HDF5 conversion:
  - `scripts/create_abla1_hdf5.py`
  - `scripts/run_abla1_hdf5_slurm.sh`
  - completed job `35393217`
- Train config / submit:
  - `scripts/create_abla1_train_configs.py`
  - `scripts/submit_abla1_train_pipeline.sh`
  - pending jobs `35393220`-`35393224`
- Rollout:
  - `examples/eval_abla1_trained_policies.py`
  - `scripts/run_abla1_eval.sh`
  - pending job `35393258`

### Temporal Files

- Collection generator:
  - `examples/main_time_mvp.py`
  - Replace hardcoded `TIME_CONDITIONS = {"T00", "T20", "Twide"}` with:
    ```python
    TIME_CONDITIONS = {
        "T00": (1.0, 1.0),
        "T25": (0.75, 1.25),
        "T50": (0.50, 1.50),
        "T75": (0.25, 1.75),
        "T100": (0.0, 2.0),
    }
    ```
    Then add a minimum positive phase-duration guard for T100.
- Collection wrapper:
  - `scripts/run_time_mvp_collect.sh`
  - Patch allowed conditions to `T00/T25/T50/T75/T100`.
- HDF5 conversion:
  - `scripts/create_time_mvp_hdf5.py`
  - `scripts/run_time_mvp_hdf5_slurm.sh`
  - completed job `35393218`
- Train config / submit:
  - `scripts/create_time_mvp_train_configs.py`
  - `scripts/submit_time_mvp_train_pipeline.sh`
  - pending jobs `35393236`, `35393254`-`35393257`
- Rollout:
  - `examples/eval_time_mvp_trained_policies.py`
  - `scripts/run_time_mvp_eval.sh`
  - pending job `35393259`

### Automation Helpers

- `scripts/run_ar_guidance_postcheck_slurm.sh`
  - `TRACK=spatial|temporal|all`
  - runs raw dataset checks and plots.
- `scripts/split_ar_guidance_hdf5.py`
  - wraps the ARCap `split_train_val.py` for all new HDF5 files.
- `scripts/run_ar_guidance_split_slurm.sh`
  - Slurm wrapper for the split helper.
- `scripts/summarize_ar_guidance_training.py`
  - parses `logs/log.txt`, records train/valid losses and checkpoints, and
    writes `training_loss_summary.json` plus `loss.png`.
- `scripts/run_ar_guidance_training_summary_slurm.sh`
  - Slurm wrapper for the loss summary helper.

### Scheduling Preference

- User preference from 2026-07-04: future rollout and data-collection jobs
  should use interruptible partitions, not plain `cpu` or `gpu`.
  - CPU-style collection/check/HDF5 work: use `interruptible_cpu`.
  - GPU rollout work: use `interruptible_gpu`.
- User preference from 2026-07-04: future rollout should be parallel where
  practical, not one all-condition sequential job. For spatial S15-S35, prefer
  one Slurm array or one job per condition.
- Preserve paired starts when parallelizing. Best implementation is to generate
  one shared start manifest, then have each condition job read that manifest.
  If using current deterministic generation instead of a manifest, all parallel
  condition jobs must use the same `--seed`, `--shared-start-radius`,
  `--num-rollouts`, `--sample-hz`, and IK thresholds, and must not race while
  writing the same aggregate `summary_seed*.json`.

### Shared-r35 Spatial Rerollout

- Current code supports the user-requested shared absolute starts:
  ```bash
  --shared-start-radius 0.35
  ```
- The cancelled job `35403050` was submitted with the command below. This is
  reproducible but sequential and used the script's current plain `gpu`
  partition unless overridden:
  ```bash
  OUTPUT_DIR=/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/ar_guidance_spatial_S15_S35/policy_rollouts_seed628_shared_r35 \
  VIDEO_DIR=/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/ar_guidance_spatial_S15_S35/policy_rollouts_seed628_shared_r35/videos \
  sbatch scripts/run_abla1_eval.sh --shared-start-radius 0.35
  ```
- If rerunning as a single fallback job, override the partition at submission
  time or patch `scripts/run_abla1_eval.sh` first:
  ```bash
  OUTPUT_DIR=/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/ar_guidance_spatial_S15_S35/policy_rollouts_seed628_shared_r35 \
  VIDEO_DIR=/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/ar_guidance_spatial_S15_S35/policy_rollouts_seed628_shared_r35/videos \
  sbatch --partition=interruptible_gpu scripts/run_abla1_eval.sh --shared-start-radius 0.35
  ```
- Preferred next implementation before rerun: add manifest/merge support, then
  submit S15-S35 in parallel on `interruptible_gpu`. Without merge support,
  per-condition parallel jobs should write to separate output directories and
  a follow-up step should combine the five JSON files into one aggregate
  summary.

### Suggested Spatial Collection

```bash
for cond in S15 S20 S25 S30 S35; do
  case "$cond" in
    S15) csr=0.15; pgr=0.036 ;;
    S20) csr=0.20; pgr=0.048 ;;
    S25) csr=0.25; pgr=0.060 ;;
    S30) csr=0.30; pgr=0.072 ;;
    S35) csr=0.35; pgr=0.084 ;;
  esac
  CONDITION="$cond" \
  RUN_NAME="spatial_${cond}_d30_seed1" \
  NUM_DEMOS=30 \
  SEED=1 \
  SAMPLE_HZ=8 \
  OUTPUT_ROOT=/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/ar_guidance_spatial_S15_S35 \
  CORRIDOR_START_RADIUS="$csr" \
  PRE_GRASP_RADIUS="$pgr" \
  MAX_COLLECTION_ATTEMPTS=300 \
  sbatch scripts/run_abla1_collect.sh
done
```

Suggested spatial raw group names:

```text
spatial_S15_d30_seed1
spatial_S20_d30_seed1
spatial_S25_d30_seed1
spatial_S30_d30_seed1
spatial_S35_d30_seed1
```

### Suggested Temporal Collection

```bash
for cond in T00 T25 T50 T75 T100; do
  CONDITION="$cond" \
  RUN_NAME="temporal_${cond}_d30_seed1" \
  NUM_DEMOS=30 \
  SEED=1 \
  SAMPLE_HZ=8 \
  OUTPUT_ROOT=/scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/ar_guidance_temporal_T00_T100 \
  MAX_COLLECTION_ATTEMPTS=300 \
  sbatch scripts/run_time_mvp_collect.sh
done
```

Suggested temporal raw group names:

```text
temporal_T00_d30_seed1
temporal_T25_d30_seed1
temporal_T50_d30_seed1
temporal_T75_d30_seed1
temporal_T100_d30_seed1
```

## Next Steps
1. Treat the original spatial/temporal experiment run as complete through
   training, loss summaries, and the first rollout summaries.
2. Use the completed shared-r35 spatial rerollout from:
   ```text
   /scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/ar_guidance_spatial_S15_S35/policy_rollouts_seed628_shared_r35_parallel
   ```
   Do not use the older cancelled partial directory
   `policy_rollouts_seed628_shared_r35` as final results.
3. If rerunning shared-r35 again, keep the manifest/array/merge pattern:
   generate one shared start manifest, run one condition per array task with
   `--start-manifest` and `--skip-aggregate`, then run
   `scripts/run_abla1_eval_merge.sh`.
4. Optional cleanup only after the user approves it: remove old partial/probe
   rollout output directories to avoid confusion.

## Open Questions
- Whether to keep or delete the old cancelled partial output:
  ```text
  /scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/ar_guidance_spatial_S15_S35/policy_rollouts_seed628_shared_r35/videos/spatial_S15_seed628_n10.mp4
  ```
- Whether to remove any empty/partial plain-`gpu` probe output under:
  ```text
  /scratch/prj/eng_demt_robot_learning/polymetics_demt/dataset/ar_guidance_spatial_S15_S35/policy_rollouts_seed628_shared_r35_parallel_gpu
  ```

## Changelog
- 2026-07-04 12:55 BST: Completed the shared absolute-start r=0.35 spatial
  rerollout with a shared manifest and per-condition Slurm array. Final output
  is under `policy_rollouts_seed628_shared_r35_parallel`; success rates are
  S15 6/10, S20 3/10, S25 4/10, S30 1/10, S35 2/10. Verified all five
  condition JSONs use `paired_shared_absolute_corridor_starts_r35` and have
  identical absolute starts.
- 2026-07-04 12:05 BST: Implemented the shared absolute-start r=0.35 spatial
  eval path, submitted rerollout job `35403050`, then cancelled it per user
  request. Confirmed the job was sequential, used plain `gpu`, and produced
  only a partial S15 video before cancellation. Added future preferences:
  rollout/data collection should use `interruptible_*` partitions and rollout
  should be parallel where practical while preserving identical starts.
- 2026-07-04 07:31 BST: Temporal eval `35393259` completed successfully. It
  wrote all temporal JSONs/videos and aggregate summary. Success rates: T00
  10/10, T25 9/10, T50 9/10, T75 7/10, T100 7/10. Final verification passed:
  spatial eval `35400911`, temporal eval `35393259`, and loss summary
  `35395079` are all `COMPLETED 0:0`; both tracks have 6 rollout JSON files
  and 5 videos; both loss summary JSONs and loss plots exist; `py_compile` and
  `git diff --check` passed.
- 2026-07-04 05:56 BST: T100 completed successfully after early stopping at
  epoch 159, latest checkpoint `model_epoch_140.pth`. Spatial eval job
  `35393258` failed on an unreachable S35 sampled start after writing partial
  outputs; patched `examples/eval_abla1_trained_policies.py` to use paired
  reachable shared offsets and resubmitted spatial eval as `35400911`.
- 2026-07-04 05:57 BST: T50 completed successfully after early stopping at
  epoch 242, latest checkpoint `model_epoch_240.pth`; T75 is the only
  remaining running training job.
- 2026-07-04 06:10 BST: T75 continues running at epoch 267 with latest
  checkpoint `model_epoch_260.pth`; resubmitted spatial eval `35400911` is
  pending on GPU priority.
- 2026-07-04 06:37 BST: T75 completed successfully after early stopping at
  epoch 284, latest checkpoint `model_epoch_280.pth`. All 10 training jobs are
  complete. Loss summary job `35395079` completed and wrote both JSON summaries
  plus loss plots. Spatial eval `35400911` and temporal eval `35393259` are
  pending on GPU priority.
- 2026-07-04 07:19 BST: Spatial eval rerun `35400911` completed successfully
  with paired reachable shared starts. It wrote all spatial JSONs/videos and
  aggregate summary. Success rates: S15 9/10, S20 3/10, S25 4/10, S30 1/10,
  S35 4/10. Temporal eval `35393259` is running.
- 2026-07-04 05:25 BST: T00 completed successfully after early stopping at
  epoch 287, latest checkpoint `model_epoch_280.pth`. T50/T75/T100 continue
  running with checkpoints through epochs 180/200/120. Spatial eval remains
  pending; no rollout outputs yet.
- 2026-07-04 04:54 BST: T100 started, so all remaining temporal training jobs
  are running. Latest temporal checkpoints are T00 epoch 260, T50 epoch 120,
  T75 epoch 100, and T100 epoch 20. Spatial eval remains pending; no rollout
  outputs yet.
- 2026-07-04 04:10 BST: T00/T50/T75 temporal jobs are running with checkpoints
  through epochs 200/80/20 respectively. T100 and spatial eval remain pending;
  no rollout outputs yet.
- 2026-07-04 03:50 BST: T25 completed successfully after early stopping at
  epoch 238, latest checkpoint `model_epoch_220.pth`. T75 started; T00 and T50
  continue running; T100 and spatial eval remain pending on GPU priority.
- 2026-07-04 03:28 BST: T00/T25/T50 temporal jobs are running with checkpoints
  through epochs 120/200/40 respectively. T75/T100 and spatial eval remain
  pending on GPU priority; no rollout outputs yet.
- 2026-07-04 03:06 BST: T50 temporal training started. T00 reached epoch 96
  with latest checkpoint `model_epoch_80.pth`; T25 reached epoch 135 with
  latest checkpoint `model_epoch_120.pth`. Spatial eval remains pending on GPU
  priority.
- 2026-07-04 02:45 BST: Spatial eval is still pending on GPU priority. T00 and
  T25 temporal training are running and have checkpoints through epochs 60 and
  80, respectively; T50/T75/T100 are still pending.
- 2026-07-04 02:23 BST: All five spatial training jobs are complete. Spatial
  eval job `35393258` is dependency-cleared and pending GPU resources. Temporal
  T00 and T25 are running; T50/T75/T100 are still pending.
- 2026-07-04 02:03 BST: S30 training job `35393223` completed successfully
  after early stopping at epoch 44, latest checkpoint `model_epoch_40.pth`.
  S35 is running and T00 has started under the temporal scratch model root.
- 2026-07-04 01:42 BST: S25 training job `35393222` completed successfully
  after early stopping at epoch 87, latest checkpoint `model_epoch_80.pth`.
  S30 job `35393223` and S35 job `35393224` are now running; temporal training
  jobs are still pending.
- 2026-07-04 00:51 BST: S20 training job `35393221` completed successfully
  after early stopping at epoch 44, with latest checkpoint
  `model_epoch_40.pth`. S25 job `35393222` is now running; the other seven
  GPU training jobs remain pending on priority.
- 2026-07-04 00:30 BST: S15 training job `35393220` completed successfully
  after validation early stopping at epoch 56, with latest checkpoint
  `model_epoch_40.pth`.
- 2026-07-03: Executed the pipeline through raw collection, checks, plots,
  HDF5 conversion, train/valid split, and queued GPU training/eval jobs.
- 2026-07-03: Added automatic post-training loss summary job `35395079`.
- 2026-07-03: Renamed handoff file from spatial-only wording to
  `ar-guidance-spatial-temporal-experiments.md` so the next agent treats both
  spatial and temporal as active experiment tracks.
- 2026-07-03: Corrected handoff per user instruction: temporal must be rerun as
  a clean `+/-0%, +/-25%, +/-50%, +/-75%, +/-100%` ladder; spatial remains
  `S15/S20/S25/S30/S35`; orientation does not need a new run.
