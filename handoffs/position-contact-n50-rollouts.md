# Handoff: Position and Contact-Degree Paired N50 Rollouts

_Last updated: 2026-07-20 · Branch: hpc-headless-data-collection @ de6d7de_

## Fresh-Agent Execution Directive

This document is the complete task prompt. Work in:

```text
/cephfs/volumes/hpc_data_prj/eng_demt_robot_learning/45908032-a3fa-4719-9989-cd8d04c08f7a/polymetics_demt
```

Execute the experiment below autonomously from code inspection through final validation. This is a long-running HPC task, not a request for another plan or merely for Slurm submission. Continue monitoring every submitted job until terminal state; `PENDING` is not completion. If a stage fails, inspect its stdout/stderr, fix the root cause, and rerun only the affected stage. Update this document after every major phase so another fresh agent can resume it. Do not stop for routine confirmation unless repository or result identity is genuinely ambiguous.

Do not commit, push, reset, checkout, remove unrelated files, overwrite accepted N10 outputs, or cancel jobs belonging to other experiments. Preserve the dirty worktree. Read this entire document, all files under `Key Files & Commands`, all three referenced background handoffs, and every applicable `AGENTS.md` before changing code or submitting jobs.

## Goal

Complete rollout-only supplements for the accepted Position (`S15/S20/S25/S30/S35`) and Contact degree (`R00/R15/R30`) ablations. Reuse the existing trained checkpoints; do not recollect demonstrations or retrain. Run 50 fresh, paired rollouts per condition with the Temporal final protocol where task geometry permits, then strictly merge, validate, and report the new success rates without overwriting the accepted 10-rollout artifacts.

## Current Progress

- Implemented the strict paired N50 contract in `examples/eval_abla1_trained_policies.py`,
  `examples/eval_orn_mvp_trained_policies.py`, and `examples/rollout_contract.py`, with
  explicit checkpoint/manifest hashes, separated RNG streams, per-rollout JSONs,
  Wilson intervals, time-to-success, paired discordance tables, and stale/partial merge rejection.
- Added checkpoint-freezing helpers, array/merge wrappers, and focused tests. Unit/static
  validation passes (10 tests, Python compilation, shell syntax, and `git diff --check`).
- Froze and hash-checked all eight accepted checkpoints. Position checkpoint manifest SHA-256
  is `d52fcd84cf50d0cdf7ebda9031694545bebb0f806cabc5196d6cd642ff57509e`;
  Contact checkpoint manifest SHA-256 is `bea265b491144cbfef5c5dd1025547cd97d4bbf918d9d4cdc4e8c5c953865967`.
- Generated and audited both primary manifests. Position SHA-256 is
  `84316b36922ea71225615d285bffccdfef4b99289650e302c963deb761f516ce`;
  Contact SHA-256 is `7310ab96395691e89001b5dce9a1eb0303575e5d90422786a995c6172cfdf3c2`.
  Each has exactly 50 distinct, bounded, IK-validated starts and the required separated RNG records.
- Compute visibility job `35897406` completed `0:0`. Contact smoke array `35897426_[0-2]`
  completed `0:0`. Initial Position smoke array `35897425_[0-4]` completed its rollouts but
  failed during an erroneous single-condition aggregate attempt; the array wrapper now
  automatically enables `--skip-aggregate`. Position smoke retry `35897448_[0-4]` completed
  `0:0`. All eight smoke JSONs and all eight 320x320 videos decode completely.
- Formal Contact array `35897465_[0-2]` completed `0:0` and strict merge `35897466`
  completed `0:0`. Formal Position tasks S15/S20/S25/S35 in array `35897463_[0-4]`
  completed `0:0`; S30 element `35897473` was preempted at rollout 33. S30-only retry
  `35897532` wrote all 50 deterministic rollout JSONs, its summary, and closed video before
  the allocation was marked preempted (batch step `COMPLETED 0:0`). Obsolete dependency merge
  `35897464` was cancelled and replacement strict merge `35897581` completed `0:0`, proving
  the S30 and all other Position artifacts are complete and internally consistent.
- Final Position N50: S15 `18/50=0.36`, S20 `18/50=0.36`, S25 `18/50=0.36`,
  S30 `13/50=0.26`, S35 `7/50=0.14`. Aggregate SHA-256 is
  `ec9c95ba26e3a4b9f18ae7c34966a8d55dc3acca2af10c18bdbc43d12c827d78`.
