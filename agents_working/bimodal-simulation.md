# Agent Work: Bimodal Simulation Pipeline

_Experiment label: `simulation_bimodal_group` · Status: COMPLETE_

## Current Execution

- Updated: `2026-08-07T23:41:42+01:00`
- Active stage: `Final analysis and validation — COMPLETE`
- Formal design seed: `20260807`
- Runtime: `/scratch/users/k23114984/conda/arcap/bin/python`
- Bimodal helper root: `examples/rebuttal_bimodal_pipeline/`
- Bimodal data root: `rebuttal_dataset/simulation_bimodal_group/`
- Local worker PID: none
- Bimodal Slurm jobs: training array `36372359` and rollout array `36373143`,
  each `1-10%2`, submitted once, both 10/10 `COMPLETED 0:0`
- Final read-only Control snapshot: array `36371239`, 10/10 `COMPLETED 0:0`;
  no Bimodal executor action was taken on it

## Ownership and Isolation

This executor may create or modify only:

- `examples/rebuttal_bimodal_pipeline/`
- `rebuttal_dataset/simulation_bimodal_group/`
- `agents_working/bimodal-simulation.md`
- `tests/test_rebuttal_bimodal_pipeline.py`

Target, Control, shared simulator/evaluator code, coordination files, and both
handoffs are read-only. In particular, never modify, cancel, adopt, duplicate,
hold, release, requeue, or otherwise act on Control array `36371239` or any
other Target/Control job.

## Frozen Inputs

- Target raw root:
  `rebuttal_dataset/simulation_target_group/full_seed20260806/protocol_release_z008_target_tol010_start_replenish/`
- Target HDF5 validation SHA-256:
  `44ad0c763badba8e41d56d1093989629fb88186ada225bbb267d35a87df20099`
- Target training manifest SHA-256:
  `610caef20d78f441df533aa2b1951029006cdf7b1d5aabf37c8bb1fdde8a5623`
- Target selected-checkpoint manifest SHA-256:
  `a06b1784234ef4f6e07f23b16fc82781e95c29a83553474b8bccf15ba870ea93`
- Paired rollout spec SHA-256:
  `10dbbe16da06b4013899e350fece05687abc8c45471b584ac5a2473a0e486dad`

All four hashes were rechecked before the first Bimodal write.

## Frozen Pairing Design

| Participant | Left source | Right source |
|---|---|---|
| B01 | T01 | T07 |
| B02 | T03 | T06 |
| B03 | T03 | T07 |
| B04 | T03 | T10 |
| B05 | T05 | T10 |
| B06 | T05 | T09 |
| B07 | T03 | T09 |
| B08 | T04 | T06 |
| B09 | T02 | T10 |
| B10 | T04 | T08 |

The table is the exact no-replacement stdlib draw from the 25 left-major
candidates using `random.Random(20260807).sample(candidates, 10)`. Do not
redraw or rebalance it.

## Stage Ledger

| Stage | Status | Evidence |
|---|---|---|
| Startup and isolation audit | COMPLETE | Required coordination/Target/Control files read; Bimodal paths and jobs absent; four frozen hashes match; Control queried read-only |
| Pairing manifest | COMPLETE | `pairing_manifest.json`, SHA-256 `a6a5198ca147744e5e82d030ed145e50a8e70296e6e40f341f6a97024766fadb`; exact frozen stdlib draw |
| 10 shuffled 60-demo symlink views | COMPLETE | `mixed_raw/B01`–`B10`; 1,200 relative symlinks; exact per-B deterministic shuffle replay |
| Mixed-view validation | COMPLETE | `mixed_raw_validation_report.json`: `passed=true`, 10 participants, 600 memberships, zero errors |
| 10 standalone HDF5 datasets | COMPLETE | Attempt 2 atomically published 10×60 physical trajectory groups after per-file closed-candidate source-equality readback; failed attempt 1 preserved under `diagnostics/` |
| HDF5 validation and 20 loader smokes | COMPLETE | `hdf5/validation_report.json`, SHA-256 `9674e71e7904a370e71a73ec3231af6a4bcf09437179b446b31f6d7e0a4b0047`: 10 files, 600 memberships, 300 underlying unique trajectories, 20 loader smokes, zero errors |
| 10 uniform DP configs | COMPLETE | `models/training_experiment_manifest.json`, SHA-256 `76da91cbfb5089acc75e218d751ee55773adde3b4569ab8b609e252f6158f3fd`; Target-matched normalized protocol SHA-256 `6c309f43...77d` |
| 10 trained policies | COMPLETE | Slurm array `36372359`: 10/10 `COMPLETED 0:0`; all postchecks passed, exact epoch 40, finite logs, zero stderr, zero retries |
| Model validation | COMPLETE | `model_validation_report.json` SHA-256 `5490809c...e06ca1`, passed 10/10; selected-checkpoint manifest SHA-256 `e05318eb...d544b`; all CPU load/inference smokes finite |
| 200 stochastic rollouts | COMPLETE | Array `36373143`: 10/10 `COMPLETED 0:0`; exactly 200 unique results/seeds, 200 nonempty unique videos, execution index zero, zero retries/infrastructure failures |
| Final analysis and validation | COMPLETE | `analysis/validation_report.json` SHA-256 `4c30d414...bdf2`: passed, zero errors; 9 final artifacts, 200/200 independently rechecked results and videos |

