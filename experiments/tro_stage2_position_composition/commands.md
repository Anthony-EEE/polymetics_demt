# T-RO Stage 2c Position Composition Commands

## Completed

```bash
python scripts/tro_position_composition.py freeze-protocol
python scripts/tro_position_composition.py audit-feasibility
python -m pytest -q tests/test_tro_position_mvp0.py \
  tests/test_tro_position_confirmation.py tests/test_tro_position_stage2.py \
  tests/test_tro_position_stage2_idood.py \
  tests/test_tro_position_composition.py
sbatch --parsable --array=0-4 \
  scripts/run_tro_position_composition_smoke.sh
sbatch --parsable --array=0-4 \
  scripts/run_tro_position_composition_collect.sh
scancel 36053381
```

Smoke job `36053326` completed 5/5. Formal collection job `36053381`
encountered scientific protocol blockers in seed4 and seed5. The remaining
seed1-3 tasks were cancelled immediately. No retry was submitted.

## Protocol v2 implementation and migration

On 2026-07-26 the user authorised atomic four-corner retry-until-success for
the same 30 frozen latents. The v2 collector was implemented and verified:

```bash
/scratch/users/k23114984/conda/arcap/bin/python -m pytest -q \
  tests/test_tro_position_mvp0.py \
  tests/test_tro_position_confirmation.py tests/test_tro_position_stage2.py \
  tests/test_tro_position_stage2_idood.py \
  tests/test_tro_position_composition.py
/scratch/users/k23114984/conda/arcap/bin/python \
  scripts/tro_position_composition.py freeze-protocol-v2
sbatch --parsable --array=0-4 \
  scripts/run_tro_position_composition_collect.sh
```

The regression suite passed 43/43. `protocol_v2.json` SHA-256 is
`85fb309d660f0821fa80102bccb1d1e987d19ad6c217b54deb897366cda59efe`.
The v2 formal collection array is job `36054403`, submitted without a
dependency. All five tasks ran on `erc-hpc-comp230` for `00:13:09` and were
then cancelled to terminal state after the causal runtime-RNG audit below:

```bash
scancel 36054403
sacct -X -j 36054403 \
  --format=JobID,JobIDRaw,State,ExitCode,Elapsed,NodeList -n -P
```

The collector generated 90 new v2 scientific attempts, in addition to the
two preserved v1 attempt-zero failures. Distinct derived attempt seeds
produced exactly identical failed outcomes for each blocked latent.
Source audit established that the paired-latent trajectory contains no RNG
draw after `random.seed` and `numpy.random.seed`; the cube, offsets, IK,
controller and PyBullet physics settings are fixed. Therefore retries are
deterministic replicas and cannot implement retry-until-success. No
unregistered cube, contact, joint, waypoint or solver perturbation was added.
The stable evidence is:

```text
experiments/tro_stage2_position_composition/manifests/
  protocol_blocker_v2_runtime_rng.json
```

HDF5, training, checkpoint freeze, common-absolute rollout, RMAX40 rollout,
merge and analysis commands have not yet been run.

## Blocker audit and storage inventory

```bash
du -sb experiments/tro_stage2_position_composition \
  dataset/tro_position_stage2_composition
du -sb \
  dataset/tro_position_stage2_composition/formal/seed*/raw \
  dataset/tro_position_stage2_composition/formal/seed*/scientific_attempts_v2 \
  dataset/tro_position_stage2_composition/formal/seed*/protocol_blocker_attempts_v2 \
  dataset/tro_position_stage2_composition/formal/seed*/infrastructure_attempts_v2
/scratch/users/k23114984/conda/arcap/bin/python -m pytest -q \
  tests/test_tro_position_mvp0.py \
  tests/test_tro_position_confirmation.py tests/test_tro_position_stage2.py \
  tests/test_tro_position_stage2_idood.py \
  tests/test_tro_position_composition.py
squeue -j 36053326,36053381,36054403
sacct -X -j 36054403 \
  --format=JobID,JobIDRaw,State,ExitCode,Elapsed,NodeList -n -P
```

