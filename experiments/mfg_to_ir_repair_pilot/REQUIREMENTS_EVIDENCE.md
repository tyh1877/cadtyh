# MFG-to-IR Repair Pilot — requirement/evidence checklist

## Frozen scope

- [x] Reuse the same 6 frozen links from `experiments/freecad_robot_link_reconstruction_pilot_v2/inputs/frozen_links.csv`.
- [x] Do not call an upstream LLM/VLM in this pilot.
- [x] Preserve failed cases in the denominator.

Evidence: `config/pilot_config.json`, `scripts/repair_mfg.py`, result CSV row counts.

## Repair policy

- [x] Repair only syntactic/canonical schema issues and deterministic field aliases.
- [x] Do not use GT mesh, STEP, CAD identity, segmentation, or feature tree as repair input.
- [x] Record repair actions per sample.
- [x] Mark incomplete geometry as `IR_INCOMPLETE`; do not silently fill missing decisions.

Evidence: `runs/*/*/*/repair_log.json`, `results/repair_generation.csv`, `results/ir_translation.csv`.

## Execution policy

- [x] Execute only schema-valid, IR-complete links with the FreeCAD API backend.
- [x] Record every operation success/failure, semantic match, and fallback flag.
- [x] Require silent fallback count to remain zero.

Evidence: `results/execution_metrics.csv`, `results/failed_operations.csv`, `results/aggregate_results.json`.

## Reporting

- [x] Compare repaired R1/R2 against v2 original counts.
- [x] Classify remaining bottlenecks as MFG parsing, MFG schema expression, MFG→IR translation, CAD parameter estimation, selector/backend execution, or vocabulary insufficiency.
- [x] Produce a concise report suitable for paper decision tracking.

Evidence: `results/mfg_to_ir_repair_pilot_report.md`.
