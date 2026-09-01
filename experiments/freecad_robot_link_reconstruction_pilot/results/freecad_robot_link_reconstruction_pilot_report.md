# FreeCAD Robot Link Reconstruction Pilot Report

Date: 2026-09-01  
Experiment: `freecad_robot_link_reconstruction_pilot`  
Backend: `FreeCADCmd + FreeCAD Python API`  
LLM planner: `qwen3.7-plus`  
Scope: frozen 6 link-level cases only; no full assembly; no GT geometry in planning.

## Executive conclusion

This pilot partially supports continuing the Mechanical Feature Graph route, but it does not yet justify moving directly to full Try-3 multi-agent assembly.

The positive result is that explicit Mechanical Feature Graph planning improved mechanical semantic coverage:

| Version | Batch success | Native ops success | Mean MFR | Mean voxel IoU | Mean Chamfer | Mean HD95 | Silent fallback |
|---|---:|---:|---:|---:|---:|---:|---:|
| R0 current IR baseline | 6/6 | 30/30 | 0.528 | 0.294 | 0.0549 | 0.1423 | 0 |
| R1 MFG -> IR -> FreeCAD | 3/6 | 52/55 | 0.778 | 0.198 | 0.0444 | 0.1072 | 0 |
| R2 local evidence + MFG -> IR -> FreeCAD | 3/6 | 57/60 | 0.750 | 0.204 | 0.0426 | 0.1040 | 0 |

Interpretation:

- R1 improves mechanical feature recall substantially over R0.
- R2 does not show clear improvement over R1 in this pilot.
- Chamfer/HD95 improve, but voxel IoU drops, which means the generated bodies became mechanically richer but global volume/scale/alignment became less accurate.
- FreeCAD execution is mostly reliable at the operation level, but final batch failures remain caused by native fillet/chamfer modifier instability after complex boolean/unions.
- The main bottleneck is no longer primitive-only FreeCAD capability. It is the upstream and middle layer: feature grounding, feature-to-IR parameterization, and robust modifier selection.

## 20 required answers

1. The six frozen links and roles are:
   - `dev_arm-dcc2b0ce1e/L2`: `upper_arm`
   - `dev_arm-dcc2b0ce1e/L3`: `elbow_housing`
   - `dev_arm-dcc2b0ce1e/L4`: `forearm`
   - `dev_arm-ab15a75247/L0`: `base_or_shoulder`
   - `dev_arm-ab15a75247/L2`: `main_link`
   - `dev_arm-ab15a75247/L4`: `wrist_or_tool_side_link`

2. Batch execution success:
   - R0: 6/6
   - R1: 3/6
   - R2: 3/6

3. IR_INCOMPLETE:
   - None for R1/R2 after canonicalization and translation. All 12 R1/R2 Mechanical Feature Graphs translated to schema-valid Executable CAD IR.

4. NATIVE_OPERATION_FAILURE:
   - Yes. Remaining R1/R2 failures are native fillet/chamfer modifier failures on already-created shapes.

5. Silent fallback:
   - Still 0. No failed complex operation was silently replaced and marked successful.

6. R1 Mechanical Feature Graph quality:
   - Yes, R1 contains meaningful mechanical features rather than only operation words. It includes joint housings, elongated bodies, flanges, bosses, recess/lightening cuts, webs, palm/tool-side features, and surface modifiers.

7. R2 local crop usage:
   - R2 used local evidence records from `inputs/local_evidence_manifest.json`. The manifest records 18 crop records, 3 per link, with `gt_geometry_used=false`.

8. Mechanical Feature Recall:
   - R0: 0.528
   - R1: 0.778
   - R2: 0.750

9. Joint housing recall:
   - Proximal joint housing: R0 5/5, R1 4/5, R2 4/5.
   - Distal joint housing: R0 0/4, R1 4/4, R2 4/4.
   - Net result: distal housing improves strongly; proximal housing slightly worsens because one expected proximal feature is not realized in R1/R2.

10. Flange / boss / recess / taper recall:
   - Flange: R0 0/1, R1 1/1, R2 1/1.
   - Mounting boss: R0 0/2, R1 2/2, R2 2/2.
   - Recess: R0 0/2, R1 1/2, R2 0/2.
   - Lightening cut: R0 0/2, R1 2/2, R2 2/2.
   - Tapered transition: R0 3/3, R1 3/3, R2 3/3.

