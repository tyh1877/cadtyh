# Try-5A Phase 4 report — A0 independent-link baseline

Status: A0 is complete. Execution stops before A1/A2.

## Execution

All 12 URDF links independently produced valid FCStd, STEP and STL files, four
renders, LinkCoarseSpec, InterfaceRefs, CAD IR, execution log and parameter
manifest. All reopen/recompute and ±5% edit checks pass; 34 CAD operations execute
with zero silent fallback. The whole robot also exports as FCStd/STEP/STL with 12
link objects placed by canonical URDF transforms and zero visual adjustment.

The A0 generator consumed only images, engineering text, sanitized URDF and the
current link's parent/child joint records. Static and artifact audits find no Robot
Assembly Plan, Joint Interface Graph, shared port or shared envelope consumption.

## Assembly and interface result

| Metric | A0 result |
| --- | ---: |
| Successful links | 12/12 |
| Whole assembly export | PASS |
| Connected Joint Rate | 9/11 = 81.8% |
| Floating Link Rate | 2/12 = 16.7% |
| Assembly connected components | 3 |
| Mean interface gap | 2.82 mm |
| Mean port-radius mismatch | 3.73 mm |
| Excessive axial penetrations | 7/11 |
| Nonadjacent canonical AABB overlaps | 4 pairs |
| Joint-axis angular error | 0° max |
| Joint-axis offset | 0 mm max |
| Interface-center error | 0 mm max |
| Joint sweep samples | 12 |
| Collision-free conservative AABB sweeps | 0/12 |

The zero frame/axis/center errors confirm that local URDF context is consumed
correctly. Independent interface sizing nevertheless produces mismatched radii,
large overlaps and gaps. J08/J09 each have a 15.5 mm analytical interface gap;
their L09/L10 finger links float, creating two extra connected components.

The seven over-penetrated interfaces are mainly the base/arm rotary chain and
fixed end branches, where both links independently place full-depth ports at the
same frame. Canonical nonadjacent AABB overlaps concentrate in the wrist/gripper
cluster: L04–L06, L04–L07, L06–L07 and L06–L08. AABB sweep collision rate is a
conservative diagnostic rather than exact B-Rep collision volume.

## Whole-robot morphology

The generated assembly bbox is approximately 339 × 120 × 234 mm and root-to-tool
reach is 314.7 mm. The contact sheet shows a recognizable serial direction but
poor morphology: oversized rectangular bodies, inconsistent arm thickness,
cluttered wrist/gripper branches and large overlapping interface plates. Several
individual links are valid on their own while the assembled structure is not a
clean mechanical skeleton.

## A0 diagnosis and stop decision

A0 is neither trivially perfect nor an evaluator failure. It demonstrates the
intended baseline phenomenon:

1. Independent link CAD generation itself succeeds.
2. URDF canonical placement and joint axes remain correct.
3. Without shared interface contracts, finger links float, port sizes disagree,
   and many interfaces over-penetrate.
4. Without Robot-Level Planning, body proportions and wrist/gripper morphology
   are poorly coordinated.

The most representative assembly problems are J08/J09 finger gaps, J01/J03/J04
radius mismatches, and the overlapping J05–J07 wrist/gripper branch. No A0 repair
was performed. The next authorized experiment after review is A1 only.
