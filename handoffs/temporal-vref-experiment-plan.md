# Handoff: Temporal Vref Experiment

_Last updated: 2026-07-05 · Branch: hpc-headless-data-collection @ a2d81a9_

## Goal
Run the temporal experiment requested by the user using the after-training human
P6/P7 timing reference (`v_ref`) instead of the previous hand-written
`T00/T25/T50/T75/T100` ladder. The main evidence should be the three
data-referenced temporal variation conditions `V075_150`, `V050_200`, and
`V025_250`, all anchored to `P6P7_post_valid_order` from
`outputs/week2_human_phase_reference_p6p7_v2/v_ref_phase_reference.json`.

## Current Progress
- Completed the full temporal `v_ref` pipeline for all three requested
  conditions:
  ```text
  V075_150: [0.75, 1.50] * v_ref
  V050_200: [0.50, 2.00] * v_ref
  V025_250: [0.25, 2.50] * v_ref
  ```
- Main `v_ref` group used:
  ```text
  v_ref_group = P6P7_post_valid_order
  n = 209 demos
  mean total duration ~= 10.766985645933016 s

  start_to_corridor        = 0.0430622009569378 s
  corridor_to_pregrasp     = 2.40829346092504 s
  pregrasp_to_first_close  = 2.3524720893141944 s
  first_close_to_end       = 5.963157894736843 s
  ```
- Implemented a separated `v_ref` mode while preserving the old temporal ladder
  defaults. Relevant code changes are in:
  ```text
  examples/main_time_mvp.py
  examples/plot_time_mvp_temporal.py
  scripts/check_time_mvp_dataset.py
  scripts/create_time_mvp_train_configs.py
  scripts/run_time_mvp_collect.sh
  scripts/run_time_mvp_eval.sh
  scripts/submit_time_mvp_train_pipeline.sh
  scripts/run_ar_guidance_postcheck_slurm.sh
  scripts/run_ar_guidance_split_slurm.sh
  scripts/split_ar_guidance_hdf5.py
  ```
- Simulator mapping is now explicit in metadata:
  ```text
  start_to_corridor:
    near-zero setup from random_start to corridor_start; clamp to one sample
    period if needed, but do not create a long artificial setup phase.

  corridor_to_pregrasp:
    full duration to move_ee(corridor_start -> pre_grasp).

  pregrasp_to_first_close:
    full duration to pick_grasp / descend, ending at close onset.

  first_close_to_end:
    split between close_gripper and lift using the legacy close:lift ratio
    1.2:2.5.
  ```
- Raw dataset root:
  ```text
  dataset/temporal_vref_p6p7_V075_V250
  ```
- Raw collection completed on Slurm:
  ```text
  35420638  V075_150  30/30 successful demos
  35420639  V050_200  30/30 successful demos
  35420640  V025_250  30/31 successful demos
  ```
  Raw metadata verification passed with no missing or wrong required `v_ref`
  fields for any condition.
- Dataset checker passed. Frame counts:
  ```text
  V075_150: min/mean/max = 72 / 95.5 / 117
  V050_200: min/mean/max = 57 / 105.1 / 147
  V025_250: min/mean/max = 43 / 115.7 / 177
  ```
- Temporal plots were generated with `--stride 4`:
  ```text
  dataset/temporal_vref_p6p7_V075_V250/temporal_plots/temporal_V075_150_temporal_xyz_phase.png
  dataset/temporal_vref_p6p7_V075_V250/temporal_plots/temporal_V050_200_temporal_xyz_phase.png
  dataset/temporal_vref_p6p7_V075_V250/temporal_plots/temporal_V025_250_temporal_xyz_phase.png
  dataset/temporal_vref_p6p7_V075_V250/temporal_plots/temporal_V075_150_V025_250_summary.png
  ```
- HDF5 conversion job `35421197` completed. Each condition produced 60
  robomimic demos from 30 raw demos, then split to `train=54`, `valid=6`:
  ```text
  dataset/temporal_vref_p6p7_V075_V250/temporal_V075_150_d30_seed1_2gap.hdf5
  dataset/temporal_vref_p6p7_V075_V250/temporal_V050_200_d30_seed1_2gap.hdf5
  dataset/temporal_vref_p6p7_V075_V250/temporal_V025_250_d30_seed1_2gap.hdf5
  ```
