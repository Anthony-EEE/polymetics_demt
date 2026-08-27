# Launch Prompt: Simulation Target Group Full Pipeline

Copy everything below this line into a fresh Long Goal agent.

---

你现在负责 CoRL rebuttal 的 **Target 模拟实验完整 pipeline**。这是一个需要持续执行直到得到最终数值的 Long Goal，不是只写计划、只提交任务或只完成某一个 stage。实验标签必须始终为：

`simulation_target_group`

工作仓库：

`/scratch/prj/eng_demt_robot_learning/polymetics_demt`

## 0. 启动顺序与唯一事实来源

开始操作前，依次完整阅读：

1. `agents_working/README.md`
2. `handoffs/handoff_rebuttal.md`
3. `agents_working/target-simulation.md`
4. `rebuttal_dataset/simulation_target_group/smoke_d01_v4/summary.json`
5. `rebuttal_dataset/simulation_target_group/smoke_d01_v4/participant_manifest.json`

`smoke_d01_v4` 是唯一权威 smoke。更早的 smoke 目录只是诊断记录，不能作为正式实验数据。若 handoff 中的旧描述与 `agents_working/README.md` 或 `target-simulation.md` 冲突，以后两者的冻结协议为准，并在 Target status 中记录冲突。

先在 `agents_working/target-simulation.md` 将状态改为 `IN_PROGRESS`，写入时间、当前 stage、PID/Slurm job ID、日志与输出路径。之后每完成或失败一个 stage 都更新该 ledger，不能等到最后才补。

## 1. 严格隔离和文件所有权

你只能写：

- `examples/main_obstacle_transport_target_participants.py`
- `examples/rebuttal_target_pipeline/`
- `rebuttal_dataset/simulation_target_group/`
- `agents_working/target-simulation.md`
- `agents_working/reviews/target-reviews-control.md`

禁止写入：

- 所有 `simulation_control_group` 数据、脚本、模型、日志和 Markdown；
- `agents_working/README.md`；
- `agents_working/target-agent-prompt.md`；
- 共享的 `examples/main_obstacle_transport.py`；
- 共享的 `examples/eval_obstacle_transport_trained_policy.py`；
- `handoffs/handoff_rebuttal.md`，除非用户或 coordinator 明确要求。

不要清理、覆盖、移动或删除现有未跟踪文件和旧诊断结果。不要提交或 push，除非用户明确要求。

如果完整 pipeline 必须修改共享代码，不要直接修改：先在 `agents_working/target-simulation.md` 的 `Shared-Change Requests` 写清楚文件、最小 patch、原因、对 Target 的影响、对未来 Control 可比性的影响，然后暂停该共享修改并请求 coordinator 批准。Target 专属 helper 一律放入 `examples/rebuttal_target_pipeline/`。

## 2. 冻结实验协议，不得漂移

- 10 个 synthetic target participants：`T01`–`T10`。
- `T01`–`T05` 为 L route；`T06`–`T10` 为 R route。
- 每人必须有 30 条成功 demonstration，共 300 条成功数据。
- 每位 participant 使用 `smoke_d01_v4/participant_manifest.json` 中冻结的个人 waypoint centre。
- 30 条 demo 的 waypoint variance 按现有 target participant 脚本从 large variance 逐渐收缩；不能为了提高成功率修改 centre、收缩曲线或 start distribution。
- 所有人和左右 route 使用同一 broad cube-start distribution。
- Cube、可倒圆柱、Panda base、固定 gripper orientation、target、容差和 success criterion 均使用冻结共享环境。
- 每次 collection 和 rollout 都先 sample cube start，再执行 scripted fixed-orientation grasp/lift。
- 初始 EE 必须为 `[box_x, box_y, box_z + 0.10]`，x/y 不得有任何 offset。
- 只有 grasp 和 transport height 验证通过后才开始保存 demonstration 或运行 policy。
- `frame_0` 必须是 `phase=policy_inference_start`、`time=0`、gripper closed；训练数据不得含任何 `scripted_*` frame。
- scripted setup 失败保存 0 帧；transport/target/cylinder 失败保留诊断记录，但不能进入成功 HDF5，必须补采直到每人恰好 30 条成功 demo。
- 成功条件：cube settle 后质心到 target XY 距离不超过 `0.03 m`，且 cylinder tilt 不超过 `10 deg`。contact 字段保留为诊断，不能擅自把“零接触”增加为成功条件。
- 长距离 scripted transport 使用 incremental Cartesian IK。

## 3. Stage A：预检与 300 条数据采集

先做只读预检：检查 git/worktree 状态、Python 环境、可用 GPU/Slurm、磁盘空间、权威 smoke 与脚本参数。不要覆盖已有实验。

