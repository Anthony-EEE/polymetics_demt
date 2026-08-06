# T-RO 实验总览：为什么做、怎么做、为什么这样做

**日期：** 2026-07-26
**当前阶段：** Stage 2c Position composition Gate 3 出现真实 runtime-RNG
protocol blocker；不得原样恢复 deterministic retry loop
**当前执行计划：**
`experiments/tro_stage2_position_composition/PLAN.md`

## 一句话目标

DEMT 已经证明 demonstration structure 会影响机器人学习。T-RO 要进一步让机器人
通过 deployment experiments 学会：

> 不同任务阶段允许多大的 demonstration variation，以及哪些阶段需要更集中；
> 然后把这些知识用于新任务的自动 guidance 和人类教学训练。

完整逻辑为：

```text
多个机器人 source tasks
        ↓
分别改变 Start / Approach / Grasp 等阶段的数据 variation
        ↓
训练 policy 并测 deployment success
        ↓
学习“哪个阶段允许多样、哪个阶段需要集中”
        ↓
在 held-out task A 上自动生成 guidance
        ↓
训练人类教师，撤除 guidance 后测 retention
        ↓
在完全未见过的 task B 上无 guidance 测 teaching transfer
```

---

## 1. 为什么做？

### 1.1 DEMT 已经证明了什么

DEMT 已经证明：

- 人能成功完成任务，不代表 demonstrations 适合机器人 learner；
- Position、Rotation、Velocity 数据结构会影响 policy deployment success；
- 相同 demonstration 数量下，更适合 learner 的数据可以训练出更好的 policy；
- AR guidance 可以帮助 novice 产生更适合 learner 的 demonstrations。

这些结果是 T-RO 的起点，不是 T-RO 要重新包装的新贡献。

### 1.2 DEMT 仍然缺少什么

DEMT 的设置主要由研究者人工决定：

- 人工选择 P/R/V candidates；
- task-level 参数可能同时改变多个 trajectory stages；
- corridor、orientation tolerance 和 speed range 由研究者设置；
- 到新任务时仍需要研究者重新设计 guidance。

以 Position S15–S35 为例，原条件同时改变：

```text
Start radius
Approach/pre-grasp radius
```

因此旧实验能说明整体 Position scale 影响 policy，但不能回答：

- Start variation 的独立作用是什么；
- Approach variation 的独立作用是什么；
- variation 的作用是否依赖 trajectory stage；
- 这些 stage-conditioned 规律能否迁移到新任务。

### 1.3 T-RO 的核心研究问题

T-RO 要回答：

> 机器人能否从多个任务的 deployment results 中学出 stage-conditioned
> demonstration requirements，并用于一个没参与训练的新任务？

可能的规律包括：

- Start variation 增加初始状态 coverage；
- Approach/Descent variation 过大时，在固定数据预算下可能降低抓取精度；
- Grasp 附近的 Position/Rotation 可能需要更集中；
- 非接触关键阶段可以允许更多 variation，从而减少对人的限制。

这些是待验证假设，不是预设结论。实验也必须允许相反结果。

### 1.4 为什么还需要 human study

Robot deployment 只能告诉我们：

> 什么 demonstrations 对固定 learner 有用。

它不能直接证明：

> 什么 guidance 容易被人理解、实现、保留和迁移。

因此整篇 T-RO 必须分开验证：

1. **Robot compatibility：** 机器人需要什么数据；
2. **Guidance realisation：** guidance 能否让人产生目标数据；
3. **Human teaching：** 撤掉 guidance 后，人能否保留并迁移教学行为。

---

## 2. 怎么做？

## Stage 1：单任务机制验证——当前 Position MVP

使用现有 PyBullet grasping：

```text
Start → Approach → Descent → Grasp → Lift
```

轨迹、generator、grasp target 和 lift target 不变，只把原 S15–S35 中共同变化的
两个 radius 拆开。

