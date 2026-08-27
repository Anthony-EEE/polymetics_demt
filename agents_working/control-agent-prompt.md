# Launch Prompt: Simulation Control Group Full Pipeline

Copy everything below this line into a fresh Long Goal agent.

---

你现在负责 CoRL rebuttal 的 **Control 模拟实验完整 pipeline**。这是一个需要持续执行直到得到最终数值的 Long Goal，不是只写计划或只提交 Slurm。实验标签必须始终为：

`simulation_control_group`

工作仓库：

`/scratch/prj/eng_demt_robot_learning/polymetics_demt`

Target pipeline 已经由另一个 Agent 独立运行。你的最高优先级是：**绝不影响、修改、覆盖、取消或重复 Target 的任何工作。**

## 0. 启动顺序与事实来源

开始操作前只按以下顺序完整阅读：

1. `agents_working/README.md`
2. `handoffs/handoff_rebuttal.md`
3. `agents_working/control-simulation.md`
4. `rebuttal_dataset/simulation_control_group/smoke_d01_v1/summary.json`
5. `rebuttal_dataset/simulation_control_group/smoke_d01_v1/validation_report.json`
6. `rebuttal_dataset/simulation_control_group/full_seed20260806/participant_manifest.json`

不要扫描 `archive/`，不要读取旧 handoff。不要读取或执行 `agents_working/target-agent-prompt.md`；其中关于“Control 未授权”的旧句子已过时。

启动后立即在 `agents_working/control-simulation.md` 记录 `IN_PROGRESS`、时间、stage、PID/Slurm job ID、日志和输出路径。之后每个 stage 都实时更新。

## 1. 第一项必须完成：未知作业与重复提交审计

上一会话有一次 Control `sbatch` 调用被用户中断，没有拿到 job ID，因此**不能假设提交成功，也不能假设没有提交**。

在任何新提交前，先只读执行：

- `squeue -u k23114984`，按 job name 查找 `simulation_control_group_collect`；
- 用 `sacct` 检查当天最近作业；
- 查看 `rebuttal_dataset/simulation_control_group/full_seed20260806/logs/` 是否出现 `collect_<job>_<task>.{out,err}`；
- 查看 C01–C10 正式目录是否已经开始产生数据。

处理规则：

- 如果已存在 Control job：把 job ID 写入 Control ledger，接管并监控，绝不重复提交。
- 如果没有 Control job 且只有 preview/manifest/logs 空目录：通过全部预检后才提交一次。
- 不得仅凭 job ID 猜归属。任何不能证明属于 Control 的 job 都不得取消。
- **绝不取消、requeue、hold、修改或干预名字含 Target、路径指向 `simulation_target_group`、或记录在 `target-simulation.md` 的作业。**

## 2. 严格所有权与隔离

你只能写：

- `examples/main_obstacle_transport_control_participants.py`
- `examples/rebuttal_control_pipeline/`
- `rebuttal_dataset/simulation_control_group/`
- `agents_working/control-simulation.md`
- `agents_working/reviews/control-reviews-target.md`

你不得写：

- `examples/main_obstacle_transport_target_participants.py`
- `examples/rebuttal_target_pipeline/`
- `rebuttal_dataset/simulation_target_group/`
- `agents_working/target-simulation.md`
- `agents_working/reviews/target-reviews-control.md`
- `agents_working/README.md`
- `agents_working/control-agent-prompt.md`
- `agents_working/target-agent-prompt.md`
- `handoffs/handoff_rebuttal.md`
- 共享的 `examples/main_obstacle_transport.py`
- 共享的 `examples/eval_obstacle_transport_trained_policy.py`

Target 文件和结果只允许 read-only 检查。不要 commit、push、reset、checkout、清理 dirty tree 或删除旧诊断产物。

若必须修改共享文件，不要直接改。先在 Control ledger 的 `Shared-Change Requests` 写明文件、最小 patch、原因、Control 影响和 Target 影响，然后暂停该共享修改并请求 coordinator。Control 专属实现放在 `examples/rebuttal_control_pipeline/`。

## 3. 冻结 Control 科学协议

- 10 个 Control participants：`C01`–`C10`。
- `C01`–`C05` 使用 L route；`C06`–`C10` 使用 R route。
- 每人必须保留恰好 30 条成功 demonstration，共 300 条。
- 每条 demo 和每次 retry 都独立从完整 route x-z 支持域采样 middle waypoint：
  - L: `x ∈ [0.10, 0.30] m`
  - R: `x ∈ [0.70, 0.90] m`
  - `y = 0.25 m`
  - `z ∈ [0.19, 0.29] m`
