# Ablation 1: Spatial Structure / Corridor Geometry Plan

_Date: 2026-06-27_

## Goal

This document plans the first short-term CoRL rebuttal ablation: spatial
structure. The goal is to explain how the DEMT spatial corridor guidance should
be translated into concrete parameters, rather than treating the corridor values
in the appendix as arbitrary.

The key correction is that the spatial corridor is not a single radius. It has
at least two meaningful variables:

- `corridor_start_radius`: the allowed spread at the wide entry of the corridor.
- `pre_grasp_radius`: the allowed spread at the bend / throat near the
  object-above `pre_grasp` waypoint.

Important: `corridor_start` is not the robot initial position. It is the wide
entry region of the guidance corridor. The robot end-effector may start anywhere
in the reachable initialization workspace, then enter the corridor.

## Current Code Reality

The current simulation scripts are useful starting points but do not yet match
the paper's real-robot setting.

### `examples/main.py`: Cube Pick-and-Lift

Current successful trajectory:

```text
home -> open_gripper -> pre_grasp -> grasp -> close_gripper -> lift
```

Relevant current targets:

```python
home = np.array([0.45, 0.00, 0.45])
base_pre_grasp = np.array([cube[0], cube[1], 0.22])
pre_grasp = base_pre_grasp + approach_offset
grasp = np.array([cube[0], cube[1], 0.04])
lift = np.array([cube[0], cube[1], 0.30])
```

Current approach variation only affects `pre_grasp`:

```text
--approach-noise-mode none | xz_grid | xz_uniform | xyz_uniform
--approach-noise-radius <meters>
```

This is useful, but it only models variation around the object-above pre-grasp
point. It does not model the full funnel-shaped spatial corridor.

### `examples/main_insert.py`: Peg Insertion

Current full insertion trajectory:

```text
home -> open_gripper -> pre_grasp -> grasp -> hold_gripper -> lift
     -> pre_insert -> align -> insert -> insert_hold -> release -> retreat
```

Relevant current targets:

```python
home = np.array([0.45, 0.00, 0.45])
pre_grasp = np.array([peg[0], peg[1], 0.25])
grasp = np.array([peg[0], peg[1], 0.11])
lift = np.array([peg[0], peg[1], 0.33])
pre_insert = np.array([hole[0], hole[1], 0.33])
align = np.array([hole[0], hole[1], 0.19])
insert = np.array([hole[0], hole[1], 0.105])
```

Current insertion code has no approach-noise CLI. It also uses a fixed `home`
target before the scripted task.

### Mismatch with the Paper

The paper's real-robot study initializes the robot end-effector randomly over a
reachable plane. For this planned simulation ablation, that plane should be the
`y = 0` plane in robot coordinates, with `x > 0` and `z > 0`. The current scripts
instead move from a fixed home target:

```text
home = [0.45, 0.00, 0.45]
```

For this spatial ablation, the fixed-home setup is not enough. If every
demonstration starts from the same scripted home point, then
`corridor_start_radius` is not really being tested. The experiment would only
test variation near `pre_grasp`, which is not the full corridor.

Therefore, random EE initialization is a required planned change before running
this ablation.

No code changes are made in this document.

## Corridor Geometry Interpretation

The AR spatial guidance can be treated as a curved funnel from left to right:

```text
random EE start on y = 0 reachable x-z plane
      |
      v
wide corridor entry / corridor_start
      |
      v
curved approach path toward object
      |
      v
narrow bend / pre_grasp above object
      |
      v
vertical descent funnel to grasp/contact
```

The corridor has two spatial bottlenecks:

1. Entry width: how much variation is allowed when the user enters the general
   approach path.
2. Pre-grasp width: how much variation is allowed at the critical object-above
   waypoint before vertical descent.

After `pre_grasp`, the descent to `grasp` should remain tight because contact
success is highly sensitive to final alignment. In the paper's appendix this is
roughly reflected by:

```text
r_start = 25 cm
r_middle = 5 cm
r_final = 3 cm
```