旧 S25 `(25 cm, 6.0 cm)` 与 Reference 完全相同，因此保留为 historical
reference，不重新采集和训练。新实验只做四个拆分条件：

| New condition | Start radius | Approach radius |
|---|---:|---:|
| Start-tight | 15 cm | 6.0 cm |
| Start-wide | 35 cm | 6.0 cm |
| Approach-tight | 25 cm | 3.6 cm |
| Approach-wide | 25 cm | 8.4 cm |

回答：

- Start variation 是否影响 outer-start coverage；
- Approach variation 是否影响最终 grasp/lift success；
- 两个阶段的 variation effect 是否不同。

评估：

- 复用旧正式 N50 shared-start manifest；
- Reference-range starts：旧 manifest 中 0–25 cm 的 25 个 states；
- Outer starts：旧 manifest 中 25–35 cm 的 25 个 states；
- Primary outcome：`cube z >= 0.20 m`；
- 每个 dataset 30 条成功 demonstrations；
- learner、40 epochs、epoch-40 checkpoint 和 rollout states 全部固定；
- 先做一个 4-policy paired block；
- 只有任一预注册 primary contrast 达到 `4/25 = 0.16` 的预期方向，才做第二个
  independent 4-policy block。

第一 block 没有方向性信号就因 futility 停止。第二 block 只用于确认第一 block
中值得确认的信号。无论结果如何，Stage 1 结束后都不自动启动 Stage 2。

本阶段的唯一执行规范见：

```text
experiments/mvp0_position_event/PLAN.md
```

## Stage 2：Position axial five-repeat replication

Stage 1b 的 single-block early-stopping confirmation 将
`START25_APP3P6` 识别为最佳 observed policy，但旧 B0/B1 learner blocks
仍然不稳定，legacy reference 也存在 dataset/training provenance mismatch。
因此当前不直接执行 Position corner/composition experiment，而先对既有 axial
条件做五个 dataset-policy repeats：

| Condition | Start | Approach |
|---|---:|---:|
| `START15_APP6` | 15 cm | 6.0 cm |
| `START35_APP6` | 35 cm | 6.0 cm |
| `START25_APP3P6` | 25 cm | 3.6 cm |
| `START25_APP6` | 25 cm | 6.0 cm |
| `START25_APP8P4` | 25 cm | 8.4 cm |

每个 condition 最终都有 canonical seed `1–5` 五个 dataset-policy slots。
为避免重复实验和浪费存储：

- seed 1–3 主要为新实验；
- canonical seed 4 复用旧 Block 1 data
  (`collection=1702`, `training=2702`) 并 early-stop 重训；
- canonical seed 5 复用 Stage 1b
  (`collection=1701`, `training=2701`)；
- legacy `START25_APP6` seed-1 data/policy 直接复用；
- reference seed 2–5 补齐为新的 matched slots。

总计为 25 个 policy slots，其中新增 16 组 data、20 个 policy；正式评估统一
使用 rollout seeds `1–5`，每 policy 每 seed 为 25 inner + 25 outer，共
6,250 rows。`1701/2701` 是一个 dataset-policy repeat，绝不拆成两个独立样本。

本阶段回答：

- tighter Approach 是否跨五个独立 policy realisations 优于 reference 和 wide；
- Start variation 的 deployment effect 是否稳定；
- Stage 1b observed winner 是否具有 paper-level repeatability。

完整执行和判定规则只以
`experiments/tro_stage2_position_axial_replication/PLAN.md` 为准。Stage 2 的
固定结果、后续 ID/OOD rerollout 和 GO-to-composition 决定记录在本文末尾。

## Stage 2c：Position composition missing cells

Stage 2 axial 和 condition-relative ID/OOD rerollout 表明 Start coverage 与
Approach variation 具有不同的 deployment trade-off，但现有五个条件只覆盖
3 x 3 Start x Approach 网格的中间行和中间列。进入多个 source tasks 前，先只补
四个缺失 cells：

