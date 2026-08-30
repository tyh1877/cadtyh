# Try-3 native Fusion joint-axis capability record — environment limitation

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

## Scope under the 2026-08-30 amendment

This record is not a Try-3 NO-GO. The frozen sanitized URDF is the external
authoritative kinematic representation, while Fusion is evaluated for editable
geometry, embodiment, interfaces, placement, export and rebuild. Native
Fusion joint semantics are desirable but non-blocking; see
`AMENDMENT_EXTERNAL_KINEMATIC_AUTHORITY.md`.

## Planning matrix retained

`build_fusion_jobs.py` deterministically produced 10 planned V1/V2 rows:
9 `READY`, 1 `UPSTREAM_FAILURE` (`V1/dev_arm-4c7b408826`, invalid model JSON).
All five frozen V0 sources are successful. The one planning failure remains in
the denominator; no Fusion result was substituted for it.
