# FreeCAD Robot Link Reconstruction Pilot v2 Report

## Protocol

- Dataset: same six frozen links from v1; no new links were added or removed.
- R0: deterministic FreeCAD baseline.
- R1-v2: Mechanical Feature Graph v2 with explicit anchors and dimensions.
- R2-v2: GLM `glm-5.3-flash` with real multimodal `image_url` inputs for global views and local crops, then MFG v2.
- Formal backend: FreeCADCmd + FreeCAD Python API. MCP is not part of acceptance.
- Failure policy: missing geometry fields are `IR_INCOMPLETE`; silent fallback is forbidden.

## Aggregate metrics

| version | links | mean MFR | mean voxel IoU | mean Chamfer | mean HD95 | success links |
|---|---:|---:|---:|---:|---:|---:|
| R0 | 6 | 0.13888888888888887 | 0.39213448613986934 | 0.03339269433640749 | 0.07454937718041214 | 6/6 |
| R1 | 6 | 0.2777777777777778 |  |  |  | 0/6 |
| R2 | 6 | 0.3055555555555556 | 0.26184538653366585 | 0.03656075715249085 | 0.09252209790251804 | 1/6 |

## Pipeline success by stage

| version | MFG schema success | IR complete | FreeCAD batch success |
|---|---:|---:|---:|
| R1-v2 | 4/6 | 2/6 | 0/6 |
| R2-v2 | 4/6 | 2/6 | 1/6 |

## Acceptance check

- Silent fallback total: `0`.
- Acceptance result: `NO-GO` for entering the full Try-3 FreeCAD multi-agent workflow.
- Main failed criteria: batch success is below 5/6; R2-v2 improves MFR but succeeds on only 1/6 links; fillet/chamfer execution failures remain visible in `failed_operations.csv`.
- Primary bottleneck: VLM/MFG schema compliance and MFG-to-IR parameter completeness. Secondary bottleneck: fillet/chamfer selector/backend robustness on complex fused bodies.
- Detailed per-link metrics are in `mechanical_feature_recall.csv`, `execution_metrics.csv`, `per_link_geometry.csv`, and `joint_local_geometry.csv`.
- R2 visual traceability is in `r2_traceability.csv`.
- Contact sheets are in `results/contact_sheets/`.

## Known interpretation limits

- This is link-level reconstruction, not full robot assembly.
- Chamfer/HD95/IoU compare normalized meshes without GT segmentation; local joint metrics are diagnostic, not final benchmark claims.
- If a generated link does not look like a robot link, inspect `local_visual_observations.json`, `mechanical_feature_graph_v2.json`, `executable_cad_ir_v1_2.json`, and `execution_log.json` to assign the bottleneck.
