# Handoff: CoRL/DEMT AR Settings Experiment Closure

_Last updated: 2026-07-23 · Branch: hpc-headless-data-collection @ de6d7de_

## Goal

本实验检验 CoRL/DEMT 论文中的 AR guidance settings 是否属于 cherry-picking。
在固定 learner、robot/task protocol 和每个 condition `N=30` demonstrations 的
teaching effort 下，对 spatial、contact/orientation 和 temporal guidance 的相邻
有限候选设置进行 deployment-evaluated sensitivity analysis，并结合真人数据检验
human compatibility。目标是证明所采用的 guidance 位于有学习效果、可由人完成的
bounded candidate range，并能在相同 teaching effort 下提升 demonstration teaching
quality；目标不是证明连续参数空间中的全局最优 threshold。

**Experiment status: COMPLETE AND CLOSED.**

## Current Progress

- 三条正式实验 track 均已完成从数据生成、检查、HDF5、共同 train/valid split、
  training、checkpoint 冻结到 paired `N=50` rollout 和严格 merge 的完整流程。
- 正式 rollout 统一采用 `seed=628`、`horizon=200`、`action_dt=0.25 s`、
  `terminate_on_success=true` 和 `cube z >= 0.20 m` 成功规则。配对只在各自 track
  内成立。
- Position fixed-ratio proxy sweep 已实际完成旧 experiment queue 中规划的 E05：
  ```text
  S15 / S20 / S25 / S30 / S35
  18/50, 18/50, 18/50, 13/50, 7/50
  36%,   36%,   36%,   26%,   14%
  ```
  Table-5-scale 对应的 S25 位于最高表现组，与更紧的 S15/S20 相同；继续放宽至
  S30/S35 后表现下降。这支持 S25 是 bounded、non-dominated practical candidate，
  不支持它是唯一或全局最优值。
- Contact/orientation sweep：
  ```text
  R00 / R15 / R30
  30/50, 37/50, 32/50
  60%,   74%,   64%
  ```
  论文采用的 15-degree scale 获得最高点估计。真人 P6/P7 post-training grasp/close
  orientation dispersion 的 p95 约为 13–14 degrees，进一步支持 15 degrees 是
  human-compatible、learner-aware finite candidate。当前证据不要求也不声称 R15
  对所有候选具有统计显著的全局优势。
- Corrected spatially-distributed reciprocal temporal sweep：
  ```text
  VR1P5 / V050_200 / VR3 / VR4
  37/50,   37/50,      33/50, 18/50
  74%,     74%,        66%,   36%
  median successful time: 5.75, 7.00, 10.75, 11.50 s
  ```
  论文使用的 `[0.5, 2.0] x v_ref` 与更紧的 VR1P5 并列最高成功率；更宽的 VR3/VR4
  同时降低成功率并增加完成时间。这证明 temporal guidance 避免过宽 pacing
  variation 具有 learner relevance，但不证明 `[0.5, 2.0]` 是唯一最优区间。
- 真人诊断提供独立的 human-compatibility evidence：
  - post-training P6/P7 spatial keypoints 明显收紧；
  - 15-degree orientation coverage 为 99.2%–100.0%；
  - `[0.5, 2.0]` duration-ratio coverage 为 86.7%–100.0%，mean-speed-ratio
    coverage 为 93.3%–100.0%。
- 论文主实验提供 teaching-quality outcome：在相同 demonstration budget 下，
  unguided pre 到 DEMT post 的 EDSR 从 P1 `14%` 提升到 P6 `75%`，从 P2 `22%`
  提升到 P7 `91%`；Table 9 中 MPCV/MCOD/MPSV 及 validation loss 同时改善。
- 因此，本阶段的正式结论是：
  ```text
  The CoRL/DEMT AR settings are not supported by a single cherry-picked
  configuration. Under a fixed 30-demonstration teaching effort, deployment-
  evaluated finite-candidate sweeps and human-compatibility diagnostics place
  the selected guidance settings inside bounded high-performing ranges.
  Together with the paper's pre/post results, this supports that DEMT guidance
  improves demonstration teaching quality without increasing the number of
  demonstrations.
  ```
- 所有正式 summary、逐 rollout JSON、checkpoint/manifest SHA-256 和视频均已验证。
  2026-07-23 再次检查时用户 Slurm queue 为空。
- 没有 commit、push、reset 或 checkout。仓库仍是有意保留的 dirty worktree；
  closure 时基线为 `hpc-headless-data-collection @ de6d7de`。

## What Worked

