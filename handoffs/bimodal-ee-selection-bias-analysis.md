# Handoff: Bimodal Route-Conditioned Collection Bias and EE Workspace Figures

_Last updated: 2026-08-09 · Branch: `hpc-headless-rebuttal` @ `72ca390`_

## Goal

Assess whether route-dependent IK/collection failures made the effective Left
and Right training data asymmetric in the completed Target-derived Bimodal
(`B01`–`B10`) and Control-derived Bimodal (`CB01`–`CB10`) experiments, and
produce readable EE-workspace trajectory figures for all twenty policies.

## Current Progress

- The formal retained trajectory counts are balanced: every source participant
  has 30 successful demonstrations, every B/CB dataset has exactly 30 L + 30 R,
  and every train mask has 27 L + 27 R.
- The collection process is not route-symmetric. Counts from the immutable
  formal attempt JSONs are:

| Source group | Route | Accepted | Attempts | Failed | Acceptance | Explicit IK/reachability failures |
|---|---:|---:|---:|---:|---:|---:|
| Target | L | 150 | 163 | 13 | 92.0% | 6 |
| Target | R | 150 | 170 | 20 | 88.2% | 13 |
| Control | L | 150 | 169 | 19 | 88.8% | 12 |
| Control | R | 150 | 218 | 68 | 68.8% | 50 |

- Here `explicit IK/reachability` is the sum of
  `middle_waypoint_reachability` and `unreachable_waypoint`. Under the stored
  route contract, smaller x is L and larger x is R. If judging left/right from
  the rendered camera view, the apparent direction may be reversed.
- Control's attempted proposal was nearly mirror-symmetric in x (L mean
  `0.2008`, R mean `0.7993`), but the retained successful waypoint means were
  L `0.204516` and R `0.778494`. Rejected Control-R waypoints had mean x
  `0.8451`; retained Control-R ended at x `0.862120` despite the proposal
  extending to `0.90`. This is direct evidence of success/IK-conditioned
  support truncation, strongest on Control-R.
- Accepted retries also differ by route: Target L/R have 13/18 retained demos
  with `attempt_index>0`; Control L/R have 17/47. Thus the final count balance
  does not preserve exact route-matched start/proposal draws.
- Summing HDF5 `num_samples` over the ten duplicated B/CB memberships gives a
  smaller sequence-level imbalance despite trajectory-level balance:
  - Target-Bimodal train: L `12,374` (50.932%), R `11,921` (49.068%).
  - Control-Bimodal train: L `12,455` (51.726%), R `11,624` (48.274%).
  These membership totals include intentional source reuse and are not counts
  of independent demonstrations.
- Interpretation frozen for continuation: call this a **route-dependent
  feasibility/selection bias in the effective retained distribution**, not an
  L/R trajectory-count imbalance. The much higher Control failure burden is
  real, but it is on stored route R rather than L.
- This bias is a plausible performance confound but is not proven to cause the
  rollout route preference. Target-Bimodal and Control-Bimodal both realised
  exactly 115 R routes out of 200; Control's R-conditional success was 40.9%
  versus Target's 46.1%.
- Final static figures are under `bimodal_ee_workspace_figures/`. Four overview
  PNGs are 2565×3895, and `per_participant/` contains 20 individual XY+XZ PNGs.
  All four overviews plus `CB07`'s individual figure were visually inspected.
  Each panel shows 30 retained L and 30 retained R demonstrations with fixed
  cross-panel axes. These are successful teaching EE trajectories, not failed
  attempts and not learned-policy rollouts.
- The displayed curves use at most 32 evenly spaced points per raw trajectory,
  extracted from the original frame-level `ee_pose.txt` files. Downsampling is
  visualization-only and does not alter any dataset or experiment artifact.
- No Target, Control, Bimodal, model, rollout, or sealed analysis artifact was
  modified. The repository already had a highly dirty worktree; do not clean or
  revert unrelated files.

## What Worked

- Separating retained-count balance from proposal/acceptance balance exposed
  the actual issue: Control-R required 218 attempts for 150 successes, while
  Control-L required 169.
- Reading every formal attempt JSON and classifying explicit reachability
  stages avoided inferring IK failure from videos or successful HDF5 payloads.
- Comparing attempted, rejected, and accepted waypoint x values demonstrated
  that the originally symmetric Control proposal became asymmetric only after
  feasibility/success conditioning.
- Static, high-resolution PNG small multiples are readable locally. Blue is L,
  orange is R, gray is the obstacle, and green marks the target/release context.

## What Didn't Work

- The first deliverable was an interactive HTML fragment under `.codex/`.
  The user reported that it was hard to access and visually disordered in local
  Chrome. Treat it as superseded; use the PNG directory instead.
