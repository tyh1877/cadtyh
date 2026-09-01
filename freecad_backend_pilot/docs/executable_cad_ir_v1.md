# Executable CAD IR v1

This IR is the strict execution contract between RobotCAD operation planning and
CAD backends such as FreeCAD. It is intentionally lower-level than a vague
semantic plan.

Hard rule: **requested operation must equal executed native operation**.

If an operation lacks required fields, the backend must record `IR_INCOMPLETE`.
If the native CAD kernel cannot execute the operation, it must record
`NATIVE_OPERATION_FAILURE`. If a fallback is used, it must record
`FALLBACK_USED` and `semantic_match=false`.

## Common operation fields

Each operation must contain:

- `op_id`: stable operation identifier.
- `op_type`: one of the supported operation types.
- `target_body`: logical body/component name.
- `dependencies`: operation IDs this operation depends on.
- `reference_frame`: origin and axes used to interpret geometric parameters.

## Supported operation types and required fields

| Operation | Required fields | Native FreeCAD mapping expected |
|---|---|---|
| `extrude` / `pad` | `profile`, `distance_mm`, `operation_mode`, `reference_frame` | Pad or Part Extrude |
| `pocket` / `cut` | `tool_bodies`, `reference_frame` | Pocket or Boolean Cut |
| `revolve` | `profile`, `axis`, `angle_deg`, `operation_mode`, `reference_frame` | native revolve/revolution feature |
| `loft` | `profiles`, `solid`, `operation_mode` | native loft |
| `sweep` / `pipe` | `profile`, `profile_frame`, `path`, `orientation_mode`, `transition_mode`, `solid`, `operation_mode` | native sweep/pipe |
| `shell` / `thickness` | `target_body`, `faces_to_remove`, `thickness_mm`, `direction`, `join_mode` | native thickness/shell |
| `boolean_union` | `target_body`, `tool_bodies` | native fuse/union |
| `boolean_cut` | `target_body`, `tool_bodies` | native cut |
| `fillet` | `target_body`, `edge_selectors`, `radius_mm` | native fillet |
| `chamfer` | `target_body`, `edge_selectors`, `distance_mm` | native chamfer |
| `pattern` | `target_features`, `pattern_type`, `axis_or_direction`, `count`, `spacing_or_angle` | native array/pattern |
| `mirror` | `target_features`, `mirror_plane` | native mirror |

Pilot v1 profile convention: profile coordinates are interpreted directly in
world coordinates. Rectangle/circle/annulus helper profiles are currently
constructed in the XY plane. Therefore a `revolve` axis must lie in the profile
plane; an axis parallel to the XY normal is rejected as `IR_INCOMPLETE` by the
generation validator.

## Failure classifications

- `IR_INCOMPLETE`: required fields are absent or malformed.
- `UNSUPPORTED_PARAMETERIZATION`: fields are complete but unsupported by the
  backend implementation.
- `NATIVE_OPERATION_FAILURE`: FreeCAD accepted the request but failed during
  native operation construction or recompute.
- `EXPORT_FAILURE`: native model exists but FCStd/STEP/STL export failed.
- `FALLBACK_USED`: backend substituted a different operation.
- `SEMANTIC_EXECUTION_FAILURE`: executed operation type does not match requested
  operation type.
