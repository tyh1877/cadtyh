# FreeCAD Robot Link Reconstruction Pilot v2 Report

## Protocol

- Dataset: same six frozen links from v1; no new links were added or removed.
- R0: deterministic FreeCAD baseline.
- R1-v2: Mechanical Feature Graph v2 with explicit anchors and dimensions.
- R2-v2: GLM `glm-5.3-flash` responses with multimodal `image_url` prompt contract. This report may be produced from repaired existing responses when `generate_feature_graphs.py --repair-existing` is used; check `feature_graph_generation.csv` and the evidence checklist before claiming a fresh live VLM rerun.
- Formal backend: FreeCADCmd + FreeCAD Python API. MCP is not part of acceptance.
- Failure policy: missing geometry fields are `IR_INCOMPLETE`; silent fallback is forbidden.

## Aggregate metrics

| version | links | mean MFR | mean voxel IoU | mean Chamfer | mean HD95 | success links |
|---|---:|---:|---:|---:|---:|---:|
| R0 | 6 | 0.13888888888888887 | 0.3811509976631512 | 0.0335807433512015 | 0.07489474953290651 | 6/6 |
| R1 | 6 | 0.3055555555555556 | 0.268407108439335 | 0.05380439423794996 | 0.11336549131852347 | 2/6 |
| R2 | 6 | 0.47222222222222227 | 0.3003562142152656 | 0.03948193339327777 | 0.09487467486838747 | 3/6 |

## Pipeline success by stage

| version | MFG schema success | IR complete | FreeCAD batch success |
|---|---:|---:|---:|
| R1-v2 | 1/6 | 2/6 | 2/6 |
| R2-v2 | 2/6 | 3/6 | 3/6 |

## Acceptance check

- Silent fallback total: `0`.
- Acceptance result: `NO-GO` for entering the full Try-3 FreeCAD multi-agent workflow.
- Main failed criteria: batch success is below 5/6; R2-v2 improves MFR but succeeds on only 3/6 links.
- Current operation failures: no native operation failures were recorded if `failed_operations.csv` is empty; remaining failed links are stage-level `IR_INCOMPLETE` cases from missing MFG/IR geometry fields.
- Primary bottleneck: VLM/MFG schema compliance and MFG-to-IR parameter completeness. Backend modifier execution is no longer the dominant failure in this run when silent fallback is 0 and `failed_operations.csv` is empty.
- Detailed per-link metrics are in `mechanical_feature_recall.csv`, `execution_metrics.csv`, `per_link_geometry.csv`, and `joint_local_geometry.csv`.
- R2 visual traceability is in `r2_traceability.csv`.
- Contact sheets are in `results/contact_sheets/`.

## Known interpretation limits

- This is link-level reconstruction, not full robot assembly.
- Chamfer/HD95/IoU compare normalized meshes without GT segmentation; local joint metrics are diagnostic, not final benchmark claims.
- If a generated link does not look like a robot link, inspect `local_visual_observations.json`, `mechanical_feature_graph_v2.json`, `executable_cad_ir_v1_2.json`, and `execution_log.json` to assign the bottleneck.
