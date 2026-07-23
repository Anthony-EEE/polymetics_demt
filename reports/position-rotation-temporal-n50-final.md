# Position、Rotation 与 Temporal 配对 N50 Rollout 最终结果

_完成日期：2026-07-20 · 分支：`hpc-headless-data-collection` @ `de6d7de`_

## 总览

本报告汇总三个最终实验 track：Position、Rotation 和 Temporal。全部主评估均采用：

- `seed=628`，每个条件 50 次全新 rollout；
- `horizon=200`，`sample_hz=8`，`action_gap=2`，`action_dt=0.25 s`；
- `terminate_on_success=true`，成功规则为 `cube z >= 0.20 m`；
- CUDA 推理，10,000 点点云，视频为 320×320、20 fps；
- 起点与 RNG 配对仅在各自 track 内成立，三个 track 之间不互相配对。

## 1. Position

Position 的五个条件共享完全相同的 50 个绝对 corridor starts。这些起点以
`[0.3, 0.0, 0.5]` 为圆心，在半径 `0.35 m` 的 XZ 圆盘中按面积均匀采样，
并逐点通过 IK 验证。

| 条件 | corridor-start 半径 | pre-grasp 半径 | Checkpoint epoch | 成功数 | 成功率 | Wilson 95% CI | 成功样本中位耗时 | 已接受 N10 | N50−N10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| S15 | 0.15 m | 0.036 m | 40 | 18/50 | 36% | 24.1%–49.9% | 7.000 s | 60% | −24 pp |
| S20 | 0.20 m | 0.048 m | 40 | 18/50 | 36% | 24.1%–49.9% | 7.000 s | 30% | +6 pp |
| S25 | 0.25 m | 0.060 m | 80 | 18/50 | 36% | 24.1%–49.9% | 7.625 s | 40% | −4 pp |
| S30 | 0.30 m | 0.072 m | 40 | 13/50 | 26% | 15.9%–39.6% | 7.500 s | 10% | +16 pp |
| S35 | 0.35 m | 0.084 m | 40 | 7/50 | 14% | 7.0%–26.2% | 6.750 s | 20% | −6 pp |

- 最终汇总：`dataset/ar_guidance_spatial_S15_S35/policy_rollouts_seed628_shared_r35_paired_n50_h200/summary_seed628_n50.json`
- Aggregate SHA-256：`ec9c95ba26e3a4b9f18ae7c34966a8d55dc3acca2af10c18bdbc43d12c827d78`
- Start manifest SHA-256：`84316b36922ea71225615d285bffccdfef4b99289650e302c963deb761f516ce`
- Checkpoint manifest SHA-256：`d52fcd84cf50d0cdf7ebda9031694545bebb0f806cabc5196d6cd642ff57509e`
- Rollout array：`35897463_[0-4]`；S30 retry：`35897532`；严格 merge：`35897581`

## 2. Rotation

Rotation 对应 R00/R15/R30 orientation/contact-degree 条件。三个条件共享相同的
50 个不同随机起点，满足 `y=0`、`x,z∈[0.2,0.6]`。每个 rollout 共享旋转轴和
common `u`，并按 `angle=(2u−1)×max_degrees` 映射；R00 始终精确为零度。

| 条件 | 旋转范围 | Checkpoint epoch | 成功数 | 成功率 | Wilson 95% CI | 成功样本中位耗时 | 已接受 N10 | N50−N10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| R00 | 0° | 40 | 30/50 | 60% | 46.2%–72.4% | 7.000 s | 70% | −10 pp |
| R15 | ±15° | 40 | 37/50 | 74% | 60.4%–84.1% | 7.000 s | 60% | +14 pp |
| R30 | ±30° | 40 | 32/50 | 64% | 50.1%–75.9% | 6.875 s | 40% | +24 pp |

