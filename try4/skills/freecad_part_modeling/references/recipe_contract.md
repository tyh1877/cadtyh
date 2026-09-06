# Reusable Phase-4 recipe contract

Recipes are shared parameterized CAD strategies, not case-specific generators.
The Agent chooses a recipe and all dimensions from visual/semantic evidence.
Every recipe key maps to explicit expected-feature IDs.

- `base_pedestal`: base plate, tapered pedestal, top seating/recess.
- `joint_housing`: stepped housing/support, transverse pivot cover, optional inset.
- `open_frame`: separated side plates, cross carrier, optional slots, fork notches and pivot.
- `dual_support`: mounting disk, two uprights with protected central gap and pivot bosses.
- `offset_housing`: tapered/offset body, side channel or opening, joint housing and optional hole pattern.
- `wrist_carrier`: central carrier, separated bracket arms/opening, roll flange and optional slots.
- `gripper`: separate opposed jaws, transverse carriage/rail and proximal attachment bracket.

Compiler code may dispatch only on these recipe names. It may not inspect
`robot_id`, `part_id`, source labels, GT geometry or evaluation results to choose
geometry. Unsupported recipe content must be explicit in the Feature Graph.
