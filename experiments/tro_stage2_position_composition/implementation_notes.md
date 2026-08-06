# T-RO Stage 2c Position Composition Implementation Notes

An independent `tro_position_composition` profile was added without changing
the old Stage 2 condition map. Its only new conditions are
`START15_APP3P6`, `START15_APP8P4`, `START35_APP3P6` and
`START35_APP8P4`.

Gate 0 rehashed all 25 old checkpoints and HDF5 anchors. Gate 1 selected the
exact final 30 accepted IDs from each Stage 2 collection progress file;
seed1 and seed5 resolved through their active whole-slot fallback manifests.
All 600 prospective corner records matched the normalized latent fields in
all five axial anchors and passed the 0.025 m waypoint IK criterion.

The five-seed smoke then completed all four corners successfully. Formal
collection preserves the frozen ID order and treats the four corners
atomically. It does not search or replace latents. During formal collection,
seed4 candidate 4 and seed5 candidate 1 failed at `START35_APP8P4` with the
cube remaining near table height. Those deterministic frozen-input outcomes
are scientific failures, not infrastructure failures. The array was stopped,
and no HDF5, training or rollout work was started.

See `manifests/protocol_blocker.json` for the hash-addressed evidence.
