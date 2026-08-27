# Agent Work: Control Simulation Pipeline

_Experiment label: `simulation_control_group` · Status: COMPLETE_

## Current Execution

- Updated: `2026-08-08T01:36:11+01:00`
- Active stage: `COMPLETE — 300 demos, HDF5, 10 policies, 100 paired rollouts,
  and Target–Control analysis independently validated`
- Formal seed: `20260806`
- New immutable formal output: `rebuttal_dataset/simulation_control_group/full_seed20260806/protocol_release_z008_target_tol010_start_replenish/`
- Fresh-agent launch prompt: `agents_working/control-agent-prompt.md`
- Agent PID: unavailable in the managed Codex runtime; no local collector process launched
- Historical Slurm array: `36353493`; C01–C03 failed and the remaining held
  tasks were cancelled after explicit user authorisation and exact ownership proof
- Prepared R2 wrapper: `examples/rebuttal_control_pipeline/collect_control_aligned_array.sbatch`
  (`simulation_control_group_collect_r2`)
- Completed R2 Slurm array: `36371239` (`1-10%3`, submitted exactly once;
  10/10 tasks `COMPLETED 0:0`)
- Completed training Slurm array: `36372730` (`1-10%2`, submitted exactly once;
  10/10 tasks `COMPLETED 0:0`; known bad node `erc-hpc-comp223` excluded)
- Completed rollout Slurm array: `36376643` (`1-10%2`, submitted exactly once;
  10/10 tasks `COMPLETED 0:0`; 100/100 valid paired results, no retry)
- Final validation: `analysis/validation_report.json`, passed with zero errors,
  SHA-256 `6287daf48d3c42f03649321104fefb527191c99baef296b508c370089df9e97f`
- Live task policy: gate each downstream stage on independent validation; do
  not replace scientific failures and do not touch Target
- Scheduler lookup: `squeue -u k23114984`, `sacct` for 2026-08-06
- Future R2 job name: `simulation_control_group_collect_r2`
- Future R2 logs: `rebuttal_dataset/simulation_control_group/full_seed20260806/protocol_release_z008_target_tol010_start_replenish/logs/collect_<job>_<task>.{out,err}`

## Ownership and Boundaries

This file and the following future paths belong to the Control agent:

- `examples/main_obstacle_transport_control_participants.py`
- `rebuttal_dataset/simulation_control_group/`
- the Control-specific HDF5, model, checkpoint and rollout roots recorded below
- `agents_working/reviews/control-reviews-target.md`

The Control agent must not modify Target scripts, datasets, checkpoints, summaries, status or review files.

## Authorised Control Protocol

The user authorised the Control spatial-distribution protocol on 2026-08-06:

- Participants: `C01`–`C10`; `C01`–`C05` use L and `C06`–`C10` use R.
- Retain exactly 30 successful post-grasp demonstrations per participant, 300
  total.
- For every demo and retry, independently sample the middle waypoint from the
  complete route support used by the Target group's widest envelope:
  - L x: `[0.10, 0.30] m`
  - R x: `[0.70, 0.90] m`
  - y: fixed at the obstacle plane, `0.25 m`
  - z: `[0.19, 0.29] m`
- No personal waypoint centre, no shrinking envelope, and no learning-order
  dependence. Every demonstration uses the full support.
- Reject and replenish IK-unreachable, invalid, target-miss, unsettled-box, or
  toppled-cylinder attempts until each participant has 30 accepted points.
- Use the same 30 broad cube starts as Target, paired by demo index.
- Keep rotation and timing frozen to the shared simulator. This is a
  position-consistency manipulation, avoiding a P/R/V confound until separate
  R/V protocols are explicitly specified.

Implementation:

- `examples/main_obstacle_transport_control_participants.py`
- `examples/rebuttal_control_pipeline/collect_control_array.sbatch`
- `examples/rebuttal_control_pipeline/validate_raw_collection.py`
- `tests/test_obstacle_transport_control_participants.py`
- `agents_working/control-agent-prompt.md` (coordinator-owned; Control reads only)

The protocol preview contains 30 unique attempt-0 waypoints per participant.
Across participants, x span is `0.177–0.199 m` and z span is `0.088–0.099 m`.
The 30 cube starts match Target exactly.

Smoke `rebuttal_dataset/simulation_control_group/smoke_d01_v1/` passed 10/10:
seven participants succeeded on attempt 0, C01 on attempt 1, and C09 on
attempt 2. All three rejected attempts were middle-waypoint IK failures and
were replenished correctly. Raw boundary checks, success thresholds, all ten
videos, and Control raw validator passed.

### Current Target-aligned revision authorised on 2026-08-07

The user superseded the earlier cross-group divergence and authorised Control
to use the physical and success semantics already frozen in Target SCR-001,
SCR-003 and SCR-004:

- fixed release EE z `0.08 m`;
- target XY success radius `0.10 m`;
- box-settled and cylinder-tilt `<=10 deg` success gates;
- box/robot cylinder contacts are diagnostics only;
- attempt 0 retains the authoritative broad cube start; every retry uses the
  same Target deterministic attempt-seeded broad LHS replenishment rule, so a
  `(demo_index, attempt_index)` candidate is common across participants;
- initial EE is exactly `[box_x, box_y, box_z+0.10]` with zero horizontal
  offset, and only validated shared scripted grasp/lift precedes frame 0;
- frame 0 remains `policy_inference_start`; no scripted setup frame is saved;
- the prior dual-offset/release-z004 diagnostic is not part of this formal
  protocol;
- the sole Control teaching-data manipulation remains independent uniform
  sampling over the full L/R waypoint x-z rectangle on every attempt.

Target's paired rollout manifest is frozen read-only at
`rebuttal_dataset/simulation_target_group/analysis/paired_rollout_specs.json`,
file SHA-256
`10dbbe16da06b4013899e350fece05687abc8c45471b584ac5a2473a0e486dad`.
Future Control rollout code must consume that file and hash directly and must
not generate replacement evaluation starts.

## Reserved Output Roots

- Raw/full pipeline root: `rebuttal_dataset/simulation_control_group/full_seed20260806/`
- HDF5 root: `rebuttal_dataset/simulation_control_group/hdf5/`
- Model root: `rebuttal_dataset/simulation_control_group/models/`
- Rollout root: `rebuttal_dataset/simulation_control_group/policy_rollouts/`
- Final analysis root: `rebuttal_dataset/simulation_control_group/analysis/`

Do not place Target artifacts in these directories.

## Stage Ledger

| Stage | Status | Evidence |
|---|---|---|
| User-defined Control protocol | COMPLETE | User instruction on 2026-08-06; frozen above |
| Control smoke | COMPLETE | `smoke_d01_v1/summary.json`, `validation_report.json`, 10 decoded videos |
| Historical full collection | FAILED (PRESERVED) | Array `36353493`: C01–C03 each exhausted 30/30 attempts at demo 2 (`FAILED 1:0`); C04–C10 remain held before start; `diagnostics/stage_a_failure_summary.json` |
| Target-aligned R2 configuration | COMPLETE | New immutable root prepared with no C01–C10 formal directories; `configuration_validation_report.json` passed, SHA-256 `ab0d8a91...`; policy-blind IK preflight accepted 300/300 within attempt 3, SHA-256 `195dbf0c...` |
| Target-aligned R2 full collection | COMPLETE | Array `36371239`: 10/10 tasks `COMPLETED 0:0`; raw validation passed with 300 demos/300 raw dirs, 387 attempts, 26,677 frames, zero successful scripted frames, errors or warnings; canonical report SHA-256 `bd36e47329a55957e688c40ac4c8d65385e0af62a62fcb025d0c228a24be33fc` |
| HDF5 conversion | COMPLETE | 10 participant HDF5 files/300 trajectories; full validator passed with 20 real loader smokes and zero errors, report SHA-256 `c617bed5ded688a1ecf7a949a401f3bfff16ed450e247aece23e4962c3eb5de5`; preserved and recovered one C03 infrastructure write-corruption event without changing raw/science configuration |
| Policy training | COMPLETE | Array `36372730`: 10/10 `COMPLETED 0:0`; exact epoch-40 checkpoints; real ten-model CPU inference validator passed with zero errors, report SHA-256 `c00c49cf164f9ba21a06efa284fa2f34070ae94a747f32bbf98644bd010641bf` |
| Paired rollouts | COMPLETE | Array `36376643`: 10/10 `COMPLETED 0:0`; 100 unique valid results and 100 nonempty videos using exact paired manifest SHA-256 `10dbbe16da06b4013899e350fece05687abc8c45471b584ac5a2473a0e486dad`; zero infra failures/retries |
| Target–Control comparison | COMPLETE | Final validation passed with zero errors at SHA-256 `6287daf48d3c42f03649321104fefb527191c99baef296b508c370089df9e97f`; Control EDSR `0.44 +/- 0.117379`, Target `0.39 +/- 0.172884`, participant-level descriptive difference `+0.05` |

