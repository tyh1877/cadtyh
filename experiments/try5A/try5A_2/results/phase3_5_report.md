# Try-5A.2 Phase 3.5 — Physical Interface Attachment Closure

D0 remains frozen. D0_physicalized modifies only body-to-carrier attachment geometry and excludes virtual L11 from all physical artifacts.

## Attachment closure

There are 20 physical carriers: 18 overlapping separate solids and 2 positive gaps. All 18 were repaired through native Boolean Fuse. L01/IF_J01 and L08/IF_J07 were closed with local, 8 mm-wide neck connectors in their measured nearest-point corridors, with 0.5 mm volumetric overlap at each end. No interface frame, radius, depth, port or mating geometry was changed.

BICR is 100%; all 11 physical links have every required carrier attached, yielding Physical Floating Link Rate 0%. L11 is `virtual_frame`, is absent from STEP/STL/render/collision, and Spurious Virtual Geometry Count is 0. All 11 generated FCStd files pass execution, recompute/reopen/export and use zero silent fallback.

## Exact physicalized collision baseline

Physicalization changes the geometry occupancy as expected. Exact collision events are 174 versus frozen D0's 130 (+44); intersection volume is 484327.7 mm³ versus 313085.5 mm³; sweep-free pose rate remains 0%. The largest new event sources are recorded in per_pair_collision_physicalized.csv, notably the now-physical L05-L06 and L08-finger carrier paths. This is a baseline only: Phase 3.5 intentionally did not attempt collision repair.

## Dataflow and gate

The counterfactual changing L01/IF_J01 connector width by 2 mm changed the executed CAD bounding box, proving attachment classification → contract → CAD IR → FreeCAD geometry. The Attachment Hard Gate passes. Phase 4–8 may begin after review; no region-level collision representation, pose-aware repair, D1, or morphology repair was started.
