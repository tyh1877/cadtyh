# Operation-plan Pilot Protocol

Date: 2026-08-31

## Question

Can the upstream LLM produce a richer editable CAD construction plan for robot
links when asked for an explicit operation sequence instead of a primitive list?

## Scope

This is a small diagnostic pilot, not a replacement for Try-3 formal results.
It uses existing non-GT Try-1 image/text packets, sanitized Try-2 URDF, and
Try-3 visual evidence. GT meshes are not provided to the model.

Frozen pilot cases:

- `dev_arm-dcc2b0ce1e`: links `L2`, `L3`, `L4`
- `dev_arm-ab15a75247`: links `L0`, `L2`, `L4`

## Required output format

For each selected link, the model must return a JSON object with:

- `case_id`
- `link_id`
- `mechanical_intent`
- `interface_constraints`
- `operations`

Each operation must be one of:

- `CreateSketchProfile`
- `Extrude`
- `Loft`
- `Revolve`
- `Sweep`
- `Shell`
- `OffsetFace`
- `BooleanUnion`
- `BooleanCut`
- `ApplyFillet`
- `ApplyChamfer`
- `CreateHole`
- `CircularPattern`
- `LinearPattern`
- `Mirror`

The pilot evaluates the operation plan as an upstream-planning artifact. Fusion
execution is optional follow-up and is not required for this first diagnostic.

## Pass criteria

The pilot passes if:

1. At least 5/6 selected links produce schema-valid plans.
2. At least 4/6 selected links contain 5 or more CAD operations.
3. At least 3/6 selected links include at least two non-primitive operations
   from `Loft`, `Revolve`, `Sweep`, `Shell`, `OffsetFace`, `BooleanCut`,
   `CircularPattern`, `LinearPattern`, or `Mirror`.
4. At least 4/6 selected links preserve explicit interface constraints using
   existing URDF link/joint identifiers only.
5. No plan uses GT mesh, original CAD, product name, or hidden labels.

## Interpretation

Passing this pilot means the next Try-3 revision should regenerate upstream
operation plans and then extend the Fusion backend to execute the subset needed
by those plans. Failing means the paper should not rely on an agentic CAD
operation-planning claim yet.
