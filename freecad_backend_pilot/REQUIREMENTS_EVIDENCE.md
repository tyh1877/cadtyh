# FreeCAD Backend Pilot requirement-to-evidence checklist

| Requirement | Evidence artifact | Status |
|---|---|---|
| Audit current FreeCAD runtime and MCP/API availability | `freecad_capability_audit.md` | blocked — FreeCAD executable/modules and FreeCAD MCP are unavailable |
| Reuse existing 6 operation-plan pilot links | `input_manifest.csv` | pass — six existing link plans listed |
| Define Executable CAD IR v1 before backend execution | `schemas/executable_cad_ir_v1.schema.json`, `docs/executable_cad_ir_v1.md` | pass |
| Run operation-level native smoke tests without silent fallback | `results/operation_smoke_results.csv` | blocked — 10/10 operations marked `BLOCKED_ENVIRONMENT`; no success claimed |
| Execute six link plans through FreeCAD backend | `results/link_execution_results.csv` | blocked — 6/6 links marked `BLOCKED_ENVIRONMENT`; no success claimed |
| Record per-operation execution status and failure reasons | `logs/*/execution_log.json` | blocked — FreeCAD runtime unavailable |
| Save/reopen FCStd and export STEP/STL | `artifacts/**`, results CSVs | blocked — FreeCAD runtime unavailable |
| Run reproducibility checks | `results/reproducibility_results.csv` | blocked — trial count 0 because FreeCAD runtime unavailable |
| Report backend migration recommendation | `freecad_backend_pilot_report.md` | pending — cannot recommend until FreeCAD is installed and smoke tests run |