## Shared-Change Requests

### SCR-C001 — Control dual-offset feasibility revision (CLOSED; NOT APPLIED FORMALLY)

- Resolution on 2026-08-07: the user instead authorised exact alignment with
  Target SCR-001/SCR-003/SCR-004 (`RELEASE_Z=0.08`, target radius `0.10 m`,
  Target deterministic start replenishment). The diagnostic dual-offset,
  Cartesian-setup and release-z004 candidate below remains historical
  non-formal evidence and is explicitly excluded from the new formal R2
  configuration.

- Read-only shared base: `examples/main_obstacle_transport.py`.
- Proposed formal implementation boundary (recommended): a Control-only
  protocol subclass/helper under `examples/rebuttal_control_pipeline/`, plus
  the Control-owned collector/wrapper/validator wiring required to use it.
  Applying the same behavior in the shared base is a separate alternative that
  would require explicit Target coordination and must not affect the active
  Target job implicitly.
- Proposed patch status: the original release-only proposal is superseded and
  must not be approved or used for a formal restart by itself. Exhaustive
  Control prevalidation proves release z=0.08 is insufficient on three frozen
  paired starts. The current bounded candidate is: precise initial IK;
  Cartesian scripted pre-grasp/grasp/lift for every start; the calibrated
  grasp offset `[+0.004, -0.008, +0.005] m` when frozen cube-start
  `x < 0.23 m`, the lower anti-retention offset
  `[+0.004, -0.016, -0.005] m` in the narrow
  `0.23 <= x < 0.25 m` boundary band, and the nominal grasp otherwise; and
  fixed release pose
  `[0.502, 0.498, 0.04] m`. It must be applied identically to Target and
  Control and remains non-formal. The final dual-offset candidate has passed
  exhaustive Control validation as described below, but is not authorised for
  formal data collection.
  Do not change
  waypoint/transport z, seed, cube starts, route support, deterministic retry
  sampling, fixed orientation/timing, tolerances, or success criteria.
- Reason: Control array `36353493` independently reproduces the Target
  SCR-001 failure at frozen paired demo index 2. C01–C03 each accepted demos 0
  and 1, then produced repeated preserved `target_miss` diagnostics at the
  common cube start despite independently resampled full-support waypoints.
  Read-only Target evidence reports the same terminal result across T01–T03
  (88 target misses among 90 demo-2 failures) and a 10/10 Target diagnostic at
  fixed release z=0.08 m.
- Control diagnostic evidence: a Control-only, explicitly non-formal
  `save=False` probe changed only each in-memory spec's release z. Frozen demo
  2 passed 10/10 on attempt 0 (maximum target error `0.0207039 m`, waypoint
  error `0.0152298 m`, cylinder tilt `5.89897 deg`, zero box-cylinder
  contacts). Frozen demo 0 also passed 10/10 while retaining the exact expected
  reachability replenishment pattern (C01 attempt 1, C09 attempt 2, all others
  attempt 0); maximum target error was `0.00407069 m`. Reports are
  `diagnostics/release_z008_demo2.json` (SHA-256
  `a90698df3dc5ebc64564783c9cdcbebce5a7f8913abc0631fa9461e2f0e15a2f`)
  and `diagnostics/release_z008_demo0.json` (SHA-256
  `584a7d31cfc8727e786784091d12d88b0ed151b97f6228e42efbf478d3dca9fc`).
- Exhaustive Control addendum: non-formal array `36354365` tested release
  z=0.08 for all 30 frozen starts and all ten participants. It produced
  `270/300` successful cases in `1,234` attempts; every participant failed the
  identical indices 17, 18 and 28. Index 17 retains terminal target misses;
  index 18 fails scripted setup as `unreachable_waypoint`; index 28 fails as
  `box_not_lifted`. The aggregate has zero validation errors, exact Target
  cube-start parity, and no raw/video/HDF5 payloads:
  `diagnostics/release_z008_all30/summary.json` (SHA-256
  `974ef9a4da48b2ac619b197a045b4d5f4cd2efea1a4fe7fe3495ce9f55c14101`).
- Low-x setup evidence: non-formal job `36355676` completed `0:0` and proves
  the exact initial EE targets for indices 18 and 28 are kinematically
  solvable with the fixed orientation (best positional errors below
  `1e-7 m`). The failure develops during dynamic scripted motion. A small
  diagnostic grasp correction lifted index 28, but not yet index 18. Report:
  `diagnostics/low_x_setup_probe/probe.json` (SHA-256
  `9b7d1059eb96d53d32d2cc551bed8e8a20f9f4e1db85b4901c01b6549debc639`).
- Combined-correction evidence: precise initial IK, Cartesian scripted setup,
  and release z=0.04 fixed frozen start 17 for all ten participants and made
  starts 18/28 physically feasible, but array `36355864` remained
  calibration-dependent. A subsequent Cartesian grasp grid selected the
  single common offset `[+0.004, -0.008, +0.005] m`: it was the best tested
  common lift with both low-x box tilts below 10 degrees and the smallest
  worst box-to-EE offset among such candidates (`0.02205 m`). Evidence:
  `diagnostics/low_x_setup_probe_v3/probe.json` (SHA-256
  `7b83b57f0a1759ea532980ffac757fc97c4de1ff1173b2a1521dfff6c8239f5a`).
- Calibrated-blocker evidence: array `36356248` tested the common grasp offset
  on starts 17/18/28. Nine participants passed 3/3; C05 passed 17/18 but
  exhausted 30 attempts on 28. Two C05/28 outcomes were settled/upright and
  only `0.03029–0.03074 m` from target. A cohort-wide margin analysis over all
  29 accepted cases supports the shared terminal calibration
  `[+0.002, -0.002] m`, retaining every accepted case below `0.0282 m` while
  moving those C05 endpoints below `0.0284 m`. This final candidate is under
  non-formal validation; it is not yet approved or present in shared code.
- Calibration evidence: C05/28 job `36356511` passed on attempt 1 with
  target error `0.0229015 m`; all other gates passed. Its Control-only summary
  has zero validation errors and is explicitly non-formal:
  `diagnostics/shared_revision_c05_final/summary.json` (SHA-256
  `17728d4662c0084cea5edcf35c7707cf0534f76ce5ea816ffef57e21072f2fcf`).
- Rejected global-calibration evidence: all-start array `36356531` applied the
  calibrated grasp offset to every cube start. C03 completed 28/30 and
  exhausted starts 21 and 25 as `box_not_lifted`; report SHA-256
  `a0c82e327ca469925cdebe7fb8ab83ed31f6acd1811dff05c7ae6711a7d71b00`.
  C01/C02 were cancelled after this decisive result and C04-C10 were
  cancelled before runtime. Therefore the grasp offset cannot be global.
- Rejected joint-setup evidence: a hybrid with the calibrated Cartesian setup
  only for low-x starts passed C03 starts 18/21/25/28 in 7 attempts (job
  `36357127`, report SHA-256
  `cc87885ffe980ff1c998344b41f8168e0b1a0241f015ce5e548fd103f684dc74`),
  but its C03 all-start gate `36357147` exhausted starts 6 and 17 in 100
  attempts (28/30; report SHA-256
  `4ba8dee9c6424dd99d2cb49f8014eda8f3b9d646358b69faa00db6c023ef0915`).
  The original joint-interpolated scripted setup is therefore not retained.
