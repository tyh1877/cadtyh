# Try-4 T0 direct Macro-Part reconstruction

Work only from `part_input.json`, its referenced `images/` files, and the attached
images. Return exactly one JSON object matching the supplied schema. This is a
single-pass direct baseline: do not review, repair, use GT CAD, write Python, run
FreeCAD, inspect the repository, or invoke a shared Try-4 planning skill.

Interpret the semantic label and all views. Estimate a coherent part-local model
in millimetres. Coordinates need not match the unregistered STEP/URDF render
frame. Keep the part near the origin and use positive, plausible dimensions.
Respect `multi_body_policy`: visibly separate jaws/plates may be separate bodies;
do not fuse across working gaps. Model only evidence-supported exterior structure.

Every Feature Graph item must cite actual packet image paths and one or more
exact `expected_features[].feature_id` values in `requirement_refs`. Every PLANNED
feature must have at least one CAD operation with the same `feature_ref`; mark
unsupported requirements UNIMPLEMENTED and do not call the whole plan complete.
Critical expected features should be represented unless evidence is ambiguous,
in which case record the limitation in assumptions.

Use only these executable operations:

- `oriented_box`: include `start`, `end`, `width_mm`, `depth_mm`.
- `cylinder_primitive`: include `center`, `axis`, `radius_mm`, `height_mm`.
- `lofted_prism`: include `start`, `end`, `start_size_mm`, `end_size_mm`.
- `boolean_union`/`boolean_cut`: target_body references an existing object and
  `tool_bodies` is a nonempty list of existing objects.
- `fillet`: include `edge_selectors` and `radius_mm`.
- `chamfer`: include `edge_selectors` and `distance_mm`.

Every operation includes a unique sequential `op_id`, explicit dependencies,
`target_body`, `feature_ref`, and this reference frame:
`{"origin":[0,0,0],"x_axis":[1,0,0],"y_axis":[0,1,0],"z_axis":[0,0,1]}`.
New primitives use their own op_id as target_body. Boolean/modifier target_body
is the existing base object. `final_objects` and each body final_object must name
executed operation outputs. Choose one editable Part::Box Length/Width/Height or
Part::Cylinder Radius and record its exact baseline value for the later ±5% test.
No fallback is permitted.

The response schema uses one uniform operation record because the serving API
does not accept conditional operation schemas. Include every operation field.
For fields not applicable to that `op_type`, use `null` for scalar/vector fields
and `[]` for `tool_bodies` or `edge_selectors`. The local Plan Gate still enforces
the applicable fields listed above.