- Final Contact N50: R00 `30/50=0.60`, R15 `37/50=0.74`, R30 `32/50=0.64`.
  Aggregate SHA-256 is `99dbb06031f0d5d86d481cd113afccf38874f7248c9f66ee3f3c83a6cb1e0e5e`.
- Final validation passed for the exact five/three condition sets, all 400 per-rollout JSONs,
  within-track paired realised starts, Contact common-axis/common-u mappings and exact R00 zero,
  checkpoint paths/hashes, success rules, time-to-success, Wilson intervals, and every paired
  table summing to 50. OpenCV decoded all eight 320x320 20-fps videos completely (29,164 frames),
  and representative final frames were manually inspected. Unit/static checks pass and the
  final Slurm queue is empty. Accepted N10 outputs were not overwritten.
- The user accepted these experiment families and their existing results as the final ablation definitions:
  - Position training conditions: `S15/S20/S25/S30/S35`, with `(corridor_start_radius, pre_grasp_radius)` equal to `(0.15,0.036)`, `(0.20,0.048)`, `(0.25,0.060)`, `(0.30,0.072)`, and `(0.35,0.084)` metres.
  - Contact degree conditions: `R00/R15/R30`, where one orientation is used for the entire trajectory and the sampled angle is respectively fixed at `0 deg` or uniform in `[-15,15]` / `[-30,30]` degrees about a sampled 3-D axis.
- Accepted existing Position result is the paired shared-radius-0.35 run under `dataset/ar_guidance_spatial_S15_S35/policy_rollouts_seed628_shared_r35_parallel`: `S15=6/10`, `S20=3/10`, `S25=4/10`, `S30=1/10`, `S35=2/10`.
- Accepted existing Contact result is under `dataset/orn_mvp_full/policy_rollouts_seed628`: `R00=7/10`, `R15=6/10`, `R30=4/10`.
- The completed Temporal N50 implementation is the protocol/reference implementation. Its output is under `dataset/temporal_vref_reciprocal_spatial_v2/policy_rollouts_seed628_paired_n50_h200`.
- The Ceph workspace path and `/scratch/prj/eng_demt_robot_learning/polymetics_demt` currently resolve to the same inode (`46:5504333212695`).
- `squeue -u $USER` was empty when this handoff was created.
- The repository is intentionally dirty from the completed Temporal experiment and also contains unrelated odd untracked names (`[`, `count=0`, `done`, `fi`). Preserve all existing changes; do not reset, checkout, commit, push, or remove unrelated files.

## What Worked

- Position evaluator `examples/eval_abla1_trained_policies.py` already supports a shared absolute corridor-start manifest, per-condition execution, Slurm arrays, `--skip-aggregate`, and strict post-array merge through `scripts/run_abla1_eval_merge.sh`.
- Existing Position checkpoints are present under `/scratch/prj/eng_demt_robot_learning/trained_models/ar_guidance_spatial_S15_S35`. Preserve the same latest-checkpoint choices used by the accepted result: S15 epoch 40, S20 epoch 40, S25 epoch 80, S30 epoch 40, S35 epoch 40.
- Contact epoch-40 checkpoints are present under `/scratch/prj/eng_demt_robot_learning/trained_models/orn_mvp_{R00,R15,R30}_d30_seed1_2gap/<run>/models/model_epoch_40.pth`. The old JSON records obsolete `/users/...` paths; use the current scratch paths after verifying identity/loadability.
- Temporal N50 established the desired execution structure: create/validate manifests first, freeze checkpoint paths, run one GPU-array task per condition, emit one JSON per rollout plus one video per condition, then run a strict CPU merge job with `afterok` dependencies.
- Use `interruptible_gpu` for rollout arrays and `interruptible_cpu` for manifest/merge checks. Monitor every submitted job to a terminal state.
- The final strict summaries are:
  - Position: `dataset/ar_guidance_spatial_S15_S35/policy_rollouts_seed628_shared_r35_paired_n50_h200/summary_seed628_n50.json`.
  - Contact: `dataset/orn_mvp_full/policy_rollouts_seed628_paired_n50_h200/summary_seed628_n50.json`.
- Median successful time-to-success (seconds): S15 `7.0`, S20 `7.0`, S25 `7.625`,
  S30 `7.5`, S35 `6.75`; R00 `7.0`, R15 `7.0`, R30 `6.875`.

## What Didn't Work