| New condition | Start | Approach |
|---|---:|---:|
| `START15_APP3P6` | 15 cm | 3.6 cm |
| `START15_APP8P4` | 15 cm | 8.4 cm |
| `START35_APP3P6` | 35 cm | 3.6 cm |
| `START35_APP8P4` | 35 cm | 8.4 cm |

旧五个 axial conditions、datasets、policies、checkpoints 和 rollouts 全部作为
immutable anchors 复用。新实验只创建四个 corners 的五个 canonical
dataset-policy repeats，共 20 个新 datasets、20 个新 policies。主分析在九个
conditions 的共同绝对 deployment states 上预注册 Start x Approach
difference-in-differences；RMAX40 condition-relative ID/OOD 作为次级泛化诊断。

本阶段回答：

- Approach-tight/reference/wide 的作用是否依赖 Start support；
- Start 和 Approach effects 在测试网格内是否存在可复现 interaction；
- 单任务 Position response surface 是否足以作为 Stage 3 compatibility table
  的第一个 source-task block。

唯一执行规范为：

```text
experiments/tro_stage2_position_composition/PLAN.md
```

本阶段完成后仍须停止，不自动启动 Stage 3。

## Stage 3：多个 source tasks 与 compatibility model

单个 grasping task 只能证明 within-task stage dependence，不能证明 cross-task
learning。

因此后续需要多个 source tasks，每个任务先使用 task code 已知的 scripted phases：

```text
Grasping:
Start → Approach → Descent → Grasp → Lift

Insertion:
Start → Approach → Align → Insert

其他 manipulation task:
Start → Transport → Contact-critical stage → Completion
```

不在第一版同时学习自动 phase segmentation。

在每个任务中：

- 一次只改变一个 stage 的 Position variation；
- Position 机制成立后再加入 Rotation 和 Velocity；
- 固定 learner 和 `N=30`；
- 训练多个 independent policies；
- 在共同 nominal 和明确 shifted deployments 中评估。

形成 robot-side 数据表：

```text
task features
stage features
variation type
variation magnitude
learner
data budget
deployment distribution
policy success
```

然后训练低复杂度 forward compatibility model：

```text
输入：task/stage features + variation setting
输出：预计 deployment success
```

第一版优先使用 regularised logistic/binomial regression、additive model 或 shallow
tree，不从小数据直接训练复杂 encoder-decoder。

## Stage 4：held-out task A 上预测并生成 guidance

选择一个未参与 compatibility model 训练的新任务 A。

流程：

1. 输入 task A 的几何和 stage features；
2. 预测各阶段适合的 variation；
3. 在查看 task A 新结果前冻结预测；
4. 用固定规则把预测转成 guidance；
5. 在 task A 上进行 robot-side held-out validation；
6. 验证人使用 guidance 后是否实际产生目标 variation。

Robot-side baselines 至少包括：

- predicted stage-conditioned；
- reversed；
- all-tight；
- all-wide/reference。

这一步分别回答：

- compatibility rule 是否跨任务有效；
- guidance 是否真正实现了目标 demonstration distribution。

## Stage 5：human teaching、retention 与 transfer

建议至少包含：

| Group | Task A training |
|---|---|
| Unguided control | 无 guidance |
| Manual/DEMT guidance | 人工设计 guidance |
| T-RO generated guidance | 模型生成 guidance |

Task A 流程：

```text
A unguided pre-test
        ↓
A guided training
        ↓
移除 guidance
        ↓
A unguided post-test
```

测量：

- human task success；
- realised demonstration structure；
- workload 和 guidance burden；
- retention；
- 用 post-test demonstrations 训练出的 A-policy deployment success。

随后使用进一步未见任务 B：

```text
Task A training 完成
        ↓
Task B 第一次出现
        ↓
完全无 guidance
        ↓
收集 demonstrations
        ↓
训练 B-policy 并 rollout
```

