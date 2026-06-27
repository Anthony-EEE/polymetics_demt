# Handoff: Main Experiments

_Last updated: 2026-06-27 · Branch: hpc-headless-data-collection @ 27a2d53_

## Goal
Prepare and implement short-term CoRL rebuttal experiments for the DEMT paper, focusing first on a cube pick-and-lift spatial corridor ablation that explains how DEMT's `P/R/V` formulation maps to concrete AR guidance parameters.

## Current Progress
- Reviewed the submitted paper PDF: `DEMT__Deployment_Evaluated_Machine_Teaching_Enhances_Learning_from_Human_Demonstrations.pdf`.
- Wrote and committed rebuttal planning docs:
  - `docs/corl-rebuttal-ablation-plan.md`
  - `docs/corl-rebuttal-ablation-plan-cn.md`
  - `docs/ablation-1.md`
- `docs/ablation-1.md` remains the source of truth for Spatial Structure / Corridor Geometry planning.
- Created a new ablation-only data generator instead of modifying the original script:
  - `examples/main_abla_1.py`
  - Original `examples/main.py` was intentionally left unchanged.
- Added cube-only ablation rollout in `examples/main_abla_1.py`:
  ```text
  random_start -> open_gripper -> corridor_start -> pre_grasp -> pick_grasp -> close_gripper -> lift
  ```
- Added random EE initialization sampled on the reachable `y = 0` x-z plane:
  - default `x in [0.20, 0.60]`
  - default `z in [0.20, 0.60]`
  - `y = 0`
  - IK/reachability check with default max error `0.025 m`
- Added object-relative corridor geometry:
  ```text
  base_pre_grasp = [cube_x, cube_y, 0.22]
  base_corridor_start = [cube_x - entry_dx, cube_y, 0.22 + entry_dz]
  default entry_dx = 0.20
  default entry_dz = 0.06
  ```
- Added x-z disk sampling for both corridor waypoint deltas:
  ```text
  corridor_start = base_corridor_start + [dx, 0, dz]
  pre_grasp = base_pre_grasp + [dx, 0, dz]
  ```
- Added 2 x 2 ablation condition table:
  | Condition | corridor_start_radius | pre_grasp_radius |
  | --- | ---: | ---: |
  | `P00` | `0.10` | `0.02` |
  | `P10` | `0.25` | `0.02` |
  | `P01` | `0.10` | `0.06` |
  | `P11` | `0.25` | `0.06` |
- Added metadata in each successful demo for:
  - `condition_label`
  - `cube_position`
  - `random_start`
  - `random_start_info`
  - `base_corridor_start`
  - `corridor_start`
  - `corridor_start_delta`
  - `corridor_start_radius`
  - `base_pre_grasp`
  - `pre_grasp`
  - `pre_grasp_delta`
  - `pre_grasp_radius`
  - `grasp`, `lift`, `entry_dx`, `entry_dz`
  - final `success` details
- User clarified failed rollout samples are not useful and can be deleted. Current script keeps the existing retry behavior: failed demo directories are removed and collection retries until the requested number of successful demos is reached or `--max-collection-attempts` is exceeded.
- Verified with `conda run -n polymetis38 python -m py_compile examples/main_abla_1.py`.
- Ran headless smoke tests in the existing `polymetis38` conda environment:
  - `P00`: success, 1/1 demo, 133 frames at `--sample-hz 10`, output `/tmp/panda_abla1_smoke/demo_0`
  - `P10`: success, 1/1 demo, output `/tmp/panda_abla1_smoke_P10/demo_0`
  - `P01`: success, 1/1 demo, output `/tmp/panda_abla1_smoke_P01/demo_0`
  - `P11`: success, 1/1 demo, output `/tmp/panda_abla1_smoke_P11/demo_0`
- Inspected P00 metadata and phase order. Phase count for the P00 smoke test:
  ```text
  random_start: 1
  open_gripper: 8
  corridor_start: 54
  pre_grasp: 15
  pick_grasp: 18
  close_gripper: 12
  lift: 25
  ```
- GitHub upload status:
  - Commit `d9821ec`: `Add ablation corridor collection script`
  - Commit `27a2d53`: `Add rebuttal ablation planning docs`
  - Both pushed to `origin/hpc-headless-data-collection` at `https://github.com/Anthony-EEE/polymetics_demt.git`.

## What Worked
- Keeping `examples/main.py` unchanged and creating `examples/main_abla_1.py` was the safest path. It avoids disturbing the existing data generator while allowing ablation-specific CLI defaults.
- The new ablation script defaults to `--mode ablation` and `--ablation-condition P00`, but still preserves copied `success` and `fail` modes from the original script for comparison.
- The existing `DatasetCollectorMixin` in `examples/collection_io.py` was sufficient; no change was needed there.
- `polymetis38` is the usable conda environment for this repo. Base Python lacks required dependencies such as `numpy`.
- Four single-demo smoke tests showed the initial radius levels are executable in headless PyBullet.
- Failed samples can be discarded per user instruction; no attempts manifest is currently needed.

