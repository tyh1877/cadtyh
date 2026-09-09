# Try-5A.4 requirement-to-evidence checklist

Protocol source: `try5/Try5-A.4.md` (hash frozen in the experiment manifest).

This checklist is frozen before the formal M0/M1/M2 run. A checked item requires
the named artifact to exist and the final validation gate to confirm it.

- [x] Freeze Robot A inputs, sanitized URDF, K1 decisions, knowledge version,
  evaluator, pose fractions, and backend in `results/try5a4/manifest.json`.
- [x] Select three real physical pilot joints from Robot A without invented IDs;
  record roles, axes, limits, and selection reasons in
  `results/try5a4/pilot_selection.json`.
- [x] Upgrade every interface-family knowledge entry with motion semantics,
  parent/child rigid structure, clearances, forbidden configurations, CAD logic,
  and verification rules in `try5/knowledge/robot_interfaces/families.json`.
- [x] Materialize motion-aware contracts and rigid-group specifications for every
  pilot in `results/try5a4/contracts/` and `rigid_group_specs.json`.
- [x] Prove strict own-body parent and child attachment, separate cross-joint
  rigid groups, forbidden-fusion absence, axis/center correctness, and mechanical
  provenance in `attachment_audit.json` and `hard_gate_audit.json`.
- [x] Build M0/M1/M2 CAD IR and execute it with the existing FreeCAD runtime;
  preserve CAD files under ignored `artifacts/try5a4/` and hashes/provenance in
  `cad_artifact_manifest.json`.
- [x] Sample at least q-min/25%/50%/75%/q-max (the frozen run uses nine poses),
  compute exact B-Rep narrow-phase collision and clearance, and preserve all
  cases/failures in `collision_table.csv` and `joint_range_metrics.json`.
- [x] Generate motion-clearance and swept-occupancy evidence from generated CAD,
  URDF motion, contracts, and rigid groups only in
  `motion_clearance_specs.json` and `swept_volume_artifacts.json`.
- [x] Generate per-pose playback, collision overlays, contact sheets, joint-state
  tables, and M2 GIFs; index them in `motion_playback_manifest.json`.
- [x] Apply at most two motion-driven repairs per M2 pilot and record scope,
  before/after evidence, acceptance, regression, and R4 usage in
  `repair_contracts.json`.
- [x] Prove the joint-limit, knowledge-family, and clearance counterfactuals in
  `dataflow_audit.json`; prove prohibited GT inputs are absent from generation in
  `leakage_audit.json`.
- [x] Report interface/attachment, joint geometry, motion, representation, repair,
  resource, and auxiliary frozen geometry metrics in `summary.json` and
  `report.md`.
- [x] Re-read the protocol and pass the completion audit in `validation.json`.

Determinism rerun: `summary.json` and `collision_table.csv` reproduced byte-for-byte;
see `results/try5a4/determinism_audit.json`.