Task B 用于检验 human teaching-skill transfer，而不是 task A corridor 的记忆。

---

## 3. 为什么这样做？

### 3.1 为什么先做 Position MVP

整个 T-RO 建立在一个最小前提上：

> variation 的作用确实随 trajectory stage 改变。

如果 Start 和 Approach variation 没有不同 effect，就没有理由立刻扩展 Rotation、
Velocity、多任务模型或 human study。

### 3.2 为什么保持 scripted phases

当前科学问题是“每个阶段需要什么数据”，不是“如何自动发现阶段”。如果同时学习
phase segmentation 和 compatibility，失败时无法判断是哪一部分出错。

### 3.3 为什么一次只改变一个 stage

这是从旧 S15–S35 中识别原因的最直接方法。两个 radius 同时改变时无法判断谁导致
policy 差异；一次只改一个 radius 才能解释结果。

### 3.4 为什么复用旧 S25 和 evaluation states

旧 S25 就是新设计的 `(25 cm, 6.0 cm)` Reference。旧正式 50-state manifest
按几何半径恰好分成 25 个 reference-range states 和 25 个 outer states，并且
旧 S25 已在这些 states 上完成 rollout。把它作为 historical anchor 可以减少
重复实验，同时不参与新四条件的 primary contrasts。

旧 S15/S35 不能被重新命名为 Start-tight/Start-wide，因为它们同时改变了
Approach radius，而且旧 demonstrations 不是跨 condition paired samples。它们只作
secondary historical evidence。

### 3.5 为什么先做一个 block

Stage 1 是机制 screening，不是最终 paper-level significance test。先执行一个
预注册 paired block；只有出现足够大的预期方向信号才付出第二个 block 的采集和
训练成本。这样 null result 最多只需 4 个新 policy，而不是无条件训练 10 个。

### 3.6 为什么固定 learner、`N=30` 和训练 protocol

实验要测 demonstration distribution 的影响。如果 demonstration 数量、learner、
training 或 checkpoint rule 同时变化，就不能把结果归因于 Start/Approach radius。
新 policy 统一训练 40 epochs，并固定使用 epoch-40 checkpoint；不得根据 validation
或 rollout outcome 为不同 condition 选择不同 epoch。

### 3.7 为什么需要多个 source tasks

只在 grasping 上得到的规律可能是 task-specific。必须在多个 source tasks 上学习，
再冻结并预测 held-out task A，才能支持 cross-task claim。

### 3.8 为什么使用 forward model

相同 deployment success 可能对应多个可行 variation setting，不存在唯一逆解。
因此先预测“某种 variation 会产生什么 deployment outcome”，再在满足 success
要求的候选中选择对人约束较小的 setting。

### 3.9 为什么 held-out A 和 B 分开

- Held-out A：检验模型能否为新任务生成 guidance；
- A 撤除 guidance：检验 retention；
- Held-out B 完全无 guidance：检验 human teaching-skill transfer。

只在 A 上测试，无法区分人真正学会教学原则，还是只记住 task A guidance。

### 3.10 为什么最终仍要训练 human-demo policies

Human trajectories 更整齐不等于机器人学得更好。最终标准仍然是：

> 用这些 demonstrations 训练出的 policy，在 deployment 中是否更成功。

---

## Claim ladder

Stage 1 通过后最多允许：

> Under a fixed learner and 30-demonstration budget in the tested grasping
> task, Start and Approach position variation have different deployment effects.

Stage 3 held-out robot task 通过后才允许：

> Deployment interventions can learn stage-conditioned demonstration
> compatibility that transfers across the tested tasks.

Stage 4 通过后才允许：

> Predicted compatibility settings can be translated into guidance for a
> held-out task.

Stage 5 A/B human study 通过后才允许：

> Generated guidance produces retained human teaching behaviour that transfers
> unguided to a further unseen task.

## 当前边界

