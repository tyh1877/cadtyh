# Structured-Qwen method prompt

You are the structured condition in a blinded CAD refinement experiment.
Derive a fresh intermediate representation from the shared evidence in this
request. You have no access to historical Try-5 plans, schemas, diagnoses,
refined CAD, metrics, or evaluator data.

Select exactly one supported executable body family and provide its complete
schema:

- `central_web`: `span_mm`, `thickness_mm`, `proximal_height_mm`,
  `mid_height_mm`, optional `lateral_offset_mm`, `major_recess`;
- `compound_profile_housing`: `span_mm`, `width_mm`, `height_mm`,
  `major_recess`;
- `gripper_support`: `span_mm`, `bar_width_mm`, `thickness_mm`,
  `working_gap`.

Return JSON only with:

```json
{
  "visual_structural_analysis": [],
  "body_family": "...",
  "semantic_inventory": {
    "required": [], "optional": [], "uncertain": []
  },
  "mechanical_topology": {
    "nodes": [], "edges": []
  },
  "executable_geometry_schema": {},
  "assumptions": []
}
```

Do not emit FreeCAD code. Do not mention or reconstruct historical F1/F2
parameters. All numeric choices must be your own inference from the shared raw
evidence.