正式 root 固定为：

`rebuttal_dataset/simulation_target_group/full_seed20260806/`

使用冻结 seed `20260806`。推荐命令基线：

```bash
/scratch/users/k23114984/conda/arcap/bin/python \
  examples/main_obstacle_transport_target_participants.py \
  --all-30 \
  --seed 20260806 \
  --max-attempts-per-demo 30 \
  --output-dir /scratch/prj/eng_demt_robot_learning/polymetics_demt/rebuttal_dataset/simulation_target_group/full_seed20260806 \
  --save-raw-frames \
  --save-videos
```

先核对 `--help` 和代码，确认参数仍匹配后再运行。资源受限时使用 2–3 个 process 的保守并发，不能一次启动 10 个 renderer。若使用 Slurm，提交后必须持续监控直到完成，检查 `squeue/sacct`、exit code、stderr、OOM/TIMEOUT/CANCELLED、产物数和部分写入；“job 已提交”不算完成。

采集完成后必须生成机器可读 validation report，至少验证：

- 10 participants 全部存在；
- 每人恰好 30 successful demos，总数恰好 300；
- demo index/participant/route/group/seed 唯一且一致；
- 每个成功 demo 的 frame 0 满足 post-grasp boundary；
- successful raw data 中零 `scripted_*` frames；
- target error、cylinder tilt、waypoint realised error 均满足冻结阈值；
- failed attempts 没有混入正式成功 demo；
- 没有空目录、截断 JSON、缺失 frame 或 stale/partial artifact。

不要通过放宽阈值、改变 seed、改变 participant waypoint 或静默重跑“更好看”的数据来修复失败。

## 4. Stage B：转换为 10 个 participant-level HDF5

先在仓库中用 `rg` 查找已有数据转换器、HDF5 schema 和现有训练数据样例，复用项目真实格式，不要发明不兼容 schema。若需要新 helper，只写到 `examples/rebuttal_target_pipeline/`。

输出 root：

`rebuttal_dataset/simulation_target_group/hdf5/`

要求：

- T01–T10 每人一个独立 HDF5；
- 每个 HDF5 恰好 30 trajectories，不得跨 participant 混合；
- 只包含 post-grasp policy segment；
- observation/action keys、dtype、shape、normalisation及时间对齐和当前 learner 完全兼容；
- 每个 trajectory 可反查到 raw demo、participant、route、demo index 和 source seed；
- 写出 schema summary、trajectory length summary、raw→HDF5 manifest、文件 hash；
- 重新读取全部 HDF5，验证可解析、无 NaN/Inf、shape 一致、action/observation 长度合法。

转换后先做一次最小 loader smoke，再开始批量训练。

## 5. Stage C：训练 10 个 participant-level policies

输出 root：

`rebuttal_dataset/simulation_target_group/models/`

先定位仓库已有 learner/training entry point 和已验证 config。训练前冻结并写入一个 experiment manifest：

- 完整 config 和 config hash；
- learner architecture；
- training seed；
- epoch/step budget、batch size、optimizer；
- observation/action schema；
- checkpoint selection rule；
- software/git state；
- T01–T10 对应 HDF5 hash。

10 个 policy 必须使用完全相同的 learner、超参数、training seed、训练预算和 checkpoint selection rule。不能逐人调参，不能根据 rollout performance 选择 checkpoint，不能对失败 participant 额外训练。checkpoint rule 必须在首个正式训练前冻结；优先沿用仓库当前研究 pipeline 的既定规则。若仓库不存在明确规则，记录一个统一、无需 test-rollout 信息的规则后再使用。

每个训练 job 检查 exit code、loss 是否有限、checkpoint 是否完整可加载。为每个 participant 保存训练日志、最终/被选 checkpoint、config、seed 和 source-HDF5 hash。10 个 checkpoint 全部通过 load/inference smoke 后才进入正式 rollout。

## 6. Stage D：冻结 10 个 paired rollout specs

所有 policy 必须评估在同一组 10 个 rollout specs 上；不能每个 policy 各 sample 一套 start。

在任何正式 policy rollout 之前，用独立、固定的 evaluation seed 生成并冻结一个 manifest，包含：

- `eval_case_id` 0–9；
- 10 个彼此不同的 cube initial positions；
- 完整 simulator/evaluation seed；
- cube pose 和所有影响随机性的字段；
- frozen task/success thresholds；
- manifest hash。

10 个 start 都从冻结的 broad cube-start distribution 产生，并先通过 scripted grasp/lift 可行性预检。预检只验证共同 scripted setup，不得看任何 policy 表现。若某个 start 对共同 setup 不可行，按预先固定、可追踪的 deterministic replenishment 规则替换，并在 manifest 中保留 rejected candidate 记录。

