# Handoff: AR Guidance OOD and Human-Data Logic

_Last updated: 2026-07-05 · Branch: hpc-headless-data-collection @ a2d81a9_

## Goal
Capture the current scientific logic for defending DEMT AR-guidance parameters after the spatial sweep, OOD stress tests, and real-human P1/P2/P6/P7 diagnostics. The next agent should not try to prove that the paper's 25 cm spatial parameter is a literal global optimum; the defensible claim is a bounded, human-facing guidance-envelope argument reconciled with learner sensitivity.

## Current Progress
- Existing branch/commit at handoff time:
  ```text
  branch: hpc-headless-data-collection
  HEAD:   a2d81a9
  ```
- Current working tree has uncommitted rollout-pipeline edits:
  ```text
  M examples/eval_abla1_trained_policies.py
  M scripts/run_abla1_eval.sh
  M scripts/run_abla1_eval_merge.sh
  M scripts/run_abla1_shared_start_manifest.sh
  ```
  These add 35-40 cm annulus OOD start sampling via
  `--shared-start-radius-min`, propagate the arg through Slurm wrappers, and
  write metadata such as `paired_shared_absolute_corridor_starts_annulus_r35_r40`.
- Original spatial/temporal S/T experiment pipeline was already complete before
  this handoff. Latest shared absolute-start r=0.35 spatial rerollout:
  ```text
  dataset/ar_guidance_spatial_S15_S35/policy_rollouts_seed628_shared_r35_parallel
  S15 6/10, S20 3/10, S25 4/10, S30 1/10, S35 2/10
  ```
- User realized the r=0.35 disk-style evaluation was not the intended stress
  test. Correct OOD stress test samples shared absolute starts from the XZ
  annulus around the AR corridor center:
  ```text
  center = [0.3, 0.0, 0.5]
  0.35 m <= radius <= 0.40 m
  area-uniform annulus sampling
  IK-reachable accepted starts only
  ```
- n=10 annulus OOD run completed:
  ```text
  output: dataset/ar_guidance_spatial_S15_S35/policy_rollouts_seed628_ood_annulus_r35_r40_parallel
  manifest job: 35404305
  rollout array: 35404313
  merge job: 35404420
  results: S15 1/10, S20 0/10, S25 2/10, S30 1/10, S35 0/10
  ```
  S25 looked best at n=10, but the sample was too small to support a strong
  claim.
- n=30 annulus OOD run completed:
  ```text
  output: dataset/ar_guidance_spatial_S15_S35/policy_rollouts_seed628_ood_annulus_r35_r40_n30_parallel
  manifest job: 35404582
  rollout array: 35404586
  merge job: 35405202
  results: S15 8/30, S20 2/30, S25 7/30, S30 1/30, S35 0/30
  ```
  Validation passed: summary exists, five condition JSONs/videos exist, all
  conditions share the same 30 absolute starts, and all radii are inside
  35-40 cm. n=30 weakens the "S25 is best" interpretation; S15 is marginally
  highest, S25 close behind, S35 worst.
- Real-human diagnostics are from:
  ```text
  outputs/week2_human_diagnostics_keypoints_v2
  ```
  P1/P2 are train-before, P6/P7 are train-after:
  ```text
  P1 = P1_target_pre_skill1  = pre-train prism / trained task
  P6 = P6_target_post_skill1 = post-train prism / trained task
  P2 = P2_target_pre_skill2  = pre-train cube / unseen object
  P7 = P7_target_post_skill2 = post-train cube / unseen object
  ```
  Each group has 4 people x 30 demos = 120 demos. This was checked against both
  `outputs/week2_human_diagnostics_keypoints_v2/demo_metrics.csv` and
  `/scratch/users/k23114984/pybullet_data/target_pooled/manifests/target_pooled_manifest.csv`.
- Human spatial diagnostics:
  ```text
  nearest-to-corridor-plane p95 radius:
    P1 -> P6: 18.28 cm -> 9.49 cm
    P2 -> P7: 26.70 cm -> 6.67 cm

  pregrasp-keypoint p95 radius:
    P1 -> P6: 5.37 cm -> 3.09 cm
    P2 -> P7: 6.99 cm -> 2.87 cm

  full-trajectory spatial-dispersion p95:
    P1 -> P6: 11.19 cm -> 9.03 cm
    P2 -> P7: 20.87 cm -> 6.72 cm
  ```
