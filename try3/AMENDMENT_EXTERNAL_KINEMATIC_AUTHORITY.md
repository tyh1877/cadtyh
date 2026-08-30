# Try-3 amendment: external kinematic authority and native-joint scope

Approved by the user on 2026-08-30. This amendment supersedes the prior
Try-3 interpretation that native Fusion joint-field persistence is a hard
experiment gate.

The frozen sanitized URDF remains the authoritative source for link topology,
parent-child structure, joint type, origin, axis, limits, forward kinematics,
and motion semantics. Fusion is responsible for editable component geometry,
mechanical embodiment and interfaces, canonical occurrence placement at the
URDF pose, parametric features, F3D/STEP/STL export, rebuild, and CAD
editability.

Native Fusion joints are an optional execution/display capability. Internal
representations such as `CustomJointDirection` and `ZAxisJointDirection` are
not acceptance targets. If a native joint can be semantically inspected, its
origin, world-space axis, limits and driven motion may be reported as PASS,
PARTIAL, or ENVIRONMENT_LIMITATION. None of those statuses blocks V1/V2
geometry, interface, placement, or URDF-driven motion evaluation.

This amendment does not change TrySet-5, frozen inputs, model, versions,
no-GT policy, evaluator, or the absence of automatic repair.
