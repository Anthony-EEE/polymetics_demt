# Agent Work: Control-Derived Bimodal Simulation Pipeline

_Experiment label: `simulation_control_bimodal_group` · Status: COMPLETE_WITH_DISCLOSED_PROTOCOL_AMENDMENT_

## Current Execution

- Updated: `2026-08-08T20:41:00+01:00`
- Active stage: `COMPLETE — final analysis and CBxx-Bxx comparison independently validated`
- Formal design seed: `20260807`
- Runtime: `/scratch/users/k23114984/conda/arcap/bin/python`
- Helper root: `examples/rebuttal_control_bimodal_pipeline/`
- Data root: `rebuttal_dataset/simulation_control_bimodal_group/`
- Slurm jobs: training array `36382599` and rollout array `36387361`
  (both `1-10%2`, submitted once, and fully terminal)
- Ownership: only this ledger, the helper/data roots above, and
  `tests/test_rebuttal_control_bimodal_pipeline.py` are writable

## Frozen Design

| Policy | Control L | Control R | Matched policy |
|---|---|---|---|
| CB01 | C01 | C07 | B01 |
| CB02 | C03 | C06 | B02 |
| CB03 | C03 | C07 | B03 |
| CB04 | C03 | C10 | B04 |
| CB05 | C05 | C10 | B05 |
| CB06 | C05 | C09 | B06 |
| CB07 | C03 | C09 | B07 |
| CB08 | C04 | C06 | B08 |
| CB09 | C02 | C10 | B09 |
| CB10 | C04 | C08 | B10 |

The selected order is the exact left-major
`random.Random(20260807).sample(C01..C05 x C06..C10, 10)` draw. Pairing,
shuffle, split, learner, evaluation cases, repeats, and policy-sampling seeds
must remain index-matched to B01–B10. No outcome-dependent redraw or retry is
allowed.

## Stage Ledger

| Stage | Status | Evidence |
|---|---|---|
| Startup and isolation audit | COMPLETE | Four reserved paths absent; no matching current/historical job; 11 PiB free; all 15 frozen Control/Target/Bimodal hashes matched the handoff |
| Pairing | COMPLETE | `pairing_manifest.json` SHA-256 `86cbe45062b32225e4e3233339c4dfd417954f2c7111cb35fd5a7d84c38895e5`; exact CBxx-Bxx/source-index match |
| Mixed Views | COMPLETE | 1,200 relative symlinks; 600 memberships; exact 30L+30R and shuffle replay; validator SHA-256 `20f77210e092e50b7e115597dd2510afcd8d151ce4ec76127a2df95565d64559` |
| HDF5 | COMPLETE | Ten closed/reopened physical 60-trajectory files; exact Control source equality; 54/6 stratified split; 20/20 loader smokes; validator SHA-256 `007cc071f2be34d05ddde49073756c8f6329e947b83e6a09c2c2c475bd3093d9` |
| Training | COMPLETE | Unique array `36382599`; all ten tasks `COMPLETED 0:0`; exact validation epochs 1--40 and epoch-40 checkpoints; zero errors/retries; all stderr empty |
| Model Validation | COMPLETE | Report SHA-256 `d48f4726...dc5a`; selected manifest SHA-256 `cd3f89fb...03f5`; 10/10 real CPU checkpoint loads/inference smokes passed |
| Rollout | COMPLETE | Array `36387361`; all ten tasks `COMPLETED 0:0`; 200 exact results + 200 complete/distinct videos; zero infrastructure failures/retries |
| Analysis | COMPLETE_WITH_DISCLOSED_AMENDMENT | Original 10 µm/0.01° gate retained as failed for 2/100 pairs; user-authorized post-rollout 2 mm/3° engineering gate passed 100/100; 11 artifacts published atomically; validation SHA-256 `05c6e003...6cfd` |
| Cross-Bimodal Comparison | COMPLETE | Exact CBxx-Bxx index-matched comparison published; JSON SHA-256 `eb4f353d...f463`; 10 policy rows and 200 matched descriptive keys independently checked |

## Safety Gates

1. Recompute frozen source hashes before every stage and every `sbatch`.
2. Creators refuse formal-output overwrite and publish from exclusive temporary
   paths only after closed-file/readback validation.
3. GPU arrays use at most `%2`, exclude `erc-hpc-comp223`, and require exact
   ownership plus duplicate-job audits before submission.
4. Scientific failures remain final. Only reviewed pre-result infrastructure
   failures may resume the identical work item.