- 没有 personal waypoint centre，没有逐 demo 收缩，没有 consistency guidance；第 1 条和第 30 条使用同样的完整支持域。
- IK 不可达、waypoint 未达到、target miss、box 未 settle 或 cylinder topple 的 attempt 只作为诊断，不能进入成功 raw/HDF5；保持同一 demo 的 cube start，换一个确定性 waypoint 重试，直到得到成功点。
- 30 个 cube starts 必须与 Target `full_seed20260806/participant_manifest.json` 逐 demo 完全一致。
- Rotation 和 velocity/timing 使用冻结共享设置，不得在当前 Control 数据中再增加 R/V 随机性。当前实验只比较 position consistency，避免 P/R/V confound。
- Cube physics、圆柱、Panda base、固定 gripper orientation、camera、sensing、target 和成功规则与 Target 完全相同。
- 初始 EE 为 `[box_x, box_y, box_z + 0.10]`，不得有 x/y offset。
- scripted grasp/lift 成功并验证 transport height 后才保存数据。
- `frame_0` 必须是 `policy_inference_start`、`time=0`、gripper closed；成功训练数据不得含 `scripted_*` frame。
- 成功条件保持 `target_xy_error <= 0.03 m`、box settled、`cylinder_tilt <= 10 deg`，且 realised middle-waypoint error `<= 0.04 m`。Contact 只作诊断，不新增“零接触”要求。

不得为了提高成功率收窄 support、改变 seed、修改阈值、只挑好看的点、改变 orientation/timing 或跳过失败记录。

## 4. 已完成且必须保留的证据

实现文件：

- `examples/main_obstacle_transport_control_participants.py`
- `examples/rebuttal_control_pipeline/collect_control_array.sbatch`
- `examples/rebuttal_control_pipeline/validate_raw_collection.py`
- `tests/test_obstacle_transport_control_participants.py`

正式 preview 已写到：

`rebuttal_dataset/simulation_control_group/full_seed20260806/`

已验证：

- 10 participants × 30 个 attempt-0 候选，共 300/300 unique waypoints；
- 每人的 x span 约 `0.177–0.199 m`，z span 约 `0.088–0.099 m`；
- 30/30 cube starts 与 Target 正式 manifest 精确一致；
- `smoke_d01_v1` 为 10/10 成功；
- C01 在 attempt 1 成功，C09 在 attempt 2 成功，其余 attempt 0 成功；
- 三个拒绝均为 `middle_waypoint_reachability`，补采逻辑有效；
- smoke raw boundary、成功阈值、10 个视频完整解码和 Control validator 均通过；
- 单元测试 5/5 通过。

不要重跑或覆盖 `smoke_d01_v1`。正式输出只能写到 `full_seed20260806/`。

## 5. Stage A：300 条正式数据

正式 root：

`rebuttal_dataset/simulation_control_group/full_seed20260806/`

冻结 seed：`20260806`。

在完成“未知作业审计”后：

- 若已有 Control array，就继续监控；
- 若没有，使用现有 wrapper 只提交一次：

```bash
sbatch --parsable examples/rebuttal_control_pipeline/collect_control_array.sbatch
```

数组应为 C01–C10，最多 3 个 renderer 并发。提交后持续监控到 terminal state；`PENDING` 或“已提交”不算完成。检查 `squeue`、`sacct`、exit code、stderr、PREEMPTED/TIMEOUT/OOM、部分写入和每人 summary。只允许恢复明确属于 Control 的失败 task，且记录原 job/task 和 deterministic retry。

10 个 participant task 全部完成后，先 merge：

```bash
/scratch/users/k23114984/conda/arcap/bin/python \
  examples/main_obstacle_transport_control_participants.py \
  --participants C01 C02 C03 C04 C05 C06 C07 C08 C09 C10 \
  --all-30 \
  --seed 20260806 \
  --output-dir rebuttal_dataset/simulation_control_group/full_seed20260806 \
  --skip-preview \
  --merge-only
```

然后运行完整 validator：

```bash
/scratch/users/k23114984/conda/arcap/bin/python \
  examples/rebuttal_control_pipeline/validate_raw_collection.py \
  --root rebuttal_dataset/simulation_control_group/full_seed20260806 \
  --expected-demos 30 \
  --seed 20260806
```

必须验证 10×30=300 条成功数据、每人 30 个独立 waypoint、经验 x/z spread、跨 participant 配对 cube starts、frame boundary、无 scripted frames、阈值、attempt provenance、JSON/frame/pointcloud 完整性。不要忽略 validator error。

## 6. Stage B：十个 participant-level HDF5

输出：

`rebuttal_dataset/simulation_control_group/hdf5/`

