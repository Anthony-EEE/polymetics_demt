# T-RO 实验总计划与本周 MVP-0 执行规范

**状态：** execution-ready
**日期：** 2026-07-23
**本周范围：** 只做 PyBullet grasping、只研究 Position variation、只验证 robot-side 的 event-conditioned compatibility/coverage 假设。
**本周不做：** encoder-decoder、forward model、AR redesign、human study、Rotation/Velocity、跨任务学习。

---

## 0. 给 Codex 的执行约定

这份文件是本周实验的 source of truth。执行时遵守以下规则：

1. 先阅读仓库中的 `AGENTS.md`、README、现有实验说明和当前 git 状态。
2. 先定位现有 S15-S35 demonstration generator、policy training、rollout evaluation 和 metric code；不要假设文件名，也不要另起一套平行框架。
3. 保留用户已有改动。只修改与本实验直接相关的代码。
4. 所有新行为必须 config-driven；不要把 condition、seed、路径或评估状态硬编码在脚本中。
5. 在通过“干预解耦”和“evaluation bank 校准”两个 gate 之前，不启动完整 policy matrix。
6. 每完成一个 gate，先产出可检查的 manifest/summary，再进入下一步。
7. 如果仓库实际语义与本计划中的 `free_reach_radius` 或 `pre_grasp_radius` 不一致，暂停训练；先在 `implementation_notes.md` 中写清真实语义及最小映射，再按科学意图实现。
8. 本周是 screening，不用 2 个 repeats 宣称显著性，也不要把 rollout 当成独立 policy 样本。

---

## 1. 研究的前因后果

### 1.1 LfD 的隐藏假设

Learning from Demonstration 通常希望机器人学习 expert behaviour，但经常默认：

> 人能成功完成任务
> 约等于
> 人提供了适合当前机器人学习的数据。

这两个命题并不等价。人可以依靠触觉、在线纠错、语义理解和自身身体能力完成任务，但固定机器人 learner 在有限数据预算下未必能从这些示范中学会。

因此：

> **Task-execution expert 不一定是 robot-teaching expert。**

### 1.2 DEMT/CoRL 已经完成了什么

DEMT 用固定 learner、固定数据预算和固定 deployment protocol，把 demonstration quality operationalise 为：

\[
D^\star=\arg\max_D J(A(D)).
\]

它不再只看 human task success，而是看由数据 \(D\) 训练出的 learner \(A(D)\) 在 deployment 中表现如何。

DEMT manuscript 已经包含：

- 在 grasping 和 insertion 中比较有限候选集
  \(C=\{z_0,z_P,z_R,z_V\}\)；
- 证明同样 task-successful 的 P/R/V 数据结构可产生显著不同的 deployment success；
- 人工将 selected structures 转译为 corridor、grasp cue 和 speed bar；
- 人工设定 corridor、orientation tolerance 和 speed thresholds；
- 用 prism 训练 novice，并在撤除 guidance 后验证 prism、cube 和 ordered pick-and-place；
- 明确主张 retained and transferable learner-aware teaching behaviour。

因此 T-RO 不能把以下内容当作新的核心贡献：

- deployment-based demonstration comparison；
- “保持 P/R/V 一致”本身；
- 用 AR guidance 训练 novice；
- 从 prism 迁移到 cube/related manipulation；
- 把人工阈值简单换成复杂 neural network。

### 1.3 T-RO 真正要新增什么

DEMT 目前是在人工给定、task-level 的有限候选集中做选择。T-RO 要进一步学习并保存：

\[
\text{task/event semantics}
\rightarrow
\text{learner-compatible demonstration distribution}.
\]

也就是从多个 source-task deployments 中自动提取：

> 在什么任务事件中，人必须保持哪些性质聚拢；在什么事件中，适度多样性可以扩展 coverage；这些约束如何随 task/event 和 deployment distribution 改变。

最终希望形成：

> **The robot does not merely learn from experts; it learns from deployment what expertise should look like, and uses that knowledge to train future human teachers.**

但严格来说，robot-only deployment 数据首先只能学习“机器人需要什么样的数据”，不能自动等价于“怎样最有效地教人”。

---

## 2. 必须保持分开的三层

### Layer 1: Robot compatibility

\[
F_{\mathrm{robot}}(x,q,\mathcal A,N,\rho)
\rightarrow p_{\mathrm{success}},
\]

其中：

- \(x\)：task/event semantic features；
- \(q\)：demonstration dataset 中实际实现的 P/R/V variation；
- \(\mathcal A\)：固定 learner；
- \(N\)：demonstration budget；
- \(\rho\)：deployment/evaluation distribution。

### Layer 2: Guidance realisation

\[
H_{\mathrm{human}}(x,g,u)
\rightarrow q_{\mathrm{realised}},
\]

其中 \(g\) 是 AR guidance setting，\(u\) 是具体用户。相同 guidance 不保证不同用户产生相同 demonstration distribution。

### Layer 3: Human teaching

\[
g
\rightarrow
\text{behaviour change, retention, workload, transfer}.
\]

本周只验证 Layer 1 的最小前提。输出是 event-local compatible variation 的证据，不是 AR setting，也不是“学会了如何教人”。

完整系统未来才求：

\[
g^\star=\arg\min_g C_{\mathrm{human}}(g)
\]

subject to

