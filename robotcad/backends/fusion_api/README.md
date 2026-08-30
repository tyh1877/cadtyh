# FusionAPIBackend v1

This is a deterministic adapter executed inside Fusion. It accepts only
`robotcad.skill_call.v1` data and records created Fusion feature IDs. It never
reads an image, robot name, GT mesh, evaluator score, MEP, or URDF directly.
The caller has already resolved those into SkillCall parameters.

`FusionAPIBackend.py` is intentionally a reusable backend implementation, not
a generated per-case program. `FusionAPIBackendSmoke.py` invokes six composite
skills with fixed non-benchmark inputs.