- 当前只允许执行 Stage 2c Position composition 的四个 missing cells；
- 已完成的 Stage 2 axial 与 RMAX40 artifacts 均为 immutable anchors，不重训、
  不重采、不覆盖；
- 不修改 trajectory 的 `Start → Approach → Descent → Grasp → Lift` 结构；
- 不实现 contact state machine、mid-episode perturbation 或自动 phase discovery；
- 不启动 Rotation、Velocity、cross-task model 或 human study；
- composition 完成后停止，不自动启动 Stage 3。

## Stage 2 Position axial replication 执行结果（2026-07-25）

Stage 2 已按
`experiments/tro_stage2_position_axial_replication/PLAN.md` 完整执行并停止。
严格验证覆盖 25/25 dataset-policy slots、250/250 正式 rollout tasks 和
6,250/6,250 rollout rows；每个 canonical slot 的五条件 accepted latents
严格配对。

两个 locked reused-slot paths 触发了 PLAN 中预注册的 whole-slot fallback：
canonical seed1 的 legacy candidate 2 在 `START35_APP6` waypoint IK 不可达，
canonical seed5 的 Block-0 candidate 2 在 reference 条件下持续未满足 lift
成功判据。因此 seed1 与 seed5 都在新 namespace 中重建完整五条件 slot，并保留
actual source seeds `1/1` 与 `1701/2701`。最终 active artifacts 为 21 个新、
4 个复用 datasets（630 条新成功 demonstrations），以及 25 个新、0 个复用
policies；25-slot 科学矩阵未改变。

预注册 primary 结果为 `partial`：

- `D_candidate_reference`：五槽 mean delta `-0.0400`，`2/5` 为正，未通过；
- `D_candidate_wide`：五槽 mean delta `+0.2088`，`4/5` 为正，通过；
- combined five-policy ranking：
  `START25_APP6 > START25_APP3P6 > START15_APP6 > START35_APP6 > START25_APP8P4`。

三条 rollout tasks 遭遇 infrastructure `PREEMPTED`；其 partial outputs 已归档，
仅使用完全相同 frozen inputs 做 clean retry。没有按 policy performance 重试。
完整统计、Wilson descriptive intervals、policy-level cluster bootstrap、
validation histories、sensitivity analyses 和 exact pairing assertion 位于
`experiments/tro_stage2_position_axial_replication/analysis/`。

Stage 2 完成时尚未启动 Position composition、Rotation、Velocity、cross-task、
AR 或 human study。

## Stage 2 condition-relative ID/OOD rerollout 结果（2026-07-26）

Stage 2 的 25 个 frozen policies 随后在 condition-relative Start support 下完成
独立 rerollout。最初的 `R_MAX=0.45 m` pilot 因 joint IK conditioning 产生明显
方向不均匀，仅作为 audit evidence 保留；经用户批准后，active protocol 冻结为
`R_MAX=0.40 m`，没有重训或覆盖任何旧 Stage 2 artifact。

Active RMAX40 v2 严格验证 250/250 tasks 和 6,250/6,250 rollout rows。结果为：

- `START25_APP3P6` 与 `START25_APP6` 的 ID mean 均为 `0.4784`；
- OOD mean 分别为 `0.3168` 与 `0.3600`；
- `APP3P6` 的跨 policy 波动更小，而 `APP6` 的平均 OOD success 更高；
- ID/OOD Pareto front 为 `START15_APP6` 与 `START25_APP6`；
- balanced ranking 只作描述，不把不同 Start families 的 condition-relative
  banks 解释成共同绝对 deployment distribution。

完整 authority、结果与审计位于：

```text
experiments/tro_stage2_position_axial_idood_rerollout/
handoffs/tro-stage2-position-axial-id-ood-rerollout.md
```

## GO-to-composition stage gate（2026-07-26）

用户明确批准 Stage 2 正式结束并进入 Position composition 协议。该 GO 决定基于：