5. Repeat setup fields match exactly. The original 10 micrometre/0.01 degree
   gate and its 2/100 failure remain recorded. After rollout, the user
   explicitly approved millimetre-scale real-rollout variation; the amended
   acceptance envelope is 2 mm/3 degrees and passed all 100 pairs. This is
   disclosed as a post-rollout amendment, not represented as preregistered.
6. Control, Target, and existing Bimodal paths and jobs remain read-only.

## Activity Log

- `2026-08-08T12:11:00+01:00`: Started from
  `handoffs/control-bimodal-dp-long-goal.md` at matching SHA-256
  `be60ffc29dccd7a4a6e270fffd1291cc182aa134e49479fd340c9ec9e4766e75`.
  Read the coordination and prior experiment ledgers, preserved the dirty
  worktree, confirmed all four new paths and matching jobs were absent, checked
  current scheduler state and capacity, and independently matched every frozen
  Control, Target, and Bimodal input hash listed in the handoff. No experiment
  job has been submitted and no prior-group artifact or job was changed.
- `2026-08-08T12:38:44+01:00`: Pairing, mixed-view and HDF5 stages COMPLETE.
  The pairing is the exact C-index analogue of B01-B10 and records 600
  memberships over 300 unique Control trajectories. Mixed validation passed
  10 policies, 1,200 in-root relative links and exact deterministic shuffle
  replay with zero errors. HDF5 attempt 1 closed and reopened every candidate
  before atomic publication; the independent validator then rechecked all 600
  copied payloads, exact provenance, finite data, 27L+27R train / 3L+3R valid
  masks and 20/20 real loaders with zero errors. A redundant pairing creator
  invocation made during output-capture diagnosis was safely rejected by the
  exclusive-write gate after the formal manifest already existed; no output
  was overwritten. Ten training configs now reproduce the existing Bimodal
  normalized protocol hash `6c309f43...77d`; run/status/log roots are empty.
- `2026-08-08T12:48:06+01:00`: Reverified all 15 frozen inputs immediately
  before `sbatch` and submitted training array `36382599` exactly once as
  `1-10%2` on `interruptible_gpu`, excluding `erc-hpc-comp223`. Scheduler
  ownership inspection proves the new job name, helper command, workdir,
  stdout/stderr and model root are Control-Bimodal-only. CB01/CB02 started
  immediately on `erc-hpc-comp053/050`, passed frozen-input and participant
  HDF5 hash gates, and reached epochs 10/9 with finite logs, approximately
  1.4 GiB memory and empty Slurm stderr. A direct read-only index audit also
  proved all ten CB/B policies have identical 600 route/source-demo shuffle
  positions and identical 20 train/valid masks.
- `2026-08-08T13:10:00+01:00`: CB01 and CB02 reached scheduler terminal state
  `COMPLETED 0:0` after 24:34 and 26:22. Both task-status records pass their
  postchecks with subprocess exit 0, empty error/retry fields and the correct
  array/task/node identity; both Slurm stderr files are empty. Each training
  log contains exactly the consecutive validation epochs 1--40, one success
  marker and no non-finite diagnostic. Their epoch-40 checkpoints are exactly
  290,106,852 bytes with SHA-256
  `ce6afbea7e66b15af9a0305af9894501e244fdd323f467522e517fb8b808f4f3`
  and `70d33b9df5b84ea17e33a79b76bc77f95923c17c17183724178d9b33b831442c`.
  CB03/CB04 then started on the same two approved nodes; no retry or duplicate
  submission occurred.
- `2026-08-08T13:29:00+01:00`: CB03 reached `COMPLETED 0:0` in 23:27 on
  `erc-hpc-comp053`, with a passed zero-error postcheck, no retry, empty Slurm
  stderr, exact validation epochs 1--40, exact completion/success markers and
  no non-finite token. Its 290,106,852-byte epoch-40 checkpoint SHA-256 is
  `07b1943c26c51e279a019da9916bf485f220bc3021bb9a3d4ae54f9facddb6d1`.
  CB05 automatically took the released array slot; no new submission occurred.
- `2026-08-08T13:34:00+01:00`: CB04 reached `COMPLETED 0:0` in 26:13 on
  `erc-hpc-comp050`. Its terminal record has a passed zero-error postcheck,
  subprocess exit 0, no retry, empty stderr, exact validation epochs 1--40,
  exact completion/success markers and no non-finite token. The 290,106,852-byte
  epoch-40 checkpoint SHA-256 is
  `072f30e76c0d9670fc500efed88e808db8b2b662de0c2d879ccb68a626a34621`.
  CB06 then started automatically on approved node `erc-hpc-comp195`; no new
  submission or protocol change occurred.
