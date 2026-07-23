# Handoff: Legacy CoRL/DEMT Experiments Archive

_Last updated: 2026-07-23 · Branch: hpc-headless-tro @ 7c043cc_

## Goal

将本分支进入 T-RO 研究前的 CoRL/DEMT AR-guidance 参数实验压缩封存为单一只读
档案。新 agent 只需通过本文了解旧实验的最终结论、正式 artifacts、无效结果和
claim boundaries；旧实验已经关闭，不应在 `hpc-headless-tro` 上继续执行或扩展。
完整逐日工程历史仍保留在旧实验分支 `hpc-headless-data-collection`。

## Current Progress

### 1. 封存范围与最终状态

- 本档案合并并取代了 12 份旧 handoff：
  ```text
  ar-guidance-ood-human-logic.md
  ar-guidance-spatial-temporal-experiments.md
  corl-demt-ar-settings-experiment-closure.md
  multiagent_history_example.md
  position-contact-n50-rollouts.md
  rebuttal_bounded_optimality_goal.md
  temporal-vref-experiment-plan.md
  temporal-vref-reciprocal-experiment.md
  week1_main-experiments.md
  week1_research_thinking.md
  week2_experiment.md
  week2_research_thinking.md
  ```
- CoRL/DEMT AR-settings anti-cherry-picking experiment was formally completed
  and closed on 2026-07-23.
- Closure baseline was `hpc-headless-data-collection @ de6d7de`. No collection,
  training, rollout, validation, or Slurm job remains open.
- The accepted experiment fixes learner, robot/task protocol and `N=30`
  demonstrations per training condition. Formal rollout uses:
  ```text
  seed=628
  50 paired rollouts per condition
  horizon=200
  sample_hz=8
  action_gap=2
  action_dt=0.25 s
  terminate_on_success=true
  success: cube z >= 0.20 m
  ```
  Pairing is valid within each track, not across Position, Contact and Temporal.

### 2. Final Position result

The accepted fixed-ratio proxy conditions were:

```text
condition  corridor_start_radius  pre_grasp_radius  success
S15        0.15 m                 0.036 m           18/50 = 36%
S20        0.20 m                 0.048 m           18/50 = 36%
S25        0.25 m                 0.060 m           18/50 = 36%
S30        0.30 m                 0.072 m           13/50 = 26%
S35        0.35 m                 0.084 m            7/50 = 14%
```

Interpretation:

- The Table-5-scale `S25` is in the highest-performing group and ties tighter
  `S15/S20`.
- Relaxing the spatial funnel further to `S30/S35` degrades deployment success.
- This supports `S25` as a bounded, non-dominated practical candidate under
  the fixed learner/task/`N=30` setting. It does not establish a unique or
  continuous-space global optimum.

Formal aggregate:

```text
dataset/ar_guidance_spatial_S15_S35/
  policy_rollouts_seed628_shared_r35_paired_n50_h200/
  summary_seed628_n50.json
SHA-256:
ec9c95ba26e3a4b9f18ae7c34966a8d55dc3acca2af10c18bdbc43d12c827d78
```

### 3. Final Contact/orientation result

```text
condition  full-trajectory orientation sampling              success
R00        fixed 0 degrees                                    30/50 = 60%
R15        uniform angle in [-15, 15] about sampled 3-D axis  37/50 = 74%
R30        uniform angle in [-30, 30] about sampled 3-D axis  32/50 = 64%
```

Interpretation:

- `R15` has the highest point estimate.
- Human post-training P6/P7 grasp/close orientation dispersion has p95 about
  `13–14 degrees`, with `15-degree` coverage `99.2%–100.0%`.
- The combined evidence supports `15 degrees` as a human-compatible,
  learner-aware finite candidate. It does not require or demonstrate global
  statistical dominance over every possible angle.

Formal aggregate:

```text
dataset/orn_mvp_full/
  policy_rollouts_seed628_paired_n50_h200/
  summary_seed628_n50.json
SHA-256:
99dbb06031f0d5d86d481cd113afccf38874f7248c9f66ee3f3c83a6cb1e0e5e
```

### 4. Final Temporal result

The accepted experiment is the corrected, spatially distributed reciprocal
P6/P7 `v_ref` sweep:

