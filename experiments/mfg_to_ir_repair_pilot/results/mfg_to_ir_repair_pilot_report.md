# MFG-to-IR Repair Pilot Report

## Scope

This pilot reuses the 6 frozen links from `freecad_robot_link_reconstruction_pilot_v2`. It does not call an LLM/VLM. It only repairs deterministic MFG schema/canonicalization issues and reruns strict MFG→IR→FreeCAD execution.

## Aggregate result

| Version | v2 MFG | repaired MFG | v2 IR | repaired IR | v2 exec | repaired exec |
|---|---:|---:|---:|---:|---:|---:|
| R1 | 4/6 | 6/6 | 2/6 | 5/6 | 0/6 | 1/6 |
| R2 | 4/6 | 6/6 | 2/6 | 4/6 | 1/6 | 0/6 |

Silent fallback total: `0`.

## Operation usage after repair

```json
{
  "R1": {
    "loft": 5,
    "revolve": 16,
    "extrude": 10,
    "boolean_union": 5,
    "boolean_cut": 7,
    "fillet": 5,
    "chamfer": 2
  },
  "R2": {
    "loft": 6,
    "revolve": 17,
    "extrude": 8,
    "boolean_union": 4,
    "boolean_cut": 5,
    "fillet": 3,
    "chamfer": 1
  }
}
```

## Failure accounting

| Version | Case | Link | Operation | Feature | Reason |
|---|---|---|---|---|---|
| R1 | dev_arm-dcc2b0ce1e | L2 | fillet | fillet_group | robotcad.backends.freecad_api.FreeCADBackend.FreeCADBackendError: native shape is null or invalid |
| R1 | dev_arm-dcc2b0ce1e | L3 | fillet | fillet_group | robotcad.backends.freecad_api.FreeCADBackend.FreeCADBackendError: native shape is null or invalid |
| R1 | dev_arm-dcc2b0ce1e | L4 | fillet | fillet_group | robotcad.backends.freecad_api.FreeCADBackend.FreeCADBackendError: native shape is null or invalid |
| R1 | dev_arm-ab15a75247 | L0 | fillet | fillet_group | robotcad.backends.freecad_api.FreeCADBackend.FreeCADBackendError: native shape is null or invalid |
| R2 | dev_arm-dcc2b0ce1e | L2 | fillet | fillet_group | robotcad.backends.freecad_api.FreeCADBackend.FreeCADBackendError: native shape is null or invalid |
| R2 | dev_arm-dcc2b0ce1e | L3 | boolean_cut | lightening_cut | robotcad.backends.freecad_api.FreeCADBackend.FreeCADBackendError: native shape is null or invalid |
| R2 | dev_arm-ab15a75247 | L2 | boolean_union | assembly_union | robotcad.backends.freecad_api.FreeCADBackend.FreeCADBackendError: native shape is null or invalid |
| R2 | dev_arm-ab15a75247 | L4 | fillet | fillet_group | robotcad.backends.freecad_api.FreeCADBackend.FreeCADBackendError: native shape is null or invalid |

## Bottleneck classification

```json
{
  "MFG-to-IR translation / CAD parameter estimation": 3,
  "selector/backend execution": 8
}
```

## Interpretation

The repair improved IR completeness but did not meet the target execution success. The remaining blocker is primarily selector/backend execution or unstable operation parameters.
