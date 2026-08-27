# Handoff: CoRL Rebuttal Simulation Target and Control Groups

_Last updated: 2026-08-07 · Branch: `hpc-headless-rebuttal` @ `72ca390`_

## Goal

Complete the auditable `simulation_target_group` and `simulation_control_group` pipelines for obstacle-constrained manipulation. Each group has ten participant-level datasets with 30 successful demonstrations, ten identically configured policies, and 100 rollouts on the same ten paired evaluation starts. The only intended teaching-data difference is Target's contracting participant-specific waypoint distribution versus Control's independent full-support waypoint sampling.

## Current Progress

### Target — complete; do not rerun

- Live ledger: `agents_working/target-simulation.md`; every Stage A–F row is `COMPLETE`.
- Formal raw root: `rebuttal_dataset/simulation_target_group/full_seed20260806/protocol_release_z008_target_tol010_start_replenish/`.
- Raw validation passed at SHA-256 `21d90c09c7c4c6e40ad3702b804455e3f3b8a27315f565198f58c5da3435b49f`: T01–T10 each have exactly 30 successful demonstrations, 300 total, from 333 retained attempts. Successful raw contains 27,060 frames and zero `scripted_*` frames.
- HDF5 validation passed at `rebuttal_dataset/simulation_target_group/hdf5/validation_report.json`, SHA-256 `44ad0c763badba8e41d56d1093989629fb88186ada225bbb267d35a87df20099`: ten files, 30 trajectories each, 300 total, and 20 real loader smokes.
- Training manifest: `rebuttal_dataset/simulation_target_group/models/training_experiment_manifest.json`, SHA-256 `610caef20d78f441df533aa2b1951029006cdf7b1d5aabf37c8bb1fdde8a5623`. Uniform protocol SHA-256 is `db0aca893cf5554b01b13c8937af49cc83d9a1024f4038007d4182f21df1b0c6`: diffusion policy, seed 1, batch 16, 40 epochs × 250 steps, exact epoch-40 selection without rollout-based checkpoint choice.
- Model validation passed for 10/10 loadable checkpoints at SHA-256 `6fa37fd86466df179a18423f81d298a4741b15043bbb028cffe9db74ef88b890`. Selected checkpoint manifest SHA-256 is `a06b1784234ef4f6e07f23b16fc82781e95c29a83553474b8bccf15ba870ea93`.
- Shared paired rollout contract: `rebuttal_dataset/simulation_target_group/analysis/paired_rollout_specs.json`, evaluation seed `20260807`, file SHA-256 `10dbbe16da06b4013899e350fece05687abc8c45471b584ac5a2473a0e486dad`. It contains ten accepted setup-feasible starts and one preserved rejected candidate.
- Target rollouts are complete: 100 unique `(participant, eval_case_id)` results, 100 videos, no infrastructure rerun, and no scripted transport. Slurm array `36360382` completed 10/10 with exit `0:0`.
- T01–T10 EDSRs are `[0.5, 0.5, 0.3, 0.1, 0.2, 0.5, 0.3, 0.7, 0.4, 0.4]`. Overall is `0.390000 ± 0.172884`, L is `0.320000 ± 0.178885`, and R is `0.460000 ± 0.151658`; all standard deviations are participant-level sample SD with `ddof=1`. Raw rollout success is 39/100.
- Final results: `rebuttal_dataset/simulation_target_group/analysis/final_results.json`, SHA-256 `23b6ca460dc15e31538e6fbdc61d6fa0482983a9e1de4cba1ac48c6681222d0d`. Final validation passed at SHA-256 `dd30c106243ecc8d9b7efaa6f0719b865e981e4cb6e0fe4e8ab71ef8362a26e5`.

### Frozen success and execution contract

- Both the completed Target pipeline and the newly authorised Control R2 pipeline use: `target_xy_error<=0.10 and box_settled and cylinder_tilt<=10deg`.
- Fixed release EE z is `0.08 m`; contacts are diagnostic only.
- Scripted execution before inference is limited to common approach/grasp/close/lift and transport-height validation. Frame 0 is `phase=policy_inference_start`, `time=0`, gripper closed. Policy performs obstacle avoidance, transport, and release.
- Initial EE is exactly `[box_x, box_y, box_z+0.10]` with zero horizontal offset. Setup failures save zero frames.
- The Target final manifest truthfully says Control still used 0.03 m at the time Target finished. A later user authorisation on 2026-08-07 superseded that state for the new Control R2 collection. Do not rewrite immutable Target artifacts; record the later Control alignment in Control artifacts and the final comparison.

### Control R2 — active collection

