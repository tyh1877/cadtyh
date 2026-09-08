# Try-5A.1 Phase 1–3 protocol

C0 is the frozen Try-5A A2 result for R01. The authoritative frozen inputs are the
sanitized URDF, Robot Plan, Joint Interface Graph, all eleven Shared Interface
Contracts, A2 LinkCoarseSpecs/InterfaceRefs/CAD IR and link FCStd outputs.

Collision analysis is evaluator-only. Broad phase uses transformed AABBs. Every
broad candidate receives narrow B-Rep common-volume evaluation. A B-Rep error is
recorded as `NARROW_ERROR`; it cannot be treated as zero volume.

Canonical adjacent pairs with negligible B-Rep common volume are `EXPECTED_INTERFACE`
only when they are URDF neighbors. Adjacent pairs with material intersection are
`ADJACENT_UNINTENDED`; nonadjacent pairs with material intersection are
`NONADJACENT_TRUE`. Sweep-only true intersections are `MOTION_INDUCED_TRUE`.

The output of this stage is a collision baseline and not a body replan. No C1/C2
artifact may be generated before user confirmation.
