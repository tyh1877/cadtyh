# Try-5B.1-A2 Strong Direct VLM Refinement Baseline

This stage must stop before any model call unless the model/version and budget
parity gate can be proven from direct evidence.

- [x] Audit the repository for Ours model/version, prompts, responses, calls, tokens, runtime, and CAD execution provenance.
- [x] Audit available executable multimodal model configurations without exposing credentials.
- [x] Define the Direct VLM raw-input allowlist and structured-information denylist.
- [x] Draft and freeze the L04 direct-refinement prompt without family/schema/topology hints.
- [ ] Prove that Ours and Direct use the same exact model and version.
- [ ] Prove equal maximum VLM calls, refinement rounds, and comparable token/context budgets.
- [ ] Freeze a fairness contract with status `PASS` before any API call.
- [ ] Implement/enable the minimal Direct VLM execution path under the passing contract.
- [ ] Run Ours and Direct exactly once on L04 with full prompt/response/code/execution logs.
- [ ] Evaluate both with identical geometry, assembly, motion, collision, and process evaluators.
- [x] Preserve `formal_holdout_lock.json` with `accessed=false`; do not start Metric Grounding or the three-link comparison.

Current state: `BLOCKED_MODEL_AND_BUDGET_PARITY`. The repository records Ours as
`current_interactive_codex` with `model_snapshot=UNAVAILABLE` and
`tokens=UNAVAILABLE`; no original Try-5B.1 prompt/response/call ledger exists.
The available `qwen3.7-plus` configuration belongs to a different experiment
and cannot be substituted silently.
