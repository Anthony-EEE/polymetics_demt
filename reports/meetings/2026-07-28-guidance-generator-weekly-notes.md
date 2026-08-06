# Guidance Generator 周会讲稿

配套幻灯片：`2026-07-28-guidance-generator-weekly.pptx`

建议主讲 12–15 分钟，附录仅在老师追问数值或实验规模时使用。

## 1. 标题（20 秒）

这周的重点不是继续做一个参数 ablation，而是给 T-RO 的核心目标建立第一块
robot-side evidence：在只有 30 条 demonstrations 时，什么阶段应该更一致，
什么阶段可以保留 variation，才能同时兼顾 DP 的 learnability 和 OOD
generalisation。

## 2. 一页总览（45 秒）

- 最终目标是 Guidance Generator，不是人工选一个全局半径。
- 本周先做 Position 的最小、可解释验证：Start × Approach 的 3×3 网格。
- 我们找到了两个互补 sweet spots，而不是唯一全局最优。
- 这意味着 generator 应输出 Pareto guidance，并根据 deployment 风险和人的负担
  做选择。

## 3. 总纲（60 秒）

输入是 task、trajectory stage、learner、30 条数据预算和 deployment target。
Compatibility model 预测不同 variance schedule 下的 ID/OOD deployment outcome，
selector 再选满足门槛且对人限制较小的方案，最后翻译成 corridor、orientation
tolerance 或 speed window。

强调：generator 输出的是 `σ(Start), σ(Approach), σ(Contact), …`，不是一个
single global `σ`。

## 4. 30 条数据下的 trade-off（50 秒）

- 太一致：learner 容易拟合，但 deployment shift 下可能脆弱。
- 太多样：coverage 增加，但固定的 30 条预算被摊薄，关键动作学不准。
- 我们要找的是随阶段和 deployment objective 变化的 sweet region。

图中的曲线是概念图，不是实验拟合结果。

## 5. 本周实验（60 秒）

轨迹保持 `Start → Approach → Descent → Grasp → Lift` 不变，只改变 Start 和
Approach 的 Position variation：

- Start：15、25、35 cm；
- Approach：3.6、6.0、8.4 cm；
- 每个 cell 五个独立 dataset-policy repeats；
- 每份 dataset 30 条 demonstrations；
- 共 45 个 frozen policies；
- common-absolute 与 RMAX40 两个 surface 共严格分析 22,500 rows。

所有 checkpoint 在 rollout outcome 前冻结；deployment states 与 RNG 严格配对。

## 6. 为什么必须分别看 common / ID / OOD（60 秒）

Common-absolute surface 让九个条件在相同绝对 states 上公平比较，是主结果。

Condition-relative surface 用每个 Start family 自己的 training support 定义 ID 和
OOD，用于理解“是否学得会”和“超出支持后是否 robust”。不同 Start family 的
relative banks 不是同一个绝对分布，因此不能把它们混成一个跨 Start 的通用总分。

## 7. Response surface（70 秒）

- Combined 最好的是 `Start15 / Approach3.6`：49.4%。
- `Start25 / Approach6.0` 几乎并列：49.0%。
- `Approach8.4` 在三种 Start 设置下都是最差的一列。
- Start35 整体较弱，说明增加 early-stage variation 并不会自动带来 robustness。

最重要的是 surface 非单调且有 interaction，所以 generator 不能使用“variance
越大越 robust”的单一规则。

## 8. ID/OOD Pareto（70 秒）

两个不被支配的 sweet spots：

1. `Start15 / Approach3.6`：ID 75.8%，OOD 26.9%，combined 49.4%。
   它是 learnability / precision-oriented 的设置。
2. `Start25 / Approach6.0`：ID 47.8%，OOD 36.0%，combined 49.0%。
   它牺牲部分 ID peak，换来最高 OOD，属于 robustness-oriented 设置。

`Start35 / Approach6.0` 的 ID/OOD gap 很小，但两者都不高。因此 gap 小不是目标；
目标仍然是同时把两个 outcome 推高。

## 9. Scientific conclusion 与 claim boundary（60 秒）

现在可以说：

- Position variation 的 deployment effect 是 stage-conditioned；
- 近抓取阶段过宽的 Position variation 在当前网格中持续不利；
- 最佳 guidance 依赖 ID/OOD objective，存在多个 sweet spots。

