# Try-5A Phase 5 report — A1 Robot-Level Planning

Status: A1 is complete. Execution stops before A2.

## Execution and dataflow

A1 consumes the frozen Robot Assembly Plan for all 12 links. Each LinkCoarseSpec
and parameter manifest records the same plan hash and the exact role, envelope,
principal direction, body family and interface-region fields used. A mutation of
the planned envelope changes the planning fingerprint. The A1 generator contains
no Joint Interface Graph, shared-port or shared-envelope access.

All 12 links build successfully with 36 native CAD operations and zero fallback.
FCStd/STEP/STL, four renders, reopen/recompute and ±5% edit checks all pass. The
whole robot is assembled at the same canonical URDF transforms with zero visual
placement adjustment.

## Corrected assembly visualization

The plane-filled A0/A1 previews were caused by the assembler collecting both STEP
hierarchy compounds and child shapes. The final assembler copies only CAD-IR
`final_objects` from each link FCStd and uses an explicit homogeneous transform.
The original link geometry and all analytical A0 metrics were unchanged. Failed
assembly previews are archived and excluded.

## A0 → A1 comparison

| Metric | A0 | A1 | Direction |
| --- | ---: | ---: | --- |
| Link build success | 12/12 | 12/12 | unchanged |
| Connected Joint Rate | 81.8% | 81.8% | unchanged |
| Floating Link Rate | 16.7% | 16.7% | unchanged |
| Connected components | 3 | 3 | unchanged |
| Mean interface gap | 2.82 mm | 3.47 mm | worse |
| Mean radius mismatch | 3.73 mm | 5.02 mm | worse |
| Excessive axial penetrations | 7 | 5 | improved |
| Nonadjacent canonical AABB overlaps | 4 | 4 | unchanged |
| Mean four-view silhouette IoU | 0.1491 | 0.1505 | slight improvement |
| Axis/offset/center error | 0 | 0 | unchanged |
| Conservative sweep collision-free rate | 0% | 0% | unchanged |

Robot-Level Planning visibly improves role consistency: A1 expresses the upper
arm as paired side plates, the forearm as a central web, the carriage as a fork
body and the fingers as tapered bodies. The overall silhouette improves only
slightly, and top-view IoU decreases. The large base and blocky wrist remain
poorly proportioned.

A1 does not improve interface connectivity. J08/J09 remain disconnected and L09/
L10 remain floating; their gaps increase to 19.06 mm. Port radii are still chosen
independently from each link's own planned envelope, so coordinated body scale
does not imply coordinated interfaces. This cleanly preserves room for A2.

## Interpretation

A1 provides limited evidence that Robot-Level Planning improves coarse role and
morphology consistency, but the gain is small and does not reach interface or
kinematic-geometry correctness. The clearest positive result is fewer excessive
penetrations; the clearest negative result is larger independent port mismatch.

No A1 repair was performed. A2 remains absent. The next authorized phase after
review is A2 Interface-First Shared Joint Design.