The final repeated regression run passed 43/43. The blocker-state storage and
hash audits are:

```text
experiments/tro_stage2_position_composition/manifests/
  storage_inventory_v2_blocker.json
  final_hashes_v2_blocker.json
```

No cleanup command, HDF5 command, training submission, rollout submission,
merge, analysis, commit, push or PR command was executed.

## Runtime-RNG continuation audit

The continuation compared all non-metadata files from four cross-attempt
pairs and probed the installed PyBullet API:

```bash
/scratch/users/k23114984/conda/arcap/bin/python -c \
  'import pybullet as p; print(p.getAPIVersion()); print(p.getPhysicsEngineParameters())'
rg -n 'np\.random|random\.' \
  examples/main_abla_1.py examples/collection_io.py \
  scripts/tro_position_composition.py
```

`randomSeed` and `solverRandomSeed` were both rejected as invalid
`setPhysicsEngineParameter` keywords. The four audited attempt-pairs contained
3,609 files after excluding provenance metadata; every paired file hash was
identical. The frozen result is:

```text
experiments/tro_stage2_position_composition/manifests/
  runtime_rng_capability_audit.json
```

No new Slurm job was submitted during this continuation.

## Protocol v3 candidate-stream continuation

On 2026-07-26 the user clarified and explicitly authorised continuing the
same deterministic candidate stream after a failed candidate (candidate 31,
32, 33, and so on) until each canonical seed has exactly 30 successful
four-corner bundles. A candidate is accepted only when all four new corners
succeed; any failed candidate is archived in full and the stream advances.
Infrastructure interruption retries the identical candidate without
advancing.

```bash
/scratch/users/k23114984/conda/arcap/bin/python -m pytest -q \
  tests/test_tro_position_mvp0.py \
  tests/test_tro_position_confirmation.py tests/test_tro_position_stage2.py \
  tests/test_tro_position_stage2_idood.py \
  tests/test_tro_position_composition.py
/scratch/users/k23114984/conda/arcap/bin/python \
  scripts/tro_position_composition.py freeze-protocol-v3
sbatch --parsable --array=0-4 \
  --export=ALL,PROJECT_DIR=/cephfs/volumes/hpc_data_prj/eng_demt_robot_learning/45908032-a3fa-4719-9989-cd8d04c08f7a/polymetics_demt \
  scripts/run_tro_position_composition_collect.sh
```

The regression suite passed 49/49. All 800 persisted source candidates
(five seeds x indices 0--159) matched the deterministic PCG64 generator
exactly. Frozen manifests:

```text
experiments/tro_stage2_position_composition/manifests/
  protocol_amendment_v3.json
  candidate_stream_v3.json
  test_evidence_v3.json
  protocol_v3.json
```

The v3 formal collection array is job `36055938`, submitted without a
dependency. It completed 5/5 tasks with exit code `0:0`. Every seed reached
30 accepted bundles and all 20 raw datasets passed strict validation. The
per-seed rejected candidate counts, including the migrated v2 frontier
candidate, were `4,2,6,10,3`; this is 20 new v3 scientific candidate
rejections plus five migrated frontier candidates. There were no collection
infrastructure retries.

## HDF5 and training

```bash
sbatch --parsable --array=0-4 \
  --export=ALL,PROJECT_DIR=/cephfs/volumes/hpc_data_prj/eng_demt_robot_learning/45908032-a3fa-4719-9989-cd8d04c08f7a/polymetics_demt \
  scripts/run_tro_position_composition_hdf5.sh
/scratch/users/k23114984/conda/arcap/bin/python -c \
  'import sys; sys.path[:0]=["scripts","examples"]; import tro_position_composition as c; [c.validate_hdf5_seed(s) for s in c.SEEDS]'
/scratch/users/k23114984/conda/arcap/bin/python \
  scripts/tro_position_composition.py validate-all-datasets
/scratch/users/k23114984/conda/arcap/bin/python \
  scripts/tro_position_composition.py create-train-configs
```

