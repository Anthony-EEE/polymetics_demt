# T-RO Stage 2c Position Composition Summary

**Interaction classification:** `interaction`

The primary common-absolute analysis uses five canonical dataset-policy seeds; rollout seeds and individual rows remain nested deployment trials.

## Frozen interaction contrasts

| Contrast | Seed values | Mean | SD | Bootstrap 95% | Sign | Signal |
|---|---|---:|---:|---|---:|---|
| `I_tight_15` | -0.556, 0.044, 0.388, 0.648, 0.288 | 0.162 | 0.456 | [-0.218, 0.475] | 4/5 | yes |
| `I_tight_35` | -0.572, 0.140, 0.088, 0.264, 0.048 | -0.006 | 0.326 | [-0.306, 0.190] | 1/5 | no |
| `I_wide_15` | -0.200, -0.012, 0.024, 0.280, 0.712 | 0.161 | 0.352 | [-0.080, 0.443] | 3/5 | no |
| `I_wide_35` | 0.064, -0.076, 0.396, 0.156, 0.112 | 0.130 | 0.172 | [0.008, 0.282] | 4/5 | yes |

## Common-absolute condition means

| Condition | Combined | Inner | Outer |
|---|---:|---:|---:|
| `START15_APP3P6` | 0.494 | 0.651 | 0.338 |
| `START15_APP6` | 0.372 | 0.472 | 0.272 |
| `START15_APP8P4` | 0.284 | 0.387 | 0.181 |
| `START25_APP3P6` | 0.450 | 0.518 | 0.381 |
| `START25_APP6` | 0.490 | 0.546 | 0.434 |
| `START25_APP8P4` | 0.241 | 0.253 | 0.229 |
| `START35_APP3P6` | 0.287 | 0.306 | 0.269 |
| `START35_APP6` | 0.334 | 0.306 | 0.362 |
| `START35_APP8P4` | 0.215 | 0.226 | 0.205 |

## Condition-relative RMAX40

| Condition | ID | OOD | ID-OOD |
|---|---:|---:|---:|
| `START15_APP3P6` | 0.758 | 0.269 | 0.490 |
| `START15_APP6` | 0.578 | 0.221 | 0.357 |
| `START15_APP8P4` | 0.418 | 0.149 | 0.269 |
| `START25_APP3P6` | 0.478 | 0.317 | 0.162 |
| `START25_APP6` | 0.478 | 0.360 | 0.118 |
| `START25_APP8P4` | 0.274 | 0.178 | 0.096 |
| `START35_APP3P6` | 0.280 | 0.251 | 0.029 |
| `START35_APP6` | 0.320 | 0.328 | -0.008 |
| `START35_APP8P4` | 0.179 | 0.163 | 0.016 |

RMAX40 is secondary and condition-relative; cross-Start balanced scores are not a common absolute deployment distribution.

Wilson intervals in `comparison.json` are rollout-level descriptions only.
