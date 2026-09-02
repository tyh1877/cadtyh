# modifier_parameter_repair_pilot report

## Controls

- Inputs: repaired MFG/IR from `mfg_to_ir_repair_pilot`.
- Frozen denominator: R1/R2 × 6 links.
- LLM/VLM calls: none.
- GT mesh/STEP/CAD use: none.
- Backend silent fallback: forbidden; execution logs remain authoritative.

## Results

- IR repair success: 9/12
- Modifier repair status: `{'PARAMETER_REPAIRED': 11}`
- R1 batch success: 5/6
- R2 batch success: 4/6
- Silent fallback total: 0
- Failure codes: `{'IR_INCOMPLETE': 3}`

## Interpretation

The pilot meets the acceptance criteria. The previous R1 fillet failures were caused by non-executable modifier parameters rather than a general FreeCAD backend limitation.

Parameter repair is counted explicitly as partial semantic match, not backend fallback. This preserves the distinction between executable CAD repair and silent success inflation.

## Modifier repair audit

| version | case | link | op | type | requested mm | resolved mm | safe cap mm | reason |
| --- | --- | --- | --- | --- | ---: | ---: | ---: | --- |
| R1 | dev_arm-dcc2b0ce1e | L2 | op_009 | fillet | 15.0 | 0.7 | 0.7 | role_scale_cap_no_local_dimension |
| R1 | dev_arm-dcc2b0ce1e | L3 | op_009 | fillet | 15.0 | 1.25 | 1.25 | role_scale_cap_no_local_dimension |
| R1 | dev_arm-dcc2b0ce1e | L4 | op_009 | fillet | 8.0 | 0.7 | 0.7 | role_scale_cap_no_local_dimension |
| R1 | dev_arm-ab15a75247 | L0 | op_008 | fillet | 4.0 | 1.05 | 1.05 | role_scale_cap_no_local_dimension |
| R1 | dev_arm-ab15a75247 | L0 | op_009 | chamfer | 1.5 | 0.5 | 0.5 | role_scale_and_feature_dimension_cap |
| R1 | dev_arm-ab15a75247 | L4 | op_009 | fillet | 1.5 | 0.6 | 0.6 | role_scale_cap_no_local_dimension |
| R1 | dev_arm-ab15a75247 | L4 | op_010 | chamfer | 2.0 | 0.5 | 0.5 | role_scale_and_feature_dimension_cap |
| R2 | dev_arm-dcc2b0ce1e | L2 | op_011 | fillet | 12.0 | 0.7 | 0.7 | role_scale_and_feature_dimension_cap |
| R2 | dev_arm-dcc2b0ce1e | L3 | op_011 | fillet | 8.0 | 1.25 | 1.25 | role_scale_and_feature_dimension_cap |
| R2 | dev_arm-ab15a75247 | L4 | op_009 | fillet | 3.0 | 0.6 | 0.6 | role_scale_cap_no_local_dimension |
| R2 | dev_arm-ab15a75247 | L4 | op_010 | chamfer | 2.0 | 0.5 | 0.5 | role_scale_and_feature_dimension_cap |
