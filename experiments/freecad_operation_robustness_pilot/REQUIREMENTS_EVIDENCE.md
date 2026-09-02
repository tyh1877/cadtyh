# FreeCAD Operation Robustness Pilot — requirement/evidence checklist

## Frozen inputs

- [x] Use `mfg_to_ir_repair_pilot` repaired IR as the only replay input.
- [x] Preserve R1/R2 × 6 frozen links in the denominator.
- [x] Do not call LLM/VLM or regenerate MFG.

Evidence: `config/pilot_config.json`, `results/replay_metrics.csv`.

## Backend behavior

- [x] `boolean_union` uses auditable sequential fuse.
- [x] `boolean_cut` records bbox preflight and fails early on non-intersection.
- [x] `fillet/chamfer` use typed selector candidates plus native trial validation.
- [x] Silent fallback remains forbidden.

Evidence: `robotcad/backends/freecad_api/FreeCADBackend.py`, `runs/*/*/*/freecad/execution_log.json`.

## Operation smoke

- [x] `boolean_union`, `boolean_cut`, `fillet`, and `chamfer` each have one expected-success smoke and one expected-failure smoke.
- [x] Expected failures must return explicit failure codes.

Evidence: `results/operation_smoke.csv`.

## Replay and report

- [x] Replay all current IR-complete samples and preserve IR-incomplete rows.
- [x] Emit failure code, preflight, and failure context for failed operations.
- [x] Report whether R1/R2 batch success reaches the acceptance threshold.
- [x] Create a local Git commit; do not push.

Evidence: `results/replay_metrics.csv`, `results/failed_operations.csv`, `results/freecad_operation_robustness_pilot_report.md`.