\[
\operatorname{LCB}
\left[
F_{\mathrm{robot}}
\left(x,H_{\mathrm{human}}(x,g,u)\right)
\right]\geq\eta.
\]

---

## 3. 整篇 T-RO 的完整逻辑链

### 科学主张

> Task- and event-conditioned demonstration compatibility can be predicted across tasks from deployment interventions.

### 系统主张

> Predicted compatibility boundaries can be translated into minimum-burden guidance for a held-out task.

### 人体主张

> Training with generated guidance produces retained teaching behaviour that transfers unguided to a further unseen task.

完整验证链为：

1. 多个 source tasks 上做 event-local deployment interventions；
2. 学习并冻结 task/event-conditioned compatibility predictor；
3. 在整个 held-out task A 上预测 \(q^\star\)；
4. 用固定、预注册的 \(q^\star\rightarrow g\) 规则生成 guidance；
5. 用 task A guidance 训练 novice；
6. 撤除 task A guidance，验证 retention 和 A-policy deployment；
7. 在 further held-out task B 上完全不给 guidance；
8. 验证 human teaching-skill transfer；
9. 训练 B-policy，并测 nominal 与明确指定的 shifted deployment。

两个 held-out task 的作用不能混：

| 测试 | 支持的主张 |
|---|---|
| Held-out A 上自动生成 guidance | selector/generalisation |
| A 上撤除 guidance 后仍有效 | retention |
| Held-out B 上完全无 guidance | human teaching-skill transfer |
| B-policy nominal/shifted rollout | downstream policy performance/generalisation |

本周 MVP-0 只回答：上述第 1 层是否存在值得学习的非平凡结构。

---

## 4. 本周唯一科学问题

> **在固定 \(N=30\) 的数据预算下，相同相对幅度的 Position variation 放在不同 event，是否产生不同 deployment effect；并且 free-reach variation 是否可能用 coverage 换取 shifted-start robustness，而 pre-contact variation 更受 precision/density 约束？**

这里不是预设“多样性好”或“一致性好”。在有限数据下，variation 同时具有：

- **Coverage benefit：** 覆盖更多状态，可能改善某个明确 shift 下的表现；
- **Density/ambiguity cost：** 数据被摊薄，局部动作分布更散，可能降低精密学习。

因此要寻找的是：

\[
q_e^\star
=
\arg\max_{q_e}
\left[
J_{\mathrm{ID}}(q_e)
+
\lambda J_{\mathrm{shift}}(q_e)
\right],
\]

并检验 \(q_e^\star\) 是否依赖 event \(e\)。

### 最小成功与强成功

**最小成功：**

> 同样的 P variation 在 `free_reach` 和 `pre_contact` 中产生方向或幅度不同的 deployment effect。

这支持 event-conditioned compatibility，但尚不证明 diversity 提高 robustness。

**强成功：**

> `Free-wide` 改善 shifted-start coverage，且 nominal cost 很小；`Pre-tight` 保持 alignment/contact precision。

这开始支持 event-conditioned consistency-coverage trade-off。

---

## 5. 预注册假设与 contrasts

令 \(J_\rho(c)\) 表示 condition \(c\) 在 evaluation regime \(\rho\) 下的 deployment success。

### H1: Free-reach coverage benefit

\[
B_{\mathrm{free}}
=
J_{\rho_{\mathrm{free}}}(\text{Free-wide})
-
J_{\rho_{\mathrm{free}}}(\text{Free-tight})
>0.
\]

同时检查 nominal cost：

\[
C_{\mathrm{free}}
=
J_{\rho_{\mathrm{ID}}}(\text{Free-wide})
-
J_{\rho_{\mathrm{ID}}}(\text{Free-tight}).
\]

期望：

\[
B_{\mathrm{free}}>0,\qquad C_{\mathrm{free}}\approx0.
\]

### H2: Pre-contact precision benefit

\[
B_{\mathrm{pre}}
=
J_{\rho_{\mathrm{ID}}}(\text{Pre-tight})
-
J_{\rho_{\mathrm{ID}}}(\text{Pre-wide})
>0.
\]

并且 `Pre-wide` 的额外失败应主要发生在 alignment/contact/lift transition，而不是 free reach。

### H3: Event interaction

\[
I_{\mathrm{event}}
=
\left[
J_{\rho_{\mathrm{ID}}}(\text{Free-wide})
-
J_{\rho_{\mathrm{ID}}}(\text{Free-tight})
\right]
-
\left[
J_{\rho_{\mathrm{ID}}}(\text{Pre-wide})
-
J_{\rho_{\mathrm{ID}}}(\text{Pre-tight})
\right].
\]

若 \(I_{\mathrm{event}}>0\)，说明 widening 的影响依赖 variation 所在 event。

### H4: Coverage-specific interaction

\[
I_{\mathrm{coverage}}
=
\left[
J_{\rho_{\mathrm{free}}}(\text{Free-wide})
-
J_{\rho_{\mathrm{free}}}(\text{Free-tight})
\right]
-
\left[
J_{\rho_{\mathrm{ID}}}(\text{Free-wide})
-
J_{\rho_{\mathrm{ID}}}(\text{Free-tight})
\right].
\]

若 \(I_{\mathrm{coverage}}>0\)，Free-wide 的价值确实与 shifted-start coverage 有关，而不是对所有 evaluation 都统一更好。

