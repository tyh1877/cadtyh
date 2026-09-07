# Try-5A Phase 1–3 requirement-to-evidence checklist

- [x] Robot A is one existing, typical, moderately simple arm with curved housings; no Robot B/transfer execution.
- [x] Formal inputs contain only multi-view images, engineering text and sanitized URDF without visual/collision/inertial/mesh data.
- [x] L0 deterministically parses every link/joint, parent-child graph, type, origin, axis, limits and mimic relation.
- [x] L0 computes canonical link/joint world transforms, relative transforms, world axes and FK chain.
- [x] FK/frame smoke tests cover tree connectivity, rigid transforms, relative reconstruction and sampled limits.
- [x] Robot Kinematics Skill documents deterministic transforms, FK and sampling.
- [x] L1 Robot Assembly Plan exists before any link CAD and covers every URDF link with role, envelope, direction, interfaces, family, neighbors and constraints.
- [x] L1 explicitly records consumed L0 values and upstream hash; visual decisions remain coarse.
- [x] L2 contains exactly one shared Interface Contract per URDF joint with one authoritative shared frame and two ports.
- [x] Each Interface Contract consumes both L0 joint fields and L1 parent/child plan fields with trace hashes.
- [x] Dataflow audit proves L0 → L1 → L2 coverage and mutation sensitivity; no “declared but unused” layer remains.
- [x] Leakage audit proves generator-facing inputs contain no GT STEP/B-Rep, meshes, per-link geometry, feature tree or GT dimensions.
- [x] Method/input hashes, smoke outputs, reports and task-only local Git commit are complete.
- [x] Stop after Phase 3; A0/A1/A2 and all CAD/assembly generation remain absent.
