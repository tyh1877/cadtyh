# RobotCAD Try-5A final report

## Outcome

Try-5A completed Phase 1–10 for one development robot and stops before Try-5B.
The implementation objective is complete: L0 skeleton, L1 Robot Plan, L2 shared
interfaces, A0/A1/A2 links, canonical assemblies, FK/workspace/sweep and unified
evaluation all exist and pass reproducibility audits. The method hypothesis is
partially supported: A2 solves the measured interface/connection failures without
materially changing whole-robot geometry, while collision-aware body design and
coarse appearance remain unsolved.

## A0/A1/A2 main comparison

| Metric | A0 independent | A1 Robot Plan | A2 interface-first |
| --- | ---: | ---: | ---: |
| Successful Link CAD | 12/12 | 12/12 | 12/12 |
| Whole assembly/reopen | PASS | PASS | PASS |
| Connected Joint Rate | 81.8% | 81.8% | 100% |
| Floating Link Rate | 16.7% | 16.7% | 0% |
| Assembly components | 3 | 3 | 1 |
| Mean interface gap | 2.82 mm | 3.47 mm | 0 mm |
| Mean nominal-radius mismatch | 3.73 mm | 5.02 mm | 0 mm |
| Excessive axial penetration | 7 | 5 | 0 |
| Axis angular/offset error | 0° / 0 mm | 0° / 0 mm | 0° / 0 mm |
| Interface-center error | 0 mm | 0 mm | 0 mm |
| Nonadjacent canonical AABB overlaps | 4 | 4 | 4 |
| Collision-free conservative sweep | 0% | 0% | 0% |

A2 consumes all 11 contracts twice, once from each owning link, for 22 verified
parent/child consumptions. Nominal radii and frames match on both sides. Contract
mutation tests prove radius, origin and prismatic limits change generated port
geometry. J08/J09 parent guides consume travel limits, eliminating the two floating
finger links found in A0/A1.

## Coarse geometry

Nine nonvirtual links have evaluator-only URDF visual meshes. Their mean metrics:

| Condition | Link IoU ↑ | Link nChamfer ↓ | Link nHD95 ↓ | Link silhouette ↑ |
| --- | ---: | ---: | ---: | ---: |
| A0 | 0.2434 | 0.07383 | 0.2366 | 0.4282 |
| A1 | 0.2172 | 0.08007 | 0.2555 | 0.4100 |
| A2 | 0.2135 | 0.08008 | 0.2545 | 0.4074 |

Whole-robot IoU is 0.4577 / 0.4479 / 0.4483 for A0/A1/A2; whole silhouette IoU
is 0.6509 / 0.6504 / 0.6486. A2 therefore does not materially degrade morphology
relative to A1, but neither Robot Plan nor interface-first construction improves
coarse fidelity. The hardest A2 bodies are L02 upper arm, L07 gripper crossbar and
L01 shoulder housing.

A2's isometric render looks less like the reference because the newly realized
parent interface housings occupy and occlude more of the already coarse bodies;
the wrist/finger branch also overlaps in projection. A visibility audit confirms
that all 12 links and every A1 BODY operation remain present in A2. Per-link A2
volume is 78.5%–100.5% of A1 after annular cuts/interface replacement, so this is
not a missing-link failure. It is an appearance, occlusion and coarse-envelope
failure caused by optimizing interfaces without replanning body surfaces.

## Kinematics and simulation

All conditions use the same sanitized URDF authority. Canonical FK is exact within
the recorded numerical tolerance. Across 256 Halton joint samples, EE position and
orientation error are zero and workspace coverage against the same URDF reference
is 1.0; workspace bbox is approximately 0.563 × 0.589 × 0.565 m. These identical
numbers verify kinematic consistency but do not distinguish the three conditions.

Twelve single-joint sweep samples traverse limits successfully. None is collision-
free under conservative transformed-STL AABB testing. Persistent overlaps occur in
the wrist/gripper cluster, so exact collision-safe geometry is not established.

## Answers to the required questions

1. **Robot A:** R01, Interbotix PincherX-100.
2. **URDF size:** 12 links, 11 joints; 4 arm revolute DOF plus gripper auxiliaries.
3. **L0:** parsed and validated; five FK samples, rigid transforms and mimic relation pass.
4. **Link success:** A0/A1/A2 are all 12/12.
5. **Whole assembly:** all three assemble, export, reopen and recompute.
6. **Connected rate:** 81.8% → 81.8% → 100%.
7. **Floating rate:** 16.7% → 16.7% → 0%.
8. **Mean gap:** 2.82 → 3.47 → 0 mm.
9. **Axis error:** 0° in all conditions.
10. **Origin/center error:** 0 mm in all conditions.
11. **Coaxiality:** axis offset is 0 mm throughout; A2 additionally matches nominal port size.
12. **Adjacent penetration:** excessive cases 7 → 5 → 0 using complementary A2 geometry.
13. **Canonical pose:** reconstructed from URDF and numerically valid.
14. **Sampled FK:** stable for all 256 workspace samples.
15. **EE pose error:** zero because all conditions preserve the authoritative skeleton.
16. **Workspace:** identical 1.0 coverage; geometry did not alter kinematic reach.
17. **Joint sweep collision:** all 12 conservative AABB samples contain nonadjacent overlap.
18. **A1 value:** weakly supported for role consistency; quantitative morphology does not improve.
19. **A2 value:** strongly supported for connectivity, floating links, gap, size matching and penetration.
20. **Reasonable individual links but failed assembly:** yes, A0/A1 fingers are valid yet float.
21. **Interfaces connect but body geometry is poor:** yes, A2 reaches one connected component while coarse fidelity remains low.
22. **Hardest joints:** J08/J09 slider engagement and the J05–J07 wrist/gripper branch.
23. **Hardest bodies:** L02, L07 and L01.
24. **FreeCAD:** 36/36 link builds across conditions succeed; it is not the main bottleneck.
25. **Current bottleneck:** coarse geometry and collision-aware body planning, after interface realization is corrected.
26. **Try-5B:** conditionally recommended only after adding a coarse-body collision gate; semantic detailing should not begin on intersecting bodies.

## Objective completion judgment

All requested Try-5A experimental stages and deliverables are complete. The core
architecture claim is supported for interface-first assembly: A2 creates a single
connected skeleton with aligned, shared interfaces. The broader desired outcome—a
collision-safe, morphologically convincing coarse robot—is not fully achieved.
Try-5A should be reported as **procedurally complete, method success partial**.
