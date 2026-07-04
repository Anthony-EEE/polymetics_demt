# Agent1 Result Card: E03 Human Orientation Diagnostics V2

Experiment ID:
E03_human_orientation_diagnostics_v2

Purpose:
Support the 15 deg orientation guidance tolerance as human-compatible and
learner-aware without claiming exact optimality.

Agent2 request:
Use available human diagnostics and Week 1 simulation to decide whether the
15 deg orientation parameter can be defended to a strict reviewer.

Code changes:
None in this run. Used the existing read-only diagnostic script and existing
Week 1 orientation MVP evidence.

Commands / Slurm jobs:

```bash
python scripts/analyze_week2_human_data.py \
  --frame-stride 10 \
  --output-dir outputs/week2_human_diagnostics_keypoints_v2 \
  --no-plots
```

Data generated:

```text
outputs/week2_human_diagnostics_keypoints_v2/orientation_event_summary.csv
outputs/week2_human_diagnostics_keypoints_v2/human_diagnostics_summary.json
```

Models generated:
None in this run. Existing Week 1 orientation models are documented in
`handoffs/week1_main-experiments.md`.

Primary metric:
Orientation dispersion at grasp-relevant events, measured as angular distance
to the group mean quaternion.

Secondary metrics:
Coverage within 15 deg and 30 deg of the group mean; Week 1 rollout success
for R00/R15/R30.

Primary facts:

```text
Week 1 orientation rollout:
  R00/R15/R30 = 7/10, 6/10, 4/10

P6 post skill1 closest_grasp:
  p95 to group mean = 13.14 deg, coverage_15deg = 100.0%

P6 post skill1 first_close:
  p95 to group mean = 13.47 deg, coverage_15deg = 100.0%

P7 post skill2 closest_grasp:
  p95 to group mean = 14.33 deg, coverage_15deg = 99.2%

P7 post skill2 first_close:
  p95 to group mean = 13.59 deg, coverage_15deg = 99.2%
```

Pre-training contrast:

```text
P1 pre closest_grasp p95 = 27.38 deg, coverage_15deg = 59.2%
P2 pre closest_grasp p95 = 33.96 deg, coverage_15deg = 53.3%
```

Verification performed:

```text
human_diagnostics_summary.json errors = 0
orientation_event_summary.csv has 18 data rows
P1/P2/P6/P7 each use n = 120 demos for closest_grasp
```

Failures / warnings:

- Human orientation diagnostics are dispersion-to-group-mean evidence. They
  should be used for human compatibility / achievable consistency, not as proof
  that the absolute FK quaternion matches the simulator's default gripper frame.
- Week 1 simulation gives learner-aware evidence, but only for finite
  candidates R00/R15/R30.

Can this support the requested claim? yes

Reason:
The learner evidence shows larger orientation variation degrades deployment
from 15 deg to 30 deg. The human diagnostics show post-training grasp-relevant
orientation dispersion is almost entirely within 15 deg of a consistent group
orientation. Together, these support 15 deg as a reasonable finite tolerance,
not an exact optimum.

Next engineering action if requested:
Optional future-paper work could add R05/R45 or align human FK quaternions to
the exact AR target frame. This is not required for the narrowed rebuttal claim.