### H5: Combined recipe，只有 MVP-0A 通过后测试

\[
J(\text{Free-wide + Pre-tight})
>
J(\text{Free-tight + Pre-wide}).
\]

这一步检验 event-conditioned recipe 是否优于把原则放反，而不是只比较单个局部效应。

---

## 6. 操作定义

### 6.1 两个 event

只使用两个 event：

- `free_reach`：episode 开始至首次进入固定 alignment/approach region；
- `pre_contact`：首次进入该 region 至 `min(gripper_close_onset, first_contact)`；若其中一个事件不存在，则使用另一个。

实现时必须：

1. 优先使用 simulator 的几何/接触/夹爪事件，不按轨迹“前 60%/后 40%”切分；
2. 冻结一个与 condition 无关的 `event_definition_version`；
3. alignment region 的边界不能使用 condition-specific variation radius；
4. 同时记录 `first_alignment_entry`、`gripper_close_onset` 和 `first_contact`，即使主分段只使用其中两个；
5. 如果当前 generator 的语义不支持上述分段，先记录真实 state machine，再做最小映射。

### 6.2 两个 manipulated knobs

- `free_reach_radius`：只控制 free-reach demonstration distribution；
- `pre_grasp_radius`：只控制 pre-contact/final-alignment demonstration distribution。

这两个量是 demonstration generator 的干预参数，不是 event boundary，也不是 AR guidance setting。

特别注意：

> 本 MVP 中的 reference `25 cm / 6 cm` 是当前 simulation intervention 的计划值。DEMT manuscript Appendix A.5 中的 AR corridor 是 `25 cm / 5 cm / 3 cm`；两者不能混写或互相引用。

### 6.3 Planned 与 realised variation

训练 condition 由 planned radius 定义，但分析必须同时报告 realised event-local variation。

在 object/event frame 中，将每个 event 按 event progress 重采样到固定长度 \(T_e\)，计算：

\[
q_{P,e}^{\mathrm{metres}}
=
\sqrt{
\frac{1}{T_e}
\sum_{t=1}^{T_e}
\operatorname{tr}
\left[
\operatorname{Cov}_i
\left(p^\perp_{i,t}\right)
\right]
}.
\]

同时保存无量纲量：

\[
a_{P,e}
=
\frac{q_{P,e}^{\mathrm{metres}}}{s_e},
\]

其中 \(s_e\) 是冻结的 local geometric scale，例如 workspace span、clearance 或 alignment tolerance。MVP 内同时报告 raw metres 和 dimensionless value；不要只报告 planned radius。

### 6.4 Evaluation regimes

每个 policy 在完全相同的三组 evaluation states 上测试：

| Regime | 定义 | 回答的问题 |
|---|---|---|
| \(\rho_{\mathrm{ID}}\) | 原始 nominal rollout distribution | 基本任务精度/成功 |
| \(\rho_{\mathrm{free}}\) | 冻结的 held-out outer-band start states | free-reach coverage |
| \(\rho_{\mathrm{pre}}\) | 在进入 pre-contact 时施加冻结的小幅 lateral/alignment perturbation | local recovery/precision |

“Robustness”只能写成对上述明确 shift 的 robustness，不能泛称 general robustness。

---

## 7. MVP-0A：五条件 screening

五个训练条件使用相同的相对 multipliers：tight = \(0.6\times\)，reference = \(1.0\times\)，wide = \(1.4\times\)。

| Condition | Free-reach radius | Pre-grasp radius | Free multiplier | Pre multiplier |
|---|---:|---:|---:|---:|
| `reference` | 25 cm | 6.0 cm | 1.0 | 1.0 |
| `free_tight` | 15 cm | 6.0 cm | 0.6 | 1.0 |
| `free_wide` | 35 cm | 6.0 cm | 1.4 | 1.0 |
| `pre_tight` | 25 cm | 3.6 cm | 1.0 | 0.6 |
| `pre_wide` | 25 cm | 8.4 cm | 1.0 | 1.4 |

### Screening 规模

- 5 conditions；
- 每个 condition 2 个 independent paired dataset-policy blocks；
- 每个 dataset 30 个 task-successful demonstrations；
- 每个 dataset 从头训练 1 个 policy；
- 每个 policy 在 3 个 regimes 下各 10 个 rollouts。

总计：

- 10 datasets；
- 10 policies；
- 300 rollouts。

这只能用于 screening 和方向判断，不能作为正式 statistical claim。

---

## 8. 配对、随机种子和独立实验单位

### 8.1 Paired block

每个 `paired_block_id`：

1. 先生成一组 30 个 canonical latent samples；
2. 五个 conditions 共用 task instances、object states、扰动方向/quantiles 和 demonstration indices；
3. 只改变目标 event 对应的 radius/multiplier；
4. 五个 policies 使用相同 training seed；
5. 第二个 block 使用另一组 demo seed 和 training seed。

建议 seed contract：

```text
block_id
demo_base_seed
policy_seed
eval_bank_version
condition_id
```

### 8.2 避免 condition-specific selection bias

所有 demonstrations 必须 task-successful，但不能让某个 condition 无限 retry，直到保留了更容易的样本。

必须：

- 预先固定 latent sample/perturbation index；
- 记录每次生成尝试、失败原因和 retry count；
- 使用所有 conditions 相同的 retry policy；
- 如果某个 latent sample 在某 condition 下不可生成，标记 invalid 并对整个 paired block 的该 index 共同重采样；
- 在 manifest 中保留 discarded indices。

