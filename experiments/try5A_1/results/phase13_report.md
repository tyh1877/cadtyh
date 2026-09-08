# Try-5A.1 Phase 1–3 report — C0 collision baseline

Status: Phase 1–3 are complete. C1/C2 have not started.

## Frozen C0

C0 directly references Try-5A A2. It does not regenerate Links, interfaces or
assembly placement. All 11 Shared Interface Contracts, A2 CAD IRs and canonical
URDF transforms are hash-frozen. Interface preservation remains 100% connected
joints, 0 floating links, 0 gap, 0 nominal-radius mismatch and 0 analytical
interface penetration.

## Broad vs exact collision result

| Scope | Pair evaluations | AABB candidates | True collision events | Narrow errors |
| --- | ---: | ---: | ---: | ---: |
| Canonical pose | 66 | 19 | 13 | 0 |
| 12 sweep poses | 792 | 273 | 168 | 0 |

Canonical broad candidates contain 4 nonadjacent AABB false positives and 2
expected interface-clearance cases. Thus 6/19 broad candidates have no material
intersection, while 13 are true collisions. In sweeps, 81 broad candidates are
nonadjacent false positives and 24 are expected interface cases; narrow phase is
therefore necessary and is working.

Canonical true pairs: 9 adjacent unintended and 4 nonadjacent. The largest sources
are L00–L01, L03–L04, L05–L06, L05–L07, L06–L07, L04–L06 and L04–L07. The wrist/
gripper cluster creates repeated motion-induced collisions; body envelopes around
the base/shoulder and forearm/wrist also create material overlap.

## Interpretation

The original AABB-only result of four nonadjacent overlaps understated collision
risk. It did identify the wrist/gripper cluster, but missed multiple adjacent
unintended intersections. C0 interfaces are geometrically consistent in frame,
radius and gap terms, while coarse body solids still penetrate them or neighboring
bodies. This is the intended Try-5A.1 starting condition.

The evaluator is adequate for C1: it separates broad candidate, exact true
intersection, expected interface clearance and narrow errors; it records per-pair
volume and clearance where available. Its remaining limitation is that sweep uses
single-joint samples and collision clearance for broad-clear pairs is AABB-based.

No collision-aware body spec, exclusion region, C1 body replan or C2 visual
morphology replan was generated. The next authorized phase after review is Phase 4.
