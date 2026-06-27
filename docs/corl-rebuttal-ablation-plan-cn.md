# CoRL Rebuttal 消融实验计划

_日期：2026-06-27_

## 背景

当前已提交 CoRL 2026 的论文提出了 Deployment-Evaluated Machine Teaching
（DEMT），核心目标是训练 novice users 提供更适合机器人学习的 visuomotor
demonstrations。

论文中定义了 teaching-structure space：

```text
Z = P x R x V
```

其中：

- `P` 表示空间路径结构，也就是 end-effector 走哪里。
- `R` 表示接触或抓取结构，也就是 gripper 如何与物体交互。
- `V` 表示时间结构，也就是不同 task phase 的速度和 timing。

论文中的理想公式是：

```text
z* = arg max J(A(D^z)),  z in Z
```

这里 `J` 由下游机器人部署表现衡量，`A(D^z)` 表示固定 learner 在 teaching
configuration `z` 诱导出的 demonstration dataset 上训练出来的 policy。

但是，当前提交版本的实验实际上只验证了一个很小的有限候选集：

```text
C = {z0, zP, zR, zV}
```

这能支持“即使 demonstrations 都 task-successful，不同 `P/R/V` 结构仍然会显著影响
learning”这个结论。但它还没有充分解释 appendix 里的具体 AR guidance 参数是怎么从
DEMT 公式里选出来的。

所以可预见的审稿意见是：论文从 DEMT 公式跳到 AR guidance 有点突兀。

## 可能的审稿意见

### 意见 1：DEMT 公式到 AR Guidance 太突兀

论文先定义了 `P/R/V`，然后给出 corridor guidance、grasp orientation guidance 和
speed-bar guidance。Appendix 中又给出具体参数，例如 corridor 半径、orientation
tolerance、speed tolerance。

审稿人很可能会问：

```text
这些 guidance structure 和具体 threshold 是怎么从 DEMT formulation 里选出来的？
```

当前论文证明了 `P/R/V` 重要，但还没有一个直接的 ablation 来说明这些 guidance
参数是 deployment-evaluated 的选择，而不是人工拍脑袋设定。

### 意见 2：人数不够，Learner 和任务验证不够

论文中的真人数量、visual-motor learner 种类、真机任务数量都比较有限。这个意见是合理的，
但不适合在 CoRL rebuttal 窗口内彻底解决。

这些更适合作为 journal 版本的扩展方向：

- 招募更多 participants。
- 在 LIBERO 多任务 benchmark 上做模拟验证。
- 测更多 visual-motor learners，例如 ACT，甚至 VLA models。
- 制定更多真机 manipulation tasks。
- 不只手动定义 `P/R/V`，而是探索更多 human-controllable structures。

## 短期 Rebuttal 策略

CoRL rebuttal 阶段最现实的补丁，不是解决完整的 `z*` 搜索问题，而是补一个小型
deployment-evaluated ablation，证明 appendix 里的 guidance 参数不是随意设定的。

建议 rebuttal 故事线是：

```text
提交版本已经验证了 P/R/V structures 会影响 learnability。为了更清楚说明
DEMT-selected structures 如何转化成具体 AR guidance 参数，我们补充一个 simulation
中的 deployment-evaluated parameter ablation。对每一个 structure dimension，我们改变
consistency constraint，同时固定 task success、learner、budget 和 deployment protocol。
结果显示，当 spatial/contact/temporal variation 超过一定范围时，deployment performance
明显下降。因此 AR guidance 参数被设置在 high-performing consistency range 内。
```

这个补丁直接回应“公式到 guidance 太突兀”的问题，而且不需要过度承诺全局最优。

## 核心实验问题

Rebuttal 阶段建议回答这个问题：

```text
在固定 learner 和有限 demonstration budget 下，P、R、V 分别需要多一致，才能得到较好的
deployment learning？
```

这个问题比下面这个更安全：

```text
如何在完整 P x R x V 空间中找到全局最优 z*？
```

Rebuttal 可以只声称做了有限候选集选择：

```text
z_hat = arg max J(A(D^z)),  z in C_ablation
```

其中 `C_ablation` 是 spatial、orientation、temporal consistency 参数的有限候选集合。

## 建议的消融实验

### 1. Spatial Structure：Tube / Pre-Grasp Region 消融

这是最容易做、最快出结果的实验，因为当前 simulation code 已经支持 approach noise。

核心问题：

```text
approach/pre-grasp region 可以有多大？超过多大之后 deployment learning 会下降？
```

候选参数：

| Candidate | 含义 | 示例参数 |
| --- | --- | --- |
| `P0` | 固定或接近 deterministic 的 approach | `0 cm` |
| `P1` | 小范围 approach variation | `1 cm` |
| `P2` | 中等 approach variation | `3 cm` |
| `P3` | 大范围 approach variation | `5 cm` |
| `P4` | 很大的 approach variation | `8 cm` |

如果时间紧，可以只做三档：

