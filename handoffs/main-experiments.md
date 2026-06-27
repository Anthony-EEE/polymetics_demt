# Handoff: Main Experiments

_Last updated: 2026-06-27 · Branch: hpc-headless-data-collection @ d933a1d_

## Goal
Prepare and implement short-term CoRL rebuttal experiments for the DEMT paper, focusing first on a spatial corridor ablation that explains how DEMT's `P/R/V` formulation is translated into concrete AR guidance parameters. The immediate next task is to modify the simulation data generator later, but this handoff records planning only; code changes for the ablation have not been made yet.

## Current Progress
- Reviewed the submitted paper PDF: `DEMT__Deployment_Evaluated_Machine_Teaching_Enhances_Learning_from_Human_Demonstrations.pdf`.
- Main interpretation: the paper defines ideal `z* = arg max J(A(D^z)), z in Z = P x R x V`, but submitted experiments only evaluate a finite set `C = {z0, zP, zR, zV}`. The likely CoRL reviewer concern is that the transition from DEMT formula to concrete AR guidance parameters is abrupt.
- Wrote rebuttal planning docs:
  - `docs/corl-rebuttal-ablation-plan.md`
  - `docs/corl-rebuttal-ablation-plan-cn.md`
  - `docs/ablation-1.md`
- `docs/corl-rebuttal-ablation-plan*.md` frame the short-term plan: add deployment-evaluated finite candidate ablations for `P/R/V`, while leaving larger participant/LIBERO/ACT/VLA/more-real-tasks work for the journal version.
- `docs/ablation-1.md` is the current source of truth for Spatial Structure / Corridor Geometry planning.
- Reviewed `examples/main.py`, `examples/main_insert.py`, and `examples/collection_io.py`.
- Confirmed `examples/main.py` implements PyBullet Panda cube grasp-and-lift through `PandaSim(DatasetCollectorMixin)`.
- Confirmed `examples/main_insert.py` implements peg insertion through `PandaPegInsertSim(DatasetCollectorMixin)`.
- Confirmed both current scripts use a fixed scripted home target, not the paper's random EE initial condition:
  - `examples/main.py`: `home = np.array([0.45, 0.00, 0.45])`
  - `examples/main_insert.py`: `home = np.array([0.45, 0.00, 0.45])`
- Confirmed successful cube demos currently run through `run_pick_and_lift()` with these saved/non-saved phases:
  - `home`: executed but not saved by `move_ee()` because it skips saving when `phase_name == "home"`.
  - `open_gripper`
  - `pick_approach`
  - `pick_grasp`
  - `close_gripper`
  - `lift`
- Confirmed current cube approach noise is injected only into the successful rollout's `pre_grasp` target:
  - `base_pre_grasp = np.array([cube[0], cube[1], 0.22])`
  - `pre_grasp = base_pre_grasp + approach_offset`
  - `pre_grasp` is then used only for `phase_name="pick_approach"`.
- Confirmed later cube targets are not offset:
  - `grasp = np.array([cube[0], cube[1], 0.04])`
  - `lift = np.array([cube[0], cube[1], 0.30])`
- Confirmed current `examples/main.py` CLI supports only a single approach-noise radius around `pre_grasp`; this is not enough for the planned corridor ablation.
- Confirmed `examples/main_insert.py` has no approach-noise/corridor-noise CLI yet.
- Confirmed per-frame saved files under `output_dir/demo_<idx>/frame_<idx>/` are:
  - `point_cloud.ply`
  - `arm_joints.txt`
  - `hand_joints.txt`
  - `ee_pose.txt`
  - `time.txt`
  - `commanded_speed.txt`
  - `commanded_dt.txt`
  - `phase.txt`
  - `cube_pose.txt` when `cube_id` exists
- No ablation implementation code changes have been made yet.

## What Worked
- The strongest short-term rebuttal strategy is to avoid claiming full global `z*`; instead, add deployment-evaluated finite candidate selection over practical guidance parameters.
- For Spatial Structure, the user clarified that the corridor is a curved/funnel-like AR structure, not a single radius:
  - wide entry on the left,
  - narrowing toward an object-above `pre_grasp` bend,
  - then descending tightly toward the target/contact region.
