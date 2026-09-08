# Try-5A Phase 6–10 / A2 and finalization checklist

- [x] A2 consumes both frozen Robot Plan and Joint Interface Graph for all links/joints.
- [x] Each joint contract produces paired parent/child interface geometry with identical nominal frame/size references.
- [x] J08/J09 guide engagement consumes prismatic limits and mimic/canonical travel.
- [x] Contract mutation tests change generated port center, radius and guide depth.
- [x] All 12 A2 plans are frozen before FreeCAD; A0/A1 link plans remain unchanged.
- [x] All 12 A2 links build/export/reopen/recompute/edit with zero silent fallback.
- [x] A2 assembly uses the same canonical URDF transforms and no visual adjustment.
- [x] One common evaluator recomputes A0/A1/A2 interface, assembly and sweep metrics.
- [x] Whole-robot contact sheet and A0/A1/A2 comparison tables exist.
- [x] Link, assembly, interface, kinematic, morphology and resource artifacts cover all conditions.
- [x] Report answers all 26 Try5-A questions and states whether the experiment objectives are complete.
- [x] Method/dataflow/leakage/determinism audits pass; no Robot B, transfer or Try-5B execution.