1. Stage 2 预注册结果保持 `partial`，其中 candidate-minus-wide contrast 通过；
2. RMAX40 rerollout 进一步确认 Start coverage 与 Approach variation 呈现不同
   的 ID/OOD、均值与复现波动 trade-off；
3. 现有证据足以支持检验 Start x Approach interaction，但不足以把
   `START25_APP3P6` 或 `START25_APP6` 宣称为普遍最优。

这个 stage gate 不改变任何旧 classification，也不授权半径搜索。下一阶段仅补
`START15/35 x APP3P6/APP8P4` 四个 missing cells，并以
`experiments/tro_stage2_position_composition/PLAN.md` 为唯一执行规范。

## Stage 2c composition v1 blocker 与 v2 修订（2026-07-26）

Composition 的 Gate 0、Gate 1 和 Gate 2 已完成：

- 25 个旧 checkpoint 与 HDF5 anchors、Stage 2/RMAX40 顶层 hashes 均复核不变；
- 600/600 个 four-corner frozen-latent records 与五个 axial anchors 的
  normalized latent 精确一致并通过 waypoint IK；
- 38 个相关测试通过；
- Slurm smoke array `36053326` 的五个 canonical seeds 全部完成四 corners。

正式 collection array `36053381` 随后出现两个 scientific failures，均为
`START35_APP8P4`：

- canonical seed4，frozen candidate 4，final cube z
  `0.03498996287124328 m`；
- canonical seed5，frozen candidate 1，final cube z
  `0.03498985718810666 m`。

两者都未达到 frozen success threshold `0.20 m`。v1 当时把它们视为 terminal
scientific failures，因此没有 retry；也没有更换 latent、缩减样本、重建旧
anchors 或放宽 pairing。剩余 seed1-3 collection tasks 已立即取消，所有
partial rows 排除于训练和分析。

用户随后明确修订协议：保持每个 canonical seed 的 30 个 frozen normalized
latents 不变；一个 latent 的四个新 corners 构成 atomic attempt bundle。任一
corner 失败，则整组四 corners 的该次 attempt 全部归档且不进入 dataset，并用
确定性的新 attempt seed 整组重试，直到同一次 attempt 四个 corners 都成功。
这不是新增 sample/latent，也不是只为失败 condition 挑一次好运结果；最终每个
dataset 仍恰好 30 条 accepted demonstrations。

v1 的两个 failures、blocker 和 hashes 必须作为历史审计证据保留，但不再构成
terminal blocker。新的 YOLO agent 必须先修改并测试 collector、冻结
`protocol_v2.json`，然后才能恢复 Gate 3。当前 Definition of Done 仍未满足；
HDF5、training、checkpoint freeze、两个 formal rollout surfaces、merge 和
interaction/ID-OOD analysis 均未启动。Rotation、Velocity、Stage 3、
cross-task、AR 与 human study 也均未启动。协议证据位于：

```text
experiments/tro_stage2_position_composition/manifests/protocol_blocker.json
experiments/tro_stage2_position_composition/manifests/protocol_amendment_v2.json
handoffs/tro-stage2-position-composition.md
```

Protocol v2 随后已实现、测试和冻结：43/43 个相关测试通过，旧 progress 迁移
保留 17 个完整 four-corner bundles、归档 3 个 interrupted bundles，并保留
seed4/5 的两个 v1 scientific failures。Formal collection v2 array
`36054403` 执行了 90 个新的 atomic scientific attempts。

这次执行发现了与失败次数无关的真实协议问题。派生 attempt seed 正确写入
metadata，并调用 Python/NumPy seeding；但 paired-latent physics path 此后使用
固定 cube、固定 normalized offsets、固定 IK/controller/PyBullet settings，
没有任何影响动力学的 RNG draw。对每个 blocked latent，多个不同派生 seeds
得到逐位相同的 failed `final_cube_z`；没有一个 failed bundle 在后续 attempt
转为 accepted。继续运行只会无限复制相同 deterministic outcome，不能实现
协议声称的 runtime physics RNG。