### 8.3 独立单位

主要独立实验单位是：

\[
\text{demonstration dataset}
\rightarrow
\text{trained policy}.
\]

rollouts 是同一 policy 的重复 deployment trials。300 个 rollouts 不能被当成 300 个独立 learner samples。

---

## 9. Evaluation bank 的构造与冻结

### 9.1 \(\rho_{\mathrm{ID}}\)

- 复用原始 nominal rollout protocol；
- 创建 10 个固定 `eval_state_id`；
- 任何 condition 都使用完全相同的 state 顺序。

### 9.2 \(\rho_{\mathrm{free}}\)

- 从机器人可达、无碰撞的 outer-band start states 中采样；
- 与 demonstration generation seeds 完全分离；
- state 应对 `free_tight` 形成 coverage challenge；
- 不要通过改变 object/grasp geometry 同时引入 pre-contact confound。

优先实现为一个版本化 `eval_state_bank`，而不是每次 rollout 在线随机采样。

### 9.3 \(\rho_{\mathrm{pre}}\)

优先方案：

- 完整执行 free reach；
- 在首次进入固定 pre-contact region 时，对 EE/object-relative alignment state 施加一次冻结的 lateral offset；
- 记录注入前后 state 和 perturbation vector；
- 之后正常闭环 rollout。

如果 simulator 不支持安全 mid-episode injection，替代方案是从已保存的 pre-contact states reset 并评估 alignment-to-lift subepisode；此时必须单独标记 `rollout_scope=precontact_subepisode`，不能与 full-task ID success 混为同一指标。

### 9.4 只用 reference policy 校准一次

在完整 matrix 运行前，可用现有/reference policy 检查 evaluation bank：

- ID 不应完全 floor；
- shifted regime 不应全部 0% 或 100%；
- perturbation 必须物理可行且不直接造成任务失败。

默认校准目标是让 reference policy 在 shifted regime 中落在约 20%-80% 的非饱和区间。只允许在看到其他 condition 结果前调整一次；冻结后写入：

```text
eval_bank_version
creation_seed
state_ids
shift_type
shift_magnitude
calibration_policy_id
frozen_at
```

---

## 10. 数据存储规范

不要只保存 aggregate success rate。至少保留四层。

### 10.1 Dataset manifest：一行一个 dataset

```text
dataset_id
paired_block_id
task_id
condition_id
event_definition_version
generator_version
demo_base_seed
free_radius_planned_m
pre_radius_planned_m
free_multiplier
pre_multiplier
q_P_free_realised_m
q_P_pre_realised_m
a_P_free_realised
a_P_pre_realised
num_demonstrations
num_generation_attempts
num_discarded_indices
all_demo_task_success
trajectory_store
created_at
```

### 10.2 Demonstration trajectory：逐步保存

尽量复用现有 trajectory format，并补充：

```text
dataset_id
demo_id
timestep
sim_time
event_label
event_progress
ee_position
ee_orientation
gripper_state
object_pose
distance_to_contact
contact_state
required_precision
constrained_dof
task_success
```

### 10.3 Policy manifest：一行一个 trained policy

```text
policy_id
dataset_id
paired_block_id
condition_id
training_seed
learner_name
learner_version
git_commit
config_path
data_budget
checkpoint_path
training_status
best_or_final_checkpoint_rule
validation_loss
created_at
```

所有 condition 必须使用同一 checkpoint selection rule。不能根据 rollout performance 选 checkpoint。

### 10.4 Rollout table：一行一个 rollout

```text
rollout_id
policy_id
dataset_id
paired_block_id
condition_id
eval_bank_version
eval_regime
eval_state_id
rollout_scope
shift_event
shift_type
shift_vector
shift_magnitude
rollout_initial_state
success
first_failure_event
reached_alignment
gripper_close_started
contact_formed
stable_contact
lift_started
lift_success
termination_reason
video_or_trace_path
```

### 10.5 推荐目录结构

适配现有仓库结构，不要机械新建重复目录。若现有结构没有等价位置，可采用：

```text
experiments/mvp0_position_event/
  configs/
    conditions.yaml
    eval_bank.yaml
    training.yaml
  manifests/
    datasets.csv
    policies.csv
    rollouts.parquet
  data/
    demonstrations/
    eval_banks/
  checkpoints/
  analysis/
    summary.md
    screening_decision.json
    figures/
  logs/
  implementation_notes.md
```

大体量 trajectory/checkpoint 是否进入 git，应遵守仓库现有规则。

---

## 11. 实现任务：按 gate 顺序执行

### Gate 0: Repository audit

先输出 `implementation_notes.md`，回答：

1. S15-S35 在哪里定义？
2. 现有一个 radius 实际影响哪些 trajectory waypoints/events？
3. 30 demonstrations 如何生成和验证 task success？
4. learner 的训练入口、seed、checkpoint selection 是什么？
5. rollout initial state 当前如何采样？
6. success 与 failure 当前如何判断？
7. 是否已有 event/contact/gripper logs？
8. 是否已有 MPCV 或 event-local variation metrics？

**Gate 0 通过条件：** 找到最小修改点，并明确现有 confound 的代码证据。

### Gate 1: 解耦 generator

将原先共同变化的参数拆为：