## What Didn't Work
- Sandboxed shell commands repeatedly failed with `bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted`; read/write commands were rerun with escalation and succeeded.
- `apply_patch` failed with the same sandbox helper issue. Controlled Python text edits with escalation were used for `examples/main_abla_1.py` and this handoff.
- Running with base `python` failed immediately with `ModuleNotFoundError: No module named 'numpy'`. Use `conda run -n polymetis38 python ...`.
- `gh` is not installed (`gh: command not found`), so PR creation via GitHub CLI was not possible. Regular `git push` to `origin` worked.
- A raw `find ... -exec cat` phase check printed phases in filesystem order and looked scrambled. Sorting by frame index showed the phase sequence was correct.

## Key Files & Commands
- Main implementation:
  - `examples/main_abla_1.py`
- Original script intentionally unchanged:
  - `examples/main.py`
- Planning and handoff docs:
  - `docs/ablation-1.md`
  - `docs/corl-rebuttal-ablation-plan.md`
  - `docs/corl-rebuttal-ablation-plan-cn.md`
  - `handoffs/main-experiments.md`
- Paper PDF:
  - `DEMT__Deployment_Evaluated_Machine_Teaching_Enhances_Learning_from_Human_Demonstrations.pdf`
- Syntax check:
  ```bash
  conda run -n polymetis38 python -m py_compile examples/main_abla_1.py
  ```
- P00 smoke test command:
  ```bash
  conda run -n polymetis38 python examples/main_abla_1.py     --no-gui     --output-dir /tmp/panda_abla1_smoke     --num-demos 1     --seed 1     --sample-hz 10     --ablation-condition P00     --max-collection-attempts 2
  ```
- Full-condition quick smoke pattern used:
  ```bash
  for cond in P10 P01 P11; do
    conda run -n polymetis38 python examples/main_abla_1.py       --no-gui       --output-dir /tmp/panda_abla1_smoke_${cond}       --num-demos 1       --seed 2       --sample-hz 5       --ablation-condition ${cond}       --max-collection-attempts 3 || exit 1
  done
  ```
- Example real collection command for one condition:
  ```bash
  conda run -n polymetis38 python examples/main_abla_1.py     --no-gui     --output-dir /tmp/panda_abla1_P00     --num-demos 30     --sample-hz 30     --ablation-condition P00
  ```
- Inspect metadata:
  ```bash
  cat /tmp/panda_abla1_P00/demo_0/metadata.json
  ```
- Inspect phase order by frame index:
  ```bash
  conda run -n polymetis38 python -c "from pathlib import Path; from collections import Counter; root=Path('/tmp/panda_abla1_P00/demo_0'); items=[]
  for p in root.glob('frame_*/phase.txt'):
      idx=int(p.parent.name.split('_')[1]); items.append((idx,p.read_text().strip()))
  items.sort(); print('frames', len(items)); print('first_12', items[:12]); print('last_12', items[-12:]); print('counts', dict(Counter(phase for _, phase in items)))"
  ```

## Next Steps
1. Commit and push this handoff update after writing it.
2. Generate a small multi-demo dataset for each condition, e.g. `N=5` first, before jumping to `N=30`.
3. Inspect metadata distributions for each condition:
   - random start positions
   - corridor_start deltas
   - pre_grasp deltas
   - final success rates
   - frame count/phase count consistency
4. Decide final data root naming convention for full ablation datasets, e.g. `/tmp/panda_abla1_P00_seed1` or an `outputs/` path.
5. If smoke tests with `N=5` remain stable, generate `N=30` for all four conditions.
6. Only after cube generation is stable, consider insert-only validation in `examples/main_insert.py` or a new insert ablation script.
7. If a PR is needed, install/authenticate `gh` or create the PR manually from branch `hpc-headless-data-collection`.

## Open Questions
- Whether to keep `docs/.obsidian/*` tracked long term. It was committed because the user explicitly requested PDF, docs, and handoffs be submitted.
- Whether full datasets should be saved under `/tmp`, `outputs/`, or an external data directory on HPC.
- Whether to train/evaluate policies immediately after `N=30` generation or first add a compact condition manifest/CSV.
- Whether the final full run should use a single seed per condition or multiple dataset seeds.

## Changelog
- 2026-06-27: Created handoff for detailed `examples/main.py` experiments and documented phase/data/noise behavior.
- 2026-06-27: Updated handoff with DEMT paper/rebuttal context, created planning docs, and recorded agreed Spatial corridor ablation design with random EE initialization on the reachable `y = 0` x-z plane.
- 2026-06-27: Updated handoff after implementing `examples/main_abla_1.py`, smoke testing all four 2 x 2 conditions, and pushing commits `d9821ec` and `27a2d53` to GitHub.