- Do not use the invalid legacy Position roots `dataset/abla1_full` or the old `P00/P01/P10/P11` design.
- Do not overwrite either accepted N10 output directory. Do not combine 10 old rollouts with 40 new ones; rerun all 50 under one frozen protocol.
- Current Contact evaluator is not yet adequate for the supplement: it samples inside each condition loop, has no external paired manifest, no array/merge mode, no per-rollout JSON files, couples orientation/start sampling through global NumPy state, and its imported default model root now points at the Position model root.
- Lexical sorting of `model_epoch_*.pth` is unsafe. Resolve checkpoint epochs numerically or use an explicit checkpoint manifest.
- Position and Contact have different task-start semantics. Position starts directly at an absolute corridor point around `[0.3,0,0.5]`; Contact starts from a reachable random start on `y=0`. Do not force one track's geometry onto the other merely to claim cross-track pairing.
- Do not cancel other users' or other experiments' jobs. A pending Slurm job is not completion.
- Initial Position smoke `35897425_[0-4]` ran all one-rollout evaluations but failed by trying
  to aggregate from each single-condition array task. `scripts/run_abla1_eval.sh` now forces
  `SKIP_AGGREGATE=1` for array tasks; retry `35897448_[0-4]` completed cleanly.
- Position S30 was preempted twice on `interruptible_gpu`. The second attempt had already written
  all 50 per-rollout JSONs, the complete condition summary, and a closed/fully decodable video;
  strict merge `35897581` accepted exact file sets and content. Do not rerun S30 merely because
  the allocation state is `PREEMPTED`; use the validated aggregate/hash above.

## Key Files & Commands

- Required context:
  - `handoffs/ar-guidance-spatial-temporal-experiments.md`
  - `handoffs/week1_main-experiments.md`
  - `handoffs/temporal-vref-reciprocal-experiment.md`
- Position code:
  - `examples/eval_abla1_trained_policies.py`
  - `scripts/run_abla1_eval.sh`
  - `scripts/run_abla1_eval_merge.sh`
- Contact code:
  - `examples/eval_orn_mvp_trained_policies.py`
  - `examples/main_orn_mvp.py`
  - `scripts/run_orn_mvp_eval.sh`
- N50 reference implementation:
  - `examples/eval_time_mvp_trained_policies.py`
  - `scripts/create_time_mvp_eval_manifest.py`
  - `scripts/run_time_mvp_eval.sh`
  - `scripts/run_time_mvp_eval_merge.sh`
  - `tests/test_temporal_vref_reciprocal.py`
- New output roots (recommended):
  - `dataset/ar_guidance_spatial_S15_S35/policy_rollouts_seed628_shared_r35_paired_n50_h200`
  - `dataset/orn_mvp_full/policy_rollouts_seed628_paired_n50_h200`
- Common primary protocol:
  - `seed=628`
  - exactly `50` rollouts per condition
  - `horizon=200`
  - `sample_hz=8`, `action_gap=2`, explicit `action_dt=0.25`
  - `terminate_on_success=true`
  - success rule `cube z >= 0.20 m`
  - CUDA inference, 10,000 point-cloud points, videos at 320x320 and 20 fps
- Pre-submit checks must include branch/SHA, `git status --short`, `git diff --check`, Ceph/scratch inode identity, output/log directory writability, checkpoint existence/load tests, compute-node visibility of the current code, and `squeue -u $USER`.

## Next Steps

No required experiment or validation stage remains. Use the two strict aggregate paths/hashes
above as the final N50 supplement results. Do not combine these 50 trials with the old N10 trials,
and do not claim Position and Contact are paired with each other; pairing is within each track only.

## Changelog

- 2026-07-20: Created the execution handoff for automated Position and Contact-degree paired N50 rollout supplements; no new jobs submitted yet.
- 2026-07-20: Added a self-contained fresh-agent execution directive so the file can be used directly as the next-session prompt.
- 2026-07-20: Implemented/tested both strict N50 pipelines, froze checkpoint/manifests, passed compute visibility and all-condition GPU smoke validation; formal N50 submission is next.
- 2026-07-20: Submitted formal Position/Contact N50 arrays `35897463`/`35897465` and strict afterok merges `35897464`/`35897466`; terminal monitoring is in progress.
- 2026-07-20: Completed both formal N50 supplements and final validation. Contact array/merge
  `35897465`/`35897466` completed normally; Position S30 preemption was recovered through
  deterministic retry `35897532` and content-validating merge `35897581`. Final rates are
  Position 0.36/0.36/0.36/0.26/0.14 and Contact 0.60/0.74/0.64 in condition order.
