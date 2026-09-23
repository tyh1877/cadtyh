# Try-6.0-C1-v2 formal development requirement-to-evidence checklist

One L04 candidate only. Frozen C1-v1/R0/R1 results remain immutable. No C2,
KFDE, formal holdout, GT-guided generation, or repeated final evaluation.

- [x] Audit frozen C0 source, R1-v3 readiness, input hashes, evaluator version parity, and holdout lock (`pre_run_manifest.json`); C0 exact values read by final validator only after candidate lock.
- [x] Extract raw-image-only right/top visible contour/profile evidence, approximate registration, residual, landmarks, ROIs and hashes before solver (`visual_metric_evidence/`).
- [x] Compute and enforce registration/evidence gates; both passed (cross-view scale discordance 3.96% < 10%).
- [x] Freeze one fresh slot protocol, active rule, normalized visual-only objective, bounded seeded solver/budget and zero retry before the formal call (commits `dfad691`, `aaefab8`).
- [x] Preserve one fresh Qwen raw response/exact request and independently validate contract/KFDG without repair (`slot/`, `kfdg/`).
- [x] Evaluate 32/32 preregistered candidates, preserve all, select the lowest legal visual objective without GT/mechanics (`solver/`, independent solver validation).
- [x] Build/export/reopen final CAD; verify bound table, one solid and frozen BREP interface signatures (`cad/`).
- [x] Freeze `evaluation/final_candidate_lock.json` with theta and upstream hashes in commit `b83ff29` before first GT evaluator event.
- [x] Run one final GT geometry evaluation and one diagnostic exact development mechanics evaluation only after lock, retaining all 96 configurations and failure IDs (`evaluation/`).
- [x] Independently validate exact C0-vs-C1 gates, objective alignment, leakage/path scope, process/failure accounting and holdout lock (`audit/independent_validation.json`); decision `GO_C2`, stop before C2.
