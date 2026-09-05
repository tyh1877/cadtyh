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
- [x] `visual_scan_plan_v1.schema.json` exists for VLM-guided focus planning.
- [x] `visual_evidence_packet_v2.schema.json` exists for local evidence and
  feature zoom packets.
- [x] Skeleton/schema existence validator passes with no missing files and no
  JSON parse errors. Full instance validators remain pending until stage
  examples are added.

## Workflow stages

- [x] Stage runner skeleton exists and encodes V0/V1/V2 dependencies.
- [x] Stale artifact guard skeleton exists.
- [x] Visual Evidence Agent deterministic infrastructure implemented and
  produces one packet per robot/link for all 5 robots.
- [x] Visual Evidence Agent VLM-backed focus/evidence generation passes.
  Evidence: `results/visual_agent_v2_case_summary.csv` records 5/5 successful
  `glm-5.3-flash` cases, 63 link packets, and 301 crop records.
- [x] Manual spot check passes for crop/evidence quality with caveat. Contact
  sheets show real feature-level zoom crops; overlapping crops remain for links
  visually contained in a shared shell and must be carried forward as
  uncertainty.
- [x] Mechanical Embodiment Architect implemented for the Codex continuation.
- [x] Interface Engineer implemented with exact sanitized-URDF joint coverage.
- [x] Per-link CAD Engineer implemented for all 63 links and three versions.
- [x] RobotCAD FreeCAD skill projection implemented for the frozen basic subset.
- [x] FreeCAD backend executor implemented for formal Try-3 skill calls.
- [x] Assembly Integrator implemented with canonical URDF placements.
- [x] Deterministic Verification Agent implemented; it performs no repair.

## Formal execution

- [x] V0 FreeCAD baseline run covers all 5 robots.
- [x] V1 run covers all 5 robots.
- [x] V2 run covers all 5 robots.
- [x] All 15 cells and the preflight parser incident are preserved.
- [x] No silent fallback is recorded (0 across 693 operations).
- [x] Per-link FCStd/STEP/STL outputs are generated for 189/189 link cells.
- [x] Full robot assembly outputs are generated and reopened for 15/15 cells.

## Evaluation

- [x] Interface gap metrics computed.
- [x] Joint axis/origin equality audited structurally against sanitized URDF;
  native moving-joint semantics remain outside the amended acceptance boundary.
- [x] Interface constraint satisfaction computed.
- [x] Disconnected-joint rate computed.
- [x] Non-adjacent AABB overlap is reported as an interference proxy.
- [x] Global/per-link/joint-local geometry metrics computed with full coverage.
- [x] Visible-feature planned/executed recall computed against pre-output Codex
  labels; executed recall is 0 and labels are not independent expert GT.
- [x] Primitive proxy degeneration rate computed as an operation-tree proxy.
- [x] FreeCAD native feature and skill execution statistics computed.
- [x] Five GT/V0/V1/V2 contact sheets generated as diagnostic artifacts.

## Reporting and repository discipline

- [x] `results/codex_agent_v1_try3_report.md` answers RQ1/RQ2/RQ3 and records
  the Codex substitution limits.
- [x] Heavy geometry remains outside Git or under ignored paths. Verified
  `experiments/try3_freecad_full_workflow/runs/` with `git check-ignore`.
- [x] Relevant skeleton-layer validation commands have been run:
  `py_compile`, `validate_skeleton.py`, and `audit_inputs.py`.
- [x] Diff inspected for skeleton-layer changes before commit.
- [x] Local Git commit created; no push unless explicitly authorized.