- Current-candidate evidence: precise initial IK and Cartesian scripted setup
  for all starts, with the grasp offset restricted to cube-start `x < 0.25 m`,
  passed the six C03 regression starts 6/17/18/21/25/28 in 13 attempts (job
  `36357407`). Its validator reports zero errors, exact paired starts, no
  unexpected payloads, maximum accepted target error `0.0269855 m`, and
  maximum waypoint error `0.001375 m`:
  `diagnostics/shared_revision_cartesian_preflight/summary.json` (SHA-256
  `9736aa5f01313d5e831767023c0005d3e1b7a86063b06ad6c5ebd3e61c8aeac4`).
  Runner SHA-256 is
  `943de698cd9048c58f4fb44f756505b3a50e39426a7ed3fc73b564d7bfcc9a5d`.
  C03 all-start gate job `36357432` completed 30/30 in 44 attempts. Its
  validator reports zero errors, maximum accepted target error `0.0276974 m`,
  waypoint error `0.0315184 m`, maximum observed cylinder tilt `4.95103 deg`,
  exact Target start parity, and no unexpected payloads:
  `diagnostics/shared_revision_cartesian_c03_all30/summary.json` (SHA-256
  `5c05a7c7e4f1584162629411e7f6ac7eda8c30574558f7100067e22b87ce8284`).
  Report SHA-256 is
  `4f977dde0594e57f148798454a3acef322d6e4492de99e1b6212780e400b4cd9`.
  The unchanged candidate entered the final non-formal 300-case gate in array
  `36357480`, but C02 completed only 29/30 in 89 attempts and exhausted frozen
  demo 5. Its 30 failed attempts comprise 25 target misses, three unsettled
  outcomes and two waypoint-reachability rejections; the best target error was
  `0.0210615 m` but that outcome was not settled. Report SHA-256 is
  `63586f85f101b8596fd01610214724082e12f4b280d1a4a73df3c784760ab1dd`.
  C01 passed 30/30 in 70 attempts (report SHA-256
  `5891defa0a34ff246aaec13029d29db48eca4ff97d257be6f5c48f5a20d68cca`)
  and C03 deterministically repeated its 30/30 result. C04 and C05 then
  independently failed the identical demo 5 (29/30; report SHA-256 values
  `bb6c58a8eedc6f8795127731dc7c2092349b1399b64be308664ba82f0f048bfb`
  and `5df36df7a48b4c4d0e2108b9b91ec02440b01fe6b65de91425014b72ca9b270d`),
  while C06 completed 30/30 in 85 attempts (report SHA-256
  `745e83ab11eebe62603193edacdd45fd7f168dc108e745c80851e3c1240f086e`).
  No formal restart or approval claim has been made, and the superseded
  universal `x < 0.25 m` branch must not be used formally.
- Route-boundary evidence: the only frozen starts with `x < 0.27 m` are demo
  5 at `0.242376 m`, demo 18 at `0.214270 m`, and demo 28 at `0.223827 m`.
  Narrowing the grasp-offset cutoff to `0.23 m` changes only demo 5 and leaves
  both demonstrated low-x setup blockers on the corrected branch. C02/C04
  demo 5 then passed on attempts 10/3 with target errors `0.0292164` and
  `0.0128612 m`; two-case report SHA-256 is
  `dc08a254045b40237fa77a9fe8c134481e2b57c6d6d267800b3c9c2041daccaa`.
  All-participant boundary array `36357788` produced an exact route split:
  C01-C06 passed demo 5, while C07-C10 each exhausted 30 attempts under the
  nominal grasp (6/10 successes, 170 attempts). This rejects a universal
  `0.23 m` cutoff. Completing the universal-offset all-start array produced
  296/300 successes in 751 attempts, with only C02/C04/C05/C09 demo 5 failing;
  aggregate validation has zero errors and exact paired starts:
  `diagnostics/shared_revision_cartesian_all30_final/summary.json` (SHA-256
  `6ce90156a84e87edb73d3adae3052e628788e52ef7736dc49460b4d0d482d820`).
  C09 showed the corrected offset could retain the box after release, while a
  four-offset probe found the lower boundary offset above passed C09/demo 5
  on attempt 1 at target error `0.00646721 m`. Applying it globally below
  `x<0.25` fixed boundary start 5 for every participant but caused retention
  at blocker 18 for C07/C10. This establishes the dual-offset split rather
  than a participant/route-specific rule.
- Dual-offset evidence: array `36359073` encoded the exact final branches and
  passed all ten participants at starts 5/18/28: 30/30 cases in 93 attempts.
  The strengthened validator reports zero errors, exact paired starts, correct
  setup strategy/offset metadata, maximum accepted target error `0.0295600 m`,
  waypoint error `0.0222246 m`, final cylinder tilt `1.77226 deg`, and no
  unexpected payloads:
  `diagnostics/shared_revision_dual_offset_blockers_all10/summary.json`
  (SHA-256
  `97ce8414f9262a0bacf8ee6fc6163bd9d3cc016e0d1a6d4a1272287acbd88e21`).
  Frozen runner SHA-256 is `a455c94f...`, validator `e58cd7c0...`.
- Exhaustive dual-offset evidence: array `36359120` completed every task
  `0:0` and passed all `300/300` participant/start cases in 587 attempts.
  Aggregate validation has zero errors, exact Target cube-start parity,
  maximum accepted target error `0.0298747 m`, waypoint error `0.0368130 m`,
  final cylinder tilt `2.23754 deg`, maximum observed cylinder tilt
  `9.99635 deg`, precise-initial-IK error `1.0133e-7 m`, no zero-byte files,
  and no unexpected payloads:
  `diagnostics/shared_revision_dual_offset_all30_final/summary.json`
  (SHA-256
  `60367dd6de2c08aa09e9b2b02ad0c43deb097fd424741e5fb36b91be5e5cdc55`).
  Frozen source hashes are runner
  `a455c94f0477f5f249c23408087f60a3e87592843a2cc06c7f69b5de596ec180`,
  validator
  `e58cd7c0d11be55533bc55d59fc9ec5a389a732339545dec266bedc28995e0ac`,
  wrapper
  `db8068e4505ceff762ac08f090b3137069efb702aa71abbc1bc28316a195d4c0`,
  shared base `991a5cca...`, and Control participants `8ab0ad2e...`. These are
  non-formal diagnostics and cannot enter HDF5.
- Coordination constraint: a read-only Target ledger audit at 22:42 records a
  later user-authorised Target-only `0.10 m` target radius, an instruction not
  to modify/restart Control from the Target workflow, and active Target array
  `36357471`. Control remains at the frozen `0.03 m` criterion. Therefore even
  a passing Control 300-case diagnostic does not authorise SCR-C001, a formal
  Control restart, any shared edit, or any Target interaction; explicit user
  resolution of the now-intentional cross-group protocol divergence is still
  required.
- Control impact: the present failed-protocol and diagnostic artifacts must
  remain non-formal and cannot enter HDF5. After explicit approval, Control
  must implement the frozen candidate, restart deterministically under a new
  immutable revision subroot without overwriting them, validate 300 fresh raw
  successes, and only then resume HDF5/training/rollouts/analysis.
- Target impact: the Target ledger records a later user-authorised Target-only
  `0.10 m` success radius and release-z-only trajectory, so this Control
  diagnostic must not be applied to Target or shared code implicitly. Any
  cross-group physical/protocol alignment now requires a new explicit user
  decision and must preserve the disclosed threshold divergence.
- Final disposition: this candidate was never applied to formal collection and
  is superseded. The new authorised R2 configuration is recorded in SCR-C002.
  Historical array `36353493` remains untouched until the separate collection
  start gate is opened.

### SCR-C002 — Target-aligned Control R2 (CONFIGURATION APPROVED/PREPARED; COLLECTION GATED)

- User authorisation: align Control with Target SCR-001/SCR-003/SCR-004 while
  retaining only Control's broad independent waypoint distribution; prepare
  configuration now but do not collect until the explicit command
  `开始收集数据`.
- Implementation boundary: all new behavior is Control-owned under
  `examples/rebuttal_control_pipeline/`; shared and Target-owned source files
  remain read-only. The historical Control collector SHA-256 remains
  `8ab0ad2e...` and the shared simulator remains `991a5cca...`.
- Frozen semantics: release z `0.08`, target radius `0.10`, box settled,
  cylinder tilt `<=10 deg`, contacts diagnostic only, exact initial EE
  `[box_x,box_y,box_z+0.10]`, validated scripted grasp/lift before frame 0, and
  Target-identical deterministic cube-start replenishment. No dual offset,
  release z004, cube centering or altered scripted setup is present.
- Immutable root:
  `rebuttal_dataset/simulation_control_group/full_seed20260806/protocol_release_z008_target_tol010_start_replenish/`.
  It contains configuration/preview/preflight evidence only and zero C01–C10
  formal participant directories.