- The first static export also attempted PDF output and was terminated while
  writing the first PDF, leaving a partial temporary directory. That directory
  was moved out of the repository to `/tmp/failed_bimodal_ee_workspace_figures_530482`.
  The successful rerun generated PNG only.
- The durable PNG directory does not yet contain a permanent plotting source.
  The current generator is ephemeral at `/tmp/export_bimodal_ee_pngs.py` and
  reads the cached, downsampled trajectory JSON from the superseded inline HTML.
  Do not claim the figure generation is fully repo-reproducible until a clean
  owned script reads the manifests/raw `ee_pose.txt` inputs directly.
- The current trajectory figures show only retained successes. They make the
  effective path geometry visible but do not themselves show rejected IK
  candidates; an attempted/accepted/rejected waypoint plot is still needed for
  a direct visual of selection bias.

## Key Files & Commands

- Figure guide: `bimodal_ee_workspace_figures/README.md`.
- Target XY overview:
  `bimodal_ee_workspace_figures/target_bimodal_ee_workspace_xy.png`
  (SHA-256 `7d415de9e03e8c09be6be06caea1c7140986c6957afb4981abcdacff131e2bf5`).
- Target XZ overview:
  `bimodal_ee_workspace_figures/target_bimodal_ee_workspace_xz.png`
  (SHA-256 `cd56bc6ed81c3446a5f6a16b61320b9d97ab4bc4967c8b24b80b110044452c11`).
- Control XY overview:
  `bimodal_ee_workspace_figures/control_bimodal_ee_workspace_xy.png`
  (SHA-256 `1c65dc9723c8a0d48343e103f1555a69b97984b5eeea99cf6ec076f09ba43ddb`).
- Control XZ overview:
  `bimodal_ee_workspace_figures/control_bimodal_ee_workspace_xz.png`
  (SHA-256 `c656beca5f76df4b6d268406bff775dac799bafc96d786d96a398014ad5845c6`).
- Individual figures:
  `bimodal_ee_workspace_figures/per_participant/{B01..B10,CB01..CB10}_ee_workspace_xy_xz.png`.
- Formal source roots:
  - `rebuttal_dataset/simulation_target_group/full_seed20260806/protocol_release_z008_target_tol010_start_replenish/`
  - `rebuttal_dataset/simulation_control_group/full_seed20260806/protocol_release_z008_target_tol010_start_replenish/`
- Bimodal mixture manifests:
  - `rebuttal_dataset/simulation_bimodal_group/mixed_raw/B01/mixture_manifest.json`
  - `rebuttal_dataset/simulation_control_bimodal_group/mixed_raw/CB01/mixture_manifest.json`
  with the same pattern through `B10`/`CB10`.
- IK gates are implemented in `examples/main_obstacle_transport.py` around
  `scripted_grasp_to_transport_start()` and the middle-waypoint reachability
  check.
- Control's already-recorded accepted-spread issue is documented in
  `agents_working/control-simulation.md` and
  `rebuttal_dataset/simulation_control_group/full_seed20260806/protocol_release_z008_target_tol010_start_replenish/diagnostics/validation_report_accepted_spread_gate_misapplied_v2.json`.

Read-only verification commands:

```bash
file bimodal_ee_workspace_figures/*.png
find bimodal_ee_workspace_figures/per_participant -type f -name '*.png' | wc -l
sha256sum bimodal_ee_workspace_figures/*.png
```

## Next Steps

1. Add a permanent, group-neutral analysis script in a newly agreed writable
   location. It should read the immutable raw attempt JSONs and successful
   frame-level `ee_pose.txt` files directly, reproduce all counts/statistics,
   and regenerate the PNGs without depending on `.codex/` or `/tmp`.
2. Produce a direct selection-bias figure with attempted, rejected, and
   accepted middle waypoints split by Target/Control and L/R. Include
   participant-level acceptance rates and explicit IK/reachability failure
   counts.
3. Quantify the distribution shift beyond means/ranges: mirrored x-distance
   from the obstacle, z, start pose, trajectory length, and preferably a
   participant-aware sensitivity analysis on a common feasible support.
4. Decide with the user whether the existing completed B/CB comparison should
   be reported with this selection-bias caveat only, or whether a new
   feasibility-matched experiment is required. Do not mutate or rerun the
   sealed experiments without explicit authorisation.

## Open Questions

- Whether the next artifact is a descriptive supplement/diagnostic or the
  basis for a new common-feasible-support experiment.
- Whether camera-view “left” should be relabelled in presentation; stored route
  L is the smaller-x side and must remain unchanged in data/results.

## Changelog

- 2026-08-09: Created the handoff with attempt-level route/IK selection-bias
  evidence, HDF5 sample-balance facts, completed static EE-workspace PNGs, and
  the reproducibility/next-analysis gaps.
