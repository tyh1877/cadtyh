# Try-6.0-C1 L04 requirement-to-evidence checklist

- [x] Read the exact frozen A2a L04 Direct-Qwen C0 metrics from its tracked result and verify artifact hashes.
- [x] Preserve the A1 32-case formal holdout lock at `accessed=false`, `evaluation_count=0`; fail closed on access.
- [x] Freeze a new Try-6 protocol, hashes, success gates, optimizer seed/budget, and independent validator before formal C1.
- [x] Audit PNG MIBA view matrices, missing pixel projection metadata, visible L04 masks, and URDF joint landmarks.
- [x] Define a minimal typed KFDG schema with functional, geometric, parameter, and relation nodes.
- [x] Pass schema round-trip, valid/invalid fixture, unknown-field, missing-field, and unit tests before the VLM call.
- [x] Record 6–10 visual parameters with value, unit, bounds, provenance, and confidence; keep URDF/interface parameters fixed.
- [x] Use Qwen only for visible topology, relations, view evidence, and dimensionless cues; validate its response without editing it. The response failed the top-level type requirement and was retained unchanged.
- [x] Build a visual objective with pre-registered silhouette, edge/profile, landmark, and prior terms, using no GT or motion feedback.
- [x] Prove a URDF anchor mutation changes the metric solver output in the nonformal smoke.
- [x] Pass 1–3 nonformal CAD/render/objective smoke points and freeze the solver budget before the single formal run.
- [ ] Generate a formal FreeCAD Sketch/Pad/Pocket/interface opening/transition/Fillet history, parameter bindings, and KFDG→feature mapping. Infrastructure smoke only; blocked by the invalid formal KFDG envelope.
- [x] Pass FreeCAD reopen/recompute and one small non-interface parameter edit smoke, limited to the nonformal infrastructure artifact.
- [ ] Evaluate the one frozen C1 candidate with the same geometry and Exact mechanical evaluators as C0. No formal candidate exists.
- [ ] Apply pre-registered representation, BICR, IoU, silhouette, nChamfer, and nHD95 gates; report motion as diagnostics only. Geometry and mechanical gates were not evaluable.
- [x] Run an independent failure-path audit, freeze provenance and failure accounting, and output one of GO_C2 / METRIC_GROUNDING_WEAK / REPRESENTATION_FAILURE.
- [x] Stop after C1; do not modify Try-5, access formal holdout, or implement KFDE/C2.

Terminal decision: `REPRESENTATION_FAILURE`. Formal solver evaluations=0,
formal CAD builds=0, GT evaluations=0, retries=0, and formal holdout access=0.