此 manifest 是未来 Control 组也要复用的 paired evaluation contract。保存到 Target analysis/rollout metadata 中，但不要写 Control 目录。

## 7. Stage E：100 次 learned-policy rollouts

输出 root：

`rebuttal_dataset/simulation_target_group/policy_rollouts/`

对 T01–T10 的每个 policy 依次运行同一组 10 specs，共 100 次正式 rollout。每次必须：

1. 使用 manifest 指定的 cube start/seed reset simulator；
2. scripted approach/grasp/close/lift 到规定 transport height；
3. 验证 grasp/height；
4. 从与训练 `frame_0` 相同的 `policy_inference_start` 状态启动 learned policy；
5. policy 负责 obstacle avoidance、transport 和 release；
6. cube settle 后按冻结的 target/cylinder criterion 计 success；
7. 保存视频、逐 rollout JSON、policy/checkpoint hash、eval spec ID、target error、cylinder tilt、contacts、termination reason 和 success。

不能把 scripted transport 偷放进 rollout；policy inference 之前只能有共同的抓取与抬升。不能重跑失败 rollout 来替换结果。基础设施崩溃与科学失败必须分开标记：只有可证明为 renderer/process/I/O 等基础设施故障、且 policy 尚未产生有效科学结果时，才能用同一 spec deterministic rerun，并保留原 failure record。

100 次跑完后验证 `(participant, eval_case_id)` 恰好一一对应、无重复无缺失，并检查每个结果引用正确 checkpoint 和 shared manifest hash。

## 8. Stage F：participant-level 统计与最终产物

最终 analysis root：

`rebuttal_dataset/simulation_target_group/analysis/`

统计单位是 participant-level policy，不是 300 demonstrations，也不是 100 rollouts。计算并报告：

- 每个 T01–T10 的 EDSR = 成功数 / 10；
- 10 个 participant EDSR 的 mean ± sample standard deviation，标准差必须 `ddof=1`；
- L participants（T01–T05）的 mean ± sample std；
- R participants（T06–T10）的 mean ± sample std；
- 100 rollouts 的原始成功表，但明确它不是独立 participant-level 显著性样本；
- failure taxonomy：target miss、cylinder topple、policy timeout、grasp/setup infrastructure issue 等；
- 关键诊断：target error、cylinder tilt、contacts、realised route/waypoint behaviour（能从 rollout 稳健计算时）。

至少产出：

- `final_results.json`
- `participant_edsr.csv`
- `rollout_results.csv`
- `validation_report.json`
- `experiment_manifest.json`
- 简洁汇总图和 representative/失败视频索引
- 一份可直接用于 rebuttal 的纯事实结果摘要（不要在结果出来前预设“Target 一定更好”）

所有 mean/std 用代码从保存的 10 个 participant EDSR 重新计算并交叉检查；JSON/CSV/正文数值必须一致。

## 9. 互相监督，但绝不互相修改

Control 协议当前尚未获得用户授权，所以不要启动、猜测或实现 Control 实验。未来 Control 有产物后，你只能 read-only audit，并把发现写入你拥有的：

`agents_working/reviews/target-reviews-control.md`

绝不能修 Control 文件。重点审核双方环境、success criterion、demonstration budget、HDF5 schema、learner/config/checkpoint rule 和 10 个 paired rollout specs 是否一致，唯一差异是否确实只有用户授权的 teaching-data manipulation。

## 10. 持续执行和完成标准

遇到失败先读取日志、定位根因并在 Target-owned 范围内修复，然后从最近完整 stage 恢复。保持可重复、可审计，不得静默改变协议。长任务期间至少每完成一个 stage 更新一次 ledger；持续监控，不能因为 shell 断连或一次 job failure 就结束。

只有以下全部满足时才可声明 Long Goal 完成：

- 300/300 成功 raw demos 已验证；
- 10/10 HDF5 各含 30 demos并通过 loader/schema validation；
- 10/10 policy 使用完全相同的冻结训练协议并有可加载 checkpoint；
- shared 10-spec manifest 已冻结；
- 100/100 有效 policy rollouts 已完成；
- 10 个 participant EDSR、overall/L/R mean ± sample std (`ddof=1`) 已产出；
- 所有 manifests、hashes、logs、videos、CSV/JSON 和 validation report 路径清楚；
- `agents_working/target-simulation.md` ledger 已逐项标成 COMPLETE 并记录证据。

最终回复必须先给实际结果，再给 artifact 路径、验证结论、任何失败/重试与仍存在的限制。若尚未满足上述标准，不要说“完成”。

---

End of launch prompt.
