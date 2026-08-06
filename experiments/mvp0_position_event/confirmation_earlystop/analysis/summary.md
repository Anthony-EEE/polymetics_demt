# T-RO Position early-stopping confirmation

Strict validation passed for five policies, five shared rollout seeds, 25 inner plus 25 outer states per seed: **1,250 rollout rows**.

`START25_APP6` is the accepted legacy S25 epoch-80 baseline. Its deployment states and RNG are exactly paired with the four new policies, but its demonstration dataset and training seed differ; baseline differences therefore include training-dataset/seed variation.

## Overall ranking

| Rank | Condition | Successes | Five-seed mean ± std |
|---:|---|---:|---:|
| 1 | `START25_APP3P6` | 144/250 | 0.576 ± 0.038 |
| 2 | `START25_APP8P4` | 126/250 | 0.504 ± 0.062 |
| 3 | `START25_APP6` | 116/250 | 0.464 ± 0.086 |
| 4 | `START15_APP6` | 112/250 | 0.448 ± 0.097 |
| 5 | `START35_APP6` | 69/250 | 0.276 ± 0.052 |

## Inner ranking

| Rank | Condition | Successes | Five-seed mean ± std |
|---:|---|---:|---:|
| 1 | `START25_APP3P6` | 78/125 | 0.624 ± 0.083 |
| 2 | `START25_APP8P4` | 71/125 | 0.568 ± 0.087 |
| 3 | `START15_APP6` | 69/125 | 0.552 ± 0.148 |
| 4 | `START25_APP6` | 62/125 | 0.496 ± 0.108 |
| 5 | `START35_APP6` | 41/125 | 0.328 ± 0.066 |

## Outer ranking

| Rank | Condition | Successes | Five-seed mean ± std |
|---:|---|---:|---:|
| 1 | `START25_APP3P6` | 66/125 | 0.528 ± 0.052 |
| 2 | `START25_APP8P4` | 55/125 | 0.440 ± 0.080 |
| 3 | `START25_APP6` | 54/125 | 0.432 ± 0.134 |
| 4 | `START15_APP6` | 43/125 | 0.344 ± 0.067 |
| 5 | `START35_APP6` | 28/125 | 0.224 ± 0.078 |

## Contrasts

- `start_outer_wide_minus_tight`: -15/125 (-0.120).
- `approach_inner_tight_minus_wide`: +7/125 (+0.056).
- `approach_combined_tight_minus_baseline`: +28/250 (+0.112).
- `approach_inner_tight_minus_baseline`: +16/125 (+0.128).
- `approach_outer_tight_minus_baseline`: +12/125 (+0.096).
- `approach_combined_wide_minus_baseline`: +10/250 (+0.040).