```text
0 cm, 3 cm, 6 cm
```

预期 rebuttal 表述：

```text
固定、小范围和中等范围的 approach variation 下，deployment performance 较高；
但 approach region 太大时，deployment performance 明显下降。这支持用 spatial corridor
guidance 来约束 novice demonstrations。
```

注意：这个实验不是为了证明某一个半径是 universal optimal。它只是证明 spatial
consistency 存在一个对 deployment learning 敏感的范围，而 AR corridor guidance 的参数被
设置在这个高性能范围内。

### 2. Contact Structure：Gripper Orientation Constraint 消融

这个实验很有说服力，因为提交版本的 simulation 结果已经显示 orientation inconsistency 对
deployment performance 的破坏最大。

核心问题：

```text
learner 能容忍多大的 closing-orientation variation？
```

候选参数：

| Candidate | 含义 | 示例参数 |
| --- | --- | --- |
| `R0` | 固定 closing orientation | `0 deg` |
| `R1` | 很小的 orientation variation | `±5 deg` |
| `R2` | 中等 orientation variation | `±15 deg` |
| `R3` | 较大的 orientation variation | `±30 deg` |
| `R4` | 很大的 orientation variation 或混合 orientation | `±45 deg` 或当前论文中的 `Rtilt` |

预期 rebuttal 表述：

```text
在 tight-to-moderate orientation variation 下，deployment performance 仍然较高；
但 large closing-orientation dispersion 会显著降低 deployment success。这支持使用
gripper-orientation guidance，并解释 appendix 中 15 degree tolerance 的来源。
```

这个实验可以直接连接 appendix 参数：

```text
Grasp orientation tolerance = 15 deg
```

### 3. Temporal Structure：Phase-Ratio / Timing Consistency 消融

这个实验概念上重要，但 rebuttal 阶段必须保持简单。不要做很大的 phase-ratio 网格搜索。

核心问题：

```text
不同 demonstrations 之间的 phase timing 需要多相似，才能让 policy 学得稳定？
```

可以把每条 trajectory 表示成一个 phase-ratio vector：

```text
q = [start, approach, descend, grasp, lift] / total_time
```

然后控制不同 demonstrations 之间的 phase-ratio jitter。

候选参数：

| Candidate | 含义 | 示例参数 |
| --- | --- | --- |
| `V0` | 固定 phase ratio | `0% jitter` |
| `V1` | 小 timing variation | `±10%` |
| `V2` | 中等 timing variation | `±25%` |
| `V3` | 大 timing variation | `±50%` |

预期 rebuttal 表述：

```text
由 phase timing 更一致的 demonstrations 训练出的 policies 部署更稳定。即使 scripted
demonstrations 都 task-successful，较大的 phase-ratio variation 仍然会降低 deployment
success。
```

这个实验可以连接 appendix 的 speed-bar 参数：

```text
relative speed tolerance = [0.5, 2.0] x v_ref
```

Rebuttal 中只需要证明 temporal inconsistency 重要，并说明 guidance 鼓励用户保持在
high-performing timing range 内。完整搜索每个 phase ratio 的最优值应留给 journal 版本。

## 最小实验矩阵

最小但有用的 rebuttal 实验可以是：

| Dimension | Levels | 条件数 |
| --- | --- | ---: |
| `P` spatial approach variation | `0, 3, 6 cm` | 3 |
| `R` orientation variation | `0, 15, 45 deg` | 3 |
| `V` phase-ratio jitter | `0, 25, 50%` | 3 |
| Shared baseline | fixed `P/R/V` | 1 |

如果 baseline 共享，总共大约 10 个 conditions。

每个 condition：

- 采集 `N = 30` task-successful demonstrations。
- 使用同一个 fixed visuomotor learner 训练。
- 使用同一个 deployment protocol 测试。
- 报告 empirical deployment success rate，即 `EDSR`。

第一轮 smoke test：

- 每个 condition 1 个 dataset seed。
- 每个 trained policy 10 次 deployment rollout。

Rebuttal-strength 版本：

- 每个 condition 3 个 dataset seeds。
- 每个 trained policy 10 次 deployment rollout。
- 报告 mean ± std。

如果算力允许，可以用 4 个 seeds，从而和论文已提交的 simulation table 保持一致。如果时间不够，
3 个 seeds 作为 additional ablation 也可以接受。

## 建议的结果表格

Rebuttal 中可以放类似这样的表：

| Structure | Candidate | Dispersion Parameter | EDSR (%) |
| --- | --- | --- | ---: |
| Spatial `P` | Fixed | `0 cm` | TBD |
| Spatial `P` | Moderate | `3 cm` | TBD |
| Spatial `P` | Large | `6 cm` | TBD |
| Contact `R` | Fixed | `0 deg` | TBD |
| Contact `R` | Moderate | `15 deg` | TBD |
| Contact `R` | Large | `45 deg` | TBD |
| Temporal `V` | Fixed | `0% jitter` | TBD |
| Temporal `V` | Moderate | `25% jitter` | TBD |
| Temporal `V` | Large | `50% jitter` | TBD |