HDF5 array `36056459` completed 5/5 with exit code `0:0`; 20/20 new HDF5
files and all 45/45 dataset slots validated. The first unified audit detected
lost `datasets.json` fields caused by five successful tasks concurrently
writing that shared small manifest. The HDF5 files themselves all passed.
Per-seed HDF5 validation was therefore rerun sequentially and the final
45-slot hash audit passed; no HDF5 was regenerated or overwritten.

The first training submission produced job IDs `36057059`--`36057078`.
After moving still-pending jobs to `interruptible_gpu`, jobs
`36057059`--`36057061` failed before `train.py` because the submitted
`PROJECT_DIR` environment variable overrode the training wrapper's code
root. Jobs `36057062`--`36057078` were cancelled while still pending.
No checkpoint was created. This infrastructure-only attempt was cleanly
resubmitted with the same 20 frozen configs and the wrapper's correct default
code root:

```bash
PARTITION=interruptible_gpu \
  bash scripts/submit_tro_position_composition_training.sh
```

Clean-retry training job IDs are `36057105`--`36057124`. Job `36057105`
successfully entered `robomimic/scripts/train.py`; terminal states and any
further infrastructure retries will be recorded after all 20 jobs finish.

All 20 clean-retry training jobs completed with exit code `0:0`. Frozen
early-stop epochs ranged from 42 to 122. The pre-rollout checkpoint audit
then revalidated the 25 immutable anchors, selected the highest numeric
emitted checkpoint in each of the 20 new slots, and froze 45/45 policy slots:

```bash
/scratch/users/k23114984/conda/arcap/bin/python \
  scripts/tro_position_composition.py freeze-checkpoints
sha256sum \
  experiments/tro_stage2_position_composition/manifests/checkpoints*.json
```

The unified checkpoint manifest SHA-256 is
`91e47d35b5f621f49dc4aba3b3a1d316131b6a080645e5089f62575bfa5fb326`.
No formal rollout outcome existed before this freeze.

Primary common-absolute formal rollout array:

```bash
sbatch --parsable --array=0-199 \
  --export=ALL,PROJECT_DIR=/cephfs/volumes/hpc_data_prj/eng_demt_robot_learning/45908032-a3fa-4719-9989-cd8d04c08f7a/polymetics_demt \
  scripts/run_tro_position_composition_rollout.sh
```

This returned job `36059233`; its 200 task states are monitored to terminal
before Gate 6.

Tasks 0--5 failed in 2--5 seconds before policy loading or the first rollout
because the composition loader required nine-condition metadata while the
immutable reused Stage 2 manifests correctly retain their original
five-condition order. The remaining 194 tasks were cancelled; zero rollout
rows or summaries were created. The loader was narrowed to accept that exact
legacy Stage 2 order only for the composition profile, while retaining the
full protocol, state, RNG, radius, ordering and IK checks. Composition tests
passed 19/19 and direct common/RMAX40 manifest-load preflights passed.

The identical frozen 200-task primary array was cleanly retried:

```bash
sbatch --parsable --array=0-199 \
  --export=ALL,PROJECT_DIR=/cephfs/volumes/hpc_data_prj/eng_demt_robot_learning/45908032-a3fa-4719-9989-cd8d04c08f7a/polymetics_demt \
  scripts/run_tro_position_composition_rollout.sh
```

Clean-retry job: `36059244`.

Job `36059244` completed 200/200 tasks with exit code `0:0`. Strict
common-absolute validation passed 200/200 new tasks and 5,000/5,000 new
rows. Together with the referenced immutable anchors, the surface contains
45 policies, 450 tasks and 11,250 rows with exact nine-condition
state/runtime-RNG/point-cloud-RNG pairing. All 45 selected checkpoint hashes
were revalidated once after rollout.

Secondary RMAX40 formal rollout array:

```bash
sbatch --parsable --array=0-199 \
  --export=ALL,PROJECT_DIR=/cephfs/volumes/hpc_data_prj/eng_demt_robot_learning/45908032-a3fa-4719-9989-cd8d04c08f7a/polymetics_demt \
  scripts/run_tro_position_composition_rmax40_rollout.sh
```

