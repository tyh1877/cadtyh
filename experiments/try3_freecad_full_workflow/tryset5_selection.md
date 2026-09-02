# TrySet-5-v1 Selection for Try-3 FreeCAD

This set is migrated from the earlier Try-3 preselection and re-frozen for the
clean FreeCAD full-workflow experiment before any V0/V1/V2 FreeCAD results are
generated in this directory.

No case may be replaced based on Try-3 FreeCAD results.

| Tier | Case | Links / joints | Why included |
|---|---|---:|---|
| Easy | `dev_arm-ab15a75247` | 5 / 4 | Compact serial arm for pipeline, schema, and FreeCAD assembly stability. |
| Medium | `dev_arm-4c7b408826` | 10 / 9 | Industrial serial arm with long links and visible elbow/wrist transitions. |
| Medium | `dev_arm-dcc2b0ce1e` | 10 / 9 | Different industrial geometry style and long-link arrangement. |
| Hard | `dev_arm-43fa322555` | 17 / 16 | High component count with compact curved housings and wrist detail. |
| Hard | `dev_arm-551a9c392e` | 21 / 20 | Highest link count in the set; stresses integration, interface preservation, and detail. |

The five cases cover easy/medium/hard complexity, different link counts, and
different expected housing/detail styles. Inputs must remain limited to
multi-view images, engineering text, and sanitized kinematic-only URDF.