- 最终汇总：`dataset/orn_mvp_full/policy_rollouts_seed628_paired_n50_h200/summary_seed628_n50.json`
- Aggregate SHA-256：`99dbb06031f0d5d86d481cd113afccf38874f7248c9f66ee3f3c83a6cb1e0e5e`
- Paired manifest SHA-256：`7310ab96395691e89001b5dce9a1eb0303575e5d90422786a995c6172cfdf3c2`
- Checkpoint manifest SHA-256：`bea265b491144cbfef5c5dd1025547cd97d4bbf918d9d4cdc4e8c5c953865967`
- Rollout array：`35897465_[0-2]`；严格 merge：`35897466`

## 3. Temporal

Temporal 使用纠正后的 spatially-distributed reciprocal-vref 设计。四个条件共享
相同的 50 个不同、IK 可达随机起点以及配对的 simulator/runtime/point-cloud RNG。
每个条件只改变 P6/P7 的 reciprocal duration-multiplier 范围。

| 条件 | reciprocal `n` | multiplier 范围 | Checkpoint epoch | 成功数 | 成功率 | Wilson 95% CI | 成功样本中位耗时 |
|---|---:|---:|---:|---:|---:|---:|---:|
| VR1P5 | 3/2 | [2/3, 3/2] | 40 | 37/50 | 74% | 60.4%–84.1% | 5.750 s |
| V050_200 | 2 | [1/2, 2] | 40 | 37/50 | 74% | 60.4%–84.1% | 7.000 s |
| VR3 | 3 | [1/3, 3] | 40 | 33/50 | 66% | 52.2%–77.6% | 10.750 s |
| VR4 | 4 | [1/4, 4] | 40 | 18/50 | 36% | 24.1%–49.9% | 11.500 s |

这些 reciprocal temporal 条件没有与其一一对应的已接受 N10，因此不报告误导性的
N50−N10 差值。旧的 fixed-point temporal 结果已被判定为无效，不得用于比较。

- 最终汇总：`dataset/temporal_vref_reciprocal_spatial_v2/policy_rollouts_seed628_paired_n50_h200/summary_seed628_n50.json`
- Aggregate SHA-256：`3c84bdecc4bb1113a7d84f0b8ed0ac8e116f98c1008d0eeaa8cca36f20f3e9ed`
- Paired manifest SHA-256：`1bb280bdf63aca2da0b261f89be3541eb1b7e91dd5833eea43d0469030d95e1b`
- Checkpoint manifest SHA-256：`61cb091e8ba666ceb43e77b2727324754b1969fede34ce1fb5d12ab86b922972`
- Training jobs：VR1P5 `35882393`、V050_200 `35882394`、VR3 `35881848`、VR4 `35881849`
- Rollout array：`35884281_[0-3]`；严格 merge：`35884542`

## 跨 Track 结果表

| Track | 最佳条件 | 最佳成功率 | 最低条件 | 最低成功率 | 主要观察 |
|---|---|---:|---|---:|---|
| Position | S15/S20/S25 | 36% | S35 | 14% | 更宽的 Position 条件整体更困难，S35 最低 |
| Rotation | R15 | 74% | R00 | 60% | N50 下 R15 最高，R30 仍达到 64% |
| Temporal | VR1P5/V050_200 | 74% | VR4 | 36% | reciprocal 范围扩大后成功率和效率明显下降 |

## 最终验证

- 严格验证 12 个条件、600 个逐 rollout JSON，无缺失、过期或额外文件。
- 验证各 track 内 realised starts、paired specs、manifest/checkpoint 路径及 SHA-256。
- 验证 Rotation common-axis/common-`u` 映射与 R00 精确零角度。
- 验证 Temporal reciprocal 分数定义、共享起点与四条件配对关系。
- 验证成功规则、提前终止、steps/time-to-success、Wilson 区间和配对列联表。
- 三个实验的 12 个正式视频均完成全帧解码与人工抽帧检查。
- 对应单元测试、Python 编译、Shell 语法及 `git diff --check` 均通过。
- 已接受 N10 文件未被覆盖；最终 Slurm 队列为空。

## 使用说明

Position 和 Rotation 的 N50 是在冻结协议下重新运行的完整 50 次 rollout，不能与旧
N10 拼接。Temporal 使用纠正后的 spatially-distributed reciprocal-vref 数据、模型与
评估，禁止替换为已删除或历史 fixed-point temporal 结果。