- `2026-08-08T13:53:00+01:00`: CB05 reached `COMPLETED 0:0` in 23:33 on
  `erc-hpc-comp053`. Its passed postcheck records subprocess exit 0, no error
  or retry, empty stderr, exact validation epochs 1--40, exact completion and
  success markers, and no non-finite token. The 290,106,852-byte epoch-40
  checkpoint SHA-256 is
  `1086b0bbf66cd0e371c6e6ea8fc5c4223c376c6ec2dc88b71804710ef7ab287c`.
  CB07 automatically took the released slot; no new submission occurred.
- `2026-08-08T14:06:00+01:00`: CB06 reached `COMPLETED 0:0` in 32:23 on
  `erc-hpc-comp195`. The selected status passed with subprocess exit 0, no
  error/retry, empty stderr, exact validation epochs 1--40, exact terminal
  markers and no non-finite token. Its 290,106,852-byte epoch-40 checkpoint
  SHA-256 is
  `32b64f1d0a736154170c173293967090539d77ed2b376ee60dd8dfba56450ef3`.
  CB08 automatically started on the same approved node; no new submission or
  scientific-protocol change occurred.
- `2026-08-08T14:16:00+01:00`: CB07 reached `COMPLETED 0:0` in 23:03 on
  `erc-hpc-comp053`. The terminal record passed with subprocess exit 0, no
  errors/retry, empty stderr, exact validation epochs 1--40, exact completion
  and success markers, and no non-finite token. Its 290,106,852-byte epoch-40
  checkpoint SHA-256 is
  `7069e3e0be63cf076745a1fbd1c38c46d800de5411c12a6240094fd36a3b6104`.
  CB09 automatically took the released slot; no new submission occurred.
- `2026-08-08T14:36:00+01:00`: CB08 reached `COMPLETED 0:0` in 29:26 on
  `erc-hpc-comp195`. Its selected status passed with subprocess exit 0, no
  error/retry, empty stderr, exact validation epochs 1--40, exact terminal
  markers and no non-finite token. The 290,106,852-byte epoch-40 checkpoint
  SHA-256 is
  `8270635d41719b67652933a88c60230f4dad2a9f6494426a1ab50eb686c05491`.
  The final training task CB10 automatically started on the same approved node;
  no new submission occurred.
- `2026-08-08T14:39:00+01:00`: CB09 reached `COMPLETED 0:0` in 22:58 on
  `erc-hpc-comp053`. Its terminal status passed with subprocess exit 0, no
  errors/retry, empty stderr, exact validation epochs 1--40, exact completion
  and success markers and no non-finite token. The 290,106,852-byte epoch-40
  checkpoint SHA-256 is
  `df001694e449dc7bcab83ca6118dfc39acc0a61b8953cc28f599fcb77fda9506`.
  CB10 is the only remaining array task and passed preflight into training; no
  new submission occurred.
- `2026-08-08T15:10:00+01:00`: CB10 and training array `36382599` reached
  `COMPLETED 0:0`; CB10 elapsed 32:46 on `erc-hpc-comp195`. Its terminal status
  passed with subprocess exit 0, no errors/retry, empty stderr, exact validation
  epochs 1--40, exact terminal markers and no non-finite token. The CB10
  290,106,852-byte epoch-40 checkpoint SHA-256 is
  `0bccd8d12dc339b551fca5ef7ad687570602c450d7c70ad6449ed5cefabc85ea`.
  An aggregate audit then proved all ten Slurm tasks `COMPLETED 0:0`, all ten
  status records passed without error/retry, all logs contain exactly 40
  consecutive validation epochs plus exact completion/success markers, every
  epoch-40 checkpoint has the expected size, and all ten stderr files are empty.
- `2026-08-08T15:53:00+01:00`: The independent model validator reverified all
  15 frozen inputs, rehashed every status/config/log/checkpoint/source HDF5,
  enforced exact training epochs and scheduler ownership, then loaded each of
  the ten 72.45M-parameter epoch-40 checkpoints on CPU and produced a finite
  `(8,)` action from a real HDF5 observation. It exited 0 with
  `passed=true`, `checkpoint_count=10`, `errors=[]`. The report SHA-256 is
  `d48f4726471747c49fae1929bea9cf1bb57a8c877d2871d42e128296577edc5a`;
  the selected-checkpoint manifest SHA-256 is
  `cd3f89fb979790f1bb53b05981857a93da078dcbb7452f87ab76523c20de03f5`.