- The Spatial ablation should separate two variables:
  - `corridor_start_radius`: radius/spread at the wide corridor entry.
  - `pre_grasp_radius`: radius/spread at the bend/throat near object-above `pre_grasp`.
- Critical clarification: random EE initial pose and corridor entry are not the same.
  - Random EE initial pose is the demonstration start state.
  - `corridor_start` is the entry region of the guidance corridor that the trajectory moves into after starting.
- User specified random EE initial pose should be sampled on the reachable part of the `y = 0` x-z plane, with `x > 0` and `z > 0`; it must pass IK/reachability checks.
- User suggested, and the plan now adopts, an object-relative corridor entry center:
  ```text
  base_corridor_start = [target_x - d_entry, target_y, pre_grasp_z + h_entry]
  ```
- For cube pick-and-lift, the planned concrete entry center is:
  ```text
  target_x = cube_x
  target_y = cube_y
  pre_grasp_z = 0.22
  d_entry = 0.20 m
  h_entry = 0.05-0.08 m
  base_corridor_start = [cube_x - 0.20, cube_y, 0.27-0.30]
  ```
- For the first Spatial ablation, keep `d_entry` and `h_entry` fixed and only ablate `corridor_start_radius` and `pre_grasp_radius`.
- The planned first implementation should use x-z plane variation for `corridor_start` and `pre_grasp`, with `y` fixed:
  ```text
  delta_start = [dx, 0, dz]
  delta_pre = [dx, 0, dz]
  ```
- Recommended first design in `docs/ablation-1.md`: a minimal 2 x 2 factorial:
  - small `corridor_start_radius`, small `pre_grasp_radius`
  - large `corridor_start_radius`, small `pre_grasp_radius`
  - small `corridor_start_radius`, large `pre_grasp_radius`
  - large `corridor_start_radius`, large `pre_grasp_radius`
- Suggested initial numeric levels:
  - small `corridor_start_radius = 0.10 m`
  - large `corridor_start_radius = 0.25 m`
  - small `pre_grasp_radius = 0.02 m`
  - large `pre_grasp_radius = 0.06 m`
- Recommended first task: cube pick-and-lift only. Add insert-only later only if cube ablation is stable.

## What Didn't Work
- Initial sandboxed shell commands repeatedly failed with `bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted`; read/write commands were rerun with escalation and succeeded.
- `apply_patch` also failed once due to the same sandbox helper issue; narrow Python replacements were used to update markdown documents after explicit escalation.
- The old single `--approach-noise-radius` plan is insufficient for the actual corridor, because it only changes `pre_grasp` and does not model the wide entry of the curved/funnel corridor.
- The earlier draft described some variation as XY/XYZ; this has been corrected in `docs/ablation-1.md` to x-z plane variation with `y = 0` fixed.
- No simulation runs, random-start reachability checks, policy trainings, or deployment evaluations have been performed yet for the ablation.

## Key Files & Commands
- Main planning docs:
  - `docs/ablation-1.md`: detailed Spatial Structure / Corridor Geometry plan.
  - `docs/corl-rebuttal-ablation-plan.md`: English rebuttal ablation overview.
  - `docs/corl-rebuttal-ablation-plan-cn.md`: Chinese rebuttal ablation overview.
- Paper PDF:
  - `DEMT__Deployment_Evaluated_Machine_Teaching_Enhances_Learning_from_Human_Demonstrations.pdf`
- Main code files to modify later:
  - `examples/main.py`: cube pick-and-lift data generation.
  - `examples/main_insert.py`: peg insertion data generation.
  - `examples/collection_io.py`: frame/data writer; likely no change needed unless metadata/manifests need extension.