```text
free_reach_radius
pre_grasp_radius
```

要求：

- 两者独立配置；
- reference config 可重现现有 S25/reference 行为；
- 其他 task geometry、orientation、velocity、data budget 保持不变；
- generator 每步输出 event label/state；
- 保存 planned 和 realised variation。

**必要测试：**

1. `reference` 的关键 trajectory statistics 与旧 reference 在容差内一致；
2. 改 `free_reach_radius` 时，planned pre setting 不变；
3. 改 `pre_grasp_radius` 时，planned free setting 不变；
4. event definition 不随 condition 改变；
5. 5 个 condition 各生成 2-3 条 smoke demos，均可 task-success；
6. trajectory visualisation 能直观看到 variation 只发生在目标 event。

**Gate 1 通过条件：** 干预在 planned 与 realised 层面均基本解耦。若非目标 event 的 realised variation 改变超过预注册容差，先诊断动力学耦合，不训练完整 matrix。

建议 screening 容差：非目标 event 的 realised variation 相对 reference 改变不超过 10%。若物理耦合使 10% 不可达，报告实际耦合量并重新定义可识别 contrast。

### Gate 2: Event labelling 与 failure state machine

实现统一 state machine：

```text
free_reach
pre_contact
contact
lift
success
failure
```

至少自动输出：

```text
reached_alignment
gripper_close_started
contact_formed
stable_contact
lift_started
lift_success
first_failure_event
```

**Gate 2 通过条件：** 在一小组成功/失败 rollout traces 上人工核验自动 label，无明显 phase misclassification。

### Gate 3: Evaluation banks

创建并版本化：

- `rho_id_v1`；
- `rho_free_v1`；
- `rho_pre_v1`。

用 reference policy 做一次非饱和校准，冻结后不再依据 condition results 修改。

**Gate 3 通过条件：**

- 每个 bank 有 10 个固定 state IDs；
- 所有 state 物理可行；
- shift 不会直接强制失败；
- 每个 policy 可按完全相同顺序复现。

### Gate 4: Generate MVP-0A datasets

生成 2 个 paired blocks × 5 conditions × 30 demonstrations。

先只生成 block 0，运行 realised-variation validation；通过后再生成 block 1。

**Gate 4 通过条件：**

- 10 个 datasets 均为 30 个 task-successful demos；
- manifest 完整；
- 配对 seed contract 正确；
- `free_tight < reference < free_wide` 的 realised free variation 单调；
- `pre_tight < reference < pre_wide` 的 realised pre variation 单调；
- 非目标 event 变化在容差内。

### Gate 5: Train policies

- 每个 dataset 从头训练；
- block 内使用相同 policy seed；
- block 间使用不同 seed；
- 固定 learner、data budget、training steps、augmentation 和 checkpoint rule；
- 不根据 rollout 结果重新选 checkpoint。

建议先训练一个完整 paired block 的 5 个 policies，确认 pipeline 后再训练第二 block。

**Gate 5 通过条件：**

- 10 个 policy jobs 均成功；
- configs、logs、git commit、checkpoint 均可追溯；
- 没有 silent resume 或 checkpoint reuse。

### Gate 6: Evaluate

每个 policy：

- `rho_id_v1`: 10 rollouts；
- `rho_free_v1`: 10 rollouts；
- `rho_pre_v1`: 10 rollouts。

总计 300 rollouts。

运行期间不按结果中途更换 state bank 或 perturbation magnitude。

**Gate 6 通过条件：** rollout table 300 行，state ID coverage 完整，无 condition-specific missingness。

### Gate 7: Analyse and decide

输出：

1. 每个 policy × regime 的 success；
2. paired block contrasts；
3. Beta-binomial/Wilson uncertainty for rollout success；
4. realised variation plots；
5. failure-event composition；
6. H1-H4 的方向和 effect size；
7. `screening_decision.json`。

本周 screening 不做以 300 rollouts 为 \(n=300\) 的普通 t-test。

---

## 12. MVP-0A 的 screening decision rule

以下阈值是工程决策阈值，不是论文显著性阈值。必须在运行完整 matrix 前冻结；如果已有更合理的领域阈值，可修改一次并在 config 中记录理由。

### Strong pass

同时满足：

1. 两个 blocks 中 \(B_{\mathrm{free}}\) 方向均为正；
2. 平均 \(B_{\mathrm{free}}\geq 0.20\)；
3. 平均 \(C_{\mathrm{free}}\geq -0.10\)；
4. 两个 blocks 中 \(B_{\mathrm{pre}}\) 方向均为正；
5. 平均 \(B_{\mathrm{pre}}\geq 0.20\)；
6. `Pre-wide` 的额外失败主要集中在 alignment/contact/lift transition。

动作：进入 MVP-0B。

### Directional but inconclusive

两类 contrast 方向基本符合，但 effect 小于 0.20、某 block 为 0，或 K=10 的离散性太大。

动作：

- 先把每个已有 policy 的每个 regime 补到 K=20；
- 不立即增加新 dataset-policy repeats；
- 使用同一 frozen evaluation bank 的扩展 state IDs；
- 重新判断方向和不确定性。

### Event-conditioned minimum pass

若 \(B_{\mathrm{pre}}>0\) 且 free/pre widening 的 effect 明显不同，但 Free-wide 没有提高 \(\rho_{\mathrm{free}}\)：

