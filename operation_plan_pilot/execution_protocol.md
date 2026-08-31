# Operation-plan Fusion Execution Pilot Protocol

Date: 2026-08-31

## Question

Can the operation plans produced by `operation_plan_pilot` be compiled into
Fusion-executable editable CAD models that the user can inspect?

## Scope

This execution pilot uses the frozen six operation plans from
`operation_plan_pilot/runs/*/*/operation_plan.json`. It does not call the LLM
again and does not alter the Try-3 formal denominator.

## Compiler v1 limitation

The plans contain both currently executable operations and not-yet-native
operations. Compiler v1 preserves the original operation as `source_op`, but
lowers not-yet-native operations into the currently verified Fusion operation
set:

- `Revolve` -> `Loft` or cylindrical `Extrude` approximation
- `Sweep` -> elongated `Extrude` approximation
- `Shell` -> `BooleanCut` recess approximation
- `BooleanUnion` -> additional joined/new body primitive approximation

This is intentionally recorded as a pilot limitation. A pass here proves that
the richer operation plan can drive visible editable Fusion geometry, not that
every planned operation already maps one-to-one to a native Fusion feature.

## Pass criteria

The execution pilot passes if:

1. 6/6 planned links are included in `fusion_jobs.json`.
2. At least 5/6 links execute successfully in Fusion and export F3D/STEP/STL.
3. Every successful link records at least 5 executed CAD calls.
4. The result contains visible modifier operations beyond base extrusions:
   holes/cuts/patterns/fillets/chamfers/lofts.

## Next step if pass

Implement native Fusion support for the high-value source operations observed
in the pilot: `Revolve`, `Shell`, `BooleanUnion`, and then rerun the same frozen
six links without lowering those operations.