```text
condition   reciprocal multiplier range  success       median successful time
VR1P5       [2/3, 3/2]                    37/50 = 74%   5.75 s
V050_200    [1/2, 2]                      37/50 = 74%   7.00 s
VR3         [1/3, 3]                      33/50 = 66%  10.75 s
VR4         [1/4, 4]                      18/50 = 36%  11.50 s
```

Interpretation:

- The paper setting `[0.5, 2.0] x v_ref` ties the tighter `VR1P5` for highest
  success.
- Wider `VR3/VR4` ranges reduce success and increase completion time.
- The result establishes learner relevance of limiting pacing variation, but
  not that `[0.5,2.0]` is the unique exact optimum.

Formal aggregate:

```text
dataset/temporal_vref_reciprocal_spatial_v2/
  policy_rollouts_seed628_paired_n50_h200/
  summary_seed628_n50.json
SHA-256:
3c84bdecc4bb1113a7d84f0b8ed0ac8e116f98c1008d0eeaa8cca36f20f3e9ed
```

The accepted temporal collection uses the P6/P7 post-training timing source:

```text
outputs/week2_human_phase_reference_p6p7_v2/v_ref_phase_reference.json
v_ref_group = P6P7_post_valid_order
```

### 5. Human compatibility and teaching-quality evidence

- Source data under `/scratch/users/k23114984/pybullet_data` are real human
  demonstrations. Pooled, shuffled, symlinked or re-split data must be
  described as `pooled and re-split real-user demonstrations`, never synthetic.
- Phase mapping:
  ```text
  P1: prism, unguided trained-task pre-test
  P2: cube, unguided unseen-object pre-test
  P6: prism, unguided trained-task post-test
  P7: cube, unguided unseen-object post-test
  P8: unguided unseen-task ordered pick-and-place
  ```
- Key spatial diagnostics:
  ```text
  nearest-to-corridor-plane p95 radius
  P1 -> P6: 18.28 cm -> 9.49 cm
  P2 -> P7: 26.70 cm -> 6.67 cm

  pregrasp-keypoint p95 radius
  P1 -> P6: 5.37 cm -> 3.09 cm
  P2 -> P7: 6.99 cm -> 2.87 cm
  ```
- Key orientation diagnostics:
  ```text
  closest-grasp p95 to group mean
  P1 -> P6: 27.38 deg -> 13.14 deg
  P2 -> P7: 33.96 deg -> 14.33 deg
  ```
- Temporal compatibility:
  ```text
  duration-ratio coverage in [0.5,2.0]: 86.7%–100.0%
  mean-speed-ratio coverage in [0.5,2.0]: 93.3%–100.0%
  ```
- Paper-level teaching-quality outcomes at the same demonstration budget:
  ```text
  EDSR P1 -> P6: 14% -> 75%
  EDSR P2 -> P7: 22% -> 91%
  ```
  Table 9 also reports improved MPCV/MCOD/MPSV and validation loss for DEMT
  post-training data.

### 6. Final claim boundary

The final accepted statement is:

```text
The CoRL/DEMT AR settings are not supported by a single cherry-picked
configuration. Under a fixed 30-demonstration teaching effort, deployment-
evaluated finite-candidate sweeps and human-compatibility diagnostics place
the selected guidance settings inside bounded high-performing ranges.
Together with the paper's pre/post results, this supports that DEMT guidance
improves demonstration teaching quality without increasing the number of
demonstrations.
```

Do not claim:

- global optimisation over continuous `P x R x V`;
- unique exact optimality of `25 cm`, `15 degrees` or
  `[0.5,2.0] x v_ref`;
- statistically significant superiority between every finite candidate.

## What Worked

- Coupled fixed-ratio Position conditions provided a cleaner funnel comparison
  than the old independent spatial 2x2 design.
- Shared manifests, separate RNG streams, frozen checkpoint hashes,
  per-rollout JSON, Wilson intervals, paired discordance tables and strict
  stale/partial merge rejection produced auditable N50 results.
- Human compatibility and learner compatibility were analysed separately,
  then connected to the paper's pre/post teaching-quality outcomes.
- The corrected Temporal experiment recollected and retrained all four
  conditions with a real spatial distribution shared across conditions.
