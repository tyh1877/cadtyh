# Try-6.0-R1-v2 API-Compatible VFP Contract Reliability

**Decision: `VFP_SEMANTIC_RELIABILITY_BLOCKED`.** The API transport problem from R1-v1 is resolved for this frozen production schema, but the required 5/5 local semantic gate is not met. This is a representation-readiness result, not a geometry or method-performance result.

## A. Schema projection and compatibility

The frozen R1-v1 canonical VFP Schema remains the only source of truth. A deterministic projection removed exactly three `uniqueItems: true` constraints, at `/visual_features/items/properties/{parameter_roles,evidence_views,relations}/uniqueItems` (full JSON Pointers are in `schema_projection/projection_report.json`). The R1-v1 HTTP 400 is the recorded endpoint evidence for this removal. No other Schema keyword was deleted. The local Draft 2020-12 validator and semantic validator still enforce uniqueness; tests demonstrate that duplicate roles, evidence views, and relations can pass the API projection but fail locally. No response repair or deduplication exists.

The single non-sample production-schema preflight returned HTTP 200. Its actual request carried the projected full Schema, and its raw message directly satisfied that transport Schema. Preflight was excluded from the five-call reliability denominator.

## B. Five fresh production-shaped calls

The reliability configuration was frozen after preflight in commit `865bad1`. Five fresh calls used the same `qwen3.7-plus` model, temperature 0, top-p 1, seed 20260923, max 4096 output tokens, zero retries, the same prompt and engineering text, and byte-identical sets of six raw robot views plus six frozen F0 renders. Independent validation confirmed **identical exact HTTP request-body hashes** and decoded every image to recheck source hashes. All five raw responses, HTTP responses, SDK responses, request metadata, failures, and token/latency records were retained.

| Gate | Count | Rate |
|---|---:|---:|
| API accepted + raw API-transport Schema valid (TSR) | 5/5 | 1.0 |
| Full canonical JSON Schema valid (before semantic rules) | 5/5 | 1.0 |
| Full local canonical/semantic VFP valid (VSR) | 1/5 | 0.2 |
| Deterministic canonical KFDG valid (GAR) | 1/5 | 0.2 |
| Response repairs / retries / manual interventions | 0 / 0 / 0 | — |

Calls 01 and 02 failed the frozen local-name reconstruction-boundary filter. Across their proposals, three names containing `joint` or `mount` were counted as unsupported: `wrist_joint_pocket`, `gripper_mount_transition`, and `gripper_mount`. Calls 03 and 05 omitted the required `pocket`; call 04 passed semantic validation, deterministic assembly, and canonical KFDG validation. The five calls had **0 duplicate roles, 0 duplicate evidence views, 0 invalid role signatures, 0 explicit functional overrides**, and 0 response repairs. One accepted KFDG had 0 dangling/duplicate references and 0 ownership violations; the four rejected proposals produced no KFDG, so zero reference defects must not be generalized to them.

The three lexical-name violations expose a **contract-design confound**: `joint` and `mount` can describe an externally visible pocket or transition without redefining a joint frame or adding hidden engineering. Thus the observed VSR=1/5 is the rate **under this frozen validator**, not a clean estimate of visual reasoning failure. The two omitted pockets are a separate observation: the prompt explicitly allowed omission when visual evidence seemed insufficient, while the semantic gate required all three classes. Neither tension was changed after the first formal call. A revised semantic policy would require a newly versioned run, not retrospective relabeling.

## C. Proposal consistency

Across all five raw transport-valid proposals (including failed ones), exact pairwise agreement over ten pairs was: feature classes **0.4**, parameter-role structure **0.4**, relation structure **0.4**, confidence structure **0.1**. This is descriptive infrastructure evidence. It indicates structural drift in proposed feature presence and confidence, but is not a paper performance metric and is affected by the intentionally strict three-class acceptance rule.

## D. Gated end-to-end result

The representation gate failed, so the end-to-end smoke was **not started**: solver candidate count **0**, no R1-v2 theta, no objective or anchor-sensitivity result, and no new R1-v2 CAD build/export/reopen or interface-invariance result. The 63 mm URDF anchor remains frozen in the Functional Backbone, but it was **not consumed by an R1-v2 solver objective**. R0's earlier parametric 3/3 result remains historical infrastructure evidence only. GT evaluations = **0**; the 32-case formal holdout lock remains `accessed=false`, `evaluation_count=0`. Independent hash audits found C1-v1, R0 and R1-v1 result files unchanged. The future C1-v2 IoU threshold was neither altered nor evaluated.

## E. Strict interpretation

The API-facing/canonical-contract separation works for transport. The frozen local semantic policy and/or VFP output are not yet reliable at 5/5; the lexical false-positive risk means those two causes cannot be cleanly separated here. The one valid KFDG proves the deterministic assembler can operate on a valid proposal, not that the complete method is reliable. No C1-v2, C2, KFDE, GT metric, 96-case mechanics, or formal-holdout run followed.

Not supported: KFDG beating Direct, Metric Grounding improving geometry, Try-6 beating Try-5, KFDE effectiveness, manufacturing readiness, or formal-holdout performance.
