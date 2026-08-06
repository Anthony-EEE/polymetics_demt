# T-RO Stage 1 Position MVP summary

**Corrected five-seed decision:** null/unstable.

The earlier single-seed rollout comparison is superseded. The corrected evaluation uses the eight existing policies without recollection or retraining. Each policy was evaluated on the same five seeds (`628`–`632`), with 25 inner and 25 outer states per seed.

Strictly validated coverage: **8 policies × 5 seeds × 50 rollouts = 2,000 rollout rows**.

## Existing checkpoint audit

Every policy directory contains only `model_epoch_20.pth` and `model_epoch_40.pth`. Following the corrected instruction to use the highest numeric existing checkpoint, all eight policies use their existing `model_epoch_40.pth`. No training was run.

## Eight-policy ranking across rollout seeds

For each policy, the five values are its five `successes/50` rollout rates. The table reports their mean ± sample standard deviation (`ddof=1`). This is the primary robustness ranking.

| Rank | Policy | Five seed results | Mean ± std |
|---:|---|---|---:|
| 1 | `block0/START25_APP3P6` | `[29/50, 25/50, 31/50, 24/50, 28/50]` | 0.548 ± 0.058 |
| 2 | `block0/START15_APP6` | `[21/50, 23/50, 27/50, 22/50, 21/50]` | 0.456 ± 0.050 |
| 3 | `block0/START25_APP8P4` | `[26/50, 20/50, 20/50, 15/50, 19/50]` | 0.400 ± 0.079 |
| 4 | `block1/START25_APP8P4` | `[14/50, 22/50, 19/50, 21/50, 17/50]` | 0.372 ± 0.064 |
| 5 | `block1/START25_APP3P6` | `[11/50, 20/50, 14/50, 17/50, 19/50]` | 0.324 ± 0.074 |
| 6 | `block0/START35_APP6` | `[12/50, 20/50, 11/50, 11/50, 17/50]` | 0.284 ± 0.082 |
| 7 | `block1/START15_APP6` | `[10/50, 10/50, 15/50, 14/50, 14/50]` | 0.252 ± 0.048 |
| 8 | `block1/START35_APP6` | `[5/50, 5/50, 2/50, 9/50, 7/50]` | 0.112 ± 0.052 |

## Inner success ranking

| Rank | Policy | Inner total | Five-seed mean ± std |
|---:|---|---:|---:|
| 1 | `block0/START15_APP6` | 80/125 | 0.640 ± 0.075 |
| 2 | `block0/START25_APP3P6` | 73/125 | 0.584 ± 0.061 |
| 3 | `block1/START25_APP8P4` | 55/125 | 0.440 ± 0.089 |
| 4 | `block1/START25_APP3P6` | 47/125 | 0.376 ± 0.073 |
| 5 | `block0/START25_APP8P4` | 46/125 | 0.368 ± 0.111 |
| 6 | `block1/START15_APP6` | 41/125 | 0.328 ± 0.033 |
| 7 | `block0/START35_APP6` | 35/125 | 0.280 ± 0.085 |
| 8 | `block1/START35_APP6` | 12/125 | 0.096 ± 0.073 |

## Outer success ranking

| Rank | Policy | Outer total | Five-seed mean ± std |
|---:|---|---:|---:|
| 1 | `block0/START25_APP3P6` | 64/125 | 0.512 ± 0.072 |
| 2 | `block0/START25_APP8P4` | 54/125 | 0.432 ± 0.107 |
| 3 | `block1/START25_APP8P4` | 38/125 | 0.304 ± 0.083 |
| 4 | `block0/START35_APP6` | 36/125 | 0.288 ± 0.087 |
| 5 | `block0/START15_APP6` | 34/125 | 0.272 ± 0.066 |
| 6 | `block1/START25_APP3P6` | 34/125 | 0.272 ± 0.087 |
| 7 | `block1/START15_APP6` | 22/125 | 0.176 ± 0.092 |
| 8 | `block1/START35_APP6` | 16/125 | 0.128 ± 0.033 |

## Hierarchical B0/B1 condition comparison

B0 and B1 each report mean ± sample std across their five rollout seeds. The final column reports mean ± sample std across the two independent policy means.

| Rank | Condition | B0 rollout seeds | B1 rollout seeds | Across blocks |
|---:|---|---:|---:|---:|
| 1 | `START25_APP3P6` | 0.548 ± 0.058 | 0.324 ± 0.074 | 0.436 ± 0.158 |
| 2 | `START25_APP8P4` | 0.400 ± 0.079 | 0.372 ± 0.064 | 0.386 ± 0.020 |
| 3 | `START15_APP6` | 0.456 ± 0.050 | 0.252 ± 0.048 | 0.354 ± 0.144 |
| 4 | `START35_APP6` | 0.284 ± 0.082 | 0.112 ± 0.052 | 0.198 ± 0.122 |

## Seed stability

| Policy | seed 628 | seed 629 | seed 630 | seed 631 | seed 632 |
|---|---:|---:|---:|---:|---:|
| `block0/START25_APP3P6` | 29/50 | 25/50 | 31/50 | 24/50 | 28/50 |
| `block0/START15_APP6` | 21/50 | 23/50 | 27/50 | 22/50 | 21/50 |
| `block0/START25_APP8P4` | 26/50 | 20/50 | 20/50 | 15/50 | 19/50 |
| `block1/START25_APP8P4` | 14/50 | 22/50 | 19/50 | 21/50 | 17/50 |
| `block1/START25_APP3P6` | 11/50 | 20/50 | 14/50 | 17/50 | 19/50 |
| `block0/START35_APP6` | 12/50 | 20/50 | 11/50 | 11/50 | 17/50 |
| `block1/START15_APP6` | 10/50 | 10/50 | 15/50 | 14/50 | 14/50 |
| `block1/START35_APP6` | 5/50 | 5/50 | 2/50 | 9/50 | 7/50 |

## Mechanism result

| Block | Start outer: wide − tight | Approach inner: tight − wide |
|---:|---:|---:|
| 0 | 2/125 (+0.016) | 27/125 (+0.216) |
| 1 | -6/125 (-0.048) | -8/125 (-0.064) |

Start variation does not replicate: corrected block effects are `[0.016, -0.048]`. Approach tightening is strong in Block 0 but reverses in Block 1: corrected block effects are `[0.216, -0.064]`.

The best individual policy is `block0/START25_APP3P6` at 137/250 (54.8%), and it is stable across seeds (24–31 successes per 50). However, its independent Block 1 counterpart reaches only 81/250 (32.4%) and loses to the wide-Approach counterpart. The evidence therefore supports a learner-block effect, not a reproducible position mechanism.

## Conclusion and stop

**Final Stage 1 classification remains `null/unstable`, now based on the corrected five-seed evaluation.** Neither primary mechanism is positive in both independent learner blocks, so there is no robust basis for Stage 2. Rotation, Velocity, AR and human experiments were not launched.

Full per-policy, per-seed, paired-discordance and checkpoint evidence is in `analysis/rollout_5seed_comparison.json`.