动作：

- 可以保留“event-conditioned sensitivity”故事；
- 不得声称 coverage/robustness benefit；
- MVP-0B 是否执行取决于 event interaction 是否稳定。

### Fail / diagnostic branch

见第 15 节 decision table。

---

## 13. MVP-0B：组合验证，仅在 Gate 7 通过后执行

增加：

| Condition | Free reach | Pre-contact | 含义 |
|---|---:|---:|---|
| `event_conditioned` | 35 cm | 3.6 cm | free 多样、pre 聚拢 |
| `swapped` | 15 cm | 8.4 cm | 将原则放反 |

规模：

- 2 conditions；
- 2 paired blocks；
- 30 demos/dataset；
- 4 policies；
- 每个 policy 3 regimes × 10 rollouts；
- 120 rollouts。

本周若 MVP-0A strong pass，总量为：

- 14 policies；
- 420 rollouts。

### MVP-0B 主要判断

报告：

\[
\Delta_\rho
=
J_\rho(\text{event-conditioned})
-
J_\rho(\text{swapped})
\]

for \(\rho_{\mathrm{ID}},\rho_{\mathrm{free}},\rho_{\mathrm{pre}}\)。

screening pass：

- 两个 paired blocks 的 equal-weight mean
  \(\frac{1}{3}\sum_\rho\Delta_\rho\) 均为正；
- 没有任一关键 regime 出现大于 10 percentage points 的不可解释 regression；
- failure modes 与“swapped 在 pre-contact 失去精度”一致。

这一步仍不是正式论文实验。

### 正式 follow-up controls，不默认纳入本周

正式实验需再加入：

| Condition | Free reach | Pre-contact |
|---|---:|---:|
| `taskwide_tight` | 15 cm | 3.6 cm |
| `taskwide_wide` | 35 cm | 8.4 cm |

并把所有关键 conditions 补到至少 4 个 independent dataset-policy repeats。这样才能证明 event-conditioned recipe 不只是“全部收紧”或“全部放宽”。

---

## 14. 分析规范

### 14.1 Primary outputs

每个 policy/regime：

\[
\hat J=\frac{\text{successes}}{K}.
\]

同时报告：

- successes / K；
- rollout-level binomial interval；
- paired-block effect；
- across-policy mean 仅作 descriptive summary。

### 14.2 Failure analysis

至少分：

```text
reach_failure
alignment_failure
no_contact
unstable_contact
lift_failure
timeout
unsafe_or_workspace
unknown
```

必须检查：

- `Pre-wide` 的失败是否在 alignment/contact；
- `Free-tight` 在 \(\rho_{\mathrm{free}}\) 下是否在进入 alignment 前失败；
- shift 注入是否直接造成 failure；
- success 变化是否来自意外的 termination logic。

### 14.3 Realised intervention check

画出：

- \(q_{P,\mathrm{free}}\) by condition/block；
- \(q_{P,\mathrm{pre}}\) by condition/block；
- planned radius vs realised variation；
- target-event effect vs leakage into non-target event。

若 planned ordering 没有反映在 realised variation 中，则 rollout 结果不能解释为 event-local P intervention。

### 14.4 正式阶段统计模型

当 repeats 至少为 4 且 design 完整后，可用 hierarchical/binomial model：

\[
y_{b,c,r,k}\sim\operatorname{Bernoulli}(p_{b,c,r}),
\]

\[
\operatorname{logit}(p_{b,c,r})
=
\alpha_b+\beta_c+\gamma_r+(\beta\gamma)_{c,r},
\]

其中 \(b\) 是 dataset-policy block，\(c\) 是 training condition，\(r\) 是 evaluation regime。

本周不需要为这个模型写复杂 neural code。

---

## 15. 结果分支与停止条件

| 观察 | 科学解释 | 下一步 |
|---|---|---|
| `Free-wide` 改善 \(\rho_{\mathrm{free}}\)，ID 基本不降；`Pre-tight` 改善 ID/contact | 强 consistency-coverage trade-off | 做 MVP-0B |
| Pre effect 强，free effect 接近 0 | event-conditioned sensitivity 成立，coverage 未证明 | 补 K；谨慎决定组合验证 |
| Free/pre widening 在所有 regimes 同样有害 | 可能是 task-wide finite-data density cost | 暂停“free diversity 有益”主张；检查 event 解耦 |
| Free/pre widening 都无影响 | amplitude 未跨边界或 learner 不敏感 | 只允许一次幅度扩展后复测 |
| Free-wide 提高 shift 但明显损害 ID | 存在 coverage-precision trade-off，但不是免费收益 | 后续显式学习 Pareto/utility，而非宣称 wide 最优 |
| Pre-wide 也提高 \(\rho_{\mathrm{pre}}\) 且不损害 ID | pre-contact 同样受 coverage benefit | 接受结果，寻找 event-dependent optimum，不强迫“pre 必须 tight” |
| 两个 blocks 效应方向相反 | dataset/policy variance 主导 | 补 repeats/检查训练稳定性，不训练 generator |
| realised intervention 泄漏到另一 event | 干预不可识别 | 回到 Gate 1，禁止解释 deployment contrast |
| reference/所有 conditions floor 或 ceiling | evaluation 缺乏分辨率 | 在解盲其他结果前重新校准 bank；否则新建预注册 follow-up |
| failure label 大量 unknown | 机制解释不可用 | 修 state machine 后重跑必要 traces |

