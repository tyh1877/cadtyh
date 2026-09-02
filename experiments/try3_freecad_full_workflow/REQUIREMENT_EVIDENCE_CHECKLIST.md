# Try-3 FreeCAD Requirement-to-Evidence Checklist

## Protocol and inputs

- [x] Clean experiment directory created at `experiments/try3_freecad_full_workflow/`.
- [x] Formal FreeCAD protocol recorded in `TRY3_FREECAD_PROTOCOL.md`.
- [x] TrySet-5 manifest recorded in `tryset5_v1.csv`.
- [x] TrySet-5 selection rationale recorded in `tryset5_selection.md`.
- [x] Input audit confirms all selected cases have multi-view images,
  engineering text, and sanitized URDF.
- [x] Leakage audit confirms no planner input contains GT mesh/STEP/CAD,
  unsanitized URDF, product identity, or GT segmentation.

## Schemas and contracts

- [x] `visual_evidence_packet_v1.schema.json` skeleton exists.
- [x] `mechanical_embodiment_plan_v1.schema.json` skeleton exists.
- [x] `interface_graph_v1.schema.json` skeleton exists.
- [x] `mechanical_feature_graph_v1.schema.json` skeleton exists.
- [x] `skill_call_v1.schema.json` skeleton exists.
- [x] `executable_cad_ir_v2.schema.json` skeleton exists.
- [x] Skeleton/schema existence validator passes with no missing files and no
  JSON parse errors. Full instance validators remain pending until stage
  examples are added.

## Workflow stages

- [x] Stage runner skeleton exists and encodes V0/V1/V2 dependencies.
- [x] Stale artifact guard skeleton exists.
- [ ] Visual Evidence Agent implemented and produces one packet per robot/link.
- [ ] Mechanical Embodiment Architect implemented.
- [ ] Interface Engineer implemented.
- [ ] Per-link CAD Engineer implemented.
- [ ] RobotCAD FreeCAD skill layer implemented.
- [ ] FreeCAD backend executor implemented for formal Try-3 skill calls.
- [ ] Assembly Integrator implemented.
- [ ] Verification Agent implemented.

## Formal execution

- [ ] V0 FreeCAD baseline run covers all 5 robots.
- [ ] V1 run covers all 5 robots.
- [ ] V2 run covers all 5 robots.
- [ ] All failures are preserved in the denominator.
- [ ] No silent fallback is recorded.
- [ ] FCStd/STEP/STL outputs are generated for successful cases.
- [ ] Full robot assembly outputs are generated for successful cases.

## Evaluation

- [ ] Interface gap metrics computed.
- [ ] Joint axis angular/offset metrics computed.
- [ ] Interface constraint satisfaction computed.
- [ ] Disconnected part and floating feature rates computed.
- [ ] Interference metrics computed.
- [ ] Global/per-link/joint-local geometry metrics computed.
- [ ] Visible mechanical feature recall computed.
- [ ] Primitive proxy degeneration rate computed.
- [ ] FreeCAD native feature and skill execution statistics computed.
- [ ] Contact sheets generated as diagnostic artifacts.

## Reporting and repository discipline

- [ ] `results/try3_report.md` answers all Try-3 final reporting questions.
- [x] Heavy geometry remains outside Git or under ignored paths. Verified
  `experiments/try3_freecad_full_workflow/runs/` with `git check-ignore`.
- [x] Relevant skeleton-layer validation commands have been run:
  `py_compile`, `validate_skeleton.py`, and `audit_inputs.py`.
- [x] Diff inspected for skeleton-layer changes before commit.
- [x] Local Git commit created; no push unless explicitly authorized.