For this ablation, `r_final` should probably be held fixed near the object size
or current successful grasp tolerance. The two variables to study are:

```text
corridor_start_radius
pre_grasp_radius
```

## Proposed Experimental Question

Main question:

```text
How wide can the spatial corridor entry and pre-grasp bottleneck be before
deployment learning degrades under the fixed learner and finite demonstration
budget?
```

More concretely:

```text
Does deployment performance depend more on the wide entry region, the
pre-grasp bottleneck, or their interaction?
```

Expected answer:

- A larger `corridor_start_radius` may be tolerable because the robot can still
  converge to a shared approach path.
- A larger `pre_grasp_radius` should hurt learning more, because it changes the
  object-relative approach and descent geometry close to contact.
- Very large values for either may produce demonstrations that are all
  task-successful but less learnable.

## Recommended Scope

For CoRL rebuttal, do not run a dense 2D grid. Use a small factorial design that
can be explained clearly.

### Minimal 2 x 2 Design

Use two levels for each variable:

| Condition | `corridor_start_radius` | `pre_grasp_radius` | Meaning |
| --- | ---: | ---: | --- |
| `P00` | small | small | Tight corridor baseline |
| `P10` | large | small | Wide entry, tight pre-grasp |
| `P01` | small | large | Tight entry, loose pre-grasp |
| `P11` | large | large | Loose corridor |

This is the cleanest design for answering whether the pre-grasp bottleneck
matters more than the entry width.

### Suggested Numeric Levels

Initial candidate values:

| Level | `corridor_start_radius` | `pre_grasp_radius` |
| --- | ---: | ---: |
| small | `0.10 m` | `0.02 m` |
| large | `0.25 m` | `0.06 m` |

These values are intentionally tied to the appendix intuition:

- `0.25 m` resembles the current `r_start = 25 cm`.
- `0.05-0.06 m` resembles the middle corridor scale.
- `0.02-0.03 m` resembles the final tight approach/grasp scale.

If smoke tests show the perturbation is too weak, increase the large
`pre_grasp_radius` to `0.08 m`. If demonstrations fail too often before policy
training, reduce it to `0.04-0.05 m`.

### Optional 3 x 3 Design

Only use this if the 2 x 2 smoke test is stable and compute is available:

| Level | `corridor_start_radius` | `pre_grasp_radius` |
| --- | ---: | ---: |
| tight | `0.05 m` | `0.01 m` |
| medium | `0.15 m` | `0.03 m` |
| loose | `0.25 m` | `0.06 m` |

This gives 9 spatial conditions, which may be too expensive for rebuttal if each
condition needs multiple dataset seeds and policy training runs.

## How to Generate Demonstrations Conceptually

The current `approach_offset` implementation only samples offsets around
`pre_grasp`. For this ablation, the planned trajectory should be parameterized
by two sampled waypoints:

```text
start_ee       sampled over reachable initialization plane
corridor_start sampled around a nominal corridor entry waypoint
pre_grasp      sampled around the object-above waypoint
grasp          fixed object-relative contact point
lift           fixed or lightly controlled
```

For cube pick-and-lift:

```text
random_start -> corridor_start -> pre_grasp -> grasp -> close -> lift
```

For insertion:

```text
random_start -> corridor_start_pick -> pre_grasp -> grasp -> lift
             -> corridor_start_insert or pre_insert -> align -> insert
```

For the first spatial ablation, I recommend starting with cube pick-and-lift.
It isolates the corridor-to-pre-grasp question more cleanly. Insertion can be
used as a second validation task if time allows.

## Random EE Initialization Plan

This is required to match the paper's setting.

Instead of always moving from fixed `home = [0.45, 0.00, 0.45]`, each demo
should begin with an end-effector pose sampled from the reachable part of the
`y = 0` x-z plane.

Suggested initialization constraint:

```text
y = 0
x > 0
z > 0
point must pass IK / reachability checks
```

Concrete bounds should be chosen after a quick IK/reachability smoke test. A
reasonable initial search box is:

```text
x in [0.20, 0.60]
y = 0
z in [0.20, 0.60]
```