This returned job `36061752`.

The first allocations on `erc-hpc-comp054` were repeatedly preempted before
their 25 rows completed. After task IDs `9,10,11,12,18,19,22,23,24,25,26,27`
were terminal `PREEMPTED`, the faulty node was excluded from every still
pending task without changing any checkpoint, rollout manifest, state, seed
or task mapping:

```bash
scontrol update JobId=36061752 \
  ExcNodeList=erc-hpc-comp035,erc-hpc-comp040,erc-hpc-comp054,erc-hpc-comp223
```

The same exclusion was added to
`scripts/run_tro_position_composition_rmax40_rollout.sh` for the eventual
clean retry. No further preemption occurred after the exclusion. The original
array reached terminal state with 188 `COMPLETED`, 12 `PREEMPTED` and no
other states. Its 40 partial rows were moved from the formal namespace to
task-owned directories under
`dataset/tro_position_stage2_composition/rollouts/rmax40/infrastructure_failures/`.
The formal namespace then contained exactly 188 summaries and 4,700 rows.

Only the exact preempted task IDs were cleanly retried:

```bash
sbatch --parsable --array=9-12,18-19,22-27 \
  --exclude=erc-hpc-comp035,erc-hpc-comp040,erc-hpc-comp054,erc-hpc-comp223 \
  --export=ALL,PROJECT_DIR=/cephfs/volumes/hpc_data_prj/eng_demt_robot_learning/45908032-a3fa-4719-9989-cd8d04c08f7a/polymetics_demt \
  scripts/run_tro_position_composition_rmax40_rollout.sh
```

Clean-retry job: `36062210`. The checkpoint manifest, start manifests,
absolute states, runtime/point-cloud seeds and task mapping are unchanged.

The complete relevant regression suite was rerun after the strict-merge
pairing, checkpoint-hash-cache and legacy immutable-manifest loader changes:

```bash
/scratch/users/k23114984/conda/arcap/bin/python -m pytest -q \
  tests/test_tro_position_mvp0.py \
  tests/test_tro_position_confirmation.py \
  tests/test_tro_position_stage2.py \
  tests/test_tro_position_stage2_idood.py \
  tests/test_tro_position_composition.py
```

Result: `51 passed in 64.76s`.

After job `36062210` completed 12/12 tasks with exit code `0:0`, the formal
RMAX40 namespace contained exactly 200 summaries and 5,000 rows. The strict
merge and analysis commands were:

```bash
/scratch/users/k23114984/conda/arcap/bin/python \
  scripts/tro_position_composition.py strict-merge
/scratch/users/k23114984/conda/arcap/bin/python \
  scripts/analyze_tro_position_composition.py
```

Strict merge passed 400/400 new tasks and 10,000/10,000 new rows. The first
local analysis pass stopped before writing `comparison.json` or `summary.md`
because a NumPy `int64` sign-count was not JSON serializable. The count was
converted to a built-in `int`, a regression test was added, and the same
frozen analysis was rerun without changing any outcome, contrast or rule:

```bash
/scratch/users/k23114984/conda/arcap/bin/python -m pytest -q \
  tests/test_tro_position_composition.py
/scratch/users/k23114984/conda/arcap/bin/python \
  scripts/analyze_tro_position_composition.py
```

Result: `20 passed`; classification `interaction`.

The complete relevant suite was rerun after the serialization regression test:

```bash
/scratch/users/k23114984/conda/arcap/bin/python -m pytest -q \
  tests/test_tro_position_mvp0.py \
  tests/test_tro_position_confirmation.py \
  tests/test_tro_position_stage2.py \
  tests/test_tro_position_stage2_idood.py \
  tests/test_tro_position_composition.py
```

Final result: `52 passed in 50.61s`.

The final read-only audit rehashed all 25 immutable checkpoints, all 25
immutable HDF5 anchors, five frozen top-level anchor files, 30 reused rollout
manifests and all 45 selected checkpoints. Storage was measured with
`du -sb`; no cleanup command was executed. Final small-artifact hashes are
recorded in `manifests/final_hashes_v3.json`.
