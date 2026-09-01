# Requirement-to-evidence checklist

Experiment: `freecad_robot_link_reconstruction_pilot`

Status: completed pilot run with documented failures

| Requirement | Evidence artifact | Status |
|---|---|---|
| Freeze the same 6 links without adding/removing cases | `inputs/frozen_links.csv`, `inputs/frozen_link_roles.md` | done |
| Document link-role grammar | `docs/robot_link_grammar_v1.md` | done |
| Define Mechanical Feature Graph schema and docs | `schemas/mechanical_feature_graph_v1.schema.json`, `docs/mechanical_feature_graph_v1.md` | done |
| Define Executable CAD IR v1.1 schema | `schemas/executable_cad_ir_v1_1.schema.json` | done |
| Preserve R0/R1/R2 fairness controls | `config/pilot_config.json` | done |
| Generate/record local visual evidence for R2 without GT geometry | `inputs/local_evidence_manifest.json`, `results/local_evidence_audit.csv` | done |
| Run R0/R1/R2 on all 6 links with failures preserved | `results/execution_metrics.csv`, `results/resource_accounting.csv` | done |
| Keep FreeCAD strict native execution with silent fallback = 0 | `results/execution_metrics.csv`, per-link execution logs | done |
| Evaluate Mechanical Feature Recall per version/link/family | `results/mechanical_feature_recall.csv` | done |
| Evaluate geometry metrics IoU/Chamfer/HD95 when GT mesh exists | `results/per_link_geometry.csv` | done |
| Evaluate joint-local geometry when URDF joint context exists | `results/joint_local_geometry.csv` | done |
| Count native feature usage as diagnostic | `results/native_feature_usage.csv` | done |
| Produce visual/contact-sheet diagnostic without AI Judge | `results/contact_sheets/` | done |
| Write final report answering the required 20 questions | `results/freecad_robot_link_reconstruction_pilot_report.md` | done |
