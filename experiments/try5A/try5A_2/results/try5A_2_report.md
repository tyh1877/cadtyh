# Try-5A.2 final report

## Outcome

Try-5A.2 completed its allowed D0 physicalization and D1 deterministic repair loop. D2 was correctly not run because D1 did not achieve a positive sweep-free pose rate. The experiment is **mechanically repaired but collision-repair unsuccessful**; Try-5B remains blocked.

| Condition | BICR | Physical floating | True collision events | Intersection volume mm³ | Sweep-free rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| D0_physicalized | 100% | 0% | 174 | 484327.7 | 0% |
| D1 final | 100% | 0% | 172 | 410133.0 | 0% |

D1 accepted Round 1 (L00 middle body) and Round 3 (L03 middle body). Round 2 (L01 middle body) lowered its target collision but reduced BICR to 95%, so it was rolled back. A scheduler state-write fault produced one redundant L01 candidate; it was explicitly discarded, then Round 3 was replanned to L03. No silent retry occurred.

D1 reduces events by 2 and volume by 74194.7 mm³, but no sweep pose becomes collision-free. Whole-robot IoU decreases from 0.450 to 0.328; this local shrinking also regresses morphology.

## Required conclusions

- Connected logical frames remain frozen at 100%; BICR is 100%; physical floating is 0%; virtual L11 geometry is 0.
- L00–L01 and L03–L04 improve locally, but L00–L01 and wrist/gripper space remain the dominant unresolved collision system.
- Progressive freezing works for accepted L00/L03 body regions and all interface regions. The L01 body region remains unresolved after its BICR rollback.
- Region-level selective rebuilding is safer than Try5-A.1 global scaling for interface preservation, but it is not sufficiently effective for articulated collision clearance.
- FreeCAD remains stable: the bottleneck is the coarse body representation and spatial corridor parameterization, not CAD execution.
- D2 has no VLM suggestion, no morphology candidate and no rollback because its mechanical entry condition was not met.
- Try-5B entry conditions fail due to sweep-free rate 0% and substantial collision residual.
