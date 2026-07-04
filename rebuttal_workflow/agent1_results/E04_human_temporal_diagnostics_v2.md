# Agent1 Result Card: E04 Human Temporal Diagnostics V2

Experiment ID:
E04_human_temporal_diagnostics_v2

Purpose:
Assess whether the submitted speed cue `[0.5, 2.0] x v_ref` can be defended as
a human-compatible temporal guidance window, while relying on Week 1 simulation
for learner-aware temporal sensitivity.

Agent2 request:
Keep temporal wording conservative because the submitted paper uses a reference
trajectory (`v_ref`) rather than a fixed metric speed threshold.

Code changes:
None in this run. Used the existing read-only diagnostic script and existing
Week 1 temporal MVP evidence.

Commands / Slurm jobs:

```bash
python scripts/analyze_week2_human_data.py \
  --frame-stride 10 \
  --output-dir outputs/week2_human_diagnostics_keypoints_v2 \
  --no-plots
```

Data generated:

```text
outputs/week2_human_diagnostics_keypoints_v2/temporal_human_summary.csv
outputs/week2_human_diagnostics_keypoints_v2/human_diagnostics_summary.json
```

Models generated:
None in this run. Existing Week 1 temporal models are documented in
`handoffs/week1_main-experiments.md`.

Primary metric:
Coverage of duration and mean-speed ratios within `[0.5, 2.0]` relative to the
group median trajectory. This is a proxy diagnostic, not the exact per-user
`v_ref` rule from the paper.

Secondary metrics:
Coverage within a tighter `[0.8, 1.25]` band; Week 1 rollout success for
T00/T20/Twide.

Primary facts:

```text
Week 1 latest-checkpoint temporal rollout:
  T00/T20/Twide = 10/10, 8/10, 7/10

Duration-ratio coverage in [0.5, 2.0]:
  P1 pre = 100.0%
  P2 pre = 93.3%
  P6 post = 100.0%
  P7 post = 100.0%
  P8 target = 100.0%
  P8 control = 86.7%

Mean-speed-ratio coverage in [0.5, 2.0]:
  P1 pre = 99.2%
  P2 pre = 96.7%
  P6 post = 99.2%
  P7 post = 100.0%
  P8 target = 100.0%
  P8 control = 93.3%
```

Verification performed:

```text
human_diagnostics_summary.json errors = 0
temporal_human_summary.csv has 6 data rows
P1/P2/P6/P7 each use n = 120 demos
P8 target/control each use n = 30 demos
```

Failures / warnings:

- This run uses ratios to the group median, not each person's first trajectory.
  It is therefore human-compatibility evidence, not exact validation of the
  paper's `v_ref` implementation.
- Week 1 T00/T20/Twide is a finite sensitivity check, not a symmetric temporal
  ladder. Avoid claiming exact optimality of `[0.5, 2.0]`.

Can this support the requested claim? partial / yes with conservative wording

Reason:
The human data show `[0.5, 2.0]` is a permissive window that covers most observed
duration and mean-speed variation. The Week 1 temporal rollout shows temporal
consistency matters to the learner. Together they support "human-compatible and
learner-aware finite candidate", but not exact threshold optimality.

Next engineering action if requested:
Future-paper work should use a clean T00/T10/T20/T30/T40 ladder and compute
phase-level statistics against the paper's per-user `v_ref` definition.