- Authoritative ledger: `agents_working/control-simulation.md`. It is the source of truth after this handoff snapshot.
- The user explicitly authorised the complete Control pipeline on 2026-08-07, including collection, HDF5 conversion, ten-policy training, 100 paired rollouts, EDSR analysis, and use of the same 0.10 m/10° success criterion as Target.
- Formal immutable R2 root: `rebuttal_dataset/simulation_control_group/full_seed20260806/protocol_release_z008_target_tol010_start_replenish/`.
- Configuration validation passed, SHA-256 `ab0d8a91ea5594c459f54a93269fb9995c64f38a7e4d6ddc252c6e97df550ac2`; policy-blind IK preflight accepted 300/300 within attempt 3, SHA-256 `195dbf0caa635350b160c2300d3fae69812ea8df5d218db10ff04099952154de`.
- Active Slurm array is `36371239`, tasks `1-10%3`, job name `simulation_control_group_collect_r2`. Snapshot at `2026-08-07T17:02:50+01:00`: C01–C03 were running on `erc-hpc-comp206`, C04–C10 pending under the array limit, with 8/9/8 successful demos already committed. This is only a snapshot; query Slurm and the ledger immediately on resume.
- Logs: `rebuttal_dataset/simulation_control_group/full_seed20260806/protocol_release_z008_target_tol010_start_replenish/logs/collect_36371239_<task>.{out,err}`.
- Control's sole intended teaching manipulation is independent full-support waypoint sampling on every attempt: L x `[0.10,0.30]`, R x `[0.70,0.90]`, y `0.25`, z `[0.19,0.29]`; no personal centre and no contraction. Cube-start distribution, retry replenishment, physical task, learner, checkpoint rule, and paired evaluation contract must match Target.
- The historical Control root and array `36353493` are failed-protocol evidence only. The old array was cancelled after explicit user authorisation; never mix it with R2.

## What Worked

- Target-only protocol isolation allowed the user-authorised 0.10 m criterion without mutating the already-running historical Control experiment. Control R2 now implements the same semantics in Control-owned code after later explicit authorisation.
- `RELEASE_Z=0.08`, the exact vertical EE start, incremental Cartesian transport, and deterministic attempt-seeded start replenishment produced the validated Target 300-demo dataset.
- Conservative concurrency (`%3` for collection, `%2` for GPU training/rollout) avoided the renderer/resource failure seen with ten simultaneous processes.
- Per-participant HDF5 files, one frozen training protocol hash, exact epoch-40 checkpoint selection, and one shared paired start manifest kept the pipeline auditable.
- Preserving scientific failures and infrastructure failures separately prevented failed rollout replacement and performance-based checkpoint selection.

## What Didn't Work

- Earlier Target formal revision roots before `protocol_release_z008_target_tol010_start_replenish/` are diagnostic or failed-protocol artifacts. Do not merge, overwrite, delete, or train from them.
- The original Control array `36353493` failed at the 3 cm/high-drop protocol and is not R2 data. The many dual-offset/release-z004 Control diagnostics are explicitly non-formal and must never enter HDF5.
- Reusing an infeasible attempt-0 cube start for all retries caused deterministic setup exhaustion. R2 must keep the Target attempt-seeded broad-distribution replenishment rule.
- Target training T04–T06 hit uncorrectable ECC on `erc-hpc-comp223`, and a first retry stopped at zero steps on an upstream existing-output prompt. The successful exact-config retry answered `n` to preserve old runs. GPU wrappers exclude `erc-hpc-comp223`; keep that exclusion.
- Ten simultaneous renderers exceeded local resources. Do not raise Control collection concurrency above the conservative configured value without evidence.
- Slurm submission is not completion. Every job must be monitored to terminal state and audited for exit code, stderr, OOM/TIMEOUT/CANCELLED, exact artifact counts, and partial files.

## Key Files & Commands

- Coordination contract: `agents_working/README.md`.
- Target ledger: `agents_working/target-simulation.md`; Target is complete and read-only to Control.
- Control ledger: `agents_working/control-simulation.md`.
- Control launch prompt: `agents_working/control-agent-prompt.md`.
- Target final analysis root: `rebuttal_dataset/simulation_target_group/analysis/`.
- Control R2 collector: `examples/rebuttal_control_pipeline/collect_control_aligned.py`.
- Control R2 wrapper: `examples/rebuttal_control_pipeline/collect_control_aligned_array.sbatch`, SHA-256 `5410167eb5463221cb43272045de3667e018dde400182325b3bddaab158bc648`.
- Control R2 protocol: `examples/rebuttal_control_pipeline/control_protocol.py`, SHA-256 `ff70588ad343c8a2b36bc2105b206cc7261924f223ea1e7d4be2cba4e4f3be3b`.
- Control raw validator: `examples/rebuttal_control_pipeline/validate_control_aligned_raw.py`.
- Control downstream helpers: `convert_control_hdf5.py`, `validate_control_hdf5.py`, `prepare_control_training.py`, `train_control_array.sbatch`, `validate_control_models.py`, `evaluate_control_policy.py`, and `evaluate_control_array.sbatch` under `examples/rebuttal_control_pipeline/`.
- Read-only shared rollout spec: `rebuttal_dataset/simulation_target_group/analysis/paired_rollout_specs.json`; Control must consume this exact file and hash.

