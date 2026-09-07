# RobotCAD Try-5A Phase 1–3 report

Status: Phase 1–3 are complete and execution stops before A0/A1/A2 or any CAD.

## Robot A and formal inputs

Robot A is R01, the Interbotix PincherX-100: a compact four-revolute-joint arm
with round joint housings, upper arm, forearm, wrist and opposed fingers. Its
geometry is typical and moderately simple; R02 is too complex for the first
development robot and R03 remains the earlier frozen transfer object.

Formal visual input contains six global views. The sanitized URDF contains 12
stable link IDs and 11 stable joint IDs. It contains no visual, collision,
inertial, geometry, mesh, material or transmission element. Engineering text is
coarse and contains no GT CAD dimensions.

## L0 Kinematic Skeleton

The tree root is L00. It contains 4 arm revolute joints, one continuous gripper
actuator, two opposed prismatic fingers (J09 mimics J08 with multiplier -1), and
four fixed joints. Canonical values are zero except the finger pair at +0.026 m
and -0.026 m, the midpoints of their allowed intervals.

Canonical tool-center position is approximately `[0.248575, 0, 0.19305]` m. Five
deterministic limit-fraction FK samples are finite. Maximum rotation
orthonormality error is 0 and maximum parent/joint relative reconstruction error
is `1.04e-17`. URDF remains the unmodified frame authority.

## L1 Robot Assembly Plan

All 12 links have a coarse role and LinkCoarseSpec. The main serial chain is:

`base housing → shoulder housing → upper-arm dual side plate → forearm central web → wrist/gripper block`

The end branch then contains an interface spacer, actuator prop, crossbar, finger
carriage, opposed prismatic fingers and tool-center marker. Every link record
copies its parent/child joint records and canonical transform from L0 and records
the L0 hash. Plans intentionally omit small holes, detailed gripper internals and
cosmetic geometry.

## L2 shared Joint Interface Graph

Exactly one contract exists for each of 11 joints. Families are limited to:

- `coaxial_rotary_interface`
- `fork_pin_interface`
- `planar_mount_interface`
- `linear_slider_interface`

Every contract owns one shared URDF frame and supplies matching parent/child ports,
protected regions, required relations, envelope, target gap and clearance rule.
Port radius/depth are derived from both adjacent L1 envelopes; origin, rotation,
axis and limits are copied from L0.

The most ambiguous interfaces are the visually underspecified J02 fork/pin, the
short J05 actuator spacer, co-located fixed gripper branches J06/J07, opposed
prismatic sliders J08/J09 and the interface-only J10 tool marker. These are
appearance ambiguities only; their kinematic frames are authoritative.

## Dataflow and leakage result

The consumption ledger has 34 verified edges: 12 L0→L1, 11 L0→L2 and 11 L1→L2.
Every copied field and upstream hash matches. Counterfactual checks show that a
1 mm J01-origin mutation changes the contract-frame hash, while scaling both
adjacent envelopes changes the derived interface radius from 16 mm to 24 mm.
Thus Robot Plan and Interface Contract are computational inputs, not unused files.

Leakage audit passes: generator-facing inputs contain no STEP/B-Rep, URDF mesh,
per-link GT geometry, GT interface, feature tree or CAD dimension. Colored views
remain visual evidence only.

No link CAD, assembled robot, A0/A1/A2 condition, simulation or Robot B/transfer
output exists. The next authorized phase after user review is Phase 4: A0.