11. Per-link geometry:
   - Aggregate voxel IoU worsened from R0 0.294 to R1 0.198 and R2 0.204.
   - Chamfer improved from R0 0.0549 to R1 0.0444 and R2 0.0426.
   - HD95 improved from R0 0.1423 to R1 0.1072 and R2 0.1040.
   - Some per-link geometry rows are marked `GT_OR_PRED_MESH_MISSING`, so geometry aggregates are based on computable cases, not all 18 version-link pairs.

12. Joint-local geometry:
   - Mean available joint-local Chamfer: R0 0.0461, R1 0.0436, R2 0.0418.
   - Mean available joint-local HD95: R0 0.1310, R1 0.1011, R2 0.0978.
   - Mean available joint-local IoU: R0 0.318, R1 0.193, R2 0.194.
   - Interpretation: local surface distance improves, but local occupied-volume overlap worsens.

13. Is R1 better than R0?
   - Yes on mechanical semantics and distance metrics; no on batch execution and voxel IoU.
   - R1 is methodologically useful but not yet production-ready.

14. Is R2 better than R1?
   - Not clearly. R2 gives slightly better Chamfer/HD95 but lower MFR and no batch-success improvement. This pilot does not prove local crops add value yet.

15. Largest improvements:
   - `dev_arm-ab15a75247/L4` wrist/tool-side link: MFR improves from 0.167 to 0.833.
   - `dev_arm-dcc2b0ce1e/L2` upper arm: MFR improves from 0.667 to 1.000.

16. Remaining failed links:
   - R1 failures: `dev_arm-dcc2b0ce1e/L4`, `dev_arm-ab15a75247/L0`, `dev_arm-ab15a75247/L2`.
   - R2 failures: `dev_arm-dcc2b0ce1e/L4`, `dev_arm-ab15a75247/L0`, `dev_arm-ab15a75247/L2`.
   - All are terminal modifier failures, mainly fillet/chamfer on complex post-boolean topology.

17. Are outputs still mainly box/cylinder?
   - Less than R0, but still too coarse. R1/R2 use more revolve/loft/boolean structures, but the feature-to-IR translator still parameterizes many features with simplified canonical dimensions. The visual result can still look like a stylized proxy rather than a faithful robot link.

18. Native Loft/Revolve/Shell/Sweep usage:
   - Revolve and Loft appear frequently in R1/R2.
   - Shell/Sweep did not appear in this six-link pilot output.
   - This is a limitation of current feature graph and translator routing, not a FreeCAD capability limitation, because backend smoke tests already validated these native operations.

19. Current largest bottleneck:
   - Primary bottleneck: Feature Graph -> CAD IR translation and CAD parameter estimation.
   - Secondary bottleneck: modifier edge selection for fillet/chamfer after boolean/union.
   - R2-specific bottleneck: local crops are recorded and consumed, but current prompts/translators do not convert them into reliably better local geometry.

20. Should the next step enter full Try-3 FreeCAD multi-agent workflow?
   - Not yet. The next step should be a focused repair pilot before full Try-3:
     1. Improve MFG-to-IR parameterization with explicit feature anchors, local coordinate frames, and per-feature dimensions.
     2. Add typed selector strategies for fillet/chamfer instead of raw edge indices.
     3. Add Sweep/Shell cases where feature graph asks for curved arms or hollow housings.
     4. Re-run this same 6-link pilot once more with no dataset changes.
   - Move to full Try-3 only if R1/R2 achieve higher batch success and maintain the MFR gain without collapsing IoU.

## Evidence artifacts

- Frozen links: `inputs/frozen_links.csv`
- Link-role grammar: `docs/robot_link_grammar_v1.md`
- MFG schema: `schemas/mechanical_feature_graph_v1.schema.json`
- CAD IR schema: `schemas/executable_cad_ir_v1_1.schema.json`
- R2 local evidence: `inputs/local_evidence_manifest.json`
- MFG generation: `results/feature_graph_generation.csv`
- IR translation: `results/ir_translation_results.csv`
- FreeCAD execution: `results/execution_metrics.csv`, `results/execution_summary.json`
- Mechanical semantics: `results/mechanical_feature_recall.csv`
- Geometry: `results/per_link_geometry.csv`, `results/joint_local_geometry.csv`
- Native feature diagnostics: `results/native_feature_usage.csv`
- Contact sheets: `results/contact_sheets/`

