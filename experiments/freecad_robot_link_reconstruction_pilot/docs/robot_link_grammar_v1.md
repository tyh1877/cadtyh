# Robot link grammar v1

This grammar defines minimal visible/externally inferable mechanical semantics
for small link-level reconstruction. It is not a GT template and must not encode
case-specific dimensions.

## Base / shoulder base

Minimum visible semantics:

- main base body or base plate
- mounting flange / mounting plate
- central or shoulder-side joint housing
- mounting holes or bosses when visible
- fillet or chamfer groups

## Shoulder-side / upper arm / main link

Minimum visible semantics:

- proximal joint housing
- distal joint housing
- elongated main body
- tapered or lofted transition
- optional recess / lightening feature / cover boundary when visible

## Elbow housing

Minimum visible semantics:

- proximal boss or joint housing
- elbow body / compact housing
- distal housing or interface
- web or local transition
- cutout or recess when visible

## Forearm

Minimum visible semantics:

- elongated housing or link body
- proximal joint region
- distal joint region
- local taper or lofted transition
- shell/recess/cover when visible

## Wrist / tool side

Minimum visible semantics:

- compact joint housing
- flange or mounting face
- local boss
- opening / gap / prongs when visible
- surface transition features

## Feature families

- Primary Geometry: `main_link_body`, `main_housing`, `support_frame`, `palm_plate`
- Functional Geometry: `proximal_joint_housing`, `distal_joint_housing`, `flange`, `bearing_boss`, `mounting_face`, `mounting_boss`, `tool_flange`, `connector_housing`
- Structural Detail: `recess`, `cutout`, `hollow_region`, `rib`, `web`, `cover_region`, `strengthening_boss`, `slot`, `gap`, `lightening_cut`
- Surface Detail: `tapered_transition`, `lofted_transition`, `rounded_section`, `fillet_group`, `chamfer_group`, `blended_joint_transition`
