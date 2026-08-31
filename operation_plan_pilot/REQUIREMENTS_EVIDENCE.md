# Operation-plan Pilot requirement-to-evidence checklist

| Requirement | Evidence artifact | Status |
|---|---|---|
| Frozen 2-case / 6-link pilot set | `cases.csv`, `protocol.md` | pass |
| No GT mesh/CAD/product identity is sent to LLM | `scripts/run_operation_plan_pilot.py`, per-link manifests | pass |
| LLM returns schema-valid operation plans | `runs/*/*/operation_plan.json`, `results/plan_quality.csv` | pass — 6/6 after deterministic alias canonicalization of saved raw responses |
| Operation plans contain richer CAD operations | `results/plan_quality.csv`, `results/aggregate.json` | pass — 6/6 have 5+ ops; 5/6 have 2+ nonprimitive ops |
| Interface constraints preserve URDF identifiers | `results/plan_quality.csv` | pass — 6/6 include interface constraints |
| Final pass/fail decision is recorded | `results/report.md` | pass — pilot PASS |
