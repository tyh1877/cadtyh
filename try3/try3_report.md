# Try-3 Fusion API Report

## Executive conclusion

Try-3 is not a hard Go/No-Go. The repaired Fusion API path is executable and editable, but the current V2 method is not yet strong enough to claim a stable method improvement over V1.

The strongest positive result is engineering feasibility: 8/10 formal V1/V2 jobs rebuilt in Fusion and exported F3D, STEP, assembled STL, and per-link STL. All successful jobs preserved canonical component correspondence.

The main negative result is method effect: on the three paired V1/V2 successes, V2 improves joint-neighborhood gap in 2/3 cases but worsens Chamfer in 2/3 cases, and the bounding-box overlap proxy does not improve. This supports Try-3.x refinement, not expansion or a paper-level method claim yet.

## TrySet-5

| case | tier | role |
|---|---|---|
| `dev_arm-ab15a75247` | easy | compact_serial_arm |
| `dev_arm-4c7b408826` | medium | industrial_serial_arm |
| `dev_arm-dcc2b0ce1e` | medium | industrial_serial_arm |
| `dev_arm-43fa322555` | hard | curved_housing_arm |
| `dev_arm-551a9c392e` | hard | high_link_count_arm |

## Fusion API execution

| version | jobs | success | failed | median Chamfer | median HD95 | median IoU | median interface gap | median bbox overlaps |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| V1 | 5 | 4 | 1 | 0.007129 | 0.197765 | 0.240299 | 0.318515 | 78.500000 |
| V2 | 5 | 4 | 1 | 0.012287 | 0.195317 | 0.247006 | 0.288225 | 45.000000 |

## Paired V1 vs V2 cases

| case | Chamfer V1 | Chamfer V2 | interface gap V1 | interface gap V2 | bbox overlaps V1 | bbox overlaps V2 |
|---|---:|---:|---:|---:|---:|---:|
| `dev_arm-43fa322555` | 0.007364 | 0.019390 | 0.327844 | 0.191554 | 136.000000 | 136.000000 |
| `dev_arm-ab15a75247` | 0.017607 | 0.022185 | 0.263804 | 0.294976 | 10.000000 | 10.000000 |
| `dev_arm-dcc2b0ce1e` | 0.002681 | 0.004923 | 0.489021 | 0.281474 | 45.000000 | 45.000000 |

## Recorded failures

- V1 `dev_arm-4c7b408826`: BlueprintError: response contains invalid JSON: Expecting ',' delimiter: line 1 column 2790 (char 2789)
- V2 `dev_arm-551a9c392e`: ValueError: no supported explicit primitives

## Skill execution evidence

`CreateSketchProfile`, `Extrude`, and `Loft` are now the primary base-geometry SkillCalls. Fusion feature types recorded in the successful batch:

- `adsk::fusion::ChamferFeature`: 6
- `adsk::fusion::CircularPatternFeature`: 41
- `adsk::fusion::ExtrudeFeature`: 490
- `adsk::fusion::FilletFeature`: 42
- `adsk::fusion::LoftFeature`: 8
- `adsk::fusion::Sketch`: 463

## Required protocol answers

V0 reproduction is provenance-only in this repaired Fusion API report: the five Try-2 D outputs are recorded in `v0_provenance.csv`, but they were not rerun through the new Fusion API skill backend.

No GT geometry was sent to the model. GT meshes and original URDF geometry are loaded only after generation by deterministic evaluators.

The Mechanical Embodiment Plan, Interface Graph, and Feature Graph schemas are frozen under `try3/schemas/`. V2 uses them before blueprint projection; V1 does not use the explicit MEP/interface/feature planning stage.

Implemented RobotCAD Skills include `CreateSketchProfile`, `Extrude`, `Loft`, `CreateCompositeLinkGeometry` for legacy compatibility, `ApplyFillet`, `ApplyChamfer`, `CreateHole`, `BooleanCut`, `CircularPattern`, placement, and shared joint references. Legacy robot-template names are projection aliases only, not formal execution skills.

Visible feature recall is not yet computed by an objective detector, so it is not claimed. The screenshot and Fusion outputs show the prior cube collapse is fixed, but that is qualitative evidence only.

Primary bottleneck: operation planning and Fusion Skill capability. Visual grounding supplies varied primitives, and external URDF preserves topology, but the current operation library still lacks robust interface-aware booleaning, collision control, and high-fidelity surface detail.

Recommended next step: Try-3.x refinement focused on interface-aware composite skills and collision/overlap control, then rerun the same TrySet-5. Do not expand the benchmark yet.