- Prepared sources: `control_protocol.py` SHA-256 `ff70588a...`,
  `collect_control_aligned.py` `b6b424c9...`, array wrapper `5410167e...`,
  preflight `3fa42bd7...`, preparation helper `76438ad1...`, R2 raw validator
  `564e5469...`, and configuration validator `99d8808b...`. Python syntax,
  every `--help`, wrapper `bash -n`, and the unchanged historical Control test
  suite (5/5) passed.
- Frozen artifacts: `protocol_configuration.json` SHA-256 `05088144...`,
  `participant_manifest.json` `acedda6d...`, IK preflight `195dbf0c...`, and
  passed `configuration_validation_report.json` `ab0d8a91...`.
- Preflight result: policy-blind IK-only checking accepted all 300
  participant/demo pairs; 61 infeasible candidates were retained, every case
  found a feasible candidate by attempt 3, and no collection outcome, policy
  frame or learned policy was queried.
- Rollout dependency: use Target
  `analysis/paired_rollout_specs.json` directly at exact file SHA-256
  `10dbbe16da06b4013899e350fece05687abc8c45471b584ac5a2473a0e486dad`;
  replacement specs are forbidden.
- Start gate: `simulation_control_group_collect_r2` has not been submitted.
  Do not release/cancel/requeue historical array `36353493` or submit R2 until
  the user explicitly says `开始收集数据`.

If a shared-code change becomes necessary, record the exact file, proposed patch, reason, Control impact and expected Target impact here. Do not apply it without coordinator approval.

## Activity Log

- 2026-08-06: Control namespace reserved; no Control scientific protocol has been assumed.
- 2026-08-06T18:30:36+01:00: User authorised broad non-converging spatial
  Control demonstrations. Implemented C01–C10 collector, exact Target cube-start
  parity, constant full-support waypoint sampling, automatic replenishment,
  protocol preview, tests, Slurm array wrapper, and raw validator. Ten-person
  smoke passed 10/10 with three correctly rejected IK candidates.
- 2026-08-06: Coordinator created the isolated Control Long Goal prompt. The
  next agent must first audit the interrupted submission and must never touch a
  Target job or Target-owned path.
- 2026-08-06T18:51:52+01:00: Fresh Control executor started. Completed the
  prescribed six-file startup read in order, marked Stage A `IN_PROGRESS`, and
  began the required unknown-job/duplicate-submission audit. No collector
  process or new Slurm job has been launched in this session.
- 2026-08-06T18:52:40+01:00: Completed the mandatory interrupted-submission
  audit before any `sbatch`: `squeue -u k23114984` was empty; `sacct` for
  2026-08-06 contained no job named `simulation_control_group_collect`; the
  formal `logs/` directory contained no `collect_*` output/error logs; and
  C01–C10 formal directories were all absent. The formal root contains only
  `participant_manifest.json`, `waypoint_spread.png`, and the empty `logs/`
  directory. Therefore no prior Control job or partial collection exists to
  adopt, and no Target or unknown job was modified or cancelled.
- 2026-08-06T18:54:42+01:00: Preflight passed: wrapper/Python syntax valid,
  focused tests `5 passed`, runtime and log directory available,
  `interruptible_cpu` UP, 30/30 cube starts exactly equal to Target, and 300
  Control candidates unique within participant. A final exact-name scheduler
  query was empty. Submitted the authorised wrapper exactly once; Slurm
  returned array job `36353493`. Expected logs are
  `full_seed20260806/logs/collect_36353493_<task>.{out,err}`.
- 2026-08-06T19:03:58+01:00: Live C01–C03 collection independently
  reproduced the Target SCR-001 pattern at frozen paired demo 2: each has two
  accepted demos followed by repeated preserved target-miss diagnostics.
  Read-only audit of `target-simulation.md` confirmed T01–T03 exhausted 30/30
  attempts on the same start and that fixed release z=0.08 passed a 10-person
  Target diagnostic. Recorded matching Control `SCR-C001`; made no shared or
  Target-owned edit and retained the frozen running attempt budget.
- 2026-08-06T19:04:53+01:00: Read-only `scontrol show job 36353493_4`
  proved the pending elements' exact Control ownership by job name, Control
  wrapper command, workdir, and Control-only stdout/stderr paths. Placed only
  pending C04–C10 in recoverable user hold to avoid seven known repetitions
  while shared approval is pending. C01–C03 remain unmodified and continue to
  the frozen 30-attempt terminal result. No Target or unknown job was changed.
- 2026-08-06T19:14:27+01:00: C01–C03 all reached terminal `FAILED 1:0`
  after exactly 30 unsuccessful attempts at frozen demo index 2. Each retained
  exactly demos 0 and 1; stderr contains only the PyBullet banner followed by
  `RuntimeError: C0x demo 2 failed after 30 attempts`. C04–C10 remain held
  with zero runtime. No scientific failure was resubmitted as infrastructure
  failure.
- 2026-08-06T19:23:16+01:00: Hardened the Control-owned raw validator to
  report missing participant directories/summaries without crashing, count
  multi-label task failure reasons accurately, and check paired starts for
  every expected demo. Full recheck of authoritative `smoke_d01_v1` passed
  with zero errors (`validation_report_recheck.json`, SHA-256
  `8e042dc8ce4d88fafa317abaa9e770b38abba3a44b65c0ae37299fcfaf2154b2`).
  The formal incomplete-stage report correctly fails 146 completeness,
  spread, and pairing gates: `diagnostics/stage_a_failed_validation.json`
  (SHA-256 `ea836400d436d45cdce79ca0bd07394e67efe9fffade4d79fa8c466c2dde757f`).
  Added Control-only `summarize_failed_collection.py` and wrote
  `diagnostics/stage_a_failure_summary.json` (SHA-256
  `08e6a207d4e23161d979d1181cd1fc3a6f029be9ffe48ac11e3f7e1c14fad32f`):
  6/300 successes, 97 attempt JSONs, 91 failed attempts, 88 target-miss
  labels, 5 middle-waypoint-not-reached labels, 3 reachability labels, 585
  retained raw frames, zero scripted frames, zero failed raw demo directories,
  and zero zero-byte files. Best failed demo-2 target errors were
  C01 `0.0342408`, C02 `0.0318326`, C03 `0.0320436` m, all above `0.03`.
  Stage A cannot be restarted protocol-correctly until shared SCR-001/C001 is
  approved for both groups.
- 2026-08-06T19:30:48+01:00: Added a Control-only non-formal release-height
  diagnostic helper (no raw data, no videos, no shared/Target edits). Proposed
  shared release z=0.08 passed 10/10 Control participants at frozen demo 2 on
  attempt 0, and 10/10 at demo 0 with the exact prior C01/C09 deterministic
  reachability replenishments. Metrics and hashes are recorded in SCR-C001.
  A final read-only Target ledger check still reports `BLOCKED` awaiting the
  same coordinator approval; no revised Target protocol hash exists yet.
- 2026-08-06T19:35:29+01:00: Extended the Control-only release-height
  diagnostic to accept participant/demo subsets and all 30 starts. Python AST,
  CLI and Slurm wrapper syntax passed; a live C01/demo-0 preflight reproduced
  attempt-0 rejection and attempt-1 success with a well-formed
  `formal_data=false` report. Exact-name `squeue`/`sacct` audit found no prior
  diagnostic job. Submitted non-formal all-30 diagnostic array `36354365`
  (`1-10%3`) with outputs under
  `diagnostics/release_z008_all30/`; formal array `36353493` remains unchanged
  and held C04–C10 were not released.
- 2026-08-06T20:21:35+01:00: Nine committed all-start release-z diagnostic
  reports independently agree on exactly three failed frozen starts (indices
  17, 18 and 28); C10 remains normally running. The first is a residual target
  miss, while the latter two fail deterministic scripted setup before policy
  inference (`unreachable_waypoint` and `box_not_lifted`). This proves that
  release z=0.08 alone is not yet a sufficient shared revision. Added a
  non-formal, no-save low-x setup probe that preserves fixed orientation,
  timing, cube starts and initial-EE target. Exact-name scheduler and output
  audit found no prior probe; submitted it exactly once as job `36355676`.
  No shared or Target-owned file/job was modified.
