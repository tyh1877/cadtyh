# Try-3 Operation-Grounded Skill Repair Status

Date: 2026-08-31

Status: implementation prepared; Fusion smoke and formal batch rerun required.

## Rationale

Visual inspection of the repaired V1/V2 Fusion outputs showed that the cube
collapse was fixed, but the geometry was still dominated by boxes and
cylinders. The remaining bottleneck is not Fusion MCP connectivity; it is that
the Skill layer used coarse mechanical templates instead of a richer CAD
operation vocabulary.

## Repair

The Try-3 Skill layer now treats robot-specific template names as historical
Feature Graph aliases only. Formal `robotcad.skill_call.v1` jobs use
operation-grounded CAD skills:

- `CreateCompositeLinkGeometry`
- `ApplyFillet`
- `ApplyChamfer`
- `CreateHole`
- `CreatePocket`
- `CreateSlot`
- `CreateGroove`
- `CreateRib`
- `CircularPattern`
- `LinearPattern`
- `MirrorFeature`

The deprecated `try3/fusion_scripts/Try3FusionBatch` executor and old
`try3/scripts/build_fusion_jobs.py` builder were removed from tracked code.

## Current job gate

After reprojection, `try3/fusion_api_jobs.json` still contains 10 jobs:

- READY: 8
- UPSTREAM_FAILURE: 2

V1 READY jobs remain base-composite controls:

- `PlaceComponentFromURDF`: 53
- `CreateCompositeLinkGeometry`: 53
- `CreateSharedJointReference`: 49

V2 READY jobs now include operation-level CAD calls:

- `CreateCompositeLinkGeometry`: 42
- `ApplyFillet`: 42
- `ApplyChamfer`: 6
- `CreateGroove`: 42
- `CircularPattern`: 41
- `CreateHole`: 20
- `CreateRib`: 5
- `CreateSlot`: 5
- `CreateSharedJointReference`: 38

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
