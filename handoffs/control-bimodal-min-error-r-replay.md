# Handoff: Control-Bimodal Minimum-Error R Replay

_Last updated: 2026-08-09 · Branch: `hpc-headless-rebuttal` @ `72ca390`_

## Goal

Deliver one non-random Control-Bimodal successful realised-R trajectory: select
the formal R success with minimum target error, convert its EE motion to the
user's left-handed workspace (`y≈0 → y≈-0.5`), replay it slowly in PyBullet,
and record actual Panda joints plus gripper command/width in the user's
`./intervention.csv` schema.

## Current Progress

The requested CSV is complete and independently validated:

- Active file: `control_bimodal_replay/min_error_R/R/intervention.csv`.
- Selection: `CB10`, eval case `07`, repeat `1`; this is rank 1 of 47 formal
  successful realised-R rows in
  `rebuttal_dataset/simulation_control_bimodal_group/analysis/rollout_results.csv`.
- Formal result:
  `rebuttal_dataset/simulation_control_bimodal_group/policy_rollouts/CB10/rollouts/rollout_case_07_repeat_1.json`.
- Formal target error: `0.004982182621892239 m`.
- CSV SHA-256:
  `b13bd4bd83b743deebdfacdf0feea46e5dc81708f5cdfa6a898bddb67a1c3683`.
- CSV: 1325 rows at nominal 30 Hz, 44.120833 s, schema `t,dt,step,state_seq,control_mode,drive_mode,gripper_cmd,gripper_width,q0..q6`.
- Independent FK with Panda base `[0,-0.15,0]`: EE y starts at
  `-0.0042269 m`, ends at `-0.5039285 m`, and ranges from `-0.5134741` to
  `-0.0028654 m`.
- Gripper command range is `[-1,+1]`; measured two-finger width range is
  `[0.0081897,0.07999997] m`.
- Recorded maximum implied joint velocity is `0.33393 rad/s`.
- Mirrored PyBullet outcome: target error `0.00999374 m`, zero box-cylinder
  contacts, zero robot-cylinder contacts, and final cylinder tilt
  `8.71e-6 degrees`.
- Full provenance is in `control_bimodal_replay/min_error_R/manifest.json` and
  `control_bimodal_replay/min_error_R/R/reproduction.json`; usage notes are in
  `control_bimodal_replay/min_error_R/README.md`.
- Relevant test suite passes: 18 tests.

The final construction is not an exact recovery of the formal policy's joint
trajectory. Formal rollout JSON stores EE positions and gripper state but not
per-step joints or EE quaternions. The exporter reflects the formal EE
positions, reflects the formal policy-start quaternion with
`R' = S R S, S=diag(1,-1,1)`, holds that orientation, resolves sequential IK,
and records the resulting PyBullet joints/gripper. A documented post-obstacle
clearance corridor holds `x>=0.70 m` and `z>=0.18 m` before blending to the
formal target after `y=-0.48 m`; this eliminated Panda link-4 contact.

Useful L/R context from the formal analyses:

- Control-Bimodal realised-route success: L `22/50 = 44.0%`; R
  `47/115 = 40.87%`; indeterminate `0/35`. Thus R has the lower
  route-conditional success rate despite more R successes in absolute count.
- Target-derived Bimodal: L `20/44 = 45.45%`; R `53/115 = 46.09%`.
- Formal rollout camera is fixed, not route-dependent. Eye is
  `[-0.35,0.25,0.70]`, target is `[0.48,0.25,0.05]`. Because L/R is defined by
  x relative to the cylinder (`x<0.5` is L), the camera is physically on the L
  side and L is closer to it; rendered apparent left/right can be confusing.

## What Worked

- Numeric sorting of all formal successful realised-R rows selected the fixed
  minimum-error result with deterministic ID tie-breaking; no random fallback
  was used.
- Reconstructing from the immutable formal successful EE trace avoided a new
  diffusion-policy sample while preserving the selected route and endpoint.
- Reflecting both position and orientation for the left-handed frame was more
  geometrically consistent than changing y alone.
- Dense sequential IK plus actual PyBullet replay produced a smooth 44 s joint
  record. Minimum 30 subdivisions per formal transition, adaptive subdivision
  up to 480, planned joint step cap `0.015 rad`, and arm max-velocity argument
  `0.30 rad/s` were used.