- 2026-08-06T20:26:26+01:00: All-start diagnostic array `36354365` reached
  terminal after atomically committing all ten reports. Each task deliberately
  exited `1:0` because its report contained 27/30 rather than 30/30 cases;
  stderr contains only the PyBullet banner and the scientific gate message.
  Control-only aggregate validation passed with zero errors: 270/300 cases,
  1,234 attempts, common failures 17/18/28, exact paired Target starts, and no
  raw/video/HDF5 or zero-byte payloads (`summary.json` SHA-256
  `974ef9a4da48b2ac619b197a045b4d5f4cd2efea1a4fe7fe3495ce9f55c14101`).
  Low-x job `36355676` completed `0:0`; its exact-pose IK and phase traces are
  recorded above. After a clean exact-name/output audit, submitted bounded
  probe revision 2 exactly once as job `36355699` to test the same alignment
  on both low-x starts and compare the existing shared Cartesian mover. Formal
  array `36353493` remains unchanged, with C04–C10 still held.
- 2026-08-06T20:31:30+01:00: Low-x probe revision 2 (`36355699`) completed
  `0:0`. Precise deterministic initial IK plus the already-shared Cartesian
  segment mover lifted both frozen setup blockers with their exact original
  grasp/transport targets, no grasp offset, fixed orientation/speeds/phase
  order, and no saved setup frames (`low_x_setup_probe_v2/probe.json`, SHA-256
  `6fdae98a4c0e039b41afd6b4a4d763da257734f841a1f19d464e7f280a0883d2`).
  A C01/demo-18 full-transport preflight then showed release z=0.08 still
  misses (`0.0446951 m`), while z=0.04 passes (`0.0244252 m`). Encoded the
  combined candidate only in a Control diagnostic subclass; exact-name and
  output audit was clean, then submitted the three shared blockers for all ten
  participants exactly once as non-formal array `36355864`. No shared/Target
  edit or formal-data write occurred.
- 2026-08-06T21:23:27+01:00: Completed bounded combined-correction array
  `36355864`, grasp-alignment job `36356005`, and calibrated blocker array
  `36356248`; all preserved atomic reports and expected scientific exit gates.
  Job `36356248` passed 29/30 participant/blocker cases; C05/28 was the sole
  exhaustion. The selected common grasp offset and two-millimetre terminal
  calibration are recorded in SCR-C001 above. Exact-name/output audit was
  clean; submitted only C05/28 as non-formal final-candidate job `36356511`.
  No shared/Target file or job was changed, and the formal array remains held.
- 2026-08-06T21:27:12+01:00: Final C05/28 calibration job `36356511`
  completed `0:0` on attempt 1; Control validator passed with zero errors.
  Added a schema/threshold/pairing validator for combined-revision diagnostics.
  Exact-name/output audit for the definitive all-30 run was clean, and the
  validated runner hash exactly matched current source. Submitted non-formal
  array `36356531` exactly once (`1-10%3`) for all 300 cases. The runner is
  frozen while any element is pending/running; no formal or Target write was
  made.
- 2026-08-06T22:00:46+01:00: Global-grasp all-start array `36356531` was
  rejected after C03 exhausted starts 21 and 25 as `box_not_lifted` (28/30).
  C01/C02 were cancelled after 33:48 without committed reports; C04-C10 were
  cancelled with zero runtime after exact Control ownership checks. Preserved
  C03 report SHA-256 is recorded above. No formal or Target job was touched.
- 2026-08-06T22:04:15+01:00: Bounded C03 hybrid preflight `36357127` passed
  starts 18/21/25/28 (4/4, 7 attempts), but exhaustive C03 gate `36357147`
  subsequently exhausted starts 6 and 17 (28/30, 100 attempts) and terminated
  `FAILED 1:0` at 22:27:20. This rejected the original joint-interpolated
  setup outside the low-x branch; both reports remain diagnostic-only.
- 2026-08-06T22:31:56+01:00: Revised the Control-only diagnostic subclass to
  use precise initial IK and Cartesian setup globally while restricting the
  calibrated grasp offset to frozen cube-start `x < 0.25 m`. Job `36357407`
  passed C03 starts 6/17/18/21/25/28 (6/6, 13 attempts); summary validation
  passed every schema, threshold, exact-start, source, and no-payload gate.
  Evidence hashes are recorded above; shared and Target code remain unchanged.
- 2026-08-06T22:34:23+01:00: After exact-name scheduler/output audit and
  wrapper/Python syntax checks, submitted the frozen C03 all-30 candidate
  exactly once as non-formal job `36357432`. Runner SHA-256 is
  `943de698cd9048c58f4fb44f756505b3a50e39426a7ed3fc73b564d7bfcc9a5d`,
  validator `2ada9f233784d2acb5873719d833350b89562dfafafa4b3ec508c223a8bd6478`,
  and wrapper `b133889de848a82171031cee35e9df3d099e88955c23dd83ac9a19afd496279a`.
  Formal array `36353493` remains unchanged with C04-C10 held.
- 2026-08-06T22:42:01+01:00: C03 all-start job `36357432` completed `0:0`
  with 30/30 successes in 44 attempts. Independent summary validation passed
  with zero errors, exact paired starts, every scientific threshold, correct
  low-x/non-low-x setup branches, stable source hashes, no zero-byte files and
  no raw/video/model payloads. Summary/report hashes and metric maxima are
  recorded in SCR-C001.
- 2026-08-06T22:43:39+01:00: Read-only audit observed concurrent Target-only
  array `36357471` and the Target ledger's explicit `0.10 m` protocol; it was
  not modified. The shared base hash remained the same `991a5cca...` consumed
  by the passing C03 gate. After a clean exact-name/output audit, submitted the
  unchanged final Control diagnostic array `36357480` exactly once (`1-10%3`).
  Runner SHA-256 is `943de698...`, validator `2ada9f23...`, and wrapper
  `f15750417c7f10eab613bfc8e6453f60dadd545f01982bae5ea2fba4a64df830`.
  This remains non-formal; no shared, formal-Control, or Target state changed.
- 2026-08-06T23:00:40+01:00: Final diagnostic array `36357480` produced a
  decisive scientific failure: C02 exhausted all 30 attempts at frozen demo 5
  and committed 29/30 overall, while C01 and C03 committed 30/30. Exact report
  hashes and failure taxonomy are recorded above. After read-only ownership
  checks of job name, command, workdir and Control-only log paths, placed only
  unstarted C07-C10 in recoverable user hold. C04-C06 were already running and
  remain unmodified. No Target or formal-Control job was touched.
- 2026-08-06T23:12:35+01:00: C04/C05 independently reproduced C02's demo-5
  failure under the universal `x < 0.25 m` corrected-grasp branch, while C06
  passed all 30 starts. A bounded shim changed only the branch cutoff to
  `0.23 m`; job `36357770` passed C02/C04 demo 5 in 15 total attempts. Exact
  start-manifest inspection proves the change affects only demo 5, not setup
  blockers 18/28. Shim SHA-256 is `15ec26a...`; report hash is recorded above.
- 2026-08-06T23:28:22+01:00: Demo-5 boundary array `36357788` reached terminal
  with C01-C06 passing and C07-C10 failing after 30 attempts each under the
  nominal grasp. This exact L/R split rejected a universal narrow cutoff and
  motivated a route-aware boundary only in the Control diagnostic subclass;
  no shared/formal code was changed. Rechecked frozen runner/wrapper hashes,
  then released the previously held C07-C10 tasks of non-formal array
  `36357480` to test corrected-grasp R-route behavior across all 30 starts.
- 2026-08-07T00:14:30+01:00: Completed the universal-offset all-start array
  (`296/300`, four demo-5 failures), the four-offset C09 retention probe, and
  the lower-offset blocker array. The lower offset fixed start 5 across all
  participants but failed start 18 for C07/C10; the original corrected offset
  passed those blockers. Encoded the evidence-derived dual branch only in the
  Control diagnostic runner and validator. No shared/formal/Target write or
  job action occurred.
- 2026-08-07T00:24:45+01:00: Exact dual-offset blocker array `36359073`
  completed all ten tasks `0:0`; aggregate validator passed 30/30 cases in 93
  attempts with zero errors. Evidence and source hashes are recorded above.
  After exact-name/output and syntax audits, submitted the unchanged exhaustive
  300-case diagnostic array `36359120` exactly once (`1-10%3`), wrapper
  SHA-256 `db8068e4505ceff762ac08f090b3137069efb702aa71abbc1bc28316a195d4c0`.
  Formal Control array `36353493` remains unchanged and held C04-C10; no
  Target state was touched.
