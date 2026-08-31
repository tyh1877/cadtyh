# FusionAPIBackend v1 basic-operation smoke — PASS

The previous 2026-08-30 smoke result used middle-layer mechanical template
names and is no longer valid for the repaired Try-3 backend.

The repaired smoke gate was rerun manually in Autodesk Fusion using the
generic, non-benchmark `FusionAPIBackendSmoke.py` script. The untracked raw
record is `try3/smoke/fusion_api_skill_smoke.json`; generated F3D/STEP/STL
artifacts remain deliberately outside Git.

| Skill | Persisted Fusion feature type | Status |
|---|---|---|
| CreateSketchProfile | Sketch | PASS |
| Extrude | ExtrudeFeature | PASS |
| Loft | LoftFeature | PASS |
| ApplyFillet | FilletFeature | PASS |
| ApplyChamfer | ChamferFeature | PASS |
| CreateHole | ExtrudeFeature with CutFeatureOperation | PASS |
| BooleanCut | ExtrudeFeature with CutFeatureOperation | PASS |
| CircularPattern | CircularPatternFeature | PASS |

The raw record has 10 successful calls, no errors, real native feature types,
successful export to F3D/STEP/STL, and no fallback to another formal Skill.
This smoke gate does not constitute a Try-3 result.
