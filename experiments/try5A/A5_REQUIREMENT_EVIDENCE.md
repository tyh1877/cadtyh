# Try-5A.5 requirement-to-evidence checklist

Frozen before the clean whole-robot run. The generator may read only the listed
formal inputs and generic code/knowledge; historical Robot A design-state paths are
forbidden until the final evaluator stage.

- [x] Freeze protocol, six input-image hashes, engineering text, sanitized URDF,
  generic KB, code, seed, sampler, backend, and evaluator in
  `results/try5a5/manifest.json`.
- [x] Reparse the sanitized URDF and regenerate the skeleton, physical/virtual
  classification, mimic mapping, frames, limits, FK tree, and EE frame from zero.
- [x] Regenerate the Robot Plan, all joint-family selections, all motion-aware
  contracts, and all LinkCoarseSpecs from formal inputs; prove forward consumption.
- [x] Generate every physical link interface-first as editable FreeCAD CAD, export
  valid FCStd/STEP/STL, reopen/recompute, use zero fallback, and generate no L11
  virtual solid.
- [x] Pass kinematic, attachment/BICR, forbidden-fusion, fixed/prismatic/mimic,
  constrained-DOF, per-joint JR3, and mechanical-meaningfulness gates.
- [x] Evaluate 128 fixed-seed Sobol coupled configurations using full-link URDF FK,
  AABB broad phase, exact B-Rep narrow phase, invariant checks, and full collision
  taxonomy; preserve every configuration and error.
- [x] Build a Global Collision Graph with edge frequency, poses, mean/max volume,
  region, adjacency, and motion-induced fields; prove the repair scheduler consumes
  it.
- [x] Run at most three selective whole-robot repair rounds through the existing
  R0–R4 arbiter, upstream design-state updates, partial CAD rebuild, progressive
  freezing, regression protection, and rollback accounting.
- [x] Reach BICR=100%, floating/fusion/virtual/meaningless counts=0, all physical
  links valid, all moving joints full-range JR3 where achievable, GCFR>=90%
  (target >=95%), and no morphology collapse.
- [x] Generate actual FreeCAD whole-robot round-0/final CAD plus a multi-joint FK
  motion sequence with renders, configuration table, exact collision status, and
  GIF/contact sheet.
- [x] Run final GT-only geometry evaluation and report whole/per-link IoU,
  silhouettes, nChamfer, nHD95, bbox and reach errors without using GT for repair.
- [x] Pass joint-limit, interface-family, and local-body-constraint counterfactuals,
  leakage audit, deterministic rerun, and the final 50-question report audit.
