# Try-6.0-R1 requirement-to-evidence ledger

R1 is a representation-reliability study, not a geometry experiment. C1-v1
and R0 are frozen. No GT, formal holdout cases, C1-v2, C2, or KFDE.

- [x] Hash-audit C1-v1 and R0 frozen files; preserve their decisions (`preflight.json`, `validation.json`).
- [x] Freeze source hashes, VFP schema/prompt, Functional Backbone, Parameter Registry, assembler rules, model config, and N=5 before calls (`aeced19`, `preflight.json`).
- [x] Pass 23 deterministic schema, signature, role, registry, ownership, assembly, authority, unsupported-feature, reference, and holdout-lock tests.
- [x] Make exactly five identical-payload production-shaped L04 HTTP attempts with zero retries; retain each request and 400 response (`reliability/call_01`…`call_05`). No model-generated raw content exists.
- [x] Independently compute the reliability gates and failure accounting (`reliability/reliability_summary.json`); gate **FAIL** because API rejected the frozen schema.
- [x] Record proposal consistency as **not evaluable** across all five absent proposals; do not infer drift.
- [x] Enforce the 5/5 gate: end-to-end smoke **not run** because representation failed.
- [ ] URDF anchor→objective→theta→CAD and export/reopen: **not reached**, cannot claim PASS.
- [x] Independently validate `SEMANTIC_CONTRACT_BLOCKED` with subtype `VFP_SCHEMA_API_REJECTED`, C1/R0 immutability, GT=0, and holdout lock before result freeze.
