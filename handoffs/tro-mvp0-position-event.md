# Handoff: T-RO MVP-0 Position Event Experiment

_Last updated: 2026-07-23 · Branch: hpc-headless-tro @ 7c043cc_

## Goal

执行 T-RO 的 MVP-0 Position-event screening：在固定 learner、`N=30`
demonstrations 和 PyBullet grasping task 下，将原 task-level Position variation
解耦为 `free_reach_radius` 与 `pre_grasp_radius` 两个 event-local interventions，
检验 free-reach coverage benefit 与 pre-contact precision/density cost 是否具有
不同的 deployment effect。本阶段只验证 robot-side Layer 1 compatibility，不实现
AR guidance、human study、Rotation/Velocity 或跨任务 generalisation。

## Current Progress

- 已从完成并封存的 CoRL/DEMT 实验分支创建并推送
  `hpc-headless-tro`，起点为 `72ca390`。
- `docs/tro_plan.md` 已写成 execution-ready source of truth，包含：
  - H1–H5 预注册 contrasts；
  - event、planned/realised variation 和三个 evaluation regimes 的操作定义；
  - MVP-0A 五条件、两个 paired blocks、10 datasets、10 policies、300 rollouts；
  - Gate 0–7、screening decision rules、failure branches 和 Definition of Done；
  - 仅在 MVP-0A strong pass 后执行的 MVP-0B。
- 当前尚未修改 generator、创建 evaluation bank、采集新 demonstrations、训练新
  policy 或提交任何 TRO Slurm job。
- 当前实验阶段为 **Gate 0: Repository audit 尚未开始**。
- 前一阶段 CoRL/DEMT AR-settings anti-cherry-picking 实验已经关闭并压缩封存于
  `handoffs/legacy-corl-demt-experiments-archive.md`；不得把该阶段结果包装为 T-RO
  新贡献，也不得在本分支重启旧实验。
- 工作树中还存在四个与本任务无关的 0-byte 未跟踪文件：
  `[`, `count=0`, `done`, `fi`。保留且不要加入提交。

## What Worked

- 现有 S15–S35 Position pipeline 已具有 `N=30` collection、HDF5、training、
  checkpoint freeze、paired rollout manifests 和严格 merge 基础，可作为最小修改
  起点。
- 现有 `examples/rollout_contract.py`、Position/contact/temporal N50 evaluators
  已验证 shared state manifests、独立 RNG streams、逐 rollout JSON、Wilson interval
  和 stale/partial merge rejection。
- 已冻结研究边界：本周只回答 event-conditioned Position compatibility 是否存在，
  不把 screening rollout 当作独立 policy samples，也不预设“wide 必然更好”。
- 计划要求先通过 intervention decoupling 与 evaluation-bank calibration gates，
  能防止在 confound 未解决前浪费完整 training matrix。

## What Didn't Work

- None yet for the new TRO experiment; no implementation or execution has started.
- 旧 S15–S35 generator 同时改变 corridor/free-reach 与 pre-grasp scale，不能直接
  用来识别 event-local effects。
- 旧 shared-radius Position rollout 只回答 task-level scale sensitivity，不能证明
  free-reach coverage benefit 或 pre-contact precision mechanism。
- 不得复用已删除的 fixed-point temporal artifacts、错误 geometry 的
  `dataset/abla1_full`，或旧 `P00/P01/P10/P11` 2x2 设计作为本实验数据。
- 不得跳过 realised-variation leakage check、用 condition-dependent event boundary，
  或在看到其他 condition 结果后调整 evaluation bank。

## Key Files & Commands

- 唯一 source of truth：
  `docs/tro_plan.md`
- 前阶段只读总档案：
  `handoffs/legacy-corl-demt-experiments-archive.md`
- 现有 Position generator/evaluator：
  `examples/main_abla_1.py`
  `examples/eval_abla1_trained_policies.py`
- 现有 Position pipeline：
  `scripts/run_abla1_collect.sh`
  `scripts/check_abla1_dataset.py`
  `scripts/run_abla1_hdf5_slurm.sh`
  `scripts/submit_abla1_train_pipeline.sh`
  `scripts/run_abla1_eval.sh`
  `scripts/run_abla1_eval_merge.sh`
- 现有 paired rollout contract：
  `examples/rollout_contract.py`
- 已完成的 S15–S35 与 Position/Contact/Temporal execution context：
  `handoffs/legacy-corl-demt-experiments-archive.md`
- Gate 0 开始前的只读检查：
  ```bash
  git status -sb
  git branch --show-current
  git rev-parse --short HEAD
  rg -n "S15|S20|S25|S30|S35|corridor_start_radius|pre_grasp_radius" \
    examples scripts training_config
  ```

## Next Steps

1. 完整阅读 `docs/tro_plan.md`，并保持其 gate 顺序与 claim boundaries。
2. 执行 Gate 0 repository audit，创建本 sub-job 的 `implementation_notes.md`：
   - 定位 S15–S35 condition 定义和 generator state machine；
   - 用代码证据说明当前 radius 分别影响哪些 waypoints/events；
   - 记录 collection success、training seed/checkpoint rule、rollout start/success
     protocol 和已有 event/contact logs；
   - 给出最小修改文件清单及任何阻碍严格 event-local intervention 的问题。
3. Gate 0 通过后才实现 Gate 1：
   - config-driven `free_reach_radius` / `pre_grasp_radius`；
   - condition-independent event definition；
   - planned 与 realised event-local variation；
   - reference compatibility tests 和五条件各 2–3 条 smoke trajectories。
4. 在 target-event ordering 和 non-target leakage gate 通过前，不创建完整 datasets，
   不训练 10-policy matrix，不提交正式 rollout。
5. 每完成一个 gate，更新本 handoff 的 Current Progress、What Didn't Work、Next Steps
   和 Changelog。

## Open Questions

- 当前 generator 的 `corridor_start_radius` 是否能严格映射为 `free_reach_radius`，
  还是必须重新定义 event-local trajectory sampling。
- 当前 simulator 是否支持安全、可复现的 mid-episode pre-contact perturbation；
  若不支持，需要采用 plan 中预注册的 precontact subepisode fallback。
- `implementation_notes.md` 应放入现有实验目录还是新建
  `experiments/mvp0_position_event/`；Gate 0 必须先审计仓库惯例再决定。

## Changelog

- 2026-07-23: 创建新 TRO MVP-0 Position-event handoff，记录 execution-ready plan、
  当前 Gate 0 状态、已有可复用基础、禁止复用的旧结果和下一步审计顺序。
- 2026-07-23: 将旧 CoRL/DEMT handoff 引用统一替换为只读总档案，并记录当前
  `hpc-headless-tro @ 7c043cc` 基线。