- Human orientation diagnostics:
  ```text
  closest-grasp orientation p95 to group mean:
    P1 -> P6: 27.38 deg -> 13.14 deg
    P2 -> P7: 33.96 deg -> 14.33 deg

  first-close orientation p95 to group mean:
    P1 -> P6: 32.62 deg -> 13.47 deg
    P2 -> P7: 40.13 deg -> 13.59 deg

  closest-grasp coverage within 15 deg:
    P1 -> P6: 59.2% -> 100.0%
    P2 -> P7: 53.3% -> 99.2%
  ```
- Human temporal diagnostics:
  ```text
  mean duration:
    P1 -> P6: 5.66 s -> 10.49 s
    P2 -> P7: 6.16 s -> 10.62 s

  mean speed:
    P1 -> P6: 0.113 m/s -> 0.055 m/s
    P2 -> P7: 0.114 m/s -> 0.059 m/s

  duration-ratio coverage in [0.8, 1.25]:
    P1 -> P6: 77.5% -> 85.8%
    P2 -> P7: 71.7% -> 87.5%
  ```

## What Worked
- The annulus OOD stress test is the right scientific version of the user's
  stress-test idea: evaluate policies on 35-40 cm shared starts, outside all
  training disks, with paired absolute starts for S15-S35.
- The n=30 result is more reliable than n=10. It shows S15 is marginally best
  and S25 close behind, while S35 is consistently poor. This supports the
  learner-side conclusion that tighter spatial consistency is better under the
  current N=30 learner and task.
- Real-human P1/P2/P6/P7 data gives the key reconciliation:
  post-training users do not uniformly occupy a 25 cm disk. They produce much
  tighter realized demonstrations, with P6/P7 nearest-to-corridor-plane p95
  radii of 9.49 cm and 6.67 cm.
- Strong scientific phrasing:
  ```text
  The effective demonstrated distribution after DEMT is much tighter than the
  displayed guidance envelope.
  ```
- Strong rebuttal-style logic:
  ```text
  We do not claim the Table 5 values are literal global optima over the
  continuous AR-parameter space. They are bounded, human-facing guidance
  thresholds. Follow-up sensitivity analysis shows the learner prefers tighter
  spatial consistency, while real-human post-training diagnostics show DEMT
  users indeed produce tighter, learner-friendly trajectories within the
  permissive guidance envelope.
  ```
- P2 -> P7 is the cleanest human-data story: spatial p95, orientation p95, and
  temporal regularity all improve substantially for the unseen-object cube task.

## What Didn't Work
- Do not claim "25 cm is globally optimal" or "25 cm is the best learner
  radius." Current uniform simulation evidence does not support that. S15 is
  better than S25 in the n=30 annulus OOD stress test and was also strong in
  normal rollout.
- Do not interpret the 25 cm AR spatial value as the desired final
  demonstration variance. It is better framed as a permissive human-facing
  capture/guidance envelope.
- Do not argue from uniform 25 cm simulation directly to real DEMT human data.
  Humans do not sample uniformly across the 25 cm disk; post-training behavior
  is clustered by human priors and guidance.
- Do not overinterpret the n=10 annulus result where S25 was 2/10 and appeared
  best. n=30 changed the ordering to S15 8/30 and S25 7/30.
- Do not use `[0.3, 0.0, 0.5]` as a measured human corridor center. In human
  diagnostics it is an AR guidance reference, not the empirical center. For
  human spatial claims, prefer nearest-to-corridor-plane keypoint spread around
  the group mean.
- Do not use old partial/probe rollout directories as final results:
  ```text
  dataset/ar_guidance_spatial_S15_S35/policy_rollouts_seed628_shared_r35
  dataset/ar_guidance_spatial_S15_S35/policy_rollouts_seed628_shared_r35_parallel_gpu
  ```

## Key Files & Commands
- Active handoffs already read during this work:
  ```text
  handoffs/ar-guidance-spatial-temporal-experiments.md
  handoffs/week2_experiment.md
  handoffs/week2_research_thinking.md
  handoffs/multiagent_history_example.md
  ```
- OOD rollout code and wrappers:
  ```text
  examples/eval_abla1_trained_policies.py
  scripts/run_abla1_shared_start_manifest.sh
  scripts/run_abla1_eval.sh
  scripts/run_abla1_eval_merge.sh
  ```
- Final OOD outputs:
  ```text
  dataset/ar_guidance_spatial_S15_S35/policy_rollouts_seed628_ood_annulus_r35_r40_parallel
  dataset/ar_guidance_spatial_S15_S35/policy_rollouts_seed628_ood_annulus_r35_r40_n30_parallel
  ```