## Active Safety Gates

1. Creators refuse to overwrite formal outputs and use temporary artifacts
   followed by atomic rename where appropriate.
2. Validators re-open payloads and do not trust creator summaries.
3. Every `sbatch` requires exact scheduler/job/path/output duplicate audit.
4. GPU arrays use at most `%2` and exclude `erc-hpc-comp223`.
5. Scientific failures are never replaced; only proven pre-result
   infrastructure failures may resume the identical frozen work item.
6. Completion requires final validation of ten policies, 200 unique outcomes,
   200 videos, route statistics, success statistics, and no Target/Control
   writes.

## Activity Log

- `2026-08-07T17:50:34+01:00`: Started the isolated Bimodal Long Goal. Read
  the handoff/coordination contract and both full group ledgers, confirmed the
  branch `hpc-headless-rebuttal` at `72ca390`, preserved the pre-existing dirty
  worktree, verified all reserved Bimodal paths and Bimodal jobs were absent,
  matched all four frozen Target hashes, and confirmed ample filesystem space.
  Read-only scheduler audit found Control array `36371239` still active; no
  Control or Target state was changed.
- `2026-08-07T17:56:40+01:00`: Froze `pairing_manifest.json` at SHA-256
  `a6a5198c...6fadb`; it reproduces the authorised ten-pair draw and records
  source HDF5/raw-result/raw-metadata hashes and multiplicities. Created
  `mixed_raw/B01`–`B10` atomically with 1,200 relative symlinks. Independent
  validation replayed every shuffle and proved exactly 30L+30R, all 60 unique
  selected-source demos, successful Target metadata, in-root relative links,
  stable hashes, no partial roots, and zero errors. No Target/Control write or
  Slurm action occurred.
- `2026-08-07T18:33:10+01:00`: HDF5 attempt 1 independently failed before
  training because only B10/demo_10 observations drifted after construction:
  arm/hand observations were all zero, one point-cloud scalar differed, and
  the file hash no longer matched its sidecar; the frozen T08 source still
  matched. Preserved the complete failed root and report under
  `diagnostics/hdf5_attempt_1_failed/` and recorded the recovery decision.
  Attempt 2 added closed-file per-dataset source equality before publication,
  then independently passed 10 files, 600 memberships, 300 underlying unique
  trajectories, exact 30/30 modes, 54/6 stratified masks, 20/20 real loaders,
  and zero errors. Froze ten DP configs at 40×250 steps, batch 16, seed 1,
  exact epoch-40 selection; normalized scientific config is identical to the
  frozen Target reference. Pre-submit audit found no Bimodal job or output.
- `2026-08-07T18:33:24+01:00`: Submitted the unique formal training array
  `36372359` as `1-10%2` on `interruptible_gpu`, job name
  `simulation_bimodal_group_train`, excluding `erc-hpc-comp223`. No Control or
  Target job was active or modified at submission.
- `2026-08-07T19:11:20+01:00`: Training milestone 3/10. B01–B03 each
  completed 40/40 epochs with Slurm `COMPLETED 0:0`, passed wrapper postchecks,
  selected exact `model_epoch_40.pth`, and produced zero-byte stderr. B04
  started automatically. No infrastructure retry, tuning, checkpoint
  reselection, duplicate submission, or cross-group action occurred.
- `2026-08-07T19:21:44+01:00`: Training milestone 4/10. B04 completed in
  11:00 with Slurm `COMPLETED 0:0`, passed its postcheck with no errors,
  selected exact epoch-40 checkpoint SHA-256 `5b599776...98c86d`, and produced
  zero-byte stderr. B05 started automatically on `erc-hpc-comp241`; there has
  been no retry, resubmission, or protocol change.