因此 job `36054403` 的 5/5 tasks 在 causal audit 后被停止并监控到 terminal
`CANCELLED`，五个 in-flight incomplete bundles 全部归档。没有擅自添加 cube、
contact、joint、waypoint、timing 或 solver perturbation，因为这些都需要新的
预注册分布并会改变 frozen experiment。当前 accepted bundle counts 为
seed1–5=`6,21,5,2,1`；HDF5、training、formal rollout、merge 与 outcome
analysis 仍未启动。完整证据位于：

```text
experiments/tro_stage2_position_composition/manifests/
  protocol_v2.json
  protocol_blocker_v2_runtime_rng.json
  runtime_rng_capability_audit.json
```

在获得对“seed 如何因果作用于 simulator physics”的明确协议授权和冻结分布前，
不得恢复原 deterministic retry loop，也不得根据已观察结果自行设计 perturbation。

后续 continuation 又完成了内容级排查：对 seeds 1/4/5 的四组不同 attempt seeds，
排除 metadata 后逐文件比较共 3,609 个 point-cloud、joint、EE、cube、time 与
command 文件，全部内容相同。本机 PyBullet 也不支持 `randomSeed` 或
`solverRandomSeed` physics 参数。仓库内没有既能改变 physics outcome、又不改变
frozen latent 或物理协议的现成机制，因此当前 blocker 不可在原 authority 下绕过。

## Stage 2c composition Protocol v3 candidate-stream continuation（2026-07-26）

用户随后澄清并明确确认真正的 collection 语义：若初始候选中的一条失败，不对
同一 deterministic latent 无限复制，而是保留完整失败证据并沿同一个确定性
normalized-latent candidate stream 继续 candidate 31、32、33……，直到每个
canonical seed 累计 30 个成功样本。每个 candidate 仍是四个新 corners 的 atomic
bundle；四角全部成功才整组接受，任一角失败则整组归档并推进。只有
infrastructure interruption 才对完全相同的 candidate 做 clean retry。

该规则由
`experiments/tro_stage2_position_composition/manifests/protocol_amendment_v3.json`
记录。v3 collector 已实现并通过 49/49 个完整相关回归测试；五个 source streams
的 0--159 共 800 条已有记录均与冻结的 NumPy PCG64 生成器逐条精确一致，index
160 以后也由相同 draw order 确定性延伸。v1/v2 progress、failures、blockers、
in-flight archives 和旧 hash snapshots 均保留，新的 v3 ledger 只增量迁移。

冻结证据为：

```text
experiments/tro_stage2_position_composition/manifests/
  candidate_stream_v3.json
  test_evidence_v3.json
  protocol_v3.json
```

Formal collection v3 array `36055938` 已提交并正在监控。最终每个新 dataset 仍
必须恰好 30 条 demonstrations。原 frozen-30 内保留成功的 rows 继续与 25 个旧
anchors 具有 normalized-latent pairing；超出原 frozen-30 的 replacement rows
只保证四个新 corners 彼此精确配对，不得声称与旧 anchors 配对。旧 anchors
保持 immutable。

## Stage 2c composition 最终结果（2026-07-27）

Protocol v3 已完整执行并通过 Definition of Done。Formal collection job
`36055938` 完成 5/5；20 个新 datasets 各含严格 30 条 accepted
demonstrations。五个 canonical seeds 中仍与旧 anchors normalized-latent
配对的 accepted counts 分别为 `28,28,24,24,29`，合计 133；其余 17 个
replacement candidates 仅在四个新 corners 间严格配对。五个 v3 ledgers
记录 25 个 rejected candidate identities，其中 5 个是从 v2 frontier
迁移的历史 candidate、20 个是 v3 新执行 rejection。旧 v1/v2 的 92 次
failed simulator executions 全部保留，因此实际 failed executions 合计 112，
不会把迁移 identity 再计一次。Collection 没有 v3 infrastructure retry。

