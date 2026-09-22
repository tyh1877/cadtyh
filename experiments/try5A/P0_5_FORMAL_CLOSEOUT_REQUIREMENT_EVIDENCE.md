# P0.5 formal experiment closeout checklist

- [x] The existing B1 entrypoint runs the paired A1 development phase from the tracked config without a copied pipeline.
- [x] Generator jobs contain only the 96 development configurations and never serialize holdout IDs.
- [x] C1/C2 consume identical raw body proposals; runtime evidence records proposal parity before mechanical policy is applied.
- [x] C1 and C2 both run FAST and Exact measurement; only rejection and rollback authority differs.
- [x] Runtime candidate history records F1 then F2 decisions, failed gates, selected candidates, and rollback/accept-with-failure outcomes.
- [x] Mechanical metrics are computed from worker artifacts rather than copied or asserted constants.
- [x] A formal development result bundle satisfies the project artifact contract and preserves every requested case.
- [x] The independent validator supports pre-holdout and formal phases; the runner never authors `validation.json`.
- [x] A separate holdout evaluator consumes frozen candidate artifacts only, refuses a second evaluation through an atomic lock, and cannot invoke generation or repair.
- [x] Development tests and dry-run pass without consuming any holdout configuration.

Closeout evidence: `results/try5b1_a1_development/validation.json` reports
`PASS`; its holdout evaluation counts are zero for both conditions. The frozen
candidate artifacts are recorded in `candidate_manifest.json`. The real holdout
remains unconsumed and is intentionally outside P0.5.
