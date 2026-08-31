# FreeCAD Backend Pilot requirement-to-evidence checklist

| Requirement | Evidence artifact | Status |
|---|---|---|
| Audit current FreeCAD runtime and MCP/API availability | `freecad_capability_audit.md` | pass for FreeCADCmd/API; MCP unavailable |
| Reuse existing 6 operation-plan pilot links | `input_manifest.csv` | pass — six existing link plans listed |
| Define Executable CAD IR v1 before backend execution | `schemas/executable_cad_ir_v1.schema.json`, `docs/executable_cad_ir_v1.md` | pass |
| Run operation-level native smoke tests without silent fallback | `results/operation_smoke_results.csv`, `results/operation_smoke_summary.json` | pass — 10/10 native semantic match; silent fallback 0 |
| Execute six link plans through FreeCAD backend | `results/link_execution_results.csv`, `results/link_ir_completeness_summary.json` | blocked by upstream IR — 6/6 existing plans are `IR_INCOMPLETE`; execution intentionally skipped |
| Record per-operation execution status and failure reasons | `logs/smoke/*/execution_log.json`, `results/link_ir_completeness_detail.csv` | pass for smoke; pass for link IR validation failures |
| Save/reopen FCStd and export STEP/STL | `artifacts/smoke/**`, `results/operation_smoke_results.csv` | pass — 10/10 smoke tests saved/reopened/exported |
| Run reproducibility checks | `results/reproducibility_results.csv`, `results/reproducibility_summary.json` | partial pass — native revolve 3/3 reproducible; complex link not run due IR incomplete |
| Report backend migration recommendation | `freecad_backend_pilot_report.md` | pass |
