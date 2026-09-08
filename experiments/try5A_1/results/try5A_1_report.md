# Try-5A.1 final report — Collision-Aware Coarse Body Planning

## Result

Try-5A.1 completed C0/C1/C2 on the frozen Try-5A Robot A only. The experiment is a **partial success**: collision-aware body constraints were consumed by FreeCAD and reduced exact collisions while preserving every interface, but the single C2 visual-morphology replan did not improve morphology enough to offset its collision-volume rebound. It therefore does **not** meet the entry condition for Try-5B.

## C0 → C1 → C2

| Condition | Connected joints | Floating links | True collision events | Exact intersection volume (mm³) | Sweep-free pose rate | Whole-robot IoU | Whole silhouette IoU |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| C0 frozen A2 | 100% | 0 | 181 | 554812.5 | 0% | 0.508 | 0.696 |
| C1 collision-aware | 100% | 0 | 130 | 313085.5 | 0% | 0.417 | 0.577 |
| C2 + morphology | 100% | 0 | 132 | 436273.8 | 0% | 0.418 | 0.577 |

C1 reduced exact collision events by 28.2% and total intersection volume by 43.6%. It removed four collision events in the canonical pose and 47 in the sampled sweeps. C1 still has no collision-free sampled sweep pose, so it is a reduction rather than a clearance solution.

C2 retained interface metrics and reduced neither pair count nor sweep risk: it has two more exact collision events than C1 and 39.3% more intersection volume. Its whole-robot IoU rises from 0.417 to 0.418, but remains below C0 (0.508); this is insufficient visual improvement.

## Interface preservation and dataflow

All conditions keep Connected Joint Rate at 100%, Floating Link Rate at 0, nominal radius mismatch at 0 mm, mean port gap at 0 mm, and axis/origin error at 0. The audit compared all 12 InterfaceRefs and all interface-bearing CAD operations with C0: both are byte/structure identical. C1/C2 changed only `BODY` operations for scheduled collision sources L00–L10; L11 remained frozen. All 24 regenerated links passed strict FreeCAD execution with zero fallback. The structured repair contracts and `collision_aware_link_spec.json` equivalents in `body_specs/` record the C0 collision sources and the exact body scales consumed by the CAD IR.

## Broad phase versus narrow phase

C0 has 292 AABB candidates, of which 38.0% have no material B-Rep intersection; C1/C2 are 46.9% and 46.1%. AABB is therefore a useful filter but cannot be a collision conclusion. Every broad candidate was evaluated with exact boolean common; narrow-phase error count is zero for all three conditions.

## Remaining collision sources

C1's dominant residual is adjacent L00–L01 (259,313 mm³ across 13 poses), followed by L04–L05, L04–L07, L07–L08, L04–L06, L03–L04 and L02–L03. They include both adjacent unintended overlap outside the port and motion-induced nonadjacent overlap in the wrist/gripper cluster. C2's dominant L00–L01 volume grows to 379,313 mm³ after visual envelope recovery, which is the principal reason it fails the collision-preservation objective.

## Interpretation and next step

FreeCAD is not the bottleneck: it generated, reopened and exported all planned models without a fallback. The bottleneck is the parameterization of free space around coupled interfaces and the coarse morphology planner: simple global cross-section scaling can reduce collision, but cannot create a collision-free sweep while retaining the reference silhouette. A later round should use link-local, pose-indexed exclusion volumes and parameterized offsets/section placement around L00–L01 and the L04–L08 wrist cluster. Do not enter Try-5B yet, because the required collision-free sweep improvement has not been achieved.
