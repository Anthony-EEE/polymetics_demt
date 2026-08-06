# T-RO Stage 2 Position Axial Condition-Relative ID/OOD Rerollout

Status: RMAX40 protocol amendment authorised on 2026-07-25; execute through
Definition of Done.

## 0. RMAX40 protocol amendment

The initial `R_MAX=0.45 m` feasibility pass is a rejected pilot protocol.
Its 30 manifests, feasibility audit, failed pre-rollout smoke logs and
registry records are immutable audit evidence. They must not be overwritten
or used for formal policy evaluation.

The user explicitly authorised reducing the global deployment boundary by
0.05 m so the rerollout can proceed. The active formal protocol is:

```text
protocol_id = tro_stage2_position_axial_condition_relative_idood_rerollout_rmax40_v2
R_MAX       = 0.40 m
```

Generate a fresh set of 30 manifests under
`manifests/rollout_5seed_rmax40/`. Use new artifact IDs containing `rmax40`.
Write all new rollout rows under
`dataset/tro_position_stage2_axial_idood_rerollout/rmax40/`.

The accepted sample is explicitly the deterministic reachable-conditioned
deployment distribution. IK rejection can make its realised angle
distribution non-uniform. This is a limitation to quantify and report, not a
claim of angle-uniform deployment after conditioning. Gate 2 passes when each
seed/bank group has 25 jointly reachable paired states, every individual
manifest represents all four XZ quadrants, pooled area quantiles cover at
least `[0.05,0.95]`, and every other bound/pairing/RNG assertion passes.
Stop only if those explicit criteria fail; do not change `R_MAX=0.40 m`,
post-select results, or alter the sampling algorithm.

## 1. Authority and scope

This PLAN is the sole scientific authority for the condition-relative ID/OOD
rerollout. It is a protocol amendment to the completed
`tro_stage2_position_axial_replication` rollout evaluation only.

The completed Stage 2 data, HDF5 files, 25 policies, checkpoints, original
rollouts and original analysis are immutable inputs. Do not recollect data,
retrain policies, replace checkpoints, overwrite the original rollout
namespace, or reinterpret the original pre-registered result as if it used
condition-relative ID/OOD banks.

This rerollout asks:

> With 30 successful demonstrations per dataset-policy slot, how does the
> spatial extent of the Start training distribution trade off in-support
> learning and out-of-support generalisation?

No Position composition, Rotation, Velocity, cross-task, AR, human study,
data collection or policy training is authorised by this PLAN.

Do not commit, push or create a PR. Protect unrelated dirty-worktree changes
and the existing untracked files named `[`, `count=0`, `done` and `fi`.

## 2. Frozen inputs

Reuse exactly the completed Stage 2 25-policy matrix and the unified
checkpoint manifest:

```text
experiments/tro_stage2_position_axial_replication/manifests/checkpoints.json
SHA-256:
240a936999281f429dd1b043b19df5bd9291ed478933305a7c051c5183227580
```

Before any smoke or formal rollout, validate all 25 checkpoint paths and
SHA-256 values against that manifest. Freeze and record the hashes of the
completed Stage 2 `comparison.json` and `summary.md`; do not modify either.

Canonical seeds and actual source seeds remain:

```text
canonical 1 -> collection/training 1/1
canonical 2 -> collection/training 2/2
canonical 3 -> collection/training 3/3
canonical 4 -> collection/training 1702/2702
canonical 5 -> collection/training 1701/2701
```

## 3. Conditions and condition-relative support

The conditions and their Start training-support radii are:

| Condition | Start support radius | Approach radius |
|---|---:|---:|
| `START15_APP6` | 0.15 m | 0.060 m |
| `START35_APP6` | 0.35 m | 0.060 m |
| `START25_APP3P6` | 0.25 m | 0.036 m |
| `START25_APP6` | 0.25 m | 0.060 m |
| `START25_APP8P4` | 0.25 m | 0.084 m |

The active global deployment boundary is frozen at `R_MAX = 0.40 m`.

For a policy whose Start training-support radius is `R`:

| Start family | ID/inner bank, 25 states | OOD/outer bank, 25 states |
|---|---|---|
| `START15` | `[0.00, 0.15]` m | `(0.15, 0.40]` m |
| `START25` | `[0.00, 0.25]` m | `(0.25, 0.40]` m |
| `START35` | `[0.00, 0.35]` m | `(0.35, 0.40]` m |