### 一次 amplitude adjustment 的规则

若 tight/reference/wide 的 realised variation 已单调，但所有 deployment effects 接近 0，可将 multiplier 从 `0.6/1.4` 改成更强的、物理可行的一组，例如 `0.4/1.6`。

要求：

- 只调整一次；
- 两个 events 使用相同相对 multipliers；
- 重新生成全部相关 paired datasets；
- 不把原、新 amplitude 混成同一 condition；
- 在 analysis 中明确标为 follow-up，不隐藏第一次 null result。

---

## 16. 本周建议执行节奏

### Day 1: Audit + 解耦

- 完成 Gate 0；
- 找到 S15-S35 confound；
- 实现两个独立 knobs；
- 生成 trajectory overlay/smoke demos。

### Day 2: Labels + evaluation banks

- 完成 event/failure state machine；
- 构建 3 个 evaluation banks；
- 用 reference policy 校准并冻结；
- 完成 config/manifest contract。

### Day 3: Dataset generation + first block

- 生成 block 0 的五个 datasets；
- 做 realised variation/leakage validation；
- 训练 block 0 的五个 policies；
- 做小规模 pipeline sanity evaluation。

### Day 4: Second block + full evaluation

- 生成/训练 block 1；
- 完成 MVP-0A 的 300 rollouts；
- 自动生成 summary 和 figures。

### Day 5: Decision

- 按 Gate 7 判定 strong/directional/fail；
- strong pass 时启动 MVP-0B；
- 否则执行对应诊断，不提前进入 insertion/model/human。

实际训练耗时若较长，保持 gate 顺序，不为赶进度跳过 realised-intervention validation。

---

## 17. 本周必须交付的 artifacts

1. `implementation_notes.md`
   - 现有代码路径；
   - 原 S15-S35 confound；
   - 实际 event/parameter 语义；
   - 所有偏离本计划的决定。
2. `conditions.yaml`
   - 五个 MVP-0A conditions；
   - 若通过，再追加两个 MVP-0B conditions。
3. `eval_bank.yaml` 与可复现 state files。
4. dataset/policy/rollout manifests。
5. event-labelled trajectory traces。
6. 三类 figures：
   - realised event-local variation；
   - success by condition × regime；
   - failure-event composition。
7. `analysis/summary.md`
   - H1-H4；
   - paired effects；
   - limitations；
   - gate decision。
8. `analysis/screening_decision.json`
   - `strong_pass` / `directional` / `minimum_pass` / `fail`；
   - 触发的证据和下一动作。
9. 可复制的 commands 或 launcher config，能从 manifest 重现全部 run。

---

## 18. Definition of Done

本周 MVP-0A 只有同时满足以下条件才算完成：

- [ ] Free/pre generator knobs 已独立；
- [ ] reference 行为与旧 pipeline 兼容；
- [ ] event definition 固定且不依赖 condition；
- [ ] realised target-event variation 单调；
- [ ] 非目标 event leakage 已量化；
- [ ] 三个 evaluation banks 已冻结；
- [ ] 10 个 datasets，每个 30 个成功 demos；
- [ ] 10 个 policies 全部从头训练；
- [ ] 300 个 rollouts 使用相同 state banks；
- [ ] rollout-level outcome 和 failure event 完整；
- [ ] 分析以 dataset-policy 为独立单位；
- [ ] H1-H4 的 effect/direction 已报告；
- [ ] 按预注册规则作出下一步决定；
- [ ] 没有训练 encoder-decoder 或启动 human study。

MVP-0B 只有在 strong pass 后才进入；完成标准为额外 4 policies、120 rollouts 和 event-conditioned vs swapped 的 paired comparison。

---

## 19. 本周明确不做什么

以下内容全部 deferred：

- 不增加 Rotation 或 Velocity；
- 不把 “need consistency/diversity” 当作人工 ground-truth label；
- 不训练 success latent 或 encoder-decoder；
- 不从 success rate 直接反解 guidance setting；
- 不重新设计 AR corridor/cue；
- 不招 human participants；
- 不做 held-out human task A/B；
- 不把 grasping 单任务结果称为 cross-task transferable knowledge；
- 不把两个 repeats 当正式统计证据；
- 不用 validation loss 替代 deployment success；
- 不把 cube/ordered transfer 再包装成 T-RO novelty。

---

## 20. MVP-0 成功后的迭代路线

### MVP-1: Frozen cross-task test on insertion

目标：验证规则是否从 grasping 迁移到 insertion，而不是记住 25 cm/6 cm。

1. 将 absolute radius 转成无量纲：

   \[
   a_P
   =
   \frac{\text{position variation}}
   {\text{local clearance/tolerance}}.
   \]

2. 冻结从 grasping 得出的 event rule、threshold 和 selection logic；
3. 在 insertion 上比较：
   - event-local predicted setting；
   - swapped setting；
   - task-wide tight；
   - task-wide wide/reference；
4. 使用全新的 dataset-policy blocks 和 frozen evaluation protocol；
5. 若在看到 insertion 结果后重新调 rule，则 insertion 不再是 held-out transfer test。

### MVP-2: Multiple source tasks + low-capacity forward model

只有在至少三个任务能提供 task/event variation 后，学习：

