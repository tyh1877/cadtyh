# Try-6.0-R0 infrastructure readiness audit

Decision: **SCHEMA_TRANSPORT_BLOCKED** (terminal bucket defined by the frozen R0 protocol). This does **not** mean the HTTP/SDK JSON Schema transport failed: all five transport probes passed. The block is full L04 KFDG *semantic-contract reliability* during the first permitted end-to-end call. Do not rerun, repair, or reinterpret that raw response as a passing graph.

## A. Frozen C1-v1

The original `try6_0_c1` manifest and all its enumerated lightweight artifacts passed an independent SHA-256 recheck. The C1-v1 outcome remains `REPRESENTATION_FAILURE`; its failed raw response was neither modified nor reused as a successful KFDG. R0 wrote only to its separate result/artifact directories. Formal holdout lock metadata still says `accessed=false`, `evaluation_count=0`. R0 did not read case data or GT.

## B. Schema transport

The frozen local protocol used `qwen3.7-plus`, temperature 0, top-p 1, seed 20260923, OpenAI SDK 2.53.0, retries 0. The actual HTTP JSON payload at every level contained `response_format.type=json_schema`, the corresponding schema, and `strict=true`. HTTP and SDK message content matched byte-for-byte. Raw JSON was parsed and validated without unwrapping or default insertion.

| Level | Probe | Result | Latency (s) | Prompt / completion tokens |
|---|---|---|---:|---:|
| 0 | object `{value:1}` | PASS | 11.469 | 46 / 718 |
| 1 | simple object with empty parameters | PASS | 6.000 | 55 / 325 |
| 2 | one parameter | PASS | 9.188 | 67 / 616 |
| 3 | simple nodes/features/constraint | PASS | 21.797 | 72 / 1274 |
| 4 | complete v1 schema, synthetic TEST graph | PASS | 43.875 | 103 / 3126 |

No evidence of SDK wrapper modification or API rejection was found. This was a *synthetic transport test*, not proof that a realistic L04 graph is semantically reliable.

## C. KFDG v1

The new contract is a single top-level object with `schema_version`, `link_id`, `functional_nodes`, `geometric_features`, `parameters`, and `constraints`. Features have one canonical `{id,type,parameter_refs}` representation; parameters have fixed value/unit/bounds/provenance/confidence fields. The schema has no union, recursion, or arbitrary dynamic keys. Compared with the prior C1-v1 visual-cue response, it directly represents parameter and feature nodes. The old response schema did not itself contain an explicit bool/object union, so no such historical deletion is claimed. Twelve local deterministic tests passed, including root type, unknown fields, enums, units, duplicate IDs, dangling references, and serialization. The JSON Schema itself does not yet express uniqueness within `parameter_refs`; that rule lives in the deterministic local validator.

Seven additional post-run evidence tests passed for transport capture, feature selection, parameter effect, recompute, frozen interface signatures, export/reopen, and holdout-lock metadata (19/19 total tests). Lock metadata and source-path audit are evidence of no intended holdout access, not a filesystem-level read trace.

## D. Parametric rebuild

One infrastructure baseline FCStd was built with the frozen F0 scaffold and interface tools. Three edits independently reopened the same baseline: `housing_width_mm` 17→17.85 (+5%), `housing_height_mm` 16→15.2 (−5%), and `recess_depth_mm` 4→4.2 (+5%). All 3/3 recomputed with valid feature states, one connected solid, STEP/STL export and FCStd reopen. The initial 3/3 smoke was repeated once with the **same frozen parameter protocol** solely to add final-volume instrumentation; no parameter or threshold was changed. The retained report is the instrumented repeat. Baseline final volume was 17004.714612 mm³; A/B/C volumes were 17256.165079 / 16657.824487 / 16998.841114 mm³. Thus sheet edits genuinely changed the final entity.

The frozen proximal bore tool, mating-envelope tool, and F0 scaffold BREP hashes, volumes, and bounding boxes matched before/after each edit. Those immutable shapes plus the unchanged 63 mm anchor support interface/frame invariance for this smoke; this is not a new motion evaluation. The historical fillet used `Edge1`. It is now disabled in the infrastructure builder because no semantic edge selector has been validated. The feature map records this omission. The active Sketch→Pad→Pocket→opening→scaffold path has no historical edge-index dependency. No geometry-performance inference is made from disabling the fillet.

## E. End-to-end stop

After both preceding gates passed, one frozen synthetic L04 Qwen call was made. Its HTTP raw content and SDK content matched; the actual request carried the full v1 schema. The raw top-level object satisfied JSON Schema, but the `transition_main` feature repeated `housing_width_mm` and `housing_height_mm` in `parameter_refs`. The local v1 validator rejected it as `duplicate parameter reference`. The model also mapped several other feature references incorrectly relative to the prompt. No response repair, retry, parser fallback, solver candidate, or CAD build occurred after that failure. End-to-end candidate count is **0**, not 2. Therefore no R0 end-to-end theta, objective, anchor-mutation result, or selected CAD can be claimed. This is a stronger and more precise failure than “API cannot emit objects”: transport works, but production-shaped graph semantics are not constrained sufficiently.

## F. Decision and unsupported claims

Under the protocol's three permitted labels, the representation/contract failure is recorded as `SCHEMA_TRANSPORT_BLOCKED`; parametric rebuild itself passed 3/3. Before a new, separately versioned attempt, the schema/prompt must constrain reference arrays or the acceptance gate must explicitly tolerate them; the frozen response cannot be repaired retroactively. No C1-v2, C2, KFDE, formal holdout, GT geometry metric, or 96-case mechanics evaluation was run.

R0 does **not** support claims that KFDG beats Direct, Metric Grounding works, C1 geometry improves, KFDE works, or the CAD is manufacturing-ready.