- `2026-08-08T15:55:00+01:00`: Reverified all 15 frozen inputs and the frozen
  Target paired-spec hash, confirmed exactly ten selected checkpoint records,
  reran the joint old/new regression suite (`20 passed`), confirmed the formal
  rollout root was absent and both active/historical duplicate-job audits were
  zero, then created only the new log directory and submitted rollout array
  `36387361` exactly once as `1-10%2`. Scheduler ownership proves the exact new
  job name, helper command, workdir, output/error root, one-GPU request,
  `interruptible_gpu` partition and exclusion of `erc-hpc-comp223`. The frozen
  wrapper/policy hashes remain `e9b1e2cd...69a1` and `1d735d51...bd7`.
- `2026-08-08T16:20:00+01:00`: Rollout tasks CB01/CB02 reached
  `COMPLETED 0:0` in 21:26/24:08 on approved nodes `comp050/comp052`, and
  CB03/CB04 automatically took their array slots. Each completed participant
  has the exact 20 case/repeat JSON keys, 20 complete videos with 20 distinct
  content hashes, one summary and zero infrastructure-failure records. CB01
  reports L/R/indeterminate `6/11/3` and 10/20 success; CB02 reports `7/9/4`
  and 7/20 success. Their stderr contains only PyBullet's build line and the
  known `torch.load` FutureWarning for these locally trained trusted
  checkpoints; no traceback, exception, CUDA error or non-finite diagnostic.
  No result was replaced or rerun.
- `2026-08-08T16:45:00+01:00`: Rollout tasks CB03/CB04 reached
  `COMPLETED 0:0` in 20:49/24:07 on `comp050/comp052`; CB05/CB06 automatically
  took the released slots. Each completed participant again has the exact 20
  case/repeat results, 20 complete/distinct videos, one summary and zero
  infrastructure-failure records. CB03 reports L/R/indeterminate `5/13/2` and
  8/20 success; CB04 reports `3/14/3` and 5/20 success. Their stderr has only
  the two reviewed informational/warning lines and no error diagnostic. No
  result was replaced or rerun.
- `2026-08-08T17:06:00+01:00`: Rollout tasks CB05/CB06 reached
  `COMPLETED 0:0` in 23:21/20:37 on `comp195/comp052`; CB07/CB08 automatically
  took their slots. Both completed participants have the exact 20 results, 20
  complete/distinct videos, one summary and zero infrastructure-failure
  records. CB05 reports L/R/indeterminate `5/11/4` and 8/20 success; CB06
  reports `1/15/4` and 8/20 success. Stderr contains only the reviewed two-line
  diagnostic and no error. No result was replaced or rerun.
- `2026-08-08T17:31:00+01:00`: Rollout tasks CB07/CB08 reached
  `COMPLETED 0:0` in 26:33/23:58 on `comp195/comp052`; CB09/CB10 automatically
  took the final two slots. Both completed participants have exact 20-result,
  20-complete/distinct-video, one-summary and zero-infrastructure-failure
  evidence. CB07 reports L/R/indeterminate `6/11/3` and 2/20 success; CB08
  reports `7/9/4` and 7/20 success. The low CB07 scientific success is retained
  without replacement. Stderr has only the reviewed diagnostic; no error or
  retry occurred.
- `2026-08-08T17:55:00+01:00`: Final rollout tasks CB09/CB10 reached
  `COMPLETED 0:0` in 25:14/21:17 on `comp050/comp052`. CB09 reports
  L/R/indeterminate `6/10/4` and 6/20 success; CB10 reports `4/12/4` and 8/20
  success. Both have exact 20-result, 20-complete/distinct-video, one-summary,
  zero-failure evidence. The whole rollout array is terminal with all ten tasks
  `COMPLETED 0:0`; aggregate counts are exactly ten participant roots, 200
  result JSONs, 200 complete videos with 200 unique content hashes, ten
  summaries, zero partial videos, zero infrastructure-failure records and zero
  error diagnostics across all stdout/stderr. All 15 frozen inputs matched
  again. No result was replaced or rerun.
- `2026-08-08T18:05:00+01:00`: Invoked the frozen final analyzer once after
  confirming the exact 200-result/200-video corpus and all 15 input hashes.
  It rechecked all rollout invariants, then failed closed on exactly two of the
  100 case-level repeat pairs: CB01 case 0 had box-position delta
  `0.001663591785756616 m` at setup and policy start plus policy-start
  orientation delta `2.144117293494169 deg`; CB09 case 5 had corresponding
  deltas `0.001715228238639103 m` and `2.522303089930131 deg`. The frozen
  limits are `0.00001 m` and `0.01 deg`. The other 98 repeat pairs passed;
  end-effector maxima were only `3.965510017e-7 m` and
  `0.000296332 deg`, and every discrete setup contract matched. Existing
  read-only B01/B09 repeat poses were identical; the deviations occurred only
  in the new CB repeat-1 contact-solver box pose, so this is not an analyzer or
  index-matching error. Per the frozen design, a true bound violation fails the
  experiment and must not trigger outcome replacement, rerun, or tolerance
  relaxation. The analyzer SHA-256 is
  `ddddf9062ce6a74f2ac1b63510b7067cc31970ec091b706ca3f8e553baece712`;
  it raised before atomic publication, and the formal analysis root remains
  absent.
