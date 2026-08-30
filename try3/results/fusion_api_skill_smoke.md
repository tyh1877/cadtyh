# FusionAPIBackend v1 composite-skill smoke — PASS

Executed manually in Autodesk Fusion on 2026-08-30 using the generic,
non-benchmark `FusionAPIBackendSmoke.py` script. The untracked raw record is
`try3/smoke/fusion_api_skill_smoke.json`; generated F3D/STEP/STL artifacts are
also deliberately outside Git.

| Skill | Persisted Fusion feature type | Status |
|---|---|---|
| CreateRotaryJointHousing | RevolveFeature | PASS |
| CreateLoftedLinkHousing | LoftFeature | PASS |
| CreateRoundedLinkHousing | FilletFeature | PASS |
| CreateFlangeInterface | ExtrudeFeature | PASS |
| CreateShellHousing | ShellFeature | PASS |
| CreateJointTransition | LoftFeature | PASS |

The raw record has six non-empty feature tokens, no errors, successful
`design.computeAll()`, and F3D, STEP, and STL paths with nonzero files. This
passes the adapter smoke gate only; it does not constitute a Try-3 result.