\[
\hat p
\left(
y=1
\mid
x_e,a_{P,e},\mathcal A,N,\rho
\right).
\]

优先模型：

- regularised logistic/binomial regression；
- monotonic/shape-constrained additive model；
- shallow tree/boosting 作为 secondary；
- leave-one-task-out evaluation。

模型输入使用 event semantics 和 dimensionless variation；`task_id` 只用于 grouping/split，不作为主要可迁移 feature。

### MVP-3: Compatibility boundary selection

先预测 forward outcome，再优化：

\[
q^\star
=
\arg\max_q C_{\mathrm{coverage}}(q)
\]

subject to

\[
\operatorname{LCB}
\left[
\hat J_{\mathrm{ID}}(q)
\right]\geq\eta,
\qquad
\operatorname{LCB}
\left[
\hat J_{\mathrm{shift}}(q)
\right]\geq\eta_{\mathrm{gen}}.
\]

多解由预注册 utility/burden rule 处理，不使用“success latent decoder”假设唯一逆解。

### MVP-4: Fixed guidance translation + human validation

- 冻结 \(q^\star\rightarrow g\) 的 AR template；
- 在 held-out A 上检验 guidance 是否实现目标 \(q_{\mathrm{realised}}\)；
- 测 workload、retention 和 A-policy deployment；
- 在 held-out B 上无 guidance 测 human teaching transfer；
- 不把 robot compatibility 与 human teachability 合并成同一未经验证的映射。

---

## 21. 本阶段允许与不允许的论文表述

### MVP-0A 最小通过后允许

> Position-variation compatibility is event-dependent within the grasping task under a fixed learner and finite data budget.

### 强通过后允许

> Under the tested shifted-start deployment, free-reach diversity improves coverage with limited nominal cost, whereas tighter pre-contact demonstrations preserve contact precision.

必须加限定：

- within the tested grasping task；
- under the fixed learner and \(N=30\)；
- for the specified deployment shifts。

### insertion frozen test 通过后才允许

> A dimensionless event-conditioned compatibility rule transfers across the tested grasping and insertion tasks.

### 多 source + held-out task 通过后才允许

> Deployment interventions can be used to learn task/event-conditioned demonstration expertise criteria that generalise to a held-out task.

### human A/B study 通过后才允许

> Generated guidance trains retained human teaching behaviour that transfers unguided to a further unseen task.

---

## 22. 配置示例

文件名和 schema 应适配现有仓库；以下仅定义必需语义。

```yaml
experiment:
  name: mvp0_position_event
  data_budget: 30
  event_definition_version: grasp_events_v1
  eval_bank_version: grasp_eval_v1

conditions:
  reference:
    free_reach_radius_m: 0.25
    pre_grasp_radius_m: 0.060
  free_tight:
    free_reach_radius_m: 0.15
    pre_grasp_radius_m: 0.060
  free_wide:
    free_reach_radius_m: 0.35
    pre_grasp_radius_m: 0.060
  pre_tight:
    free_reach_radius_m: 0.25
    pre_grasp_radius_m: 0.036
  pre_wide:
    free_reach_radius_m: 0.25
    pre_grasp_radius_m: 0.084

paired_blocks:
  - block_id: b0
    demo_base_seed: 1000
    policy_seed: 2000
  - block_id: b1
    demo_base_seed: 1001
    policy_seed: 2001

evaluation:
  regimes:
    - rho_id
    - rho_free
    - rho_pre
  rollouts_per_policy_per_regime: 10
  use_frozen_state_ids: true
```

seed 数字可以改，但必须写入 manifest 并冻结。

---

## 23. Codex 首个工作回合的具体输出

第一次执行本计划时，先不要直接运行 10 个 policies。先完成并汇报：

1. 仓库和当前 git 状态摘要；
2. S15-S35 相关代码路径；
3. 当前 radius 如何同时影响 free reach 和 pre-grasp 的证据；
4. 最小修改方案；
5. 预计新增/修改文件；
6. 现有训练与 rollout commands；
7. 任何会阻止严格 event-local intervention 的技术问题。

然后实现 Gate 1，并提供：

- reference/free-tight/free-wide/pre-tight/pre-wide 的 2-3 条 smoke trajectories；
- event-coloured trajectory overlay；
- planned/realised variation summary；
- unit/integration test 结果。

只有 Gate 1 的干预解耦通过后，才开始 evaluation bank 和完整训练。

---

## 24. Source boundary notes

本计划以 DEMT manuscript 为边界依据：

- §3.2：selected structures 被人工转译为 corridor、grasp cue、speed bar；
- §4.1 / Table 2：固定候选集、grasping/insertion、每 condition 4 个 independently scripted datasets、每 dataset 30 demos、每 policy 10 rollouts；
- §4.2 / Table 1：prism curriculum、cube pre/post、ordered pick-and-place P8；
- Appendix A.5：AR guidance 数值为 25/5/3 cm、15 deg、\([0.5,2.0]\times v_{\mathrm{ref}}\)；
- Appendix A.9 / B：rollout protocol 和 demonstration-level structural metrics；
- Failure analysis：主要 bottleneck 在 contact-critical transitions。

这些内容用于防止 T-RO 重复已有贡献；MVP-0 的新增点是：

> **把 task-level P variation 拆成 event-local interventions，并显式测试 training variation × evaluation shift，从而判断何时聚拢、何时 coverage 有益。**
