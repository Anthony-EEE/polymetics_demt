# T-RO Stage 2 Position axial replication

**Classification: `partial`.**

Strict validation passed for 25 dataset-policy slots, 250/250 formal policy/rollout-seed/bank tasks and 6,250/6,250 rollout rows. Every canonical slot has exact five-condition accepted-latent pairing.

## Policy results

| Canonical seed | Actual collection/training seed | Condition | Successes/250 | Five rollout seeds mean ± sample std | Checkpoint epoch |
|---:|---|---|---:|---:|---:|
| 1 | 1/1 | `START15_APP6` | 143/250 | 0.572 ± 0.033 | 180 |
| 1 | 1/1 | `START35_APP6` | 55/250 | 0.220 ± 0.051 | 40 |
| 1 | 1/1 | `START25_APP3P6` | 171/250 | 0.684 ± 0.038 | 60 |
| 1 | 1/1 | `START25_APP6` | 77/250 | 0.308 ± 0.069 | 40 |
| 1 | 1/1 | `START25_APP8P4` | 32/250 | 0.128 ± 0.041 | 40 |
| 2 | 2/2 | `START15_APP6` | 98/250 | 0.392 ± 0.083 | 60 |
| 2 | 2/2 | `START35_APP6` | 79/250 | 0.316 ± 0.030 | 40 |
| 2 | 2/2 | `START25_APP3P6` | 92/250 | 0.368 ± 0.048 | 40 |
| 2 | 2/2 | `START25_APP6` | 60/250 | 0.240 ± 0.076 | 40 |
| 2 | 2/2 | `START25_APP8P4` | 28/250 | 0.112 ± 0.030 | 40 |
| 3 | 3/3 | `START15_APP6` | 89/250 | 0.356 ± 0.079 | 80 |
| 3 | 3/3 | `START35_APP6` | 104/250 | 0.416 ± 0.071 | 40 |
| 3 | 3/3 | `START25_APP3P6` | 115/250 | 0.460 ± 0.106 | 40 |
| 3 | 3/3 | `START25_APP6` | 166/250 | 0.664 ± 0.075 | 40 |
| 3 | 3/3 | `START25_APP8P4` | 113/250 | 0.452 ± 0.041 | 80 |
| 4 | 1702/2702 | `START15_APP6` | 53/250 | 0.212 ± 0.058 | 40 |
| 4 | 1702/2702 | `START35_APP6` | 29/250 | 0.116 ± 0.055 | 40 |
| 4 | 1702/2702 | `START25_APP3P6` | 77/250 | 0.308 ± 0.033 | 40 |
| 4 | 1702/2702 | `START25_APP6` | 133/250 | 0.532 ± 0.063 | 40 |
| 4 | 1702/2702 | `START25_APP8P4` | 93/250 | 0.372 ± 0.097 | 40 |
| 5 | 1701/2701 | `START15_APP6` | 82/250 | 0.328 ± 0.033 | 60 |
| 5 | 1701/2701 | `START35_APP6` | 150/250 | 0.600 ± 0.032 | 40 |
| 5 | 1701/2701 | `START25_APP3P6` | 107/250 | 0.428 ± 0.077 | 60 |
| 5 | 1701/2701 | `START25_APP6` | 176/250 | 0.704 ± 0.065 | 60 |
| 5 | 1701/2701 | `START25_APP8P4` | 35/250 | 0.140 ± 0.032 | 60 |

## Condition-level policy replication

| Rank | Condition | Five policy rates | Mean ± sample std |
|---:|---|---|---:|
| 1 | `START25_APP6` | `[0.308, 0.24, 0.664, 0.532, 0.704]` | 0.490 ± 0.208 |
| 2 | `START25_APP3P6` | `[0.684, 0.368, 0.46, 0.308, 0.428]` | 0.450 ± 0.143 |
| 3 | `START15_APP6` | `[0.572, 0.392, 0.356, 0.212, 0.328]` | 0.372 ± 0.131 |
| 4 | `START35_APP6` | `[0.22, 0.316, 0.416, 0.116, 0.6]` | 0.334 ± 0.186 |
| 5 | `START25_APP8P4` | `[0.128, 0.112, 0.452, 0.372, 0.14]` | 0.241 ± 0.159 |

## Canonical-seed deltas

| Seed | Candidate − reference | Candidate − wide | Start outer wide − tight | Approach inner tight − wide |
|---:|---:|---:|---:|---:|
| 1 | +0.376 | +0.556 | -0.240 | +0.600 |
| 2 | +0.128 | +0.256 | +0.072 | +0.304 |
| 3 | -0.204 | +0.008 | +0.160 | +0.120 |
| 4 | -0.224 | -0.064 | +0.072 | -0.032 |
| 5 | -0.276 | +0.288 | +0.384 | +0.336 |

## Pre-registered decision

- `D_candidate_reference`: mean `-0.040`, 2/5 positive slots, passed=`False`.
- `D_candidate_wide`: mean `+0.209`, 4/5 positive slots, passed=`True`.

Combined ranking: `['START25_APP6', 'START25_APP3P6', 'START15_APP6', 'START35_APP6', 'START25_APP8P4']`.

Inner ranking: `['START25_APP6', 'START25_APP3P6', 'START15_APP6', 'START35_APP6', 'START25_APP8P4']`.

Outer ranking: `['START25_APP6', 'START25_APP3P6', 'START35_APP6', 'START15_APP6', 'START25_APP8P4']`.

Wilson intervals in `comparison.json` are rollout-level descriptive intervals only. The cluster bootstrap resamples canonical dataset-policy slots as the top-level units. Rollout seeds are nested deployment trials, not independently trained policies.
