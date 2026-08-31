# Try-3 Basic CAD Operation Skill Repair Status

Date: 2026-08-31

Status: explicit basic-operation implementation validated. Fusion smoke passed
and formal Fusion batch rebuilt 8/10 jobs; the remaining two failures are
upstream generation failures retained in the denominator.

## Rationale

Visual inspection of the repaired V1/V2 Fusion outputs showed that the cube
collapse was fixed, but the Skill layer still mixed formal executable
operations with middle-layer structure names. That made it impossible to prove
that a SkillCall name matched the native Fusion operation actually executed.

## Repair

The Try-3 Skill layer now treats robot-specific template names and middle-layer
feature names as projection aliases only. Formal `robotcad.skill_call.v1` jobs
use explicit executable basic CAD operation skills:

- `CreateSketchProfile`
- `Extrude`
- `Loft`
- `ApplyFillet`
- `ApplyChamfer`
- `CreateHole`
- `BooleanCut`
- `CircularPattern`
- `PlaceComponentFromURDF`
- `CreateSharedJointReference`

The removed middle-layer names are `CreatePocket`, `CreateSlot`,
`CreateGroove`, `CreateRib`, `LinearPattern`, and `MirrorFeature`.

The deprecated `try3/fusion_scripts/Try3FusionBatch` executor and old
`try3/scripts/build_fusion_jobs.py` builder were removed from tracked code.

## Current job gate

After reprojection and Fusion execution, `try3/fusion_api_jobs.json` and
`try3/fusion_api_batch_results.json` still contain 10 jobs:

- Fusion SUCCESS: 8
- UPSTREAM_FAILURE retained: 2

V1 READY jobs now use explicit base modeling operations:

- `PlaceComponentFromURDF`: 53
- `CreateSketchProfile`: 258
- `Extrude`: 258
- `Loft`: 2
- `CreateSharedJointReference`: 49

V2 READY jobs include only basic-operation CAD calls:

- `PlaceComponentFromURDF`: 42
- `CreateSketchProfile`: 205
- `Extrude`: 205
- `Loft`: 6
- `ApplyFillet`: 42
- `ApplyChamfer`: 6
- `CreateHole`: 20
- `BooleanCut`: 7
- `CircularPattern`: 41
- `CreateSharedJointReference`: 38

Validation confirms zero formal calls to removed middle-layer skills.

## Formal batch evidence

The latest Fusion batch created explicit native feature types:

- `adsk::fusion::Sketch`: 463
- `adsk::fusion::ExtrudeFeature`: 490
- `adsk::fusion::LoftFeature`: 8
- `adsk::fusion::FilletFeature`: 42
- `adsk::fusion::ChamferFeature`: 6
- `adsk::fusion::CircularPatternFeature`: 41

Deterministic geometry and interface metrics were regenerated after this batch.