but the final set should be the reachable subset of this x-z plane, not the
entire rectangle.

Important design detail:

```text
The random initial EE position is not the same as corridor_start.
```

The random initial EE position creates deployment-like start variation on the
`y = 0` x-z plane. The `corridor_start` waypoint represents the first shared
spatial structure that the teacher is supposed to enter before moving along the
funnel. These must be recorded separately in metadata.

A planned data-generation sequence should therefore be:

1. Reset robot joints to a stable configuration.
2. Sample a reachable random initial EE pose.
3. Move or kinematically place the EE at that random initial pose before saving
   task frames.
4. Begin the recorded demonstration from the random initial pose.
5. Move toward sampled `corridor_start`.
6. Move toward sampled `pre_grasp`.
7. Descend to `grasp`.
8. Complete the task.

Whether step 3 should be saved depends on the exact learning dataset definition.
For matching the real-robot study, the initial pose and motion from it should be
part of the demonstration. The old fixed `home` phase should not dominate the
dataset.

## Candidate Geometry for Cube Pick-and-Lift

Use the cube position as the task anchor:

```text
cube = [cube_x, cube_y, cube_z]
base_pre_grasp = [cube_x, cube_y, 0.22]
grasp = [cube_x, cube_y, 0.04]
lift = [cube_x, cube_y, 0.30]
```

Define a nominal `corridor_start` as an object-relative corridor entry center:

```text
base_corridor_start = [target_x - d_entry, target_y, pre_grasp_z + h_entry]
```

For cube pick-and-lift this becomes:

```text
target_x = cube_x
target_y = cube_y
pre_grasp_z = 0.22
d_entry = 0.20 m
h_entry = 0.05-0.08 m

base_corridor_start = [cube_x - 0.20, cube_y, 0.27-0.30]
```

Rationale:

- The entry center should align with the target object's `y`, so the corridor
  does not introduce an extra lateral bias.
- The entry center should be slightly higher than `pre_grasp`, so the funnel can
  narrow into the object-above bend before the vertical descent.
- The entry center should be offset to the left in `x`, so the planned path
  preserves the left-to-right funnel shape.

For this ablation, keep `d_entry` and `h_entry` fixed. Only ablate the two
radii: `corridor_start_radius` and `pre_grasp_radius`.

Then sample:

```text
corridor_start = base_corridor_start + delta_start
pre_grasp = base_pre_grasp + delta_pre
```

where:

```text
delta_start_xz sampled inside radius corridor_start_radius, with y fixed
delta_pre_xz sampled inside radius pre_grasp_radius, with y fixed
```

Keep `y` fixed at the task plane for the first version. Because your corridor is
drawn in the `y = 0` x-z plane, the first spatial ablation should vary `x` and
`z`, not `y`.

```text
delta_start = [dx, 0, dz]
delta_pre = [dx, 0, dz]
```

The interpretation is therefore in the same plane as the guidance: a wide
left-side entry narrows toward the object-above `pre_grasp`, then descends
tightly toward contact.

## Candidate Geometry for Peg Insertion

There are two possible spatial bottlenecks in insertion:

1. Pick-side corridor: approach peg, grasp peg, lift.
2. Insert-side corridor: approach hole, align, insert.

For rebuttal, avoid doing both at once. It would create too many variables.

Recommended plan:

- Use cube pick-and-lift for the main spatial corridor ablation.
- Use insertion only as a confirmatory task if time allows.
- If insertion is used, focus on the insert-side bottleneck:

```text
random_start_with_held_peg -> corridor_start_insert -> pre_insert -> align -> insert
```

This can use `--start-with-peg` / `run_insert_only()` conceptually, because it
isolates insertion geometry without adding pick-side variation.

For insert-only:

```text
base_pre_insert = [hole_x, hole_y, 0.33]
align = [hole_x, hole_y, 0.19]
insert = [hole_x, hole_y, 0.105]
base_corridor_start_insert = [hole_x - 0.20, hole_y, 0.35]
```

Then sample:

