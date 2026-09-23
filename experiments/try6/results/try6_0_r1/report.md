# Try-6.0-R1 KFDG Semantic Contract Hardening — frozen result

**Decision: `SEMANTIC_CONTRACT_BLOCKED`**, with the precise failure subtype **`VFP_SCHEMA_API_REJECTED`**. This is the only applicable blocked label in the pre-registered three-label R1 vocabulary. It must **not** be paraphrased as a VLM semantic error: the API rejected the frozen VFP schema before any model-generated proposal existed.

## A. Architecture and provenance

R1 changed the intended responsibility split, without changing C1-v1 or R0 results:

1. The VLM would propose only externally visible L04 feature classes, local names, semantic roles, evidence views, confidence, and visual relations. It received engineering text and the same six raw robot views plus six frozen F0 neutral renders. It did **not** receive the canonical Parameter Registry, frozen Functional Backbone, joint IDs/frames, or solver variable IDs.
2. The Functional Backbone is deterministic from the sanitized URDF, the frozen J03/J04 interface contract, the L04 local frame specification, the F0 scaffold source, and the 63 mm J03–J04 anchor. The authority audit passed before calls.
3. The frozen Parameter Registry maps eight active CAD variables to owner-feature/semantic-role pairs and explicitly retains the inactive legacy fillet radius as a permitted dormant orphan. It uses the existing bounds; no new CAD feature or objective was introduced.
4. The deterministic assembler maps the required visible classes (`main_housing`, `pocket`, `profile_transition`) and their validated roles to canonical feature IDs, owned parameter references, and backbone-derived functional relations. Local tests showed deterministic assembly, unique references, referential integrity, and rejection of functional overrides.

The three-class vocabulary is deliberately limited to the existing stable L04 compiler. It is a representation-compliance test, not a general feature-discovery benchmark. The VFP prompt contains role signatures, so even a future 5/5 result would not prove autonomous discovery of those classes.

## B. Five-attempt reliability result

The protocol, prompt, VFP schema, registry, backbone, assembler and 12 image hashes were frozen in commit `aeced19` before the first request. Five independent HTTP attempts were made with an identical captured request-body SHA-256, zero SDK/technical retries, and no manual intervention. All five received HTTP 400. The service error said the supplied `response_format.json_schema.schema` could not include `uniqueItems` on an array. The VFP schema used `uniqueItems` to constrain role/evidence lists, which is valid for local Draft 2020-12 validation but was rejected by this API endpoint. No raw VFP content was produced.

| Gate | Observed |
|---|---:|
| HTTP attempts retained | 5/5 |
| API schema accepted | 0/5 |
| Raw VFP schema-valid responses | 0/5; **no raw responses generated** |
| VFP semantic validation | not evaluable (0/5 successful) |
| Graph assembly | not reached (0/5) |
| Canonical KFDG validation | not reached (0/5) |
| Response repair / retry | 0 / 0 |
| Observed duplicate/dangling KFDG refs | 0 / 0, **no graphs to evaluate** |
| Observed unsupported visual features | 0, **no proposals to inspect** |

The `no_repair_rate=1.0` field is a procedural fact about five unmodified attempts, **not** evidence that outputs were correct. No response was dropped or replaced. The prompt/schema/registry/assembler were not changed after the first failure, and no sixth call was made.

## C. Proposal consistency

Feature, role, and relation agreement are **not evaluable**: there are no VFP proposals. The consistency artifact records all five missing proposals and does not infer stochastic structural drift from API failures.

## D. End-to-end and frozen-state gates

The 5/5 representation gate failed before generation, so the gated end-to-end smoke was **not run**. Solver candidate evaluations = 0; no theta, anchor-sensitivity result, final R1 CAD, or export/reopen result exists. R0's prior 3/3 parametric rebuild remains the most recent CAD infrastructure evidence, but it does not close the R1 end-to-end gate. GT evaluations = 0. The formal holdout lock metadata remains `accessed=false`, `evaluation_count=0`; no case data was read. Independent hash checks confirm C1-v1 and R0 lightweight result files unchanged. The future C1-v2 C0 IoU and 1.10× gate remain frozen and were not evaluated.

## E. Interpretation and next version

This R1 version exposes a **new API-schema compatibility defect** despite R0's simpler JSON Schema transport success. It does not establish whether the VFP semantic proposal, assembler, or solver chain would succeed under an API-compatible schema. A corrected transport projection would require a separately frozen **R1-v2**, with fresh N=5 attempts; these five rejected requests cannot be reused or relabeled. Keep uniqueness as a local semantic-validator requirement even if an API-facing schema must omit `uniqueItems`.

Not supported: KFDG outperforming Direct, Metric Grounding improving geometry, Try-6 outperforming Try-5, KFDE effectiveness, manufacturing readiness, or formal-holdout performance. No C1-v2, C2, or KFDE run followed.