- A post-obstacle x/z corridor and a smooth Panda null-space IK-rest blend
  eliminated both box and robot contact with the cylinder.
- Failed/unsafe attempts were retained under
  `control_bimodal_replay/diagnostics/`; the final active directory contains
  only the accepted result and documentation.

## What Didn't Work

- `examples/rebuttal_control_bimodal_pipeline/export_min_error_r_replay.py`
  attempted direct policy re-execution. Slurm job `36425619` reran the same
  CB10/case07/repeat1 three times; every fresh run remained R but timed out at
  200 policy steps with target error `0.6615767 m`, instead of reproducing the
  formal 18-step success. It correctly refused to fall back to another case.
- Emulating the formal evaluator's persistent simulator history also failed.
  Slurm job `36425775` matched case00/repeat0 but case00/repeat1 reproduced R
  instead of the formal indeterminate route. Cross-job policy re-execution is
  therefore not an authoritative way to recover the formal joint trajectory.
- Mirroring only EE y while keeping the world quaternion unchanged reached the
  target but caused Panda link 4 to topple the cylinder.
- Reflecting orientation and adding only a null-space bias kept the cylinder
  upright but still produced sustained link-4 contact.
- Initial x-only clearance corridors moved contact later in the motion but did
  not remove it. The accepted x+z corridor was required.

## Key Files & Commands

- Accepted exporter:
  `examples/rebuttal_control_bimodal_pipeline/export_min_error_r_trace_replay.py`
- Direct policy exporter retained for diagnostics:
  `examples/rebuttal_control_bimodal_pipeline/export_min_error_r_replay.py`
- Slurm wrapper for the direct exporter:
  `examples/rebuttal_control_bimodal_pipeline/export_min_error_r_replay.sbatch`
- Generic joint recorder:
  `examples/rebuttal_bimodal_pipeline/export_success_replays.py`
- Generic y-mirror utility used for the earlier Target L/R files:
  `examples/rebuttal_bimodal_pipeline/mirror_intervention_y.py`
- Control-specific tests:
  `tests/test_control_bimodal_min_error_r_replay.py`

Replay using the user's existing workflow:

```bash
cd control_bimodal_replay/min_error_R/R
# The user's existing replay command reads ./intervention.csv here.
```

Regenerate only into a new directory; the exporter intentionally refuses to
overwrite an existing result:

```bash
PYTHONDONTWRITEBYTECODE=1 \
  /scratch/users/k23114984/conda/arcap/bin/python \
  examples/rebuttal_control_bimodal_pipeline/export_min_error_r_trace_replay.py \
  --output-root control_bimodal_replay/regeneration_check
```

Run the relevant regression suite:

```bash
PYTHONDONTWRITEBYTECODE=1 \
  /scratch/users/k23114984/conda/arcap/bin/python -m pytest -q \
  tests/test_control_bimodal_min_error_r_replay.py \
  tests/test_mirror_intervention_y.py \
  tests/test_bimodal_success_replay_export.py \
  tests/test_rebuttal_control_bimodal_pipeline.py
```

## Next Steps

1. On the real robot, confirm that its left-handed frame/base convention
   corresponds to the PyBullet base assumption `[0,-0.15,0]`; do not infer a
   physical base relocation solely from the coordinate sign convention.
2. Replay `./intervention.csv` first at reduced speed with collision monitoring
   and an accessible stop; verify the initial arm configuration before enabling
   the full motion.
3. Confirm real gripper command sign and width calibration (`-1=open`,
   `+1=closed`, recorded width is the sum of both simulated finger joints).
4. If exact formal-policy arm joints or orientations are required, rerun the
   entire formal evaluator from case00 while instrumenting it to record joints
   in the original execution, rather than attempting a standalone stochastic
   re-execution of case07.

## Open Questions

- The real robot has not yet replayed this CSV, so hardware frame alignment,
  joint limits, gripper calibration, and physical clearance remain to be
  validated by the user.
- Confirm whether the user's replay consumer honors the final shorter `dt`
  sample (`0.0208333 s`); all other post-initial samples are nominally
  `1/30 s`. The timestamps are strictly increasing and internally consistent.

## Changelog

- 2026-08-09: Created the handoff with the accepted minimum-error Control-Bimodal R replay, left-handed transform, validation evidence, failed approaches, L/R statistics, and camera geometry.
