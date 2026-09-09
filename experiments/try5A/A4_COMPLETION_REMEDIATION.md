# Try-5A.4 completion remediation: requirement-to-evidence checklist

This checklist is frozen before the completion rerun. The seven gaps come from
`results/try5a4/protocol_gap_audit.json`; no numeric result may close a gate unless
the named direct evidence exists.

- [x] **Frozen M0 replay:** load the existing A2/K1 FreeCAD link documents for
  J01/J02/J03, preserve their file/IR hashes, and prove the M0 evaluator consumed
  those shapes in `results/try5a4_completion/m0_replay_audit.json`.
- [x] **True URDF FK:** compute every pose with canonical `kinematics.py`, pass all
  physical-link world transforms to FreeCAD, and verify joint axes, centers,
  relative transforms, descendant motion, and L11 EE pose in
  `fk_motion_audit.json`.
- [x] **Mechanically constrained DOF:** realize family-specific parent pin/bearing
  and child bore/rotor geometry; demonstrate intended-axis motion clearance and
  rejection of all five forbidden infinitesimal DOFs in
  `mechanical_dof_audit.json`.
- [x] **Causal swept design:** generate child/interface swept shapes before M2,
  persist their hashes, feed them into the body-region planner, and prove joint
  limit and clearance counterfactuals change downstream CAD in
  `swept_design_dataflow_audit.json`.
- [x] **Repair arbiter:** call the existing `repair_scope_arbiter.arbitrate`, record
  its evidence/decision, cap each pilot at two repairs, and preserve acceptance or
  rollback in `repair_arbiter_audit.json`.
- [x] **CAD playback:** render actual transformed FreeCAD B-Rep geometry for all
  frozen poses, including start/mid/end, overlays, contact sheets, and GIFs; index
  them in `cad_playback_manifest.json`.
- [x] **Collision/metric coverage:** use AABB only as broad phase and exact B-Rep as
  the formal judge; classify expected contact, adjacent unintended,
  nonadjacent, and motion-induced events across all physical links, and report
  per-link/whole-robot auxiliary geometry metrics.
- [x] **Counterfactuals and leakage:** joint-limit, family, and clearance changes
  must alter their intended downstream artifacts without generator access to GT.
- [x] **Completion gate:** preserve every failed case, re-read the protocol, answer
  questions 1–35 from direct evidence, pass a deterministic rerun, then set
  `validation.json` and `protocol_gap_audit.json` to PASS/COMPLETE.