The common boundary belongs to ID and is excluded from OOD. In continuous
sampling it has probability zero, but validators must enforce the convention.

`ID` and `OOD` in this PLAN refer only to the geometric support of the Start
XZ offset. They do not claim IID sampling from the finite accepted
demonstration dataset and do not define Approach-space ID/OOD.

## 4. Frozen state-manifest protocol

Formal rollout seeds are exactly `1,2,3,4,5`.

For every rollout seed, create one ID and one OOD manifest for each distinct
Start radius. Expected manifest count:

```text
3 Start radii x 5 rollout seeds x 2 banks = 30 manifests
```

Conditions with the same Start radius must use the exact same absolute state
IDs, state order, corridor starts, runtime RNG and point-cloud RNG. Therefore
the three `START25_*` conditions share manifests exactly.

Across different Start radii, absolute states necessarily differ. Pair them
using the same frozen normalized record for a given rollout seed, bank and
index:

```text
area quantile q
XZ direction theta
runtime RNG seed
point-cloud RNG seed
normalized state index
```

Map normalized records by:

```text
ID:  r = R * sqrt(q)
OOD: r = sqrt(R^2 + q * (0.40^2 - R^2))
```

This produces area-uniform disks and annuli. Cross-Start comparisons are
paired by normalized radial quantile and direction, not by identical absolute
positions. Analysis and prose must state this distinction.

All generated corridor starts must pass the existing deterministic IK
realisation check with `corridor_start_max_error = 0.025 m`. Scientific
unreachability for any Start family rejects that normalized candidate for all
three Start families at the same rollout-seed/bank/index. Advance all three to
the same deterministic replacement candidate; never replace only one Start
family. Record every rejection and replacement. Validate the explicit Gate 2
coverage criteria in section 0. The realised reachable-conditioned angular
distribution may be non-uniform and must be reported. If 25 valid paired
states or the explicit coverage criteria cannot be obtained, stop and report;
do not change 0.40 m or alter the sampling distribution.

Freeze the 30 manifests and their SHA-256 values before policy evaluation.
Register them under a new protocol ID in the shared rollout-manifest registry.
Do not replace or edit the original Stage 2 ten manifests.

## 5. Fixed rollout protocol

Reuse the completed Stage 2 runtime protocol:

```text
horizon              = 200
sample_hz            = 8
action_gap            = 2
action_dt             = 0.25 s
num_points            = 10000
terminate_on_success = true
success              = final cube z >= 0.20 m
formal videos        = disabled
```

Coverage:

```text
25 policies
x 5 rollout seeds
x 2 condition-relative banks
x 25 states
= 6,250 rollout rows

task unit:
5 canonical seeds x 5 conditions x 5 rollout seeds x 2 banks
= 250 tasks, exactly 25 rows per task
```

Use `sbatch --parsable`, an appropriate array throttle and supported
A100/L40S/H100/H200-class hardware. Avoid known Blackwell `sm_120`
incompatibility and previously identified faulty nodes.

## 6. Artifact namespace

Small artifacts:

```text
experiments/tro_stage2_position_axial_idood_rerollout/
  PLAN.md
  commands.md
  implementation_notes.md
  manifests/
    protocol.json                       # rejected RMAX45 pilot, immutable
    checkpoint_reuse.json               # rejected RMAX45 pilot, immutable
    protocol_rmax40.json
    checkpoint_reuse_rmax40.json
    rollout_5seed/                       # rejected RMAX45 pilot, immutable
    rollout_5seed_rmax40/
    jobs.json
    final_hashes.json
    storage_inventory.json
  analysis/
    comparison.json
    summary.md
    figures/
```

New rollout rows and logs:

```text
dataset/tro_position_stage2_axial_idood_rerollout/rmax40/
```

Infrastructure retry residue:

```text
dataset/tro_position_stage2_axial_idood_rerollout/rmax40/infrastructure_retries/
```

Do not copy models. Reference the original checkpoint paths and hashes.

## 7. Analysis

The independent learner unit remains the dataset-policy slot. Rollout rows
and rollout seeds are nested deployment trials.

Report for every policy:

- ID successes/125 and rate;
- OOD successes/125 and rate;
- five rollout-seed rates for each bank, mean and sample standard deviation
  with `ddof=1`;
