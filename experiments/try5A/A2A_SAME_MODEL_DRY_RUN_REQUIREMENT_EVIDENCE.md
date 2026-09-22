# Try-5B.1-A2a Same-Model Structured-vs-Direct VLM Baseline

This stage ends after one L04 call/build/evaluation per condition. Formal
holdout, three-link execution, iterative repair, and Metric Grounding are out of
scope.

- [ ] Freeze one Qwen model/config, seed, call ceiling, output-token ceiling, timeout, and zero-retry policy for both conditions.
- [ ] Materialize one shared L04 evidence bundle: raw images, engineering text, sanitized URDF, F0 CAD/renders, neutral interfaces, scaffold safeguard, and FreeCAD environment.
- [ ] Prove identical shared-input hashes and isolate all historical structured outputs, repair logs, and evaluator-only data from both VLM calls.
- [ ] Freeze full Structured-Qwen and Direct-Qwen prompts before calling the model.
- [ ] Dispatch exactly one call per condition with the same requested/returned model identifier and record request ID, seed, tokens, latency, full response, and system fingerprint when available.
- [ ] Structured-Qwen must generate fresh visual/structural analysis, body family, semantic inventory, topology, and executable schema from shared raw inputs.
- [ ] Structured-Qwen must not read historical F1/F2 IR or schema.
- [ ] Direct-Qwen must generate direct FreeCAD body code without receiving structured IR, family results, schema parameters, repair logs, GT, or prior refined CAD/metrics.
- [ ] Execute Direct code through a fail-closed AST allowlist with no network, shell, subprocess, or uncontrolled filesystem access.
- [ ] Apply identical protected cuts and frozen scaffold safeguard to both generated bodies through the same canonical worker.
- [ ] Preserve one-shot failures without repair, deletion, human edits, or rerun.
- [ ] Evaluate both candidates with identical geometry and Exact mechanical evaluators over the same 96 development configurations and J03 sweeps.
- [ ] Record CAD build success, invalid attempts, FreeCAD failures, API calls, tokens, latency, runtime, and manual intervention count.
- [ ] Keep Historical Frozen Try-5 separate from the controlled paired comparison.
- [ ] Run an independent result audit and stop before three links, formal holdout, or Metric Grounding.