先 read-only 查看 Target 已冻结的 HDF5 schema、转换 manifest 和 loader 验证结果。Control 使用自己的 helper，在 Control 路径生成 C01–C10 十个独立 HDF5，每个恰好 30 trajectories，不能混 participant，不能写 Target。

HDF5 observation/action keys、dtype、shape、action gap、point count、post-grasp boundary、augmentation 和 split 规则必须与 Target 完全一致。若 Target 此 stage 尚未冻结，等待/监控 Target 产物，不要自行发明不同 schema。保存 raw→HDF5 provenance、hash、trajectory lengths，并重新读取全部文件验证无缺失和 loader 兼容。共享 simulator 在 release/settle 的 `commanded_speed` 可用 NaN 表示“不适用”；不要把该诊断字段误当 learner action，实际 learner 输入/动作必须按 Target schema 验证有限值。

## 7. Stage C：十个完全同配置 policies

输出：

`rebuttal_dataset/simulation_control_group/models/`

Control 必须 read-only 复用 Target 已冻结的 learner config、training seed、预算、split、checkpoint selection rule 和软件协议。不得逐 participant 调参，不得根据 rollout 选 checkpoint，不得给失败 participant 额外预算。

如果 Target training manifest 尚未冻结，先完成 Control raw/HDF5 并等待；不得抢先创建另一套不一致训练协议。所有 C01–C10 checkpoint 都要记录 config/HDF5 hash、job ID、日志并完成 load/inference smoke。

## 8. Stage D/E：复用 Target 的 paired rollout manifest，完成 100 rollouts

输出：

`rebuttal_dataset/simulation_control_group/policy_rollouts/`

Control 不生成一套新的 evaluation starts。必须等待并 read-only 复用 Target 冻结的 10-spec paired rollout manifest，核对 manifest hash，并在 Control 结果中引用相同内容/hash。

每个 C01–C10 policy 在同一 10 specs 上评估，共 100 rollouts。scripted 部分只到 grasp/lift 和 `policy_inference_start`；之后 obstacle avoidance、transport、release 必须由 learned policy 完成。保存逐 rollout JSON、视频、checkpoint hash、eval case、终止原因、target error、cylinder tilt、contacts 和 success。科学失败不得重跑替换；只有明确的基础设施失败可用相同 spec deterministic rerun，并保留原记录。

如果共享 evaluator 缺少 Control group label 或必要接口，不得直接修改共享文件。先在 Control ledger 提 change request；能在 `examples/rebuttal_control_pipeline/` 用 Control-only adapter 解决时优先使用 adapter，并证明行为与 Target evaluator 相同。

## 9. Stage F：Control 统计和只读 Target 对比

输出：

`rebuttal_dataset/simulation_control_group/analysis/`

计算：

- C01–C10 每人的 EDSR = 成功数 / 10；
- 10 participant EDSR 的 mean ± sample std，`ddof=1`；
- L（C01–C05）和 R（C06–C10）mean ± sample std；
- 100 rollout 原始成功表与 failure taxonomy；
- waypoint spread、target error、cylinder tilt、contacts 等诊断。

至少写出 `final_results.json`、`participant_edsr.csv`、`rollout_results.csv`、`validation_report.json`、`experiment_manifest.json` 和图/视频索引。

Target 结果可 read-only 用于最终 group comparison，但比较产物只能写入 Control analysis 或 Control review，绝不改 Target。确认双方 demo budget、HDF5 schema、learner config、checkpoint rule 和 paired manifest hash 一致后，才报告 Target–Control 差异。不要预设哪组一定更好。

## 10. 完成标准

只有以下全部满足才可说完成：

- 300/300 Control 成功 raw demos 已验证；
- C01–C10 每人 30 个 accepted broad waypoints，无中心/收缩，spread gate 通过；
- 10/10 HDF5 各 30 trajectories，schema 与 Target 一致；
- 10/10 policies 使用 Target 同一冻结训练协议并有可加载 checkpoint；
- 复用 Target 相同 10-spec manifest；
- 100/100 有效 Control policy rollouts 完成；
- overall/L/R participant-level EDSR mean ± sample std (`ddof=1`) 已产出；
- 所有 hashes、logs、videos、CSV/JSON 和 validation report 路径明确；
- `agents_working/control-simulation.md` 全部 stage 标记 COMPLETE；
- 全程没有修改、覆盖或取消任何 Target 文件或作业。

最终回复先给实际数值，再给 artifacts、验证结果、失败/重试和限制。未达到这些标准时不要说“完成”，继续从最近完整 stage 执行和监控。

---

End of launch prompt.
