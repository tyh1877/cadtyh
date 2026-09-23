# Try-6.0-R1-v3 requirement-to-evidence checklist

Final representation-hardening round. C1-v1, R0, R1-v1 and R1-v2 are frozen.
No GT, formal holdout cases, C1-v2, C2 or KFDE.

- [x] Hash-audit prior results/holdout lock and freeze three slots, authority sources, unchanged Parameter Registry and prompt before calls (`preflight/report.json`, `reliability_freeze.json`).
- [x] Project API schema from one canonical slot schema; local uniqueness and completeness remain enforced (`schema/projection_report.json`, tests).
- [x] Pass 26 local tests covering completeness, IDs, enum, evidence, status-dependent assembly, mapping, relations, authority, no-repair and holdout-lock metadata.
- [x] Run exactly one production compatibility preflight; HTTP 200, raw transport valid (`preflight/report.json`).
- [x] After preflight, freeze N=5 inputs/model/budget and implementation hashes (commit `039b509`, `reliability_freeze.json`).
- [x] Retain five same-input calls; independent gate 5/5 and per-slot stability computed without voting (`reliability/contract_summary.json`, `perception_stability.json`).
- [x] Only after independent 5/5 gate, use one fresh non-denominator VLM call and four non-GT CAD candidate builds (`e2e_smoke/`).
- [x] Independently verify URDF 63 mm anchor→synthetic objective→theta→CAD, interface invariance, one solid, export/reopen (`e2e_smoke/anchor_sensitivity.json`, `validation.json`).
- [x] Independently validate `READY_FOR_C1_V2` infrastructure decision, complete failure accounting, prior-result immutability, GT=0 and holdout lock; stop before C1-v2 (`validation.json`).