- Human diagnostic outputs:
  ```text
  outputs/week2_human_diagnostics_keypoints_v2/demo_metrics.csv
  outputs/week2_human_diagnostics_keypoints_v2/group_summary_long.csv
  outputs/week2_human_diagnostics_keypoints_v2/keypoint_spread_summary.csv
  outputs/week2_human_diagnostics_keypoints_v2/orientation_event_summary.csv
  outputs/week2_human_diagnostics_keypoints_v2/temporal_human_summary.csv
  outputs/week2_human_diagnostics_keypoints_v2/human_diagnostics_summary.json
  ```
- Human source/manifest facts:
  ```text
  /scratch/users/k23114984/pybullet_data/target_pooled/pooled_symlinks/target_pre_skill1
  /scratch/users/k23114984/pybullet_data/target_pooled/pooled_symlinks/target_pre_skill2
  /scratch/users/k23114984/pybullet_data/target_pooled/pooled_symlinks/target_post_skill1
  /scratch/users/k23114984/pybullet_data/target_pooled/pooled_symlinks/target_post_skill2
  /scratch/users/k23114984/pybullet_data/target_pooled/manifests/target_pooled_manifest.csv
  ```
- Reusable OOD run shape:
  ```bash
  OUTPUT_DIR=dataset/ar_guidance_spatial_S15_S35/policy_rollouts_seed628_ood_annulus_r35_r40_n30_parallel \
  START_MANIFEST=$OUTPUT_DIR/shared_start_manifest_seed628_n30_annulus_r35_r40.json \
  SHARED_START_RADIUS_MIN=0.35 \
  SHARED_START_RADIUS=0.40 \
  NUM_ROLLOUTS=30 \
  SEED=628 \
  sbatch scripts/run_abla1_shared_start_manifest.sh

  OUTPUT_DIR=dataset/ar_guidance_spatial_S15_S35/policy_rollouts_seed628_ood_annulus_r35_r40_n30_parallel \
  VIDEO_DIR=$OUTPUT_DIR/videos \
  START_MANIFEST=$OUTPUT_DIR/shared_start_manifest_seed628_n30_annulus_r35_r40.json \
  SHARED_START_RADIUS_MIN=0.35 \
  SHARED_START_RADIUS=0.40 \
  NUM_ROLLOUTS=30 \
  SEED=628 \
  SKIP_AGGREGATE=1 \
  sbatch --array=0-4 scripts/run_abla1_eval.sh

  OUTPUT_DIR=dataset/ar_guidance_spatial_S15_S35/policy_rollouts_seed628_ood_annulus_r35_r40_n30_parallel \
  START_MANIFEST=$OUTPUT_DIR/shared_start_manifest_seed628_n30_annulus_r35_r40.json \
  SHARED_START_RADIUS_MIN=0.35 \
  SHARED_START_RADIUS=0.40 \
  NUM_ROLLOUTS=30 \
  SEED=628 \
  sbatch scripts/run_abla1_eval_merge.sh
  ```
  In practice, if using interruptible partitions, verify per-condition JSONs
  exist before merge because Slurm preemption status can make `afterok`
  dependencies brittle.

## Next Steps
1. If writing rebuttal/paper language, stop asking "why is 25 cm globally
   optimal?" Reframe as: "25 cm is a bounded human-facing envelope; the realized
   post-training demonstrations are much tighter and learner-friendly."
2. Use P1/P2 -> P6/P7 evidence as the central human-data story:
   spatial tightens, orientation tightens into about 15 deg, and temporal
   behavior becomes slower and more regular.
3. Present S15/S25/S35 simulation results conservatively:
   S15 is best in the n=30 annulus OOD run; S25 is not learner-optimal under
   uniform sampling; S35 does not confer robustness. This supports a
   learner-sensitivity argument, not a direct attack on the DEMT envelope.
4. If more experiments are needed, the best next scientific design is not
   another uniform disk sweep. Prefer human-prior or percentile-truncated
   sampling based on P6/P7 post-training distributions, then train/evaluate the
   learner under that structured distribution.
5. Consider committing the annulus OOD pipeline edits after review. They are
   useful and currently uncommitted.

## Open Questions
- Whether to commit/push the annulus OOD pipeline edits.
- Whether to update `handoffs/ar-guidance-spatial-temporal-experiments.md` with
  the n=10/n=30 annulus OOD results, or keep this separate logic handoff as the
  primary continuation artifact.
- Whether the next experiment should be human-prior sampling from P6/P7
  distributions, percentile-truncated sampling, or a coupled fixed-ratio
  spatial funnel sweep.

## Changelog
- 2026-07-05: Created this handoff to capture the full conversation logic:
  annulus OOD stress-test results, why S15/S25 results do not prove 25 cm
  optimality, and how real P1/P2/P6/P7 human diagnostics support the bounded
  guidance-envelope interpretation.