- Model outputs and large generated artifacts were stored under project
  scratch rather than `/users`, avoiding the real 50 GB quota failure.

## What Didn't Work

- `dataset/abla1_full` used the wrong corridor geometry and an extra
  `random_start`; none of its raw data, HDF5, models, loss, rollout or stress
  results may be cited.
- The historical `P00/P01/P10/P11` independent 2x2 sweep was mixed and does
  not identify the final Position mechanism or replace S15–S35.
- Small N10 runs were useful for engineering but must not be combined with or
  substituted for the formal N50 aggregates.
- Uniform spatial OOD annulus tests showed generally weak performance and did
  not establish that wider training improves robustness.
- `T00/T20/Twide` and `T00/T25/T50/T75/T100` were not clean evidence for the
  paper's relative speed window.
- The 2026-07-05 `V075_150/V050_200/V025_250` experiment used a fixed-point
  spatial geometry and is superseded.
- The 2026-07-18 reciprocal Temporal fixed-path run was scientifically invalid.
  Its dedicated artifacts were deleted; never cite jobs `35870393–35872331`.
- A configured `corridor_start_radius` is not proof of realised variation.
  Validators must inspect empirical waypoint deltas and cross-demo variance.
- Human percentile coverage establishes feasibility, not learner optimality.
  The AR spatial radius is a permissive human-facing envelope, not the desired
  final demonstration variance.
- Orientation dispersion is measured relative to group mean, not exact AR
  target-frame alignment. Temporal human ratios are group-reference
  diagnostics, not exact validation of each person's `v_ref`.
- W&B `PrintLogger.isatty` exceptions occurred after valid early stopping and
  checkpoint writes. GPU ECC failures, by contrast, produced no valid
  checkpoint and had to be retried away from the faulty node.

## Key Files & Commands

- Final Chinese report:
  `reports/position-rotation-temporal-n50-final.md`
- Formal Position aggregate:
  `dataset/ar_guidance_spatial_S15_S35/policy_rollouts_seed628_shared_r35_paired_n50_h200/summary_seed628_n50.json`
- Formal Contact aggregate:
  `dataset/orn_mvp_full/policy_rollouts_seed628_paired_n50_h200/summary_seed628_n50.json`
- Formal Temporal aggregate:
  `dataset/temporal_vref_reciprocal_spatial_v2/policy_rollouts_seed628_paired_n50_h200/summary_seed628_n50.json`
- Human diagnostics:
  `outputs/week2_human_diagnostics_keypoints_v2/`
- Human compatibility audit:
  `rebuttal_workflow/agent1_results/E00_human_percentile_bound_audit.md`
- Claim boundaries:
  `rebuttal_workflow/claim_ledger.md`
- Core regression tests:
  ```bash
  pytest -q \
    tests/test_position_contact_n50.py \
    tests/test_temporal_vref_reciprocal.py
  ```
- Inspect formal aggregates:
  ```bash
  jq '{condition_statistics,paired_success_discordances}' \
    dataset/ar_guidance_spatial_S15_S35/policy_rollouts_seed628_shared_r35_paired_n50_h200/summary_seed628_n50.json
  jq '{condition_statistics,paired_success_discordances}' \
    dataset/orn_mvp_full/policy_rollouts_seed628_paired_n50_h200/summary_seed628_n50.json
  jq '{condition_statistics,paired_success_discordances}' \
    dataset/temporal_vref_reciprocal_spatial_v2/policy_rollouts_seed628_paired_n50_h200/summary_seed628_n50.json
  ```
- Full granular history remains on `hpc-headless-data-collection`; this T-RO
  branch intentionally retains only the compact archive.

## Next Steps

1. Treat this file as historical context only.
2. Do not restart, extend or reinterpret the closed CoRL/DEMT parameter
   experiments on `hpc-headless-tro`.
3. For active work, read `handoffs/tro-mvp0-position-event.md` and
   `docs/tro_plan.md`.
4. Any future cross-seed, cross-learner, cross-task or joint `P x R x V`
   research must be opened as a new sub-job with new outputs and claims; it
   must not overwrite the closed results above.

## Changelog

- 2026-07-23: Consolidated the completed CoRL/DEMT experiment history into one
  read-only archive for the T-RO-focused branch and retired the granular legacy
  handoffs.