- `2026-08-07T19:33:07+01:00`: Training milestone 5/10. B05 completed in
  11:22 with Slurm `COMPLETED 0:0`, exact epoch-40 checkpoint SHA-256
  `80ea87e7...b724fa`, a passing postcheck, empty errors, and zero-byte stderr.
  B06 continues on `erc-hpc-comp231`; the scheduler briefly used both allowed
  `%2` slots without any executor-side concurrency or budget change.
- `2026-08-07T19:45:05+01:00`: Training milestone 6/10. B07 completed in
  11:46 with Slurm `COMPLETED 0:0`, passed its postcheck with no errors,
  selected exact epoch-40 checkpoint SHA-256 `30a0e9f7...94e383d`, and produced
  zero-byte stderr. B06 remains healthy on the slower `erc-hpc-comp231`; B08
  is awaiting the scheduler's array-slot release.
- `2026-08-07T19:59:25+01:00`: Training milestone 7/10. B08 completed in
  13:36 with Slurm `COMPLETED 0:0`, exact epoch-40 checkpoint SHA-256
  `775f1a38...31486a`, passing postcheck, empty errors, and zero-byte stderr.
  B09 started automatically on `erc-hpc-comp241`, while B06 continued unchanged
  on `erc-hpc-comp231`.
- `2026-08-07T20:01:37+01:00`: Training milestone 8/10. B06 completed on the
  slower node in 32:00 with Slurm `COMPLETED 0:0`, exact epoch-40 checkpoint
  SHA-256 `d1991df6...f8d900`, passing postcheck, empty errors, and zero-byte
  stderr. The longer wall time was observed without retry or budget change.
- `2026-08-07T20:11:45+01:00`: Training milestone 9/10. B09 completed in
  11:57 with Slurm `COMPLETED 0:0`, exact epoch-40 checkpoint SHA-256
  `a3f38bd3...f8fb51f`, passing postcheck, empty errors, and zero-byte stderr.
  B10 is the only remaining training task and continues on
  `erc-hpc-comp231`.
- `2026-08-07T20:31:31+01:00`: Training milestone 10/10. B10 completed in
  29:30 with Slurm `COMPLETED 0:0`, exact epoch-40 checkpoint SHA-256
  `991ed7e0...34c154`, passing postcheck, empty errors, and zero-byte stderr.
  Full array audit proved ten terminal `COMPLETED 0:0` tasks, ten exact
  epoch-40 checkpoints, finite logs, no retries, and no stderr content.
- `2026-08-07T20:36:55+01:00`: Model validation passed 10/10 after re-hashing
  every participant config, 13 GB of source HDF5, and every selected epoch-40
  checkpoint, then loading each policy with the real loader and obtaining a
  finite eight-dimensional CPU inference action. Froze
  `model_validation_report.json` (`5490809c...e06ca1`) and
  `selected_checkpoints_manifest.json` (`e05318eb...d544b`). All eight focused
  tests passed; the four frozen Target hashes still matched. Pre-rollout audit
  found the Bimodal rollout root absent and no current or historical duplicate
  Bimodal rollout job.
- `2026-08-07T20:38:18+01:00`: Created only the empty Bimodal-owned rollout
  `logs/` directory, repeated the duplicate/output audit, and submitted the
  unique formal rollout array `36373143` as `1-10%2` on `interruptible_gpu`,
  job name `simulation_bimodal_group_rollout`, excluding
  `erc-hpc-comp223`. Wrapper SHA-256 is `b643e48a...a7f4d1`; evaluator SHA-256
  is `029113bd...a011d`. The exact frozen Target spec hash is consumed
  read-only; no Target or Control job/path was modified.
- `2026-08-07T21:01:33+01:00`: Rollout milestone 20/200. B01 completed in
  23:19 with Slurm `COMPLETED 0:0`, exactly 20 unique case/repeat keys, 20
  unique policy seeds, 20 nonempty unique videos, execution index zero, and no
  infrastructure record. Its observed summary is L=4, R=10,
  indeterminate=6, successes=6/20 (L successes 1, R successes 5); all
  scientific failures were retained. B02 started automatically.
- `2026-08-07T21:18:48+01:00`: Rollout milestone 40/200. B02 completed in
  17:15 with Slurm `COMPLETED 0:0`, exact 20-key/seed/video coverage,
  execution index zero, and no infrastructure record. Its observed summary is
  L=2, R=15, indeterminate=3, successes=11/20 (all 11 realised as R).
  B03 started automatically; no outcome was replaced.
- `2026-08-07T21:36:15+01:00`: Rollout milestone 60/200. B03 completed in
  17:26 with Slurm `COMPLETED 0:0`, exact 20-key/seed/video coverage,
  execution index zero, and no infrastructure record. Its observed summary is
  L=1, R=15, indeterminate=4, successes=11/20 (all 11 realised as R). B04
  started automatically; every scientific failure remains final.