- Important current code locations:
  - `examples/main.py`: `PandaSim.run_pick_and_lift()`
  - `examples/main.py`: `build_approach_offsets()`
  - `examples/main.py`: CLI args for `--approach-noise-mode`, `--approach-noise-radius`, `--approach-grid-size`
  - `examples/main_insert.py`: `PandaPegInsertSim.run_insert_only()`
  - `examples/main_insert.py`: `PandaPegInsertSim.run_peg_insertion()`
  - `examples/main_insert.py`: `PandaPegInsertSim.pre_insert_pos()`
- Existing example cube collection command:
  ```bash
  python examples/main.py \
    --no-gui \
    --output-dir /tmp/panda_main_xz_uniform \
    --num-demos 10 \
    --sample-hz 30 \
    --approach-noise-mode xz_uniform \
    --approach-noise-radius 0.03
  ```
- Useful inspection commands after future generation:
  ```bash
  find /tmp/panda_main_xz_uniform -maxdepth 3 -type f | sort | head -80
  cat /tmp/panda_main_xz_uniform/demo_0/metadata.json
  find /tmp/panda_main_xz_uniform/demo_0 -name phase.txt -print -exec cat {} \;
  ```

## Next Steps
1. Start the new conversation by reading `docs/ablation-1.md` first; it contains the current agreed Spatial ablation design.
2. Before editing, inspect current `examples/main.py` around `run_pick_and_lift()`, `build_approach_offsets()`, and CLI parsing.
3. Implement random EE initialization for cube pick-and-lift:
   - sample from reachable `y = 0`, `x > 0`, `z > 0` x-z plane;
   - use IK/reachability filtering;
   - keep random initial EE pose separate from `corridor_start` in metadata.
4. Replace or extend the current single `approach_offset` system with corridor sampling:
   - object-relative `base_corridor_start = [target_x - d_entry, target_y, pre_grasp_z + h_entry]`;
   - sampled `corridor_start = base_corridor_start + [dx, 0, dz]`;
   - sampled `pre_grasp = base_pre_grasp + [dx, 0, dz]`;
   - fixed `grasp` and `lift` for the first version.
5. Add metadata for every demo:
   - random initial EE pose;
   - `base_corridor_start`;
   - sampled `corridor_start`;
   - `corridor_start_radius` and sampled delta;
   - `base_pre_grasp`;
   - sampled `pre_grasp`;
   - `pre_grasp_radius` and sampled delta;
   - condition label, success details, and attempt/rejection information.
6. Keep the first implementation cube-only and run smoke tests before touching insertion.
7. Smoke test each 2 x 2 condition with a few demos; inspect metadata, phase labels, frame counts, point clouds, and success rates.
8. Decide whether failed sampled trajectories should be preserved or at least counted in metadata; do not silently retry until success without recording rejected samples.
9. Only after stable cube generation, consider adding insert-only validation using `run_insert_only()` with similar corridor logic around `pre_insert`.

## Open Questions
- Exact reachable bounds for random initial EE sampling on the `y = 0`, `x > 0`, `z > 0` x-z plane.
- Whether random initial EE placement should be saved as part of the recorded trajectory or treated as setup. Current preference: record from random initial pose so fixed `home` does not dominate the dataset.
- Exact `h_entry` for cube: choose one fixed value in `0.05-0.08 m`, likely `0.06 m` unless smoke tests suggest otherwise.
- Exact sampling distribution inside the x-z radius: uniform disk, grid, or uniform square clipped to disk.
- Whether `corridor_start` should always use `target_y` even when target object `y` differs from 0; current plan says yes, object-relative `target_y`.
- Whether the final descent/grasp should remain fully fixed or allow a very small fixed final tolerance matching object size.
- Whether to add a compact manifest/CSV summarizing each demo's condition, sampled points, attempt count, phase counts, frame count, and success state.

## Changelog
- 2026-06-27: Created handoff for detailed `examples/main.py` experiments and documented phase/data/noise behavior.
- 2026-06-27: Updated handoff with DEMT paper/rebuttal context, created planning docs, and recorded agreed Spatial corridor ablation design with random EE initialization on the reachable `y = 0` x-z plane.
