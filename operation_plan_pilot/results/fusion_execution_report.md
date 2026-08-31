# Operation-plan Fusion Execution Pilot Report

Decision: PASS

## Aggregate

- links_total: 6
- fusion_success: 5
- links_with_5plus_calls: 5
- links_with_exports: 5
- feature_counts: {'adsk::fusion::ChamferFeature': 5, 'adsk::fusion::CircularPatternFeature': 2, 'adsk::fusion::ExtrudeFeature': 37, 'adsk::fusion::FilletFeature': 5, 'adsk::fusion::LoftFeature': 8, 'adsk::fusion::Sketch': 33}
- pass: True

## Per-link execution

| case | link | status | calls | exports | source op types |
|---|---|---:|---:|---:|---|
| `dev_arm-dcc2b0ce1e` | `L2` | SUCCESS | 17 | True | ApplyChamfer,ApplyFillet,BooleanCut,BooleanUnion,CircularPattern,CreateHole,CreateSketchProfile,Extrude,Loft,Revolve,compiler_base |
| `dev_arm-dcc2b0ce1e` | `L3` | FAILURE | 20 | False | ApplyChamfer,ApplyFillet,BooleanUnion,CreateHole,CreateSketchProfile,Extrude,Revolve,Shell,compiler_base |
| `dev_arm-dcc2b0ce1e` | `L4` | SUCCESS | 14 | True | ApplyChamfer,ApplyFillet,BooleanUnion,CircularPattern,CreateHole,CreateSketchProfile,Loft,Revolve,Sweep,compiler_base |
| `dev_arm-ab15a75247` | `L0` | SUCCESS | 11 | True | ApplyChamfer,ApplyFillet,BooleanCut,CreateHole,CreateSketchProfile,Extrude,Revolve,compiler_base |
| `dev_arm-ab15a75247` | `L2` | SUCCESS | 14 | True | ApplyChamfer,ApplyFillet,BooleanUnion,CreateHole,CreateSketchProfile,Extrude,Loft,Revolve,Shell,compiler_base |
| `dev_arm-ab15a75247` | `L4` | SUCCESS | 14 | True | ApplyChamfer,ApplyFillet,BooleanUnion,CreateHole,CreateSketchProfile,Extrude,Shell,compiler_base |

## Limitation

Compiler v1 lowers not-yet-native source operations such as Revolve, Shell, Sweep, and BooleanUnion into the currently executable Fusion operation subset. The outputs are viewable/editable execution artifacts, not final one-to-one native operation reproductions.