- 固定 `N=30`、learner、training/evaluation protocol，只改变被测 guidance dimension，
  使结果能够直接回应 cherry-picking concern。
- 使用 shared manifests、独立 RNG streams、冻结 checkpoint hash 和每条件 50 个配对
  rollout，显著减少 evaluation sampling noise，并允许检查 paired discordance。
- Spatial 使用 coupled fixed-ratio proxy，而不是旧的独立 `P00/P01/P10/P11` 2x2
  设计，从而能围绕 Table 5 scale 比较更紧和更松的候选。
- Temporal 从头重做 spatially-distributed reciprocal design，使 V050_200、VR1P5、
  VR3、VR4 只在 temporal range 上不同。
- 将 learner compatibility 与 human compatibility 分开论证，再结合论文 pre/post
  teaching-quality evidence，形成完整而不过度承诺的结论。

## What Didn't Work

- 旧 `dataset/abla1_full` 使用错误 corridor geometry 和额外 `random_start`，不得引用。
- 旧 `P00/P01/P10/P11` 是独立 2x2 设计，不能替代正式 S15–S35 fixed-ratio sweep。
- 2026-07-18 temporal fixed-point experiment 没有真实 spatial distribution，相关专用
  artifacts 已删除，任何旧 fixed-point temporal 结果均不得引用。
- 旧 `T00/T20/Twide` 不是干净的 reciprocal ladder，不能证明论文 speed window。
- 旧 N10 结果只适合历史对照，不能与新 N50 拼接，也不能替代正式 N50 aggregate。
- 人类 percentile/coverage 只能证明 feasible/human-compatible range，不能单独证明
  learner optimality。
- 本实验不支持以下表述：
  - “DEMT solved the global optimum over continuous `P x R x V`.”
  - “25 cm、15 degrees 或 `[0.5, 2.0] x v_ref` 是唯一精确最优值。”
  - “每一个有限候选之间都存在统计显著差异。”

## Key Files & Commands

- 中文最终结果报告：
  `reports/position-rotation-temporal-n50-final.md`
- Position formal aggregate：
  `dataset/ar_guidance_spatial_S15_S35/policy_rollouts_seed628_shared_r35_paired_n50_h200/summary_seed628_n50.json`
- Contact/orientation formal aggregate：
  `dataset/orn_mvp_full/policy_rollouts_seed628_paired_n50_h200/summary_seed628_n50.json`
- Temporal formal aggregate：
  `dataset/temporal_vref_reciprocal_spatial_v2/policy_rollouts_seed628_paired_n50_h200/summary_seed628_n50.json`
- Position/contact execution record：
  `handoffs/position-contact-n50-rollouts.md`
- Corrected temporal execution record：
  `handoffs/temporal-vref-reciprocal-experiment.md`
- Human compatibility audit：
  `rebuttal_workflow/agent1_results/E00_human_percentile_bound_audit.md`
- Claim boundaries：
  `rebuttal_workflow/claim_ledger.md`
- 查看三个正式 aggregate 的核心统计：
  ```bash
  jq '{condition_statistics,paired_success_discordances}' \
    dataset/ar_guidance_spatial_S15_S35/policy_rollouts_seed628_shared_r35_paired_n50_h200/summary_seed628_n50.json
  jq '{condition_statistics,paired_success_discordances}' \
    dataset/orn_mvp_full/policy_rollouts_seed628_paired_n50_h200/summary_seed628_n50.json
  jq '{condition_statistics,paired_success_discordances}' \
    dataset/temporal_vref_reciprocal_spatial_v2/policy_rollouts_seed628_paired_n50_h200/summary_seed628_n50.json
  ```
- 关键回归测试：
  ```bash
  pytest -q tests/test_position_contact_n50.py tests/test_temporal_vref_reciprocal.py
  ```

## Next Steps

本实验没有未完成的 collection、training、rollout、validation 或 Slurm job；不需要继续
追加 parameter conditions，也不需要为了追求 exact optimum 重启本实验。

后续工作只能作为新的研究阶段单独立项，例如跨 dataset/training seeds、不同 learner/task
的 generalisation，或联合 `P x R x V` interaction。新阶段应使用新的 handoff、输出目录和
实验主张，不得改写或覆盖本 closure 记录。

## Changelog

- 2026-07-23: 正式关闭 CoRL/DEMT AR-settings anti-cherry-picking 与 fixed-30-demo
  teaching-quality 实验，记录最终证据、claim boundary、有效 artifacts 和禁止复用的旧结果。
