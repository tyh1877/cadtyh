# FusionAPIBackend v1 basic-operation smoke — PENDING RERUN

The previous 2026-08-30 smoke result used middle-layer mechanical template
names and is no longer valid for the repaired Try-3 backend.

The current smoke gate must be rerun manually in Autodesk Fusion using the
generic, non-benchmark `FusionAPIBackendSmoke.py` script. The untracked raw
record is `try3/smoke/fusion_api_skill_smoke.json`; generated F3D/STEP/STL
artifacts remain deliberately outside Git.

| Skill | Persisted Fusion feature type | Status |
|---|---|---|
| CreateCompositeLinkGeometry | ExtrudeFeature / LoftFeature | pending |
| ApplyFillet | FilletFeature | pending |
| ApplyChamfer | ChamferFeature | pending |
| CreateHole | ExtrudeFeature with CutFeatureOperation | pending |
| BooleanCut | ExtrudeFeature with CutFeatureOperation | pending |
| CircularPattern | CircularPatternFeature | pending |

The smoke passes only if every listed SkillCall produces the corresponding
native Fusion feature without fallback to another formal Skill. This smoke gate
does not constitute a Try-3 result.
