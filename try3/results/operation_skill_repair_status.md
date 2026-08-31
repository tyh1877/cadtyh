# Try-3 Basic CAD Operation Skill Repair Status

Date: 2026-08-31

Status: explicit basic-operation implementation prepared and SkillCall/Fusion
job projection validated; Fusion formal batch rerun required after the latest
projection change.

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

After reprojection, `try3/fusion_api_jobs.json` still contains 10 jobs:

- READY: 8
- UPSTREAM_FAILURE: 2

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

## Next Fusion actions

First run the smoke script:

`D:\CADtest\papertest\robotcad\backends\fusion_api\FusionAPIBackendSmoke`

Expected dialog:

`RobotCAD Fusion API skill smoke: SUCCESS`

Then run the formal batch:

`D:\CADtest\papertest\robotcad\backends\fusion_api\FusionAPIBackendBatch`

Expected dialog:

`RobotCAD Fusion API formal batch complete`

After the formal batch rerun, regenerate deterministic geometry/interface
tables and update `try3/try3_report.md`.