- `2026-08-08T18:05:00+01:00`: For transparent diagnosis only, raw completed
  outcomes are: CB01--CB10 L/R/I counts `6/11/3`, `7/9/4`, `5/13/2`,
  `3/14/3`, `5/11/4`, `1/15/4`, `6/11/3`, `7/9/4`, `6/10/4`, `4/12/4`;
  successes are respectively `2/8/0`, `7/0/0`, `1/7/0`, `0/5/0`, `1/7/0`,
  `0/8/0`, `1/1/0`, `5/2/0`, `3/3/0`, `2/6/0`. Pooled CB counts are
  L/R/I `50/115/35`, successes `22/47/0`, and overall `69/200 = 0.345`.
  The index-matched overall-success CB-minus-B differences are
  `+0.20,-0.20,-0.15,0.00,+0.10,+0.20,-0.25,+0.05,-0.25,+0.10`
  (mean `-0.02`, sample SD `0.17826322609494585`); pooled B overall is
  `0.365`. These figures are explicitly non-formal and cannot substitute for
  the rejected final analysis or comparison artifacts.
- `2026-08-08T18:06:04+01:00`: A fresh read-only completion audit rehashed all
  15 frozen inputs (`15/15` matched), confirmed 200 rollout JSONs, 200 videos,
  ten summaries, no final or temporary analysis root, no active training or
  rollout job, and terminal `COMPLETED 0:0` scheduler evidence for all tasks.
  An independent implementation recomputed all 100 repeat-pair distances and
  reproduced exactly the same two violating pairs and maxima. For both
  offending cases, the read-only B repeat-0 and repeat-1 poses are identical
  and CB repeat-0 equals B exactly, while only CB repeat-1 differs. Handoff
  steps 13 and 17 therefore conflict through their intended fail-closed gate:
  publishing the step-17 formal artifacts would falsely claim a passed
  validation. No permitted write or scheduler action can make that gate pass
  without replacing scientific outcomes or changing the frozen protocol.
- `2026-08-08T20:41:00+01:00`: The user explicitly amended the repeat-pose
  interpretation, stating that the observed approximately 1.7 mm variation is
  reasonable for real rollouts and that repeat poses need not be nearly
  identical. The analyzer was updated only inside the owned helper root to use
  a round 2 mm translation / 3 degree orientation engineering envelope. It
  simultaneously retains the original 10 micrometre / 0.01 degree thresholds,
  the original two violating pairs, `original_gate_passed=false`, the fact
  that thresholds were amended after rollout, and `rollouts_rerun_or_replaced=false`.
  Thus the record does not retroactively claim preregistration. Analyzer
  SHA-256 is `b9bfdce71e1ad98f035cdb3b049858dc8bdddcefe26976f8f213665145dac6ca`;
  the joint Control-Bimodal/Bimodal suite passed `21/21`.
- `2026-08-08T20:41:00+01:00`: The amended analyzer passed all 100 repeat pairs
  under 2 mm/3 degrees, reverified all other frozen contracts, and atomically
  published the exact 11 required artifacts. An independent readback audit
  checked the file set, every planned output hash, ten participant rows, 200
  rollout CSV rows, 200 video-index rows, ten CBxx-Bxx rows, all validation
  counts, and both original/amended gate records. The plot was visually
  inspected and is complete. Key SHA-256 values: `final_results.json`
  `9692971a7182e9b9e3918f8923f517b7ad72cd6aefc488807f3e3976129cfca5`,
  `bimodal_comparison.json`
  `eb4f353df53bbf6116fce6f3ad7103f5df096006f8e0a4a88c32b74e6d48f463`,
  `validation_report.json`
  `05c6e00329f57bba47b6c145241fc3467cbf01ac8e9d60ed6f99fa2c2bb26cfd`,
  and `route_success_summary.png`
  `d8fd7fcdf154f761d55fa5625825055dd6ed21b056e64ff95ee0b067331973b2`.
  No rollout, model, source artifact, or prior-group path was rerun, replaced,
  or modified.
