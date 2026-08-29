# Try-2 final report (amended external-URDF protocol)

## Protocol and validity
C/D use sanitized URDF as the external authoritative kinematic representation. Fusion creates editable parameterized link components and places occurrences at canonical FK transforms; native Fusion joints are a non-gating demonstration. The acceptance checklist records this amendment.

## Coverage and execution
A=13/15, B=13/15 (the two A planning failures are retained as UPSTREAM_FAILURE), C=15/15, D=15/15. All 28 eligible B/D jobs produced native F3D/STEP/STL and per-component STL. The repaired executor records occurrence FK transforms, and the selected smoke plus formal execution logs confirm the transforms are persisted at creation time. Formal Fusion CAD time totals 35.756 s for B (13 cases) and 57.943 s for D (15 cases).

## Main geometry and motion
Median Chamfer/HD95/IoU: A 0.00291/0.1221/0.341; B 0.00249/0.1006/0.326; C 0.00088/0.0631/0.505; D 0.00147/0.0860/0.404. Median motion error: A 0.259, B 0.266, C 0.0264, D 0.0250. Per-link median Chamfer: A 0.017413, B 0.018141, C 0.001083, D 0.001499. Joint-local median Chamfer: A 0.001297, B 0.001060, C 0.000562, D 0.000725.

## Resource accounting
A used 15 model calls and 43,968 total tokens (two calls ended in planning failures); C used 15 model calls and 72,895 total tokens. B and D use no additional LLM calls; their Fusion operation counts and per-case CAD latency are in `fusion_execution_log.csv`. Latency for LLM planning is in `token_call_accounting.csv`.

## 2x2 interpretation
URDF improves whole-robot, per-link and joint-local geometry substantially in the primitive track (A¡úC), while also making origin error zero and lowering motion error. Fusion improves no-URDF Chamfer and HD95 on eligible paired cases but not IoU or per-link geometry consistently (A¡úB). Under URDF, Fusion preserves motion but is geometrically behind the primitive backend (C¡úD), reflecting the minimal primitive Tool Layer rather than a negative result about editable CAD. Corrected placement is evidenced separately from geometric quality.

## Recommendation
The evidence supports kinematic-conditioned CAD generation as the next paper direction. Keep Fusion as an editable execution substrate; improve the Fusion embodiment Tool Layer before claiming a backend advantage.