- 2026-08-07T01:13:25+01:00: Exhaustive dual-offset array `36359120`
  completed all ten tasks `0:0`; aggregate validation passed 300/300 cases in
  587 attempts with zero errors. Exact metrics, artifact hash and source hashes
  are recorded above. This exhausts safe non-formal feasibility work. Formal
  Control remains blocked on the explicit three-part user approval recorded in
  SCR-C001; no formal/shared/Target state was changed.
- 2026-08-07T01:17:31+01:00: Second consecutive approval audit after automatic
  continuation found no new user approval or external protocol change. Read-only
  Target inspection shows its 300-demo and HDF5 stages complete and its distinct
  Target-only 10 cm protocol now in training; this does not authorize or satisfy
  Control's 3 cm protocol. Formal array `36353493` still has only C04-C10 held
  with zero runtime; shared, formal-Control, diagnostic and exhaustive-summary
  hashes remain `991a5cca...`, `8ab0ad2e...`, `a455c94f...`, `e58cd7c0...` and
  `60367dd6...`. No job or scientific artifact was changed.
- 2026-08-07T01:18:18+01:00: Third consecutive approval audit found the same
  blocking condition. No user approval was received; C01-C03 remain failed and
  C04-C10 remain `JobHeldUser` with zero runtime. The shared/formal-Control/
  diagnostic/validator/exhaustive-summary hashes are unchanged at
  `991a5cca...`, `8ab0ad2e...`, `a455c94f...`, `e58cd7c0...`, and
  `60367dd6...`. Target remains read-only and independently in Stage C under its
  Target-only 10 cm protocol. Safe non-formal feasibility work is exhausted, so
  the long goal is marked blocked pending the exact three-part approval in
  SCR-C001. No job or scientific artifact was changed.
- 2026-08-07T12:45:03+01:00: User superseded the prior divergence and
  authorised Control preparation under the same physical/success configuration
  as Target SCR-001/SCR-003/SCR-004, while explicitly withholding collection
  authorisation until `开始收集数据`. Read all three Target SCRs plus the
  Target collector, success subclass, raw validator, setup preflight, rollout
  freezer/evaluator and frozen paired manifest read-only. Preserved the old
  Control collector/wrapper and excluded the dual-offset/z004 diagnostic from
  formal use. Added only Control-owned R2 protocol, collector, wrapper,
  preparation/preflight and validators; froze the immutable R2 root named in
  SCR-C002. Static checks and historical tests passed 5/5. Policy-blind IK
  preflight accepted 300/300 within attempt 3 after retaining 61 rejected
  candidates; configuration validation passed with zero errors and confirmed
  zero formal participant directories. Exact hashes are in SCR-C002. Final
  `squeue`/`sacct` audit found no R2 job: historical C01-C03 remain failed and
  C04-C10 remain `JobHeldUser` with zero runtime. No shared/Target file or job
  was modified, and no collection was started.
- 2026-08-07T16:56:01+01:00: User explicitly authorised formal collection and
  every downstream stage through HDF5, ten-policy training, 100 paired
  rollouts and EDSR analysis. Fresh pre-submit audit found no R2 job, no R2
  participant directory, a passed frozen configuration, and the exact paired
  manifest hash. `scontrol` proved held array `36353493` used the historical
  Control wrapper/workdir/log root; cancelled that old Control array only and
  verified it left the queue. Submitted R2 wrapper exactly once as Slurm array
  `36371239` (`1-10%3`). No Target file or job was modified.
- 2026-08-07T17:16:07+01:00: Stage A R2 first wave complete. C01-C03 each
  exited `COMPLETED 0:0` with exactly 30 accepted demos and participant
  summaries (90 total; 34/33/36 attempt records). All three accepted-waypoint
  spreads pass the future raw gates; cross-wave extrema are target error
  `0.0380375 m < 0.10`, final cylinder tilt `3.40525 deg < 10`, and realised
  waypoint error `0.0330673 m < 0.04`. Their stderr files contain only the
  42-byte PyBullet banner. C04-C06 started automatically under the unchanged
  `%3` array; no manual task action or Target interaction occurred.
- 2026-08-07T17:43:19+01:00: Stage A R2 second wave complete. C04-C06 each
  exited `COMPLETED 0:0`, retained exactly 30 demos, and produced 32/34/46
  immutable attempt records. Their accepted x spans are `0.17723/0.19600/
  0.15585 m`, z spans `0.09052/0.09367/0.09884 m`; maximum target error,
  final tilt and waypoint error are respectively `0.0346251 m`, `2.87583 deg`
  and `0.0347624 m`, all within the Target-aligned gates. C07 and C08 are
  running, total accepted is 197, and no manual retry occurred. In parallel,
  prepared hash-locked Control adapters for the exact Target HDF5 converter/
  validator, training freezer/runner/model validator and learned-policy
  evaluator, plus a Control final analyzer; all AST/bash/light CLI checks pass.
  These downstream helpers remain gated on completed upstream validation.
