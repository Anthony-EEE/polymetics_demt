# T-RO Stage 1 Position MVP implementation notes

## Frozen semantics

The accepted generator remains `examples/main_abla_1.py`. Execution is still:

```text
Start → Approach → Descent → Grasp → Lift
```

The cube, fixed grasp target `(cube_x, cube_y, 0.04)`, fixed lift target
`(cube_x, cube_y, 0.30)`, motion controller, sampling rate and final
`cube z >= 0.20 m` success criterion are unchanged.

The frozen legacy S25 demonstration metadata records `sample_hz=8.0`; raw
validation rejects any new formal dataset with a different sampling rate.

The only generator extension is an optional explicit paired latent. It maps
the same Start and Approach angles and radial quantiles into each condition's
configured radii. Legacy conditions still use their original RNG path.

## Paired collection

`scripts/tro_position_mvp0.py` freezes a block-level candidate pool before
collection. A candidate is staged for all four conditions. If any condition is
unreachable or unsuccessful, all staged data for that candidate is rejected
and the next frozen replacement candidate is tried. Only a four-condition
success is promoted into the final raw datasets.

## Legacy isolation

All new raw data, HDF5 files and rollouts are under
`dataset/tro_position_mvp0/`. New models are under
`../trained_models/tro_position_mvp0/`. No new launcher or config uses the
closed `dataset/ar_guidance_spatial_S15_S35/` tree as an output.

The legacy summary, 50-state parent manifest and S25 epoch-80 checkpoint are
opened read-only for hashing or evaluation provenance. Child bank manifests
copy the selected state records without modifying the parent.

## Training and evaluation

Training configs are deep copies of the legacy S15–S35 learner template with
only dataset path, output path, experiment name, fixed block seed,
`num_epochs=40` and fixed epoch-40 saving changed.

The existing evaluator retains its legacy defaults and adds an explicit
`tro_position_mvp0` profile. The profile consumes the two frozen child
manifests, keeps the original state records and RNG seeds, and records both
the bank-local rollout index and immutable legacy state ID.
