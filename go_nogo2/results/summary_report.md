# Go/No-Go 2 pilot summary

**Decision: INCONCLUSIVE**

The fixed dataset and deterministic evaluator are ready. `NOT_RUN` records are availability
blockers and are not model scores.

## Run coverage

| method | FAILURE | NOT_RUN | SUCCESS |
| --- | --- | --- | --- |
| direct_frontier_mllm | 4 | 0 | 6 |
| cadir_simplecad | 1 | 0 | 9 |
| articad | 0 | 10 | 0 |
| assemcad | 0 | 10 | 0 |

## Simultaneous successes

| method | cases |
| --- | --- |
| direct_frontier_mllm | 0 |
| cadir_simplecad | 0 |
| articad | 0 |
| assemcad | 0 |

## Executable-method aggregate

Metric medians below use successful generated outputs only; generation failures remain
visible in their own columns and in the fixed denominator of ten.

| method | terminal_cases | generation_success_cases | generation_failure_cases | not_run_cases | attempts_total | latency_seconds_median_success | simultaneous_success_cases | chamfer_median_successful_outputs | hd95_median_successful_outputs | voxel_iou_median_successful_outputs | part_f1_median_successful_outputs | assembly_graph_f1_median_successful_outputs | joint_type_accuracy_median_successful_outputs | axis_error_degrees_median_median_successful_outputs | joint_origin_error_normalized_median_median_successful_outputs | link_translation_error_normalized_median_median_successful_outputs | link_rotation_error_degrees_median_median_successful_outputs |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| direct_frontier_mllm | 10 | 6 | 4 | 0 | 10 | 92.05007114999171 | 0 | 0.005048188037280871 | 0.14932388648201603 | 0.30037927610952414 | 0.7666666666666666 | 0.6666666666666666 | 0.6666666666666666 | 45.0 | 0.2356483852520474 | 0.3446073568519982 | 103.28526114520103 |
| cadir_simplecad | 10 | 9 | 1 | 0 | 16 | 130.56621409999207 | 0 | 0.006486960771210763 | 0.17644695894156082 | 0.29880478087649404 | 0.7 | 0.6666666666666666 | 0.6666666666666666 | 45.0 | 0.1851961535222213 | 0.30925707566657984 | 92.664786571387 |

## Failure patterns

| method | category | failure_pattern | case_count |
| --- | --- | --- | --- |
| cadir_simplecad | model_failure | invalid_cad | 1 |
| cadir_simplecad | model_failure | poor_curved_geometry | 9 |
| cadir_simplecad | model_failure | poor_geometry | 6 |
| cadir_simplecad | model_failure | wrong_joint_axis | 5 |
| cadir_simplecad | model_failure | wrong_joint_origin | 9 |
| cadir_simplecad | model_failure | wrong_joint_type | 7 |
| cadir_simplecad | model_failure | wrong_motion | 9 |
| cadir_simplecad | model_failure | wrong_topology | 7 |
| direct_frontier_mllm | model_failure | invalid_cad | 4 |
| direct_frontier_mllm | model_failure | poor_curved_geometry | 6 |
| direct_frontier_mllm | model_failure | poor_geometry | 6 |
| direct_frontier_mllm | model_failure | wrong_joint_axis | 3 |
| direct_frontier_mllm | model_failure | wrong_joint_origin | 6 |
| direct_frontier_mllm | model_failure | wrong_joint_type | 4 |
| direct_frontier_mllm | model_failure | wrong_motion | 6 |
| direct_frontier_mllm | model_failure | wrong_topology | 4 |

## Interpretation

The four-baseline comparison is incomplete, so neither a SOTA gap nor its absence is established.
For the two executable tracks, both have 0/10 simultaneous successes. The SDK-conditioned
CADIR track improves generation success from 6/10 to 9/10, but it does not close the joint
geometry-assembly-kinematics gap. This is provisional evidence, not a four-method decision.