- Training configs were generated in:
  ```text
  training_config/temporal_vref_p6p7
  ```
  Model root:
  ```text
  /scratch/prj/eng_demt_robot_learning/trained_models/temporal_vref_p6p7_V075_V250
  ```
- Training completed on `interruptible_gpu`:
  ```text
  35421786  V075_150  COMPLETED  latest checkpoint model_epoch_180.pth
  35421787  V050_200  COMPLETED  latest checkpoint model_epoch_220.pth
  35421788  V025_250  COMPLETED  latest checkpoint model_epoch_180.pth
  ```
- Rollout evaluation job `35425749` completed with latest checkpoints,
  `seed=628`, `num_rollouts=10`, `horizon=80`, shared fixed start, and videos:
  ```text
  V075_150: 10/10 = 1.000
  V050_200: 10/10 = 1.000
  V025_250:  8/10 = 0.800
  ```
  Summary:
  ```text
  dataset/temporal_vref_p6p7_V075_V250/policy_rollouts_seed628_latest/summary_seed628_n10.json
  ```
- Verification passed:
  ```text
  git diff --check
  python -m py_compile examples/main_time_mvp.py examples/plot_time_mvp_temporal.py scripts/check_time_mvp_dataset.py scripts/create_time_mvp_train_configs.py scripts/split_ar_guidance_hdf5.py examples/eval_time_mvp_trained_policies.py
  ```

## What Worked
- The P6/P7 after-training human reference provides a concrete temporal
  scaffold grounded in real user behavior. This is the correct main evidence
  for `[0.5, 2] * v_ref`.
- Keeping `V075_150`, `V050_200`, and `V025_250` as new condition names avoided
  overloading the old `T00/T25/T50/T75/T100` semantics.
- Recording the reference JSON, group, phase durations, sampled multipliers,
  target durations, and simulator mapping in every raw demo made the dataset
  auditable.
- The existing Week 1 / Week 2 pipeline shape worked after small configurability
  updates:
  ```text
  collect raw demos -> visualize -> convert to HDF5 -> split train/valid
  -> train diffusion-policy models -> rollout compare with videos
  ```
- `interruptible_gpu` was materially faster to schedule than the plain `gpu`
  partition during this run.

## What Didn't Work
- Do not use the old `T00/T20/Twide` result as exact speed-bar evidence. It
  used fixed / +/-20% / broad arbitrary phase-duration multipliers.
- Do not use the newer `T00/T25/T50/T75/T100` ladder as the final rebuttal
  evidence for `[0.5, 2] * v_ref`. It is still based on hand-written simulator
  base durations.
- Do not describe `[0.5, 2] * v_ref` as a fixed metric-speed threshold. It is
  relative to a reference trajectory/speed.
- Do not blindly map the human event reference into the old six simulator
  phases. In the human P6/P7 reference, `nearest-to-corridor-plane` occurs very
  close to the start, so the old artificial `random_start -> corridor_start`
  phase is not a good proxy for after-training `v_ref`.
- The first full plotting attempt with stride 1 was interrupted because it got
  stuck on many small-file stats without visible progress. Re-running the plot
  command with `--stride 4` completed and produced the expected figures.
- Initial training submissions to the plain `gpu` partition stayed pending on
  priority. Those jobs were canceled and resubmitted to `interruptible_gpu`,
  where the three trainings completed.

## Key Files & Commands
- Reference source:
  ```text
  outputs/week2_human_phase_reference_p6p7_v2/v_ref_phase_reference.json
  outputs/week2_human_phase_reference_p6p7_v2/phase_reference_summary.csv
  outputs/week2_human_phase_reference_p6p7_v2/phase_reference_per_demo.csv
  scripts/analyze_human_phase_reference.py
  ```
- Main experiment outputs:
  ```text
  dataset/temporal_vref_p6p7_V075_V250
  training_config/temporal_vref_p6p7
  /scratch/prj/eng_demt_robot_learning/trained_models/temporal_vref_p6p7_V075_V250
  ```
- Raw condition directories:
  ```text
  dataset/temporal_vref_p6p7_V075_V250/temporal_V075_150_d30_seed1
  dataset/temporal_vref_p6p7_V075_V250/temporal_V050_200_d30_seed1
  dataset/temporal_vref_p6p7_V075_V250/temporal_V025_250_d30_seed1
  ```
