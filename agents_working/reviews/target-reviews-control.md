# Target Agent Review of Control

_Owner: Target agent · Control agent access: read-only_

The Target agent records read-only audits of the Control pipeline here. It must not modify Control artifacts.

## Review Checklist

- [ ] Control outputs are labelled `simulation_control_group`.
- [ ] No Control file appears under Target data/model/rollout roots.
- [ ] Frozen simulator and success criteria match Target.
- [ ] Scripted initial pose is `[box_x, box_y, box_z + 0.10]`.
- [ ] Training data starts after validated grasp/lift.
- [ ] Demonstration budget and HDF5 schema match Target.
- [ ] Learner, training seed/config and checkpoint rule match Target.
- [ ] Rollouts use the same frozen paired specs as Target.
- [ ] Statistics use participant-level policies as the independent units.

## Findings

None yet. Control protocol has not been authorised.