- generalisation gap `OOD rate - ID rate`;
- balanced descriptive score `0.5 * (ID rate + OOD rate)`.

Report for every condition:

- five-policy ID mean and sample standard deviation;
- five-policy OOD mean and sample standard deviation;
- five-policy generalisation-gap mean and sample standard deviation;
- separate ID and OOD rankings;
- the balanced score only as a descriptive condition-relative summary.

Do not describe the balanced score as performance on a common absolute test
distribution: the ID and OOD radial intervals differ across Start families.
Use a two-dimensional ID/OOD table and Pareto interpretation as the primary
answer to which training distribution learns well and generalises.

Required comparisons:

1. Start-radius response among `START15_APP6`, `START25_APP6` and
   `START35_APP6`, reported separately for ID and OOD.
2. Approach-radius response among the three `START25_*` conditions, for which
   absolute states remain exactly paired.
3. Canonical-seed paired deltas and all-five policy-level means.
4. Canonical seed1-3 and alias seed4-5 sensitivities.
5. Wilson intervals as rollout-level descriptions only.
6. Canonical-seed cluster bootstrap as policy-level uncertainty.
7. Exact checkpoint-hash, bank-bound, state-order and RNG assertions.
8. IK rejection/replacement counts and realised radial distributions.

No result-dependent retries, checkpoint changes, bank-bound changes or
post-hoc threshold changes are permitted.

## 8. Gates

### Gate 0: audit

- Protect the dirty worktree and all completed Stage 2 artifacts.
- Verify the unified checkpoint-manifest hash and all 25 checkpoint hashes.
- Freeze old Stage 2 analysis hashes.
- Write the new `protocol.json` and `checkpoint_reuse.json`.

### Gate 1: implementation and tests

- Add a new ID/OOD rerollout profile without changing old Stage 2 manifests or
  analysis semantics.
- Add validators for condition-specific bounds, normalized pairing, exact
  same-Start absolute pairing and checkpoint hashes.
- Test the three exact ID/OOD interval pairs, area-uniform mappings,
  `R_MAX=0.40`, 30 manifests, 250 tasks and 6,250 rows.
- Run existing Stage 2 tests plus the new tests.

### Gate 2: manifest feasibility and smoke

- Generate the 30 manifests in a new namespace.
- Audit IK rejection rates and realised radius/angle coverage.
- Run a separate smoke for all three Start families and both banks.
- Smoke rows never enter formal analysis.

### Gate 3: formal rerollout

- Submit exactly 250 tasks.
- Monitor `squeue`, `sacct` and logs until terminal.
- Retry only infrastructure failures with identical frozen inputs.
- Archive partial outputs before clean retry.

### Gate 4: strict merge

- Require 250/250 task summaries and 6,250/6,250 unique rows.
- Require every policy to have exactly 125 ID and 125 OOD trials.
- Verify checkpoint hashes, rollout seeds, condition-specific bounds,
  normalized pairing, state order and both RNG streams.

### Gate 5: analysis and handoff

- Produce ID, OOD and gap results, rankings, paired comparisons, uncertainty,
  figures and limitations.
- Update commands, jobs, hashes, registries and storage inventory.
- Update the dedicated rerollout handoff.
- Stop; do not launch any further experiment.

## 9. Infrastructure retries

Clean retry is allowed only for `PREEMPTED`, `TIMEOUT`, node failure, GPU ECC,
scheduler/infrastructure failure, or a task confirmed to lack a complete
valid artifact. Low success, an unfavorable ranking or a large
generalisation gap is never a retry reason.

## 10. Definition of Done

- Original Stage 2 artifacts and hashes are unchanged.
- The original 25 checkpoints are revalidated and no policy is retrained.
- 30/30 condition-relative state manifests are frozen.
- All new and existing tests pass.
- Smoke validates the 0.40 m boundary and all three ID/OOD definitions.
- 250/250 formal tasks reach a valid terminal state.
- 6,250/6,250 rollout rows pass strict validation.
- Every policy has exactly 125 ID and 125 OOD trials.
- Same-Start absolute pairing and cross-Start normalized pairing both pass.
- ID, OOD, generalisation gap and descriptive balanced results are complete.
- Jobs, retries, commands, figures, hashes, registries and storage inventory
  are complete.
- The dedicated handoff is updated.
- No data collection, policy training or out-of-scope experiment is started.