如果有图，最好做三个小 line plots：

- EDSR vs spatial radius。
- EDSR vs orientation variation。
- EDSR vs temporal jitter。

这种图比大表更容易让审稿人理解。

## Rebuttal 可以怎么写

建议英文 rebuttal wording：

```text
We agree that the submitted version did not sufficiently detail how the
deployment-evaluated structure selection is translated into concrete AR guidance
parameters. To address this, we added a parameter ablation in simulation. For
each structure dimension P, R, and V, we constructed task-successful
demonstration datasets with controlled spatial dispersion, closing-orientation
dispersion, and phase-timing dispersion, respectively. The learner, embodiment,
budget, and rollout evaluation were kept fixed. Results show that deployment
performance remains high only within bounded consistency ranges and drops under
large spatial, contact, or temporal variation. The AR corridor, grasp-orientation
tolerance, and speed-bar thresholds used in Appendix A.5 were selected to keep
novice demonstrations within these high-performing ranges.
```

重要的是，不要这样 claim：

```text
We solved for the global z* over P x R x V.
```

更准确的表述是：

```text
We performed deployment-evaluated finite candidate selection over practical
guidance parameters.
```

这个说法更稳，也更符合当前实验能支持的结论。

## Rebuttal 阶段不建议做什么

短期 CoRL rebuttal 不建议做：

- 不要把 LIBERO 作为主要补丁。
- 不要把 ACT 或 VLA training 作为主要补丁。
- 不要临时招募大量新 participants，除非数据采集已经准备好了。
- 不要做完整 factorial `P x R x V` 搜索。
- 不要声称找到 universal optimal thresholds。

这些方向都很有价值，但更适合 journal 版本，不适合 rebuttal 窗口。

## Journal 版本方向

Journal extension 可以把方向扩展成：

```text
From hand-designed P/R/V structures to deployment-discovered teaching structures.
```

可能的扩展包括：

- 定义比 `P/R/V` 更大的 structure space。
- 在 LIBERO 这类 simulation benchmark 上做多任务验证。
- 测多个 learners：3D Diffusion Policy、ACT，甚至 VLA models。
- 增加更多真机 manipulation tasks。
- 招募更多 participants，提高 human-study statistical power。
- 研究不同 learner 是否偏好不同 teaching structures。
- 从 deployment sensitivity 自动发现哪些 structure dimensions 重要，而不是完全手动定义。

Journal 版本可以这样讲：

```text
CoRL 版本：DEMT 证明 deployment-selected P/R/V structures 可以训练 novice users
提供更 learnable 的 demonstrations。

Journal 版本：DEMT 进一步成为一种通用方法，用于发现不同 learners、tasks 和 embodiments
下，哪些 human-controllable demonstration structures 真正影响 robot learning。
```

## 推荐时间安排

### 第 1-2 天：确定候选参数

确定以下参数的具体 levels：

- Spatial approach radius。
- Closing-orientation variation。
- Temporal phase-ratio jitter。

候选集要小。目标是 rebuttal 故事清楚，而不是完整搜索。

### 第 3-5 天：实现并验证数据生成

每个 condition 都要检查：

- 能否生成 demo dataset。
- demonstrations 是否 task-successful。
- metadata 是否记录 condition 参数。
- phase labels 和 frame counts 是否正常。
- headless 模式下 point clouds 和 poses 是否有效。

### 第 6-8 天：Smoke Experiment

运行：

- 每个 condition 1 个 seed。
- 每个 policy 10 次 deployment rollout。

目标：

- 看趋势是否明显。
- 如果 effect 太小，增大 perturbation 幅度。
- 如果 demonstrations 还没训练就失败太多，减小 perturbation 幅度。

### 第 9-14 天：Rebuttal-Strength Ablation

运行：

- 每个 condition 3 个 seeds。
- 每个 trained policy 10 次 deployment rollout。

产出：

- EDSR 表格。
- 三个 line plots。
- 可选 secondary diagnostics：MPCV、MCOD、MPSV、validation loss。

### 第 15-18 天：写 Rebuttal 和 Appendix Patch

写：

- 简洁 rebuttal paragraph。
- 小表格或小图。
- 一段 appendix addition，解释 candidate construction。

文字上要强调这是在澄清 DEMT-to-guidance translation，而不是新增一个很大的 main
contribution。

## 个人建议

如果时间有限，先做 spatial ablation，因为现有代码最接近。然后做 orientation ablation，
因为它最有说服力。Temporal ablation 最后做，而且保持 coarse。

最强的最小补丁是：

```text
P/R/V 各三档，fixed learner，fixed budget，fixed deployment protocol，报告三组 seeds
上的 EDSR。
```

这足够回答最直接的审稿问题：

```text
AR guidance 参数不是任意设定的；它们被选择为让 demonstrations 落在
deployment-validated consistency ranges 内。
```
