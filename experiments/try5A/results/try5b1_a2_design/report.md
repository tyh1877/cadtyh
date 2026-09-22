# Try-5B.1-A2 Direct VLM baseline design audit

Status: **BLOCKED_MODEL_AND_BUDGET_PARITY**

The repository contains a valid, secret-safe `qwen3.7-plus` multimodal API
configuration and reusable request/token logging code. It also contains all raw
L04 inputs, the F0 FCStd, frozen interfaces, FreeCAD runtime, and scaffold
safeguard needed to implement a strong Direct VLM baseline.

However, frozen Try-5B.1 Ours records its generator as
`current_interactive_codex` with `model_snapshot=UNAVAILABLE` and
`tokens=UNAVAILABLE`. No original prompt, response, call ledger, or token/context
record exists. The current frozen Ours execution is deterministic and makes zero
VLM calls. Therefore the required same-model/version, call-budget, and token
parity cannot be proven.

Using `qwen3.7-plus` only for Direct would introduce a model and process-budget
confound. Treating an unused or dummy Qwen call as Ours would not repair that
confound. Re-running Structured with Qwen would be a new paired experiment, not
the frozen Ours comparison requested here.

The raw-input allowlist, structured-information denylist, and L04 prompt are
frozen, but the fairness contract remains failed. No A2 API call, CAD build,
evaluation, formal-holdout access, Direct VLM metric, or Metric Grounding run was
performed.