- `2026-08-07T22:01:40+01:00`: Rollout milestone 80/200. B04 completed in
  24:59 with Slurm `COMPLETED 0:0`, exact 20-key/seed/video coverage,
  execution index zero, and no infrastructure record. Its observed summary is
  L=1, R=15, indeterminate=4, successes=5/20 (all five realised as R). B05
  started automatically with all prior outcomes preserved.
- `2026-08-07T22:25:07+01:00`: Rollout milestone 100/200. B05 completed in
  22:57 with Slurm `COMPLETED 0:0`, exact 20-key/seed/video coverage,
  execution index zero, and no infrastructure record. Its observed summary is
  L=7, R=9, indeterminate=4, successes=6/20 (L successes 2, R successes 4).
  B06 started automatically; the experiment reached half of its 200 frozen
  outcomes with no replacement or retry.
- `2026-08-07T22:49:49+01:00`: Completed-participant milestone 120/200. B06
  completed in 24:38 with Slurm `COMPLETED 0:0`, exact 20-key/seed/video
  coverage, execution index zero, and no infrastructure record. Its observed
  summary is L=4, R=11, indeterminate=5, successes=4/20 (L successes 2, R
  successes 2). B07 had reached 14/20 and B08 started in the newly released
  second slot; total sealed results were 134/200 with no replacement.
- `2026-08-07T22:54:28+01:00`: Completed-participant milestone 140/200. B07
  completed in 21:37 with Slurm `COMPLETED 0:0`, exact 20-key/seed/video
  coverage, execution index zero, and no infrastructure record. Its observed
  summary is L=8, R=7, indeterminate=5, successes=7/20 (L successes 6, R
  successes 1). B08 continued and B09 started; total sealed results were
  143/200 with no replacement.
- `2026-08-07T23:10:25+01:00`: Completed-participant milestone 160/200. B09
  completed in 15:58 with Slurm `COMPLETED 0:0`, exact 20-key/seed/video
  coverage, execution index zero, and no infrastructure record. Its observed
  summary is L=5, R=11, indeterminate=4, successes=11/20 (L successes 4, R
  successes 7). B08 continued and B10 started; total sealed results were
  177/200 with no replacement.
- `2026-08-07T23:14:25+01:00`: Completed-participant milestone 180/200. B08
  completed in 24:30 with Slurm `COMPLETED 0:0`, exact 20-key/seed/video
  coverage, execution index zero, and no infrastructure record. Its observed
  summary is L=5, R=13, indeterminate=2, successes=6/20 (L successes 2, R
  successes 4). B10 was the only remaining participant at 2/20; total sealed
  results were 182/200 with no replacement.
- `2026-08-07T23:32:05+01:00`: Rollout milestone 200/200. B10 completed in
  21:18 with Slurm `COMPLETED 0:0`, exact 20-key/seed/video coverage,
  execution index zero, and no infrastructure record. Its observed summary is
  L=7, R=9, indeterminate=4, successes=6/20 (L successes 3, R successes 3).
  Full raw-output audit proved 200 unique participant/case/repeat keys, 200
  unique policy seeds, 200 nonempty unique videos, ten summaries, ten terminal
  `COMPLETED 0:0` tasks, valid scientific results throughout, and zero retries
  or infrastructure records.
- `2026-08-07T23:41:42+01:00`: Final analysis passed closed and atomically
  published exactly nine formal artifacts under `analysis/`. A deliberately
  strict first analysis attempt wrote nothing because 19/100 paired repeats
  were not bitwise-identical after the scripted grasp. Numeric diagnosis
  proved all frozen task/setup fields were exact and bounded the PyBullet
  contact-solver variation to 0.761 micrometres translation and 0.004951
  degrees box orientation (EE translation at most 1.16e-10 m). The final
  validator therefore records and enforces explicit 10 micrometre / 0.01
  degree physical-equivalence limits rather than claiming bitwise equality;
  no rollout was rerun or replaced. Independent raw-file reanalysis matched
  all 200 recorded route and success labels: pooled L=44, R=115,
  indeterminate=41, with 20/44, 53/115, and 0/41 successes respectively;
  total success was 73/200=0.365 and participant-policy mean +/- sample SD was
  0.365 +/- 0.133437. `validation_report.json` is SHA-256
  `4c30d414...bdf2`, all planned artifact hashes match, the plot was visually
  inspected, all nine focused tests pass, all four frozen Target hashes still
  match, and the completed Control array was queried read-only.
