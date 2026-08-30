# Try-3 Fusion native joint-axis gate — NO-GO

Date: 2026-08-30. Environment: the installed local Fusion 360 API, parametric
design, `AsBuiltJoint` executor. The source smoke script is
`try3/fusion_scripts/Try3JointFrameLimitSmoke/Try3JointFrameLimitSmoke.py`.

## Fixed acceptance condition

For a revolute joint at world origin `(2, 3, 4)` cm, the persisted native
motion must use a world-Y custom axis, and retain limits `[-1.25, 1.5]` rad.
The script reads the native AsBuiltJoint state after `design.computeAll()`.

## Direct evidence

The final run's lightweight record (`joint_frame_limit_smoke_result.json`,
intentionally kept outside Git) reports:

| Field | Observed | Expected | Result |
|---|---:|---:|---|
| Origin | `(2, 3, 4)` cm | `(2, 3, 4)` cm | pass |
| Limits | `[-1.250000000000822, 1.49999999999959]` rad; both enabled | `[-1.25, 1.5]` rad | pass |
| Native axis mode | `2` (Fusion's `ZAxisJointDirection`) | `3` (`CustomJointDirection`) | fail |
| Custom entity | `null` | persistent world-Y line | fail |

The last implementation followed Autodesk's documented mutation path: roll the
timeline immediately before the AsBuiltJoint, then call
`setAsRevoluteJointMotion(CustomJointDirection, geometry, sketchLine)`.
Fusion returned `redefine_success: true`, but after recompute it still stored
Z-axis mode and no custom axis entity. Earlier input-object and construction-
axis attempts produced the same persisted Z mode. This rules out a mere
comparison, cache, or input-signature error in this environment.

## Consequence

The formal Try-3 executor must **not** run the 9 otherwise-ready V1/V2 jobs:
their claim requires preserved native URDF axis/origin/limits. It can currently
prove only native origin and limits, not the arbitrary axis. Therefore Try-3 is
an executor-level **NO-GO**, not evidence about V1/V2 geometry quality or the
mechanical-embodiment hypothesis.

## Planning matrix retained

`build_fusion_jobs.py` deterministically produced 10 planned V1/V2 rows:
9 `READY`, 1 `UPSTREAM_FAILURE` (`V1/dev_arm-4c7b408826`, invalid model JSON).
All five frozen V0 sources are successful. The one planning failure remains in
the denominator; no Fusion result was substituted for it.