- 2026-08-07T18:29:47+01:00: Stage A R2 COMPLETE. All ten collection tasks
  are terminal `COMPLETED 0:0` (elapsed `13:33`–`28:18`), with exactly 30
  immutable accepted demos per participant, 300 raw demo directories and 387
  attempt records (87 retained failures). The first raw-validator run exposed
  only a directory-parser bug (`demo_00` versus the collector's `demo_0`);
  preserved its failed report at SHA-256 `f9a756d4...903a` and changed only
  that Control validator path. The complete rerun then exposed that the old
  empirical `0.14 m` spread sanity check was incorrectly applied to the
  post-success sample rather than the frozen sampling design: C07 retained 30
  unique in-support waypoints but selection reduced its diagnostic x span to
  `0.1382502 m`. Preserved that failed report at SHA-256 `c025069c...df5a`;
  retained the same `0.14/0.07 m` gates on the 30 frozen attempt-0 candidates,
  while continuing to report accepted spans diagnostically. This matches the
  prepared configuration gate and exact per-attempt deterministic-spec checks;
  no data was recollected or changed. Final validator hash is
  `a6e27d42...55fa8`. Canonical `validation_report.json` passed with no errors
  or warnings at SHA-256 `bd36e473...33fc`: 300 successes, 387 attempts,
  26,677 raw frames, zero successful `scripted_*` frames, zero partial/empty/
  zero-size artifacts; maxima are target error `0.0483504 m`, final cylinder
  tilt `3.40525 deg`, maximum transient cylinder tilt `9.80381 deg`, and
  realised waypoint error `0.0368160 m`. Advanced to Stage B without writing
  Target or overwriting any collection artifact.
- 2026-08-07T19:19:26+01:00: Stage B COMPLETE. Three disjoint local workers
  converted C01-C10 through the hash-locked Target converter at fixed gap 2,
  10,000 points, float64 and future-joint `t+2` actions. The first full HDF5
  validator correctly failed only C03/demo_23: observations matched raw but
  action rows 6-38 had become zeros; its sidecar's completion-time file hash
  `d8b79d38...5741` also disagreed with two stable current hashes
  `613471bc...5fc7` despite unchanged mtime/ctime. This established a derived-
  file infrastructure write-corruption event, not a raw/scientific failure.
  Preserved the corrupt C03 HDF5, sidecar, old aggregates and failed report
  (report SHA-256 `e6614eeb...8761`) under
  `hdf5/diagnostics/infra_c03_write_corruption_v1/`. Reconverted only C03 from
  unchanged raw using the exact same converter/seed, with no in-place repair;
  the new HDF5 hash `1c60c547...17aa` matched its sidecar and repeated hashes,
  and all 30 C03 action/arm/hand arrays matched raw exactly. Rebuilt aggregate
  manifest SHA-256 `95c5125e...ae43`; schema and trajectory-length summary
  hashes remained unchanged (`98c0b97d...02f0`, `4169e7ad...2c13`). Final
  `hdf5/validation_report.json` passed at SHA-256 `c617bed5...5de5`: 10 files,
  300 trajectories, 10 sidecars, 20/20 real train/valid loader smokes,
  `valid={demo_0,demo_23,demo_6}`, and zero unexpected/partial, empty,
  zero-byte or validation errors. Advanced to Stage C; Target remains read-only.
- 2026-08-07T19:26:12+01:00: Froze Stage C and submitted training array
  `36372730` exactly once as `1-10%2` on `interruptible_gpu`, excluding
  `erc-hpc-comp223`. The first preparation-only attempt produced ten internally
  uniform configs but hash `a43e0ee1...2e6a`; recursive Target-Control diff
  proved the sole canonical difference was the operational group-owned
  `train.output_dir`, because the Target freezer masks experiment/data paths
  but historically leaves its output path in the protocol hash. Preserved the
  complete non-training preparation root under
  `diagnostics/training_preparation_output_dir_hash_v1/` (manifest SHA-256
  `e162482e...c68`). The Control adapter now maps only the copied value used
  for hashing to Target's historical output string, while fail-closed checks
  prove all executable configs still write only Control `models/runs` and the
  frozen Target manifest remains SHA-256 `610caef2...5623`. Final Control
  training manifest SHA-256 `422f1e9a...8f4a` records exact Target protocol
  hash `db0aca89...b0c6`, HDF5 validation hash `c617bed5...5de5`, diffusion
  seed 1, batch 16, 40 epochs x 250 steps, 50 validation steps/epoch, and
  performance-blind exact epoch-40 selection. Ten configs/HDF5 hashes passed
  independent readback; run/log roots were empty before submit. `scontrol`
  confirms the job command, workdir and output paths are Control-only; all ten
  elements initially pending, with no duplicate `control-policy` job.
- 2026-08-07T20:37:09+01:00: Training array `36372730` remains the unique
  Control submission with all ten elements pending on global priority; no run,
  status or Slurm log artifact exists yet. The preceding same-account bimodal
  array completed and left the queue without any Control intervention. Read-
  only `sbatch --test-only` comparisons showed a new ordinary `gpu` job would
  start substantially later and a new interruptible submission would forfeit
  the existing array's accumulated priority, so neither was submitted. After
  exact ownership/command/state checks, reduced only the still-pending array's
  conservative Slurm walltime from 8h to 2h to improve safe backfill; Target
  same-architecture observed training took at most 32 minutes, leaving more
  than 3.7x margin. This did not change partition, GPU/CPU/memory, `%2`, data,
  configs, seed, training budget or checkpoint rule; current scheduler estimate
  is `2026-08-07T23:42:58+01:00`. Read-only 30-second monitor session `19577`
  remains active; do not resubmit while job `36372730` is pending/running.
- 2026-08-07T21:05:29+01:00: Stage C first formal result complete. The
  scheduler started C01 at `20:37:10+01:00` on `erc-hpc-comp222`; it completed
  40/40 epochs and wrapper postchecks in `25:21`, with Slurm `COMPLETED 0:0`,
  zero-byte stderr and no infrastructure retry. Immutable status `status/C01.json`
  has SHA-256 `e061cd36...0882` and `passed_postcheck=true`; selected exact
  `model_epoch_40.pth` is 290,106,788 bytes and independently matches status at
  SHA-256 `3d706191...ba98`. Losses remained finite and checkpoint selection
  did not use them. C02 then started automatically on the same node without
  resubmission; by `21:05:29` it had completed epoch 4/40 with finite train/
  validation losses, stable ~1.31 GiB memory and empty stderr. Array state is
  one completed, one running and eight pending under the unchanged `%2` limit.
- 2026-08-07T21:28:13+01:00: C02 completed 40/40 epochs and wrapper postchecks
  in `24:22` with Slurm `COMPLETED 0:0`, empty stderr and no retry. Its status
  SHA-256 is `67ceaafa...7136`; exact epoch-40 checkpoint is 290,106,788 bytes
  and independently matches status at SHA-256 `c301996c...e81b`. Independent
  readback confirms C01 and C02 each contain exactly one `Validation Epoch 40`
  record and their status/config/checkpoint chains pass. C03 then started
  automatically on `erc-hpc-comp222`, completed epoch 1 with finite logs and
  empty stderr. Array state is two completed, one running and seven pending;
  there has been no resubmission, infrastructure retry or Target write.
- 2026-08-07T21:53:18+01:00: C03 completed 40/40 epochs and wrapper postchecks
  in `24:47` with Slurm `COMPLETED 0:0`, empty stderr and no retry. Its status
  SHA-256 is `7897a336...78eb`; exact epoch-40 checkpoint is 290,106,788 bytes
  and independently matches status at SHA-256 `134c47d0...9f36`. The training
  log contains exactly 40 validation records and exactly one `Validation Epoch
  40`; `passed_postcheck=true`, subprocess exit is zero and the status records
  the matching array/task job IDs. C04 then started automatically on
  `erc-hpc-comp222` without resubmission. Array state is three completed, one
  running and six pending; no infrastructure retry or Target write occurred.
- 2026-08-07T22:20:15+01:00: C04 completed 40/40 epochs and wrapper postchecks
  in `27:11` with Slurm `COMPLETED 0:0`, empty stderr and no retry. Its status
  SHA-256 is `63165146...2cfb`; exact epoch-40 checkpoint is 290,106,788 bytes
  and independently matches status at SHA-256 `8a650eec...0674`. The log has
  exactly 40 validation records and one epoch-40 record, with
  `passed_postcheck=true`, zero subprocess exit and no errors. C05 started
  automatically on `erc-hpc-comp222`; array state is four completed, one
  running and five pending, with no resubmission or Target write.
- 2026-08-07T22:45:28+01:00: C05 completed 40/40 epochs and wrapper postchecks
  in `24:49` with Slurm `COMPLETED 0:0`, empty stderr and no retry. Its status
  SHA-256 is `47e63a82...6de0`; exact epoch-40 checkpoint is 290,106,788 bytes
  and independently matches status at SHA-256 `7ce5413c...29c0`. Its log has
  exactly 40 validation records and one epoch-40 record, with
  `passed_postcheck=true`, zero subprocess exit and no errors. The scheduler
  had independently started C06 on `erc-hpc-comp202` under the original `%2`
  limit; C06 remains healthy while C07-C10 are pending. No resubmission,
  infrastructure retry or Target write occurred.
- 2026-08-07T23:01:41+01:00: C06 completed 40/40 epochs and wrapper postchecks
  in `27:32` with Slurm `COMPLETED 0:0`, empty stderr and no retry. Its status
  SHA-256 is `da66a033...96ad`; exact epoch-40 checkpoint is 290,106,788 bytes
  and independently matches status at SHA-256 `543de254...9298`. Its log has
  exactly 40 validation records and one epoch-40 record, with
  `passed_postcheck=true`, zero subprocess exit and no errors. C07 continues
  on `erc-hpc-vm065`, and C08 started automatically on the released
  `erc-hpc-comp202` slot. Array state is six completed, two running and two
  pending, with no resubmission, infrastructure retry or Target write.
- 2026-08-07T23:20:42+01:00: C07 completed 40/40 epochs and wrapper postchecks
  in `29:33` with Slurm `COMPLETED 0:0`, empty stderr and no retry. Its status
  SHA-256 is `ddbe1b47...d8e0`; exact epoch-40 checkpoint is 290,106,788 bytes
  and independently matches status at SHA-256 `65879b28...8772`. Its log has
  exactly 40 validation records and one epoch-40 record, with
  `passed_postcheck=true`, zero subprocess exit and no errors. C08 continues
  on `erc-hpc-comp202`, and C09 started automatically on `erc-hpc-comp048`.
  Array state is seven completed, two running and one pending, with no
  resubmission, infrastructure retry or Target write.
- 2026-08-07T23:27:43+01:00: C08 completed 40/40 epochs and wrapper postchecks
  in `25:34` with Slurm `COMPLETED 0:0`, empty stderr and no retry. Its status
  SHA-256 is `4acbf8c3...bda2`; exact epoch-40 checkpoint is 290,106,788 bytes
  and independently matches status at SHA-256 `e4f3d786...43ec`. Its log has
  exactly 40 validation records and one epoch-40 record, with
  `passed_postcheck=true`, zero subprocess exit and no errors. C09 continues
  on `erc-hpc-comp048`, and the final participant C10 started automatically on
  `erc-hpc-vm065`. Array state is eight completed and two running, with no
  remaining pending elements, resubmission, retry or Target write.
- 2026-08-07T23:46:31+01:00: C09 completed 40/40 epochs and wrapper postchecks
  in `25:36` with Slurm `COMPLETED 0:0`, empty stderr and no retry. Its status
  SHA-256 is `aff72f91...7f6b`; exact epoch-40 checkpoint is 290,106,788 bytes
  and independently matches status at SHA-256 `0440de0d...1723`. Its log has
  exactly 40 validation records and one epoch-40 record, with
  `passed_postcheck=true`, zero subprocess exit and no errors. Only C10 remains
  running under the original array; no elements are pending and there has been
  no resubmission, infrastructure retry or Target write.
- 2026-08-07T23:56:01+01:00: All ten formal training elements COMPLETE. C10
  completed in `28:25` with Slurm `COMPLETED 0:0`; its status SHA-256 is
  `7640dc50...d70a`, and its 290,106,788-byte epoch-40 checkpoint independently
  matches status at SHA-256 `6ad0a5d4...7cfb`. The parent array and every
  C01-C10 child are `COMPLETED 0:0` (elapsed `24:22`-`29:33`). Independent
  aggregate readback confirms all ten have `passed_postcheck=true`, zero
  subprocess exit, no status errors, empty stderr, exactly 40 validation
  records, exactly one epoch-40 record, selected epoch 40, expected checkpoint
  size and matching checkpoint hash. No training element was rerun and no
  infrastructure retry or Target write occurred. Stage C remains gated on the
  frozen ten-model load/inference validator before rollout preparation.
- 2026-08-08T00:40:18+01:00: Stage C COMPLETE. Ran the hash-locked exact Target
  ten-model validator once in the same CPU inference mode recorded by Target.
  The system-default Python lacked `h5py` during an initial `--help` import
  only, before argument parsing or output creation; used the same arcap Python
  environment as training for the actual validator. It loaded every C01-C10
  epoch-40 checkpoint and ran real inference against each frozen HDF5, yielding
  `passed=true`, 10 checkpoints, zero errors, CPU device, observation horizon
  7 and finite action shape `[8]` for all ten. No participant has a retry.
  Immutable `model_validation_report.json` SHA-256 is
  `c00c49cf...41bf`; `selected_checkpoints_manifest.json` SHA-256 is
  `666e3cb0...a9e6`. The emitted `torch.load(weights_only=False)` future warning
  is non-fatal and the report contains no error. Stage D rollout preparation
  is now allowed; Target remains read-only.
- 2026-08-08T00:47:42+01:00: Froze Stage D and submitted rollout array
  `36376643` exactly once as `1-10%2` on `interruptible_gpu`, excluding
  `erc-hpc-comp223`. Pre-submit audit confirmed the direct read-only Target
  paired manifest and sidecar both gate exact SHA-256 `10dbbe16...86dad`, the
  Control selected-checkpoint manifest is SHA-256 `666e3cb0...a9e6`, all ten
  checkpoints are present, the Control output root and duplicate rollout jobs
  were absent, and the hash-locked evaluator imports successfully. The active
  protocol assertion passed for target radius `0.10 m`, cylinder tilt
  `<=10 deg`, diagnostic-only contacts and the exact paired manifest. Target's
  same-protocol task durations were `06:38`-`13:41`, safely inside the unchanged
  six-hour limit. Created only the empty Control `policy_rollouts/logs/`
  directory before submit. `scontrol` confirms the Control-only command,
  workdir/log paths, one GPU, six-hour limit and throttle 2; all ten elements
  initially pending. A preliminary import probe without `examples/` on
  `sys.path` failed before protocol execution or output creation; the corrected
  exact probe passed. No Target write or rollout result existed at submission.
- 2026-08-08T00:55:02+01:00: First Stage D pair COMPLETE. C01 and C02 ran on
  `erc-hpc-comp222` and exited Slurm `COMPLETED 0:0` in `10:55` and `10:32`.
  Independent readback confirms each has exactly ten immutable valid scientific
  JSON results for case IDs 0-9, ten nonempty videos, exact paired-manifest hash,
  valid policy-after-scripted-setup boundaries, no scripted transport, matching
  summary counts and no infrastructure-failure records. C01 summary SHA-256 is
  `d0d6d4e3...4752`; C02 summary SHA-256 is `83c75cee...dca2`; both have 5/10
  successes and EDSR `0.5`. Observed policy timeouts were retained as scientific
  failures and not rerun. C03 and C04 started automatically on the released
  slots without resubmission; Target remains read-only.
- 2026-08-08T01:04:12+01:00: Second Stage D pair COMPLETE. C03 and C04 exited
  Slurm `COMPLETED 0:0` in `08:50` and `09:36`. Both pass independent readback:
  ten immutable valid case JSONs, ten nonempty videos, correct paired hash and
  policy boundary, no scripted transport, matching summary counts and no
  infrastructure-failure records. C03 summary SHA-256 is
  `61ce235c...b2f3`, with 5/10 successes and EDSR `0.5`; C04 summary SHA-256 is
  `1e56c3b1...600a`, with 4/10 successes and EDSR `0.4`. C05 started
  automatically; remaining array elements stay under the original submission,
  with no retry or Target write.
- 2026-08-08T01:15:51+01:00: Third Stage D pair COMPLETE. C05 and C06 exited
  Slurm `COMPLETED 0:0` in `10:26` and `11:23`. Both pass the same independent
  ten-JSON/ten-video, paired-hash, policy-boundary, no-scripted-transport,
  summary-count and zero-infrastructure-failure gates. C05 summary SHA-256 is
  `51bb9fe0...027f`, with 3/10 successes and EDSR `0.3`; C06 summary SHA-256 is
  `1c59b457...3319`, with 2/10 successes and EDSR `0.2`. C07 started
  automatically on a released slot; later elements remain in the single
  original array. No scientific outcome was rerun and Target remains read-only.
- 2026-08-08T01:25:19+01:00: Fourth Stage D pair COMPLETE. C07 and C08 exited
  Slurm `COMPLETED 0:0` in `09:26` and `08:23`. Both again pass all ten-result,
  ten-video, paired-hash, policy-boundary, no-scripted-transport, summary-count
  and zero-infrastructure-failure gates. C07 summary SHA-256 is
  `bdcc7ef0...2f45`, with 4/10 successes and EDSR `0.4`; C08 summary SHA-256 is
  `c5a84c8a...8e86`, with 5/10 successes and EDSR `0.5`. C09 and C10 now run
  automatically as the final two elements; no pending elements, retry,
  duplicate submission or Target write exists.
- 2026-08-08T01:32:41+01:00: Stage D COMPLETE. C09 and C10 exited Slurm
  `COMPLETED 0:0` in `08:22` and `07:25`, with summary SHA-256 values
  `837ea56f...3a89` and `3680796d...3f3d`; their successes are 5/10 and 6/10
  (EDSR `0.5` and `0.6`). All ten array elements are `COMPLETED 0:0`, elapsed
  `07:25`-`11:23`. Aggregate independent audit passes: ten participant
  summaries, 100 unique participant/case JSONs, 100 nonempty videos, every
  result valid and execution index zero, exact Target paired hash, exact
  participant checkpoint hash, policy started only after validated scripted
  setup, no scripted transport and zero infrastructure-failure records. No
  scientific result was rerun. Raw Control outcome is 44/100 successes, split
  evenly as 22/50 for L and 22/50 for R. Stage E analysis is now allowed;
  Target remains read-only.
- 2026-08-08T01:35:02+01:00: Stage E and the full authorized Control pipeline
  COMPLETE. Ran the exclusive final analyzer once; it revalidated the entire
  300-demo, 10-HDF5, 10-checkpoint and 100-rollout chain against Target's
  read-only artifacts and emitted exactly eight analysis files. Immutable
  `analysis/validation_report.json` passed with zero errors at SHA-256
  `6287daf4...e97f`; all cross-checks are true and every planned-output hash
  matches independent readback. `final_results.json` SHA-256 is
  `cd90fd78...0915`; experiment manifest SHA-256 is `f3c1ddb5...56c8`;
  participant CSV SHA-256 is `3c3dbdcb...242a`; rollout CSV SHA-256 is
  `9c519b17...ca0c`; plot SHA-256 is `68340083...ed7d`; video index SHA-256 is
  `898080f6...32e1` and records 100 unique video hashes. Recomputed Control
  participant-level EDSR is `0.44 +/- 0.117379` sample SD (`n=10`, `ddof=1`),
  with L `0.44 +/- 0.089443` and R `0.44 +/- 0.151658`. Target is
  `0.39 +/- 0.172884`; descriptive Control-minus-Target differences are overall
  `+0.05`, L `+0.12`, R `-0.02`, with no independence claim for 100 rollouts.
  Raw Control outcomes are 44 successes and 56 failures; exclusive primary
  failures are 26 cylinder topples and 30 target misses. Contacts remain
  diagnostic-only. A first independent audit invocation used system Python and
  stopped on missing NumPy before reading outputs; the same read-only audit in
  the arcap environment passed. The exact Target paired manifest remains
  SHA-256 `10dbbe16...86dad`; Target was never written.