现在不能说：

- 已找到连续空间全局最优；
- 规律已经跨任务或跨 learner；
- robot-side 参数已经能被人准确实现；
- human teaching retention/transfer 已得到证明。

## 10. Generator 架构（70 秒）

建议第一版做 forward model：

- 输入 task/stage features、variation、learner、N、deployment target；
- 输出 `p(ID)`、`p(OOD)`、interaction 和 uncertainty；
- selector 在 success thresholds 下选择 Pareto setting；
- translator 把 setting 变成 corridor、orientation tolerance、speed window。

不直接学习 inverse generator，因为同一个 deployment success 可能对应多个可行
schedule。先学 forward outcome，再选对人最宽松的解，更适合小数据且可解释。

## 11. 数据表与目标函数（60 秒）

每条 compatibility record 包含：

`task features + stage features + variation + learner + N + deployment + successes/trials`

第一版模型优先 regularised binomial、additive model 或 shallow tree，不立即使用
复杂 encoder-decoder。

Selector 可以用：

`λ pID + (1−λ) pOOD − β guidance burden`

但更稳妥的产品输出是 Pareto set、置信度和推荐理由，而不是伪精确单点。

## 12. 路线图（70 秒）

1. 当前完成单任务 Spatial evidence。
2. 在多个 source tasks 上保持 scripted phases，先只做 Position。
3. Position 规律成立后再逐轴加入 Rotation、Velocity。
4. 训练低复杂度 compatibility model。
5. 在 held-out Task A 上先冻结预测，再做 robot validation 和 guidance
   realisation。
6. Task A 撤除 guidance 测 retention，再在完全未见 Task B、无 guidance 条件下
   测 teaching transfer。

每一步只扩大一个 claim，避免把 robot success 直接等同于 human teaching success。

## 13. 希望老师拍板（90 秒）

建议下一阶段：

- 选择 2–3 个已有 scripted phases、工程风险低的 source tasks；
- 只做 Position 的紧凑候选，不继续无边界搜索 grasping 半径；
- 固定 common 与 ID/OOD banks，每条件仍保持 N=30 和 matched repeats；
- 开始形成 compatibility table。

希望老师确认三个方向：

1. 论文先明确为 DP-specific guidance，还是从一开始追求 learner-agnostic？
2. Generator 输出固定权重下的一个 setting，还是输出 Pareto menu？
3. 哪 2–3 个 source tasks 最能同时满足论文说服力和工程可控性？

我的建议是：先 DP-specific、Pareto output、scripted multi-task phases。

## 14. Take-home（30 秒）

1. Variance 是 stage-conditioned control variable。
2. 30 条 demonstrations 已经能暴露可操作的 Pareto structure。
3. 下一步的贡献不是继续调当前半径，而是跨任务学习 compatibility，并把冻结预测
   转成真实的人类 guidance。

---

## 老师可能追问

### 为什么不直接宣布 15/3.6 最佳？

它的 combined 和 ID 最高，但 OOD 明显低于 25/6.0；且证据仍限于单任务、离散网格。
因此更准确的结论是两个 Pareto sweet spots，而不是唯一最优。

### 为什么 25/6.0 的 ID 不高，却仍是重要结果？

它与 15/3.6 的 common combined 几乎相同，但 OOD 更好，说明相同总体成功可以来自
不同的 learnability–robustness profile。这正是 generator 需要显式建模 deployment
objective 的原因。

### 为什么不用深度网络直接生成 guidance？

当前数据由少数 task × stage × setting cells 构成；低复杂度 forward model 更容易
校准 uncertainty、检查 interaction、做 held-out validation，也不要求逆映射唯一。

### 这是否只对 Diffusion Policy 有效？

当前 claim 应明确为固定 DP learner 下的 evidence。Compatibility table 中保留
learner 字段；后续可加入另一 learner 作为 external validation，但不应在当前证据上
提前声称 learner-agnostic。

### 22,500 rows 是否等于 22,500 个独立样本？

不是。科学重复单位是五个独立 dataset-policy seeds；rollout seeds 与 rows 是嵌套的
deployment trials。PPT 中用 rows 描述验证规模，不用它夸大统计独立性。
