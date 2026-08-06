# T-RO Stage 2 Position axial replication implementation notes

## Authority and isolation

- `PLAN.md` is the sole scientific authority.
- Stage 2 uses new collection, training, rollout and analysis namespaces.
- Existing Stage 1/1b condition maps and manifests remain unchanged.
- The evaluator gained a separate `tro_position_stage2` profile; the existing
  `tro_position_mvp0` and `tro_position_confirmation` profiles retain their
  prior condition maps and behavior.
- Formal raw/HDF5/log outputs are under
  `dataset/tro_position_stage2_axial/`.
- New checkpoints are under
  `/scratch/prj/eng_demt_robot_learning/trained_models/tro_position_stage2_axial/`.

## Gate 0 audit

- The four explicitly frozen Stage 1b/legacy SHA-256 values matched.
- All eight reused Stage 1 HDF5 files and all four reused Stage 1b
  early-stopped checkpoints were independently rehashed and matched their
  source manifests.
- The nine reused dataset slots and five reused policy slots are recorded in
  `manifests/artifact_reuse.json`.
- Legacy seed-1 normalized Start/Approach latents are reconstructed from the
  exact 30 raw `metadata.json` offset records. The old raw data did not record
  a simulator runtime seed; Stage 2 records that limitation and uses a
  deterministic runtime alias without changing the reconstructed directions
  or radial fractions.
- Canonical seed4 and seed5 use the exact accepted candidate records from old
  Block 1 and Block 0 respectively, including their original runtime seeds.

## Pairing and failure behavior

- Seeds 2 and 3 use frozen whole-five-condition candidate pools.
- Seeds 1, 4 and 5 initially use locked accepted records. A locked record is
  tried twice to distinguish a persistent deterministic scientific failure
  from a transient execution issue.
- A persistent locked-record failure is recorded as
  `fallback_required=true`; it must trigger the pre-registered whole-slot
  fallback and cannot be replaced only for the reference condition.
- The locked seed-1 legacy slot persistently failed at candidate 2 because
  `START35_APP6` was not waypoint-IK reachable. The locked seed-5 Block-0
  reference persistently failed at candidate 2 under the final cube-height
  criterion. Both canonical slots therefore used the pre-registered
  whole-five-condition fallback while retaining actual source seeds `1/1`
  and `1701/2701`, respectively.
- The active primary matrix consequently contains 21 new and four reused
  dataset slots, 630 new successful demonstrations, and 25 new policies.
  This is the protocol-preserving fallback expansion of the original
  16/9-dataset and 20/5-policy plan, not a change to the 25-slot matrix.
- Seeds 2 and 3 reject a candidate for the full five-condition slot when any
  condition fails, then advance all conditions to the next deterministic
  candidate.

## HDF5 and training

- Each new HDF5 retains two-episode-per-demo augmentation and the exact legacy
  S25 `54/6` train/valid episode-name masks.
- New HDF5 files record `sample_hz=8`, `action_gap=2`, augmentation and split
  provenance as root attributes.
- Exactly 25 active training configs were generated after all 25 dataset
  slots validated; the original count of 20 increased only because both
  whole-slot fallbacks removed all five originally reusable policies.
- Configs use `max_epochs=3000`, repository patience 41, checkpoints every 20
  epochs, W&B project `TRO_MVP`, no training rollouts and no rollout-based
  checkpoint selection.
- Run names include `stage2`, canonical seed, actual source training seed and
  condition.
- Parallel HDF5 jobs exposed a manifest-only lost-update race. All HDF5 bytes
  had already passed their per-seed validator; the ledger was repaired by
  sequentially revalidating all five seeds and a second independent 25-slot
  hash audit. No HDF5 was rebuilt or modified during the repair.

## Evaluation and analysis

- Ten rollout manifests use formal rollout seeds `1..5`; each seed has 25
  inner and 25 outer states with explicit runtime and point-cloud RNG seeds.
- The 250-task mapping is canonical seed × condition × rollout seed × bank.
- Strict analysis requires 250/250 tasks, 6,250/6,250 rows, exact state order,
  runtime RNG, point-cloud RNG and checkpoint hashes.
- Canonical dataset-policy seed is the top-level analysis and bootstrap unit.
  Rollout seeds are nested deployment trials.
- All 25 training jobs completed with exit `0:0`. Selected checkpoint epochs,
  in condition order, were:
  `seed1=[180,40,60,40,40]`, `seed2=[60,40,40,40,40]`,
  `seed3=[80,40,40,40,80]`, `seed4=[40,40,40,40,40]`, and
  `seed5=[60,40,60,60,60]`.
- Formal rollout produced 247 clean completions in the original array and
  three infrastructure `PREEMPTED` tasks. Only those three task indices were
  rerun with identical frozen inputs. Their partial rows and logs are
  preserved under `dataset/tro_position_stage2_axial/infrastructure_retries/`
  and excluded from formal merge.
- Strict validation passed 250/250 final tasks and 6,250/6,250 rows. The
  pre-registered classification is `partial`: candidate-minus-wide passed
  (`mean=+0.2088`, 4/5 positive), while candidate-minus-reference did not
  (`mean=-0.0400`, 2/5 positive).

## Test environment

The existing PyBullet `arcap` environment initially lacked pytest, while the
available `libero` pytest environment lacked PyBullet. Pytest 8.3.5 was added
to `arcap`; the Stage 1, Stage 1b and Stage 2 test set then passed in the same
environment used by collection and evaluation.
