# upstream modifier contract repair evidence checklist

- [x] MFG schema supports `modifier_intent` for fillet/chamfer features.
- [x] GLM prompt forbids unsupported absolute fillet/chamfer values and asks for relative intent.
- [x] Translator resolves modifier values from intent and records requested/resolved/safe-cap provenance.
- [ ] Fresh R1/R2 live GLM multimodal generation completed. Attempted on 2026-09-02, but the first live request produced no case output after about five minutes; the current artifact rerun therefore used `--repair-existing` over the stored GLM responses/MFG files.
- [x] IR translation rerun for R0/R1/R2 on the repaired existing MFG artifacts.
- [x] FreeCAD execution rerun for latest generated parts.
- [x] Evaluation rerun and report updated.
- [ ] Tracked code/results committed locally; heavy geometry remains ignored.

## Current rerun summary

- R0 FreeCAD batch success: `6/6`.
- R1 FreeCAD batch success: `2/6`.
- R2 FreeCAD batch success: `3/6`.
- Silent fallback: `0`.
- Native operation failures: `0`; remaining failures are `IR_INCOMPLETE`.
- Latest generated `.FCStd/.step/.stl` files are under `experiments/freecad_robot_link_reconstruction_pilot_v2/runs/*/*/*/freecad/`.
