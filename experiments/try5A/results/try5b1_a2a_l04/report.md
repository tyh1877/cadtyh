# Try-5B.1-A2a Same-Model Structured-vs-Direct — L04 dry run

Status: **L04_DRY_RUN_COMPLETE_FORMAL_NOT_RUN**

Independent validation: **PASS** (17/17 checks)

## 1–2. Prompts

- Structured template: `prompts/a2a_structured_qwen_l04.md`
- Direct template: `prompts/a2a_direct_qwen_l04.md`
- Expanded Structured request: `STRUCTURED_QWEN/request_manifest.json`
- Expanded Direct request: `DIRECT_QWEN/request_manifest.json`

Both received identical shared user text and the same 12 image attachments:
six raw robot views and six neutral F0 L04 renders. Only the method prompt
differed. Structured received the public compiler family/schema contract;
Direct received an allowlisted FreeCAD-code contract and no structured result.

## 3–6. Model and budget

Both calls requested and returned `qwen3.7-plus`. They were launched in
parallel with temperature 0, top-p 1, seed 20260923, one-call ceiling, zero
repair rounds, 32768 maximum output tokens, 300-second timeout, SDK retries 0,
and manual intervention 0. The provider returned no system fingerprint.

| Condition | Input tokens | Output tokens | Total tokens | Model latency s |
|---|---:|---:|---:|---:|
| Structured-Qwen | 15750 | 5591 | 21341 | 98.984 |
| Direct-Qwen | 15710 | 3561 | 19271 | 64.060 |

## 7. Structured IR

Structured-Qwen independently selected `central_web` and generated:

- span 76.5 mm;
- thickness 18.0 mm;
- proximal height 23.0 mm;
- mid height 18.0 mm;
- lateral offset 0.0 mm;
- major recess enabled;
- a fresh visual analysis, semantic inventory, and J03→J04 rigid topology.

No historical F1/F2 schema or IR was supplied. The complete artifact is
`STRUCTURED_QWEN/structured_ir.json`.

## 8. Direct CAD output

Direct-Qwen emitted FreeCAD Python that read the supplied `f0_shape` envelope
and produced a box-like forearm with two cylindrical joint housings. The code
passed the AST allowlist and produced a valid B-Rep. The original code remains
verbatim in `DIRECT_QWEN/raw_response.txt`; its B-Rep and final FCStd hashes are
recorded in `artifact_manifest.json`.

## 9. Build success

Both conditions built, exported, and reopened successfully:

- CAD build success: 2/2;
- invalid CAD attempts: 0;
- FreeCAD failures: 0;
- repair/retry: 0;
- manual interventions: 0.

One local execution incident occurred after both model calls: the Structured IR
validator incorrectly rejected legal `lateral_offset_mm=0`. The validator was
corrected and execution resumed from immutable saved responses. No new model
call, response edit, CAD repair, or manual geometry edit occurred.

## 10–11. Geometry and mechanical metrics

| Metric | Structured-Qwen | Direct-Qwen | Better |
|---|---:|---:|---|
| Final voxel IoU | 0.164283 | 0.113516 | Structured |
| Final silhouette IoU | 0.340108 | 0.303852 | Structured |
| nChamfer ↓ | 0.107781 | 0.121191 | Structured |
| nHD95 ↓ | 0.284190 | 0.310735 | Structured |
| BICR | 1.0 | 1.0 | Tie |
| Connected solids | 1 | 1 | Tie |
| J03 JR3 | 0.666667 | 1.0 | Direct |
| GCFR | 0.614583 | 0.739583 | Direct |
| Exact collision events | 62 | 48 | Direct |
| Intersection volume mm³ | 29359.75 | 22067.23 | Direct |
| Failed development configurations | 37 | 25 | Direct |

The same frozen scaffold safeguard gives both conditions valid one-solid
attachment. Structured has a clear geometry advantage on L04, while Direct has
a clear motion/collision advantage.

## 12. Runtime

- Structured model + canonical CAD: approximately 101.02 seconds.
- Direct model + body-code execution + canonical CAD: approximately 66.58 seconds.
- Shared Exact evaluator: 354.18 seconds total.
- Shared geometry evaluator: 3.13 seconds total.

## 13. Fairness confounds

1. Both responses have the same exact returned model identifier, but the API
   exposes no system fingerprint or immutable backend snapshot.
2. The Structured treatment includes both explicit IR and the constrained
   existing compiler. Direct receives general allowlisted FreeCAD code. The
   result therefore estimates the value of the **structured IR + compiler
   pathway**, not IR serialization alone.
3. Actual token usage differs naturally; maximum budgets and source evidence
   are equal.
4. This is one Link and one call per condition, so stochastic and link-level
   generalization are unknown.

## 14. Three-link recommendation

**CONDITIONAL GO** for a three-link A2a, provided the current prompts, Qwen
configuration, one-call budget, seed policy, scaffold wrapper, and evaluator are
frozen unchanged. The paper claim must be framed as Structured-Qwen
IR+compiler versus Direct-Qwen code generation, not as pure IR-only causality.

Historical Frozen Try-5 remains a context-only third record. Its metrics are not
used to claim model-controlled superiority.

The 32-case formal holdout remains `accessed=false / evaluation_count=0`.
