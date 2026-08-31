# FusionAPIBackend v1

This is a deterministic adapter executed inside Fusion. It accepts only
`robotcad.skill_call.v1` data and records created Fusion feature IDs. It never
reads an image, robot name, GT mesh, evaluator score, MEP, or URDF directly.
The caller has already resolved those into SkillCall parameters.

`FusionAPIBackend.py` is intentionally a reusable backend implementation, not
a generated per-case program. `FusionAPIBackendSmoke.py` invokes the formal
basic CAD operation set with fixed non-benchmark inputs.

Formal Try-3 jobs use `CreateCompositeLinkGeometry` as the primary link body
skill. Its parameters contain normalized `box`, `cylinder`, `cone`, and
`sphere` primitives produced by the frozen planner output. V2 then applies
verified basic CAD operation skills: `ApplyFillet`, `ApplyChamfer`,
`CreateHole`, `BooleanCut`, and `CircularPattern`. The backend creates these
features generically inside the target component and does not apply any
case-specific robot template. Middle-layer feature names such as slot, groove,
rib, and pocket are not valid formal SkillCalls.