Monitor the active Control collection:

```bash
squeue -j 36371239 -o '%.18i %.30j %.2t %.10M %.10l %R'
sacct -j 36371239 --format=JobIDRaw,State,ExitCode,Elapsed,NodeList -n -P
tail -n 80 rebuttal_dataset/simulation_control_group/full_seed20260806/protocol_release_z008_target_tol010_start_replenish/logs/collect_36371239_1.{out,err}
```

Validate R2 raw after all ten tasks finish:

```bash
/scratch/users/k23114984/conda/arcap/bin/python \
  examples/rebuttal_control_pipeline/validate_control_aligned_raw.py \
  --root rebuttal_dataset/simulation_control_group/full_seed20260806/protocol_release_z008_target_tol010_start_replenish
```

Downstream wrappers already exclude the known bad GPU node:

```bash
sbatch examples/rebuttal_control_pipeline/train_control_array.sbatch
sbatch examples/rebuttal_control_pipeline/evaluate_control_array.sbatch
```

Do not submit either wrapper until its upstream validation gate passes, output roots are confirmed absent, configs/manifests are frozen, and the Control ledger is updated.

## Next Steps

1. On resume, read `agents_working/README.md`, this handoff, `agents_working/control-agent-prompt.md`, and the full current `agents_working/control-simulation.md` before acting.
2. Adopt and continuously monitor Slurm array `36371239`; do not submit a duplicate. Inspect every element's `squeue`/`sacct` state, exit code, stderr, artifacts, and partial files until all ten are terminal.
3. Validate exactly C01–C10 × 30 successful post-grasp demonstrations (300 total), the shared success criterion, zero scripted frames, failed-attempt exclusion, exact broad start/replenishment metadata, and no stale/partial artifacts. Update the Control ledger immediately.
4. Convert into ten participant-level Control HDF5 files with exactly 30 trajectories each. Re-read all files, run loader smokes, validate hashes/provenance/schema, and keep participants separate.
5. Freeze a Control training manifest matching Target's learner, seed, batch size, 40×250-step budget, optimizer/config, and exact epoch-40 selection rule. Train C01–C10 with no per-participant tuning and validate 10/10 checkpoint loads/inference.
6. Run every Control policy on the exact read-only Target paired manifest hash `10dbbe16...86dad`, ten cases per policy, for 100 unique outcomes. Preserve scientific failures; only reviewed pre-result infrastructure failures may be deterministically resumed.
7. Produce Control `final_results.json`, participant EDSR CSV, rollout CSV, validation report, experiment manifest, plot, video index, and factual summary. If no Control-owned analysis helper exists yet, create it under `examples/rebuttal_control_pipeline/` by adapting the validated Target logic without modifying Target.
8. Only after both final validations pass, compute the Target–Control comparison using participant-level policy as the inferential unit. Do not treat 100 rollout outcomes as 100 independent participants.

## Open Questions

- Control R2 scientific completion and downstream success rate are unknown until array `36371239` and all later stages finish.
- Confirm or implement the final Control-owned analysis helper before Stage F; none was present in the helper file listing at this handoff snapshot.

## Changelog

- 2026-08-06: Added the fresh Control Long Goal launch prompt with strict Target isolation and an initial duplicate-submission audit.
- 2026-08-06: User authorised the Control spatial protocol. Added ten broad, non-converging Control participants with automatic validity/success replenishment, exact Target start parity, validated 10/10 smoke, and formal collection tooling.
- 2026-08-06: Made this the sole active handoff and froze all prior DEMT AR-guidance handoffs under `archive/handoffs-frozen-2026-08-06/` with a compact historical index.
- 2026-08-06: Added the strict post-grasp collection boundary, vertical-only EE initialisation, Cartesian transport, ten synthetic Target participants, the authoritative `smoke_d01_v4`, isolated ownership, and the ten-policies-by-ten-paired-starts contract.
- 2026-08-07: Updated the handoff after Target completed 300 raw demos, ten HDF5 files, ten policies, 100 paired rollouts, and final EDSR analysis; recorded the later user-authorised aligned Control R2 pipeline and active collection array `36371239`.
