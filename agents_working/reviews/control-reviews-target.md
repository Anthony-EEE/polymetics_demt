# Control Agent Review of Target

_Owner: Control agent · Target agent access: read-only_

The Control agent records read-only audits of the Target pipeline here. It must not modify Target artifacts.

## Review Checklist

- [ ] Target outputs are labelled `simulation_target_group`.
- [ ] No Target file appears under Control data/model/rollout roots.
- [ ] Exactly 10 participant datasets exist with 30 successful demos each.
- [ ] Every raw demo begins at `policy_inference_start` after validated grasp/lift.
- [ ] Ten participant-specific HDF5 files share one schema.
- [ ] Ten policies share training config, seed and checkpoint rule.
- [ ] All policies use the same 10 distinct paired rollout specs.
- [ ] Exactly 100 rollout records exist and pass artifact validation.
- [ ] Final mean ± std uses the 10 participant EDSRs, not 100 rollouts as independent human samples.

## Findings

None yet. Target full pipeline has not started.

