# Rebuttal Simulation Agent Coordination

_Created: 2026-08-06 · Branch: `hpc-headless-rebuttal` @ `72ca390`_

This directory coordinates two independent rebuttal simulation pipelines:

- `simulation_target_group`: active and fully specified.
- `simulation_control_group`: active and user-authorised on 2026-08-06.

## Ownership

| File or path | Owner | Other agent's access |
|---|---|---|
| `agents_working/target-simulation.md` | Target agent | Read-only |
| `agents_working/control-simulation.md` | Control agent | Read-only |
| `agents_working/reviews/target-reviews-control.md` | Target agent | Read-only |
| `agents_working/reviews/control-reviews-target.md` | Control agent | Read-only |
| `rebuttal_dataset/simulation_target_group/` | Target agent | Read-only |
| `rebuttal_dataset/simulation_control_group/` | Control agent | Read-only |
| `examples/main_obstacle_transport_target_participants.py` | Target agent | Read-only |
| `examples/main_obstacle_transport_control_participants.py` | Control agent | Read-only |
| `examples/rebuttal_target_pipeline/` | Target agent | Read-only |
| `examples/rebuttal_control_pipeline/` | Control agent | Read-only |
| `agents_working/target-agent-prompt.md` | Coordinator | Read-only |
| `agents_working/control-agent-prompt.md` | Coordinator | Read-only |

`README.md` and shared task/evaluation code are coordinator-owned. Neither group agent may edit them without recording a proposed shared change in its own status file and receiving coordinator approval.

## Frozen Shared Interface

The current shared environment is defined by:

- `examples/main_obstacle_transport.py`
- `examples/eval_obstacle_transport_trained_policy.py`

The following protocol is frozen for comparability unless the user explicitly changes it:

- Cube physics, obstacle geometry, target and success criteria.
- Panda base pose and fixed gripper orientation.
- Scripted EE initial pose `[box_x, box_y, box_z + 0.10]`, with no horizontal offset.
- Scripted grasp/lift before data collection or policy inference.
- `frame_0 = policy_inference_start`; no scripted setup frames in training data.
- Incremental Cartesian IK during scripted demonstration transport.
- HDF5 observation/action schema, training configuration and paired rollout protocol must be identical across groups except for the intended teaching-data manipulation.

The authorised Control manipulation is spatial only: C01–C05 use L and
C06–C10 use R; every participant retains 30 successful demonstrations sampled
independently from the full corresponding route x-z support. Control has no
personal waypoint centre and no across-demo contraction. Invalid, unreachable,
or unsuccessful samples are replenished. Rotation and velocity remain at the
frozen shared settings so the group comparison isolates spatial consistency.

## Isolation Rules

1. Never write outside the owner's data, script, status and review paths listed above.
2. Never reuse, rename, delete or overwrite the other group's datasets, HDF5 files, checkpoints, manifests, logs or summaries.
3. Use explicit group labels in every manifest and result: `simulation_target_group` or `simulation_control_group`.
4. Use separate Slurm job names, log directories, model roots and rollout output roots.
5. Never edit a shared file to fix only one group. Propose the change, document its effect on both groups and wait for coordinator approval.
6. Failed attempts remain diagnostic artifacts but must not enter successful training HDF5 files.
7. Before declaring a stage complete, run the validators described in the group's status file and record exact artifact paths.
8. An agent may audit the other group read-only and write findings only in its own review file.

## Mutual Supervision

Target agent audits Control in `reviews/target-reviews-control.md`. Control agent audits Target in `reviews/control-reviews-target.md`.

Each review must check:

- group/path isolation;
- shared environment and success-criterion parity;
- demonstration counts and post-grasp collection boundary;
- HDF5 schema parity;
- identical training hyperparameters and checkpoint selection rule;
- paired rollout seeds/specs;
- participant-level statistical aggregation;
- missing, stale or partially written artifacts.

A review finding is advisory: the reviewer does not modify the other group's files. The owning agent fixes it and records the resolution in its own status file.

## Start Procedure

Every agent must, in order:

1. Read this file without editing it.
2. Read `handoffs/handoff_rebuttal.md`.
3. Read only its own group status file.
4. Confirm its output root does not overlap the other group.
5. Record `IN_PROGRESS`, current timestamp and active stage in its own status file.
6. Proceed only within its assigned group.