```text
corridor_start_insert = base_corridor_start_insert + delta_start
pre_insert = base_pre_insert + delta_pre
```

Again, keep the final `align` and `insert` tight so the task remains
task-successful and the ablation tests learnability rather than failure to
generate successful demos.

## Metrics

Primary metric:

```text
EDSR = empirical deployment success rate
```

Fixed controls:

- Same learner.
- Same demonstration budget, ideally `N = 30`.
- Same sample rate, currently `30 Hz`.
- Same rollout count, ideally `K = 10`.
- Same object distribution within each task.
- Same success criterion.

Secondary diagnostics:

- MPCV: path geometry consistency.
- Frame count per phase.
- Distribution of sampled `corridor_start`.
- Distribution of sampled `pre_grasp`.
- Distance from trajectory to nominal corridor centerline.

For this ablation, the most important diagnostic is to separately report:

```text
std / radius of corridor_start samples
std / radius of pre_grasp samples
```

This prevents the result from collapsing into a vague "approach noise" claim.

## Expected Outcomes

Likely pattern:

| Condition | Expected Learnability |
| --- | --- |
| small start, small pre-grasp | highest or near-highest |
| large start, small pre-grasp | still high |
| small start, large pre-grasp | lower |
| large start, large pre-grasp | lowest |

If this happens, the story is strong:

```text
The wide entry of the corridor can tolerate natural start variation, but the
pre-grasp bottleneck must remain tight. This explains why the AR spatial
guidance is funnel-shaped instead of a uniform tube.
```

This is more precise than the current paper story, which only says spatial
consistency matters.

## Smoke Test First

Before running full policy training:

1. Generate a few demos for each of the four 2 x 2 conditions.
2. Inspect `metadata.json`.
3. Verify the sampled random starts are reachable.
4. Verify `corridor_start` and `pre_grasp` are saved.
5. Verify phase labels are sensible.
6. Verify all demos are task-successful.
7. Check that failed demos are not silently biasing the dataset toward easier
   samples.

Potential failure mode:

```text
Large pre_grasp radius may create off-center descents that fail to grasp.
```

If too many demos fail, do not simply retry until success without recording the
attempt distribution. Otherwise, the successful dataset may no longer represent
the intended radius. The metadata should record attempts, rejected samples, and
the final accepted sampled points.

## Rebuttal Claim Enabled by This Ablation

If the experiment works, the rebuttal can say:

```text
We added a spatial-parameter ablation that separates the corridor entry width
from the pre-grasp bottleneck. The results show that deployment performance is
more sensitive to variation near the pre-grasp bend than to variation at the
wide corridor entry. This supports the funnel-shaped spatial guidance used in
DEMT: a permissive entry region helps accommodate random initial robot poses,
while a tight pre-grasp bottleneck preserves a learnable object-relative
approach before contact.
```

This directly addresses:

```text
Why does the spatial AR guidance look like a curved funnel rather than a single
uniform tube?
```

## Practical Recommendation

For the next implementation step, keep the first version narrow:

1. Cube pick-and-lift only.
2. Random EE initialization enabled.
3. Four spatial conditions from the 2 x 2 design.
4. X-z plane variation only for `corridor_start` and `pre_grasp`, with `y = 0`.
5. Fixed final descent/grasp/lift.
6. Full metadata recording for sampled start, corridor entry, pre-grasp, and
   success/failure.

After the cube result is stable, decide whether to add insert-only as a second
task. Do not start with both cube and full peg insertion, because that will mix
too many sources of variation.

## Open Decisions

- Exact reachable EE initialization range on the `y = 0`, `x > 0`, `z > 0`
  plane.
- Whether random initial EE placement should be saved as a phase or treated as
  setup before recording.
- Whether `corridor_start` should be object-relative or fixed in world space.
- Exact x-z sampling distribution for `corridor_start` variation.
- Exact x-z sampling distribution for `pre_grasp` variation.
- Whether insertion should use full pick-and-insert or insert-only with the peg
  already held.
- Whether failed sampled trajectories should be saved separately for analysis or
  only counted in metadata.
