# T-RO Stage 2 Position condition-relative ID/OOD rerollout

Strict validation passed for 25 reused checkpoints, 30 frozen state manifests, 250/250 formal tasks and 6,250/6,250 rollout rows. Every policy has exactly 125 ID and 125 OOD trials.

## Policy results

| Seed | Actual collection/training | Condition | ID | OOD | OOD − ID | Balanced (descriptive) |
|---:|---|---|---:|---:|---:|---:|
| 1 | 1/1 | `START15_APP6` | 97/125 (0.776) | 46/125 (0.368) | -0.408 | 0.572 |
| 1 | 1/1 | `START35_APP6` | 30/125 (0.240) | 20/125 (0.160) | -0.080 | 0.200 |
| 1 | 1/1 | `START25_APP3P6` | 87/125 (0.696) | 48/125 (0.384) | -0.312 | 0.540 |
| 1 | 1/1 | `START25_APP6` | 43/125 (0.344) | 16/125 (0.128) | -0.216 | 0.236 |
| 1 | 1/1 | `START25_APP8P4` | 13/125 (0.104) | 3/125 (0.024) | -0.080 | 0.064 |
| 2 | 2/2 | `START15_APP6` | 83/125 (0.664) | 26/125 (0.208) | -0.456 | 0.436 |
| 2 | 2/2 | `START35_APP6` | 33/125 (0.264) | 34/125 (0.272) | +0.008 | 0.268 |
| 2 | 2/2 | `START25_APP3P6` | 47/125 (0.376) | 29/125 (0.232) | -0.144 | 0.304 |
| 2 | 2/2 | `START25_APP6` | 20/125 (0.160) | 34/125 (0.272) | +0.112 | 0.216 |
| 2 | 2/2 | `START25_APP8P4` | 16/125 (0.128) | 14/125 (0.112) | -0.016 | 0.120 |
| 3 | 3/3 | `START15_APP6` | 67/125 (0.536) | 22/125 (0.176) | -0.360 | 0.356 |
| 3 | 3/3 | `START35_APP6` | 48/125 (0.384) | 51/125 (0.408) | +0.024 | 0.396 |
| 3 | 3/3 | `START25_APP3P6` | 71/125 (0.568) | 43/125 (0.344) | -0.224 | 0.456 |
| 3 | 3/3 | `START25_APP6` | 68/125 (0.544) | 68/125 (0.544) | +0.000 | 0.544 |
| 3 | 3/3 | `START25_APP8P4` | 57/125 (0.456) | 44/125 (0.352) | -0.104 | 0.404 |
| 4 | 1702/2702 | `START15_APP6` | 49/125 (0.392) | 18/125 (0.144) | -0.248 | 0.268 |
| 4 | 1702/2702 | `START35_APP6` | 19/125 (0.152) | 24/125 (0.192) | +0.040 | 0.172 |
| 4 | 1702/2702 | `START25_APP3P6` | 45/125 (0.360) | 33/125 (0.264) | -0.096 | 0.312 |
| 4 | 1702/2702 | `START25_APP6` | 71/125 (0.568) | 49/125 (0.392) | -0.176 | 0.480 |
| 4 | 1702/2702 | `START25_APP8P4` | 66/125 (0.528) | 28/125 (0.224) | -0.304 | 0.376 |
| 5 | 1701/2701 | `START15_APP6` | 65/125 (0.520) | 26/125 (0.208) | -0.312 | 0.364 |
| 5 | 1701/2701 | `START35_APP6` | 70/125 (0.560) | 76/125 (0.608) | +0.048 | 0.584 |
| 5 | 1701/2701 | `START25_APP3P6` | 49/125 (0.392) | 45/125 (0.360) | -0.032 | 0.376 |
| 5 | 1701/2701 | `START25_APP6` | 97/125 (0.776) | 58/125 (0.464) | -0.312 | 0.620 |
| 5 | 1701/2701 | `START25_APP8P4` | 19/125 (0.152) | 22/125 (0.176) | +0.024 | 0.164 |

## Condition-level ID/OOD trade-off

| Condition | ID mean ± policy std | OOD mean ± policy std | Gap mean ± policy std | Pareto |
|---|---:|---:|---:|---|
| `START15_APP6` | 0.578 ± 0.147 | 0.221 ± 0.086 | -0.357 ± 0.081 | yes |
| `START35_APP6` | 0.320 ± 0.158 | 0.328 ± 0.183 | +0.008 ± 0.052 | no |
| `START25_APP3P6` | 0.478 ± 0.148 | 0.317 ± 0.065 | -0.162 ± 0.109 | no |
| `START25_APP6` | 0.478 ± 0.235 | 0.360 ± 0.164 | -0.118 ± 0.171 | yes |
| `START25_APP8P4` | 0.274 ± 0.202 | 0.178 ± 0.123 | -0.096 ± 0.127 | no |

ID ranking: `['START15_APP6', 'START25_APP3P6', 'START25_APP6', 'START35_APP6', 'START25_APP8P4']`.

OOD ranking: `['START25_APP6', 'START35_APP6', 'START25_APP3P6', 'START15_APP6', 'START25_APP8P4']`.

ID/OOD Pareto front: `['START15_APP6', 'START25_APP6']`.

The balanced ranking in `comparison.json` is descriptive only. Its banks have different absolute radial intervals across Start families and therefore do not form a common deployment distribution.

## Pairing and uncertainty

The three `START25_*` conditions use identical absolute states, state order and RNG streams. Cross-Start comparisons use identical area quantiles, XZ directions, normalized state indices and RNG streams, while absolute positions necessarily differ.

Wilson intervals are rollout-level descriptions only. The cluster bootstrap resamples the five canonical dataset-policy seeds as top-level policy units.
