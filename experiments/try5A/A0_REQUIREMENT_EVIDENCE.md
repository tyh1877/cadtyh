# Try-5A Phase 4 / A0 requirement-to-evidence checklist

- [x] A0 consumes only images, engineering text, sanitized URDF and per-link local joint context.
- [x] A0 generator has no read/import/reference to Robot Assembly Plan, Joint Interface Graph, shared ports or shared envelopes.
- [x] All 12 independent link decisions are frozen before FreeCAD execution and remain in the denominator.
- [x] Every link emits FCStd/STEP/STL, LinkCoarseSpec, InterfaceRefs, CAD IR, execution log and parameter manifest.
- [x] All link files reopen/recompute/export with zero silent fallback.
- [x] Whole robot is assembled only by canonical URDF transforms with no visual placement adjustment.
- [x] Deterministic metrics cover connected joints, floating links, gap, penetration, contact locality, axis angular/offset and origin/center errors.
- [x] Canonical kinematic consistency and lightweight joint-sweep collision results are saved.
- [x] Whole-robot contact sheet and morphology diagnostics exist.
- [x] Typical independent-design assembly failures are identified without repairing A0.
- [x] Dataflow/leakage audit proves L1/L2 files were not consumed.
- [x] Stop after A0 report; A1/A2 remain absent.