- HDF5 files:
  ```text
  dataset/temporal_vref_p6p7_V075_V250/temporal_V075_150_d30_seed1_2gap.hdf5
  dataset/temporal_vref_p6p7_V075_V250/temporal_V050_200_d30_seed1_2gap.hdf5
  dataset/temporal_vref_p6p7_V075_V250/temporal_V025_250_d30_seed1_2gap.hdf5
  ```
- Rollout results:
  ```text
  dataset/temporal_vref_p6p7_V075_V250/policy_rollouts_seed628_latest/summary_seed628_n10.json
  dataset/temporal_vref_p6p7_V075_V250/policy_rollouts_seed628_latest/videos/temporal_V075_150_seed628_n10.mp4
  dataset/temporal_vref_p6p7_V075_V250/policy_rollouts_seed628_latest/videos/temporal_V050_200_seed628_n10.mp4
  dataset/temporal_vref_p6p7_V075_V250/policy_rollouts_seed628_latest/videos/temporal_V025_250_seed628_n10.mp4
  ```
- Useful commands:
  ```bash
  /scratch/users/k23114984/conda/envs/polymetis38/bin/python \
    scripts/analyze_human_phase_reference.py \
    --demo-metrics outputs/week2_human_diagnostics_keypoints_v2/demo_metrics.csv \
    --output-dir outputs/week2_human_phase_reference_p6p7_v2

  /scratch/users/k23114984/conda/envs/polymetis38/bin/python \
    scripts/check_time_mvp_dataset.py \
    --root dataset/temporal_vref_p6p7_V075_V250 \
    --conditions V075_150 V050_200 V025_250 \
    --expect-v-ref

  /scratch/users/k23114984/conda/envs/polymetis38/bin/python \
    examples/plot_time_mvp_temporal.py \
    --root dataset/temporal_vref_p6p7_V075_V250 \
    --conditions V075_150 V050_200 V025_250 \
    --v-ref-source-json outputs/week2_human_phase_reference_p6p7_v2/v_ref_phase_reference.json \
    --v-ref-group P6P7_post_valid_order \
    --stride 4
  ```
- Current relevant working-tree changes from this job:
  ```text
  M examples/main_time_mvp.py
  M examples/plot_time_mvp_temporal.py
  M scripts/check_time_mvp_dataset.py
  M scripts/create_time_mvp_train_configs.py
  M scripts/run_ar_guidance_postcheck_slurm.sh
  M scripts/run_ar_guidance_split_slurm.sh
  M scripts/run_time_mvp_collect.sh
  M scripts/run_time_mvp_eval.sh
  M scripts/split_ar_guidance_hdf5.py
  M scripts/submit_time_mvp_train_pipeline.sh
  ?? training_config/temporal_vref_p6p7/
  ```
- Pre-existing unrelated or parallel-work changes are still present; do not
  revert them unless the user explicitly asks:
  ```text
  M examples/eval_abla1_trained_policies.py
  M scripts/run_abla1_eval.sh
  M scripts/run_abla1_eval_merge.sh
  M scripts/run_abla1_shared_start_manifest.sh
  ?? handoffs/ar-guidance-ood-human-logic.md
  ?? scripts/analyze_human_phase_reference.py
  ```

## Next Steps
1. Use the completed `V075_150 / V050_200 / V025_250` results as the main
   temporal `v_ref` evidence. Do not present the old `T00/T25/T50/T75/T100`
   ladder as the primary result.
2. Summarize the rollout result in the paper/rebuttal logic as:
   ```text
   [0.75, 1.50] * v_ref: 10/10
   [0.50, 2.00] * v_ref: 10/10
   [0.25, 2.50] * v_ref:  8/10
   ```
   The central interpretation is that the policy remains robust at the exact
   paper-style `[0.5, 2] * v_ref` range under this setup, with degradation only
   at the wider `[0.25, 2.5] * v_ref` range.
3. If more evidence is needed, run a second evaluation seed or a larger rollout
   count using the same trained checkpoints and fixed paired-start setup.
4. If the code needs to be committed, separate this temporal `v_ref` work from
   the unrelated OOD/ABLA1 edits already present in the working tree.

## Changelog
- 2026-07-05: Created handoff for the corrected P6/P7 `v_ref` temporal
  experiment plan and the three requested multiplier conditions.
- 2026-07-05: Updated handoff after completing collection, plotting, HDF5
  conversion, splits, training, rollout evaluation, and verification for all
  three temporal `v_ref` conditions.
