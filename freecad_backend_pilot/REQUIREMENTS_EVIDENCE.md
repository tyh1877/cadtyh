# FreeCAD Backend Pilot requirement-to-evidence checklist

| Requirement | Evidence artifact | Status |
|---|---|---|
| Audit current FreeCAD runtime and MCP/API availability | `freecad_capability_audit.md`, `freecad_mcp_audit.md` | pass for FreeCADCmd/API; MCP audited but not used for acceptance |
| Reuse existing 6 operation-plan pilot links | `input_manifest.csv` | pass — six frozen links listed |
| Prove old operation plans are not directly executable | `results/link_ir_completeness_summary.json`, `results/link_ir_completeness_detail.csv` | pass — 6/6 old vague plans are `IR_INCOMPLETE` |
| Define Executable CAD IR v1 before backend execution | `schemas/executable_cad_ir_v1.schema.json`, `docs/executable_cad_ir_v1.md` | pass |
| Regenerate Executable CAD IR for six frozen links | `results/executable_ir_generation_results.csv`, `results/executable_ir_generation_summary.json` | pass — 6/6 schema-valid and IR-complete via `qwen3.7-plus` |
| Run operation-level native smoke tests without silent fallback | `results/operation_smoke_results.csv`, `results/operation_smoke_summary.json` | pass — 10/10 native semantic match; silent fallback 0 |
| Execute six generated link IRs through FreeCAD backend | `results/link_execution_results.csv`, `results/link_execution_summary.json` | pass — 6/6 links executed; 30/30 operations native-successful |
| Record per-operation execution status and failure reasons | `logs/smoke/*/execution_log.json`, `runs/*/*/freecad/execution_log.json` | pass |
| Save/reopen FCStd and export STEP/STL | `artifacts/smoke/**`, `runs/*/*/freecad/model.*`, result CSVs | pass — all executed smokes and generated links saved/reopened/exported |
| Run reproducibility checks | `results/reproducibility_results.csv`, `results/reproducibility_summary.json` | pass — native revolve and one complex link each reproduced 3/3 |
| Report backend migration recommendation | `freecad_backend_pilot_report.md` | pass |
