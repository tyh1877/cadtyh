# Try-6.0-R0 requirement-to-evidence checklist

R0 is infrastructure readiness. The frozen C1-v1 result is immutable. No GT,
formal holdout cases, C1 rerun, C2/KFDE, or paper geometry metric is in scope.

- [ ] Hash-audit C1-v1 tracked artifacts and record starting commit without modifying that result directory.
- [ ] Freeze Level 0–4 schemas, exact prompts, model config, zero-retry policy, and the simplified KFDG v1 contract before API calls.
- [ ] Pass all 12 deterministic KFDG contract tests, including root type, unit, ID/ref, unknown-field, and round-trip cases.
- [ ] Capture the actual outgoing SDK/HTTP JSON payload, including `response_format.json_schema`, at each attempted transport level.
- [ ] Save raw HTTP content, SDK content, request ID, model, usage, latency, validation, and errors without response repair.
- [ ] Stop transport escalation at the first failed level; classify missing schema, API rejection, invalid raw response, SDK modification, or valid raw response.
- [ ] Enter R0-B only if Levels 0–4 raw responses all validate.
- [ ] Freeze housing_width, housing_height, and recess_depth as the three independent edit parameters before rebuild tests.
- [ ] Remove or replace historic edge-index fillet dependence and document any disabled fillet.
- [ ] Run three independent ±5% parameter edits from one baseline FCStd; verify recompute, feature tree, one solid, interface invariance, export, and reopen.
- [ ] Enter the 2–5 candidate non-GT end-to-end smoke only after transport and all three rebuild edits pass.
- [ ] Verify URDF anchor mutation changes the metric objective and generated parameters without GT.
- [ ] Independently audit the applicable readiness decision and stop before C1-v2, C2, GT evaluation, or formal holdout access.