HDF5 job `36056459` 完成 5/5，20/20 新 HDF5 严格有效；每个文件 60 episodes，
使用冻结的 54/6 train/valid masks。首次 training submission
`36057059`--`36057078` 因 code-root export 错误在进入 learner 前失败或取消，
没有产生 checkpoint；完全相同 configs 的 clean retry
`36057105`--`36057124` 完成 20/20 from-scratch policies。随后在任何 formal
rollout outcome 出现前，按最高 numeric emitted epoch 规则冻结 45/45
checkpoint paths 与 hashes。

Primary common-absolute 首次 job `36059233` 因 immutable Stage 2 manifests
仍保留合法的五条件 metadata order 而在 policy loading 前停止，产生 0 rows。
profile-scoped loader 修正不改变 state、RNG、半径或 IK 校验；identical-input
retry `36059244` 完成 200/200 tasks 与 5,000/5,000 rows。Secondary RMAX40
job `36061752` 完成 188 tasks，另有 12 tasks 在 `erc-hpc-comp054` 上
`PREEMPTED`。其 40 条 partial rows 按 task ownership 归档；冻结输入不变的
retry `36062210` 完成 12/12，最终同样为 200/200 tasks 与 5,000/5,000 rows。

Strict merge 验证：

```text
new tasks / rows                 = 400 / 10,000
common-absolute full surface     = 45 policies, 450 tasks, 11,250 rows
condition-relative RMAX40 surface = 45 policies, 450 tasks, 11,250 rows
```

Primary common-absolute 的四个预注册 interaction means 为：

```text
I_tight_15 = +0.1624  (4/5 same non-zero sign; signal)
I_tight_35 = -0.0064  (1/5; no signal)
I_wide_15  = +0.1608  (3/5; no signal)
I_wide_35  = +0.1304  (4/5; signal)
```

因此按预注册的 `abs(mean) >= 0.05` 且至少 4/5 同号规则，实验级 classification
为 `interaction`。Common-absolute condition means 为：

```text
START15: APP3P6 0.4944, APP6 0.3720, APP8P4 0.2840
START25: APP3P6 0.4496, APP6 0.4896, APP8P4 0.2408
START35: APP3P6 0.2872, APP6 0.3336, APP8P4 0.2152
```

Secondary RMAX40 的 ID/OOD means 为：

```text
START15_APP3P6 0.7584 / 0.2688
START15_APP6   0.5776 / 0.2208
START15_APP8P4 0.4176 / 0.1488
START25_APP3P6 0.4784 / 0.3168
START25_APP6   0.4784 / 0.3600
START25_APP8P4 0.2736 / 0.1776
START35_APP3P6 0.2800 / 0.2512
START35_APP6   0.3200 / 0.3280
START35_APP8P4 0.1792 / 0.1632
```

ID/OOD Pareto front 为 `START15_APP3P6` 与 `START25_APP6`。RMAX40 仍是
condition-relative secondary view；不同 Start families 不被解释成共同绝对
deployment trials。

最终相关测试 52/52 通过。25 个旧 checkpoints 与 25 个旧 HDF5 hashes
逐项复核无 mismatch；旧 Stage 2/RMAX40 顶层 hashes 也保持不变。新 dataset
namespace 约 32.70 GB，新 model namespace 约 15.68 GB。没有自动清理；
仅把约 59.68 MB smoke 与 34 个未选 checkpoints（约 9.86 GB）列为需用户另行
批准的 cleanup candidates。

完整结果与审计位于：

```text
experiments/tro_stage2_position_composition/analysis/
experiments/tro_stage2_position_composition/manifests/
handoffs/tro-stage2-position-composition.md
```

Stage 2c 在此停止。没有启动 Stage 3、Rotation、Velocity、cross-task model、
compatibility model、AR guidance 或 human study；没有重采、重训或修改任何旧
anchor，也没有 commit、push 或创建 PR。
