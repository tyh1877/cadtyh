# Mechanical Feature Graph v2

Mechanical Feature Graph v2 is the link-level representation between
multimodal evidence and `Executable CAD IR v1.2`. Its nodes are mechanical
features, not raw CAD operations.

The v2 change is strict parameterization: every feature must carry enough
local geometric information for a backend translator to either emit executable
CAD IR or mark the case as `IR_INCOMPLETE`.

## Required graph fields

- `case_id`
- `link_id`
- `functional_role`
- `kinematic_context`
- `primary_features`
- `functional_features`
- `structural_features`
- `surface_features`
- `feature_dependencies`
- `visual_evidence_refs`
- `interface_refs`

## Required feature fields

- `feature_id`
- `feature_type`
- `priority`
- `role`
- `evidence`
- `anchor`: `link_local_normalized` or `link_local_mm` position.
- `local_frame`: explicit `x_axis`, `y_axis`, `z_axis`.
- `dimensions`: numeric dimensions such as `length_mm`, `width_mm`,
  `height_mm`, `radius_mm`, `thickness_mm`, `depth_mm`.
- `attachment`: `attached_to` and `attachment_face`.
- `visible_evidence_refs`: concrete refs such as `global_view:isometric`,
  `crop:link_level_crop`, or a local observation id.
- `intended_cad_operation`: one of the operation vocabulary values.
- `confidence`

## Failure policy

- Missing anchor, frame, attachment, or operation intent makes the MFG schema
  invalid.
- Missing dimensions required by a target operation makes CAD IR translation
  `IR_INCOMPLETE`.
- The translator may canonicalize field aliases, but it must not invent
  geometry to turn an incomplete feature into a successful case.
- Backends must not silently substitute unsupported operations. Any fallback
  must be logged as `fallback_used=true` and `semantic_match=false`.

## Forbidden planner inputs

GT mesh, GT CAD, GT STEP, product identity, segmentation masks, and GT feature
trees are forbidden in MFG generation.
