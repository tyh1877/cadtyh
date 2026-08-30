# Try-3 Fusion API Composite Geometry Repair Status

Date: 2026-08-30

Status: prepared for manual Fusion execution, not yet evaluated.

## Invalidated failure

The first Fusion API formal batch must not be used for geometry conclusions.
Visual inspection showed near-identical rounded cubes because the SkillCall
projection discarded the planner's explicit primitives and executed only a
single envelope skill per link. Missing geometry also fell back to a 10 mm
sphere, which rendered as a 20 mm rounded block in the backend.

## Repair

The repaired pipeline now requires:

- parser support for `link_id`, `primitive_type`, `radius_bottom`, and
  `radius_top`;
- hard rejection of missing or unsupported explicit primitives;
- `CreateCompositeLinkGeometry` as the primary per-link SkillCall;
- Fusion backend construction from explicit `box`, `cylinder`, `cone`, and
  `sphere` primitives;
- formal job gating that rejects stale envelope-only or fallback-sphere jobs.

## Current formal job gate

`try3/fusion_api_jobs.json` contains 10 jobs:

- READY: 8
- UPSTREAM_FAILURE: 2

Recorded upstream failures:

- V1 `dev_arm-4c7b408826`: model response contained invalid JSON.
- V2 `dev_arm-551a9c392e`: model response contained no supported explicit
  primitives.

Primitive-preserving READY jobs:

- V1 `dev_arm-ab15a75247`: 5 links, 40 primitives
- V2 `dev_arm-ab15a75247`: 5 links, 37 primitives
- V2 `dev_arm-4c7b408826`: 10 links, 44 primitives
- V1 `dev_arm-dcc2b0ce1e`: 10 links, 80 primitives
- V2 `dev_arm-dcc2b0ce1e`: 10 links, 53 primitives
- V1 `dev_arm-43fa322555`: 17 links, 68 primitives
- V2 `dev_arm-43fa322555`: 17 links, 77 primitives
- V1 `dev_arm-551a9c392e`: 21 links, 72 primitives

## Next external action

Run the packaged Fusion script:

`D:\CADtest\papertest\robotcad\backends\fusion_api\FusionAPIBackendBatch`

Expected completion dialog:

`RobotCAD Fusion API formal batch complete`

After Fusion execution, inspect `try3/fusion_api_batch_results.json` and the
per-case `fusion_api_model.f3d`, `fusion_api_model.step`, `fusion_api_model.stl`,
and `meshes/L*.stl` outputs before geometry evaluation.
