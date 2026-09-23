# Try-6.0-R1-v2 requirement-to-evidence checklist

R1-v2 is a new, isolated infrastructure reliability version. C1-v1, R0 and
R1-v1 remain frozen. No GT, formal holdout cases, C1-v2, C2 or KFDE.

- [x] Hash-audit C1-v1, R0, and R1-v1 and record starting commit (`preflight/compatibility_report.json`, `validation.json`).
- [x] Deterministically project the API Schema; record all three `uniqueItems` paths, R1-v1 API evidence and complete local-validator replacement (`schema_projection/projection_report.json`).
- [x] Pass 31 projection, local uniqueness, signature, authority, assembly, no-repair and holdout-lock tests.
- [x] Run exactly one full production API-Schema compatibility preflight; HTTP 200 and raw transport-valid (`preflight/`).
- [x] After preflight PASS, freeze prompt/schema/projection/model/backbone/registry/assembler/input hashes (`reliability_freeze.json`, commit `865bad1`).
- [x] Retain five fresh identical-input L04 calls with zero retries, repair or manual selection (`reliability/call_01`…`call_05`).
- [x] Independently compute TSR 5/5, VSR 1/5, GAR 1/5, violation counts and five-proposal consistency (`reliability/reliability_summary.json`).
- [x] Enforce the representation gate: E2E **not run** because semantic reliability failed.
- [ ] Anchor→objective→theta→CAD sensitivity: **not reached**, cannot claim PASS.
- [x] Independently validate `VFP_SEMANTIC_RELIABILITY_BLOCKED`, failure accounting, prior-result immutability, GT=0 and holdout lock; stop before C1-v2 (`validation.json`).
