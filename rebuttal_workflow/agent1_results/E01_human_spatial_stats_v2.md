# Agent1 Result Card: E01 Human Spatial Statistics V2

Experiment ID:
E01_human_spatial_stats_v2

Purpose:
Audit real-user spatial keypoint distributions for the 25 cm spatial guidance
claim, especially "why 25 cm rather than 10 cm?"

Agent2 request:
Use real human data diagnostics to justify the spatial guidance design without
claiming global optimality or treating a 25 cm uniform disk as the desired final
demonstration distribution.

Code changes:
None in this run. Used the existing read-only diagnostic script
`scripts/analyze_week2_human_data.py`.

Commands / Slurm jobs:

```bash
python scripts/analyze_week2_human_data.py \
  --frame-stride 10 \
  --output-dir outputs/week2_human_diagnostics_keypoints_v2 \
  --no-plots
```

Data generated:

```text
outputs/week2_human_diagnostics_keypoints_v2/demo_metrics.csv
outputs/week2_human_diagnostics_keypoints_v2/group_summary_long.csv
outputs/week2_human_diagnostics_keypoints_v2/keypoint_spread_summary.csv
outputs/week2_human_diagnostics_keypoints_v2/human_diagnostics_summary.json
```

Models generated:
None.

Primary metric:
Radius of each group's nearest-to-corridor-plane early approach keypoint in the
x-z plane, measured relative to that group's empirical mean keypoint.

Secondary metrics:
Pre-grasp keypoint x-y spread after the first sustained z drop, post-training
spatial spread, and error count.

Plots / summaries:
This V2 run used `--no-plots`; use V1 plot files only as visual aids. The
auditable V2 evidence is in CSV/JSON tables.

Verification performed:

```text
human_diagnostics_summary.json errors = 0
frame_stride = 10
mirror_y_applied = true
P1/P2/P6/P7 each have n = 120 demos
P8 target/control each have n = 30 demos
```

Primary facts:

```text
P1 pre skill1 nearest-to-corridor-plane x-z:
  center = (43.19, 17.04) cm
  std_x = 8.32 cm, std_z = 6.19 cm
  radius p50/p90/p95/max = 8.13 / 15.83 / 18.28 / 23.71 cm

P2 pre skill2 nearest-to-corridor-plane x-z:
  center = (44.00, 20.45) cm
  std_x = 12.74 cm, std_z = 8.83 cm
  radius p50/p90/p95/max = 12.84 / 23.63 / 26.70 / 32.64 cm

P6 post skill1 nearest-to-corridor-plane x-z:
  radius p50/p90/p95/max = 4.03 / 7.22 / 9.49 / 16.80 cm

P7 post skill2 nearest-to-corridor-plane x-z:
  radius p50/p90/p95/max = 3.53 / 6.26 / 6.67 / 7.54 cm
```

The earlier 2026-07-02 summary also computed direct coverage against fixed
10 cm and 25 cm radii:

```text
P1 pre: 10 cm covers 65.0%, 25 cm covers 100.0%
P2 pre: 10 cm covers 32.5%, 25 cm covers 90.8%
```

Failures / warnings:

- The key name `corridor_crossing` in CSV/JSON means "trajectory point closest
  to the y=0 corridor plane"; many real-user trajectories do not literally
  cross y=0. Reviewer-facing text should say "nearest-to-corridor-plane early
  approach keypoint" or define the term explicitly.
- The 25 cm value must be described as an outer AR guidance/capture envelope,
  not desired final variance and not a uniform sampling distribution.
- Pre-grasp concentration is mostly a fixed-target sanity check, not the main
  evidence.

Can this support the requested claim? yes

Reason:
The pre-training data show that 10 cm would exclude a large fraction of natural
approach behavior, while 25 cm covers most natural behavior. The post-training
data show actual demonstrations are much tighter than the outer 25 cm envelope,
which addresses the reviewer trap that a wide guidance envelope would imply
uniform wide demonstrations.

Next engineering action if requested:
Run E02 human-prior simulation only as a backup or future-paper experiment. It
is not required for the narrowed rebuttal claim if wording stays conservative.
