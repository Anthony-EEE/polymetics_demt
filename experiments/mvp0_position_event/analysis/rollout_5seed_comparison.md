# Corrected five-seed rollout comparison

This comparison uses the eight existing policies without retraining. For every existing training run, the checkpoint with the highest numeric `model_epoch_*.pth` suffix was selected and hash-verified.

All eight policies use the same five seeds (`628`–`632`). Each seed has 25 inner states and 25 outer states, giving 250 rollouts per policy and 2,000 strictly validated rollout rows in total.

## Eight-policy ranking by five rollout seeds

For each policy, the five observations are the five `successes/50` rates. Values are mean ± sample standard deviation (`ddof=1`).

| Rank | Policy | Five-seed rates | Mean ± std |
|---:|---|---|---:|
| 1 | `block0/START25_APP3P6` | `[0.58, 0.5, 0.62, 0.48, 0.56]` | 0.548 ± 0.058 |
| 2 | `block0/START15_APP6` | `[0.42, 0.46, 0.54, 0.44, 0.42]` | 0.456 ± 0.050 |
| 3 | `block0/START25_APP8P4` | `[0.52, 0.4, 0.4, 0.3, 0.38]` | 0.400 ± 0.079 |
| 4 | `block1/START25_APP8P4` | `[0.28, 0.44, 0.38, 0.42, 0.34]` | 0.372 ± 0.064 |
| 5 | `block1/START25_APP3P6` | `[0.22, 0.4, 0.28, 0.34, 0.38]` | 0.324 ± 0.074 |
| 6 | `block0/START35_APP6` | `[0.24, 0.4, 0.22, 0.22, 0.34]` | 0.284 ± 0.082 |
| 7 | `block1/START15_APP6` | `[0.2, 0.2, 0.3, 0.28, 0.28]` | 0.252 ± 0.048 |
| 8 | `block1/START35_APP6` | `[0.1, 0.1, 0.04, 0.18, 0.14]` | 0.112 ± 0.052 |

## Inner success ranking across five rollout seeds

| Rank | Policy | Inner successes | Mean ± std |
|---:|---|---:|---:|
| 1 | `block0/START15_APP6` | 80/125 | 0.640 ± 0.075 |
| 2 | `block0/START25_APP3P6` | 73/125 | 0.584 ± 0.061 |
| 3 | `block1/START25_APP8P4` | 55/125 | 0.440 ± 0.089 |
| 4 | `block1/START25_APP3P6` | 47/125 | 0.376 ± 0.073 |
| 5 | `block0/START25_APP8P4` | 46/125 | 0.368 ± 0.111 |
| 6 | `block1/START15_APP6` | 41/125 | 0.328 ± 0.033 |
| 7 | `block0/START35_APP6` | 35/125 | 0.280 ± 0.085 |
| 8 | `block1/START35_APP6` | 12/125 | 0.096 ± 0.073 |

## Outer success ranking across five rollout seeds

| Rank | Policy | Outer successes | Mean ± std |
|---:|---|---:|---:|
| 1 | `block0/START25_APP3P6` | 64/125 | 0.512 ± 0.072 |
| 2 | `block0/START25_APP8P4` | 54/125 | 0.432 ± 0.107 |
| 3 | `block1/START25_APP8P4` | 38/125 | 0.304 ± 0.083 |
| 4 | `block0/START35_APP6` | 36/125 | 0.288 ± 0.087 |
| 5 | `block0/START15_APP6` | 34/125 | 0.272 ± 0.066 |
| 6 | `block1/START25_APP3P6` | 34/125 | 0.272 ± 0.087 |
| 7 | `block1/START15_APP6` | 22/125 | 0.176 ± 0.092 |
| 8 | `block1/START35_APP6` | 16/125 | 0.128 ± 0.033 |

## Hierarchical condition comparison across Block 0 and Block 1

B0/B1 cells summarize five rollout seeds within each policy. The last column summarizes the two policy means and therefore measures learner-block sensitivity.

| Rank | Condition | B0: seed mean ± std | B1: seed mean ± std | Across blocks: mean ± std |
|---:|---|---:|---:|---:|
| 1 | `START25_APP3P6` | 0.548 ± 0.058 | 0.324 ± 0.074 | 0.436 ± 0.158 |
| 2 | `START25_APP8P4` | 0.400 ± 0.079 | 0.372 ± 0.064 | 0.386 ± 0.020 |
| 3 | `START15_APP6` | 0.456 ± 0.050 | 0.252 ± 0.048 | 0.354 ± 0.144 |
| 4 | `START35_APP6` | 0.284 ± 0.082 | 0.112 ± 0.052 | 0.198 ± 0.122 |

## Results by seed

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

## Within-block mechanism contrasts

| Block | Start outer: wide − tight | Per-seed differences | Approach inner: tight − wide | Per-seed differences |
|---:|---:|---|---:|---|
| 0 | 2/125 (+0.016) | `[0, 2, -2, -2, 4]` | 27/125 (+0.216) | `[1, 3, 9, 5, 9]` |
| 1 | -6/125 (-0.048) | `[1, 1, -4, -3, -1]` | -8/125 (-0.064) | `[-1, -3, -2, 0, -2]` |

The earlier single-seed epoch-40 rollout analysis is retained for provenance but is superseded for policy comparison by this five-seed evaluation.
