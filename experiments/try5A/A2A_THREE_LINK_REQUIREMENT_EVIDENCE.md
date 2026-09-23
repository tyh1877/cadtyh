# Try-5B.1-A2a three-link formal development comparison

Evidence is required for each item before a cross-link claim is made.

- [x] Freeze the L04 audited method prompts by SHA-256; substitute only Link ID and raw Link-specific evidence.
- [x] Freeze qwen3.7-plus, seed, temperature, top-p, one call, zero refinement rounds, output ceiling, timeout, SDK, and zero manual intervention.
- [x] Freeze three pilot Links, the development-only 96 configurations, relevant joint sweeps, F0 CAD, interfaces, scaffold policy, and evaluator hashes.
- [x] Confirm the 32-case formal holdout lock remains `accessed=false` and `evaluation_count=0` before and after execution.
- [x] Save six expanded requests; prove each Link pair has identical shared text and attachments, with only the method prompt differing.
- [x] Save all six request IDs, returned model identifiers, full responses, token usage, latency, and any infrastructure failures.
- [x] Perform one model generation per Link × condition; do not retry model-output, CAD, or evaluator failures.
- [x] Prove Structured response → fresh IR → compiler dispatch → CAD for each successful run; retain failures without fallback.
- [x] Prove Direct response → exact generated code → FreeCAD body → CAD for each successful run; retain failures without editing generated code.
- [x] Apply the same frozen scaffold and protected-interface policy, FreeCAD runtime, canonical pose, and evaluators in both methods.
- [x] Preserve all 96 development configurations in every mechanical denominator; record failures explicitly.
- [x] Save geometry, assembly, motion, collision, process, per-link delta, mean delta, median delta, and a six-run main table without an overall score.
- [x] Independently audit model/input/scaffold/call/evaluator/prompt parity, GT isolation, manual intervention, and retry accounting.
- [x] Report observed failure modes by Link, cross-link pattern, FACTS, INTERPRETATION, NOT_SUPPORTED, and bounded Try-6 design implications.
- [x] Stop after the three-link development comparison; do not evaluate formal holdout or implement Try-6.

Final state: six one-shot model generations attempted; four CAD candidates fully
evaluated over all 96 development configurations; two Structured schemas failed
before CAD. The independent integrity audit passed after correcting two
analysis-only defects. Paired geometry and mechanics have n=1 of 3 links;
cross-link pattern is MIXED/INCONCLUSIVE. Formal holdout remains untouched.
