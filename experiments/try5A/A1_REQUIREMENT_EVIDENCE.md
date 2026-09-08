# Try-5A Phase 5 / A1 requirement-to-evidence checklist

- [x] A1 consumes the frozen Robot Assembly Plan for all 12 links and records its hash/fields.
- [x] A1 does not read the Joint Interface Graph, shared contracts, shared ports or shared envelopes.
- [x] A0 link plans remain unchanged and all 12 A1 plans are frozen before FreeCAD execution.
- [x] Robot Plan role, envelope, principal direction and body family affect LinkCoarseSpec/CAD IR; mutation tests prove sensitivity.
- [x] All 12 A1 links build/export/reopen/recompute/edit with zero silent fallback.
- [x] A1 whole robot is assembled only with the same canonical URDF transforms.
- [x] A0/A1 use one common deterministic evaluator and identical sweep settings.
- [x] Compare link success, connected/floating rates, gap, radius mismatch, penetration, collision and morphology.
- [x] Unified A0/A1 contact sheet and typical remaining interface failures are recorded.
- [x] Stop after A1; A2 remains absent.
