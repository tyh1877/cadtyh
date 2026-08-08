# Strengthened final Go/No-Go pilot report

## Decision: GO

This is a 10-case strengthened pilot, not a claim of a completed benchmark or universal SOTA comparison.
The decision is computed from the frozen cases, preserved manifests and deterministic evaluator outputs; no thresholds were changed.

## A. Evaluator sanity

Sanity status: **PASS**. The complete perturbation record is in `results/evaluator_sanity/`.
It confirms exact GT identity, monotone axis/origin/scale/translation perturbations, and degradation or invalidity for large structural corruptions.

## B. Equal-budget rerun

Every track used the same ten prompts, six renders, temperature, CAD runtime, 300-second API timeout, 32,768 total output-token cap, 100,000 total model-token cap, and at most one repair iteration. Direct receives one call by definition; CADIR/SimpleCAD may use the one repair call. Actual input usage can differ because repair replays the identical visual context.

| backbone | method | generation_success_cases | generation_failure_cases | simultaneous_success_cases | api_calls_total | repair_iterations_total | total_tokens_total |
| --- | --- | --- | --- | --- | --- | --- | --- |
| qwen3.7-plus | direct_frontier_mllm | 6 | 4 | 0 | 10 | 0 | 81706 |
| qwen3.7-plus | cadir_simplecad | 6 | 4 | 0 | 16 | 6 | 99335 |
| qwen3.7-max-2026-06-08 | direct_frontier_mllm | 7 | 3 | 0 | 10 | 0 | 54144 |
| qwen3.7-max-2026-06-08 | cadir_simplecad | 8 | 2 | 0 | 14 | 4 | 94147 |

Successful-output medians (rather than silently discarding failed cases from the denominator) are recorded in `backbone_generalization.csv`; all 40 case rows and token/call/latency accounting are in `equal_budget_results.csv`.

## C. Second-backbone generalization

The second run uses Qwen3.7-Max-2026-06-08, a distinct released Max snapshot, under the identical protocol. It is independent model evidence but not cross-provider evidence, since both backbones are from the same provider/family.
All four tracks have 0 simultaneous successes: **True**. Deterministic structural failure patterns occur in 4/4 tracks.

## D. Runnable public-agent baseline

CADSmith was audited at the recorded commit. Its official repository has no declared license file, requires an Anthropic key not available in this environment, and targets single-part CAD rather than native URDF/articulation. The official Claude configuration remains NOT_RUN. A Qwen client adaptation preserved the execution-only workflow but disabled the LLM Judge; its frozen-case status is `UNSUPPORTED_INPUT=10` because all ten articulated inputs are outside CADSmith's native contract. It is not scored as zero for unsupported dimensions.

## E. Case-level structural gap

The failure taxonomy is deterministic: invalid CAD, missing/extra part, wrong decomposition, topology, joint type, axis, origin, poor geometry/curved geometry and wrong multi-pose motion. Self-collision is UNSUPPORTED by this evaluator. See `results/final_validation/case_level_failures.csv` and `failure_breakdown.csv`.

**Recommendation: continue the paper.** Under two released multimodal backbones and Direct/SimpleCAD execution styles, no output jointly clears geometry, assembly, kinematics and multi-pose motion. SimpleCAD execution conditioning can improve artifact production, but does not close the joint structural gap. This supports (rather than proves) headroom for a surface-aware and kinematic/interface-aware method.
The future paper must add a broader, cross-provider baseline suite and a runnable licensed public-agent comparison before making field-wide claims.
