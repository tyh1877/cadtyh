# Try-6.0-R0 requirement-to-evidence checklist

R0 is infrastructure readiness. The frozen C1-v1 result is immutable. No GT,
formal holdout cases, C1 rerun, C2/KFDE, or paper geometry metric is in scope.

- [x] Hash-audit C1-v1 tracked artifacts and record starting commit without modifying that result directory (`validation.json`).
- [x] Freeze Level 0–4 schemas, prompts, model config, zero-retry policy, and simplified KFDG v1 before API calls (`16e4038`).
- [x] Pass all 12 deterministic KFDG contract tests (`kfdg_contract/contract_test_report.json`).
- [x] Capture actual outgoing HTTP JSON including `response_format.json_schema` at every level (`schema_transport/level*_request.json`).
- [x] Save HTTP response, SDK response, raw message content, model, usage, latency, and validation without repair.
- [x] Pre-register stop-on-first-failure and classifications; Levels 0–4 all passed.
- [x] Enter R0-B only after Levels 0–4 passed.
- [x] Freeze three independent edit parameters before rebuild (`2b392f4`).
- [x] Remove the historical `Edge1` fillet dependence and document the disabled feature.
- [x] Run 3/3 independent edits; check feature tree, single solid, frozen BREP signatures, export, reopen, and changed final volume.
- [x] Enter synthetic non-GT end-to-end smoke only after both preceding gates passed (`27551e3`).
- [ ] Verify anchor mutation and two candidate evaluations: **not reached**; the one raw Qwen response failed the local KFDG reference contract. No retry or repair.
- [x] Independently audit the blocked decision and stop before C1-v2, C2, GT evaluation, or formal holdout access (`validation.json`).
