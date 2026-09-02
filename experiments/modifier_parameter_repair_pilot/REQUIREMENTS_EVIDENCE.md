# modifier_parameter_repair_pilot requirement-to-evidence checklist

## Frozen inputs

- [x] Use only `mfg_to_ir_repair_pilot` R1/R2 repaired MFG and IR outputs.
- [x] Preserve R1/R2 × 6 frozen links in the denominator.
- [x] Do not call Qwen/GLM or any VLM/LLM.
- [x] Do not use GT mesh/STEP/CAD/product identity.

## Modifier parameter repair

- [x] Treat LLM/MFG modifier values as requested parameters, not authoritative executable CAD parameters.
- [x] Record requested value, resolved value, safe cap, repair status, and repair reason.
- [x] Emit `PARAMETER_REPAIRED`, `NO_REPAIR_NEEDED`, or `IR_INCOMPLETE`.
- [x] Strengthen edge selectors without backend silent fallback.

## Execution and reporting

- [x] Execute repaired IR with the existing FreeCAD backend.
- [x] Preserve all execution failures with explicit failure codes.
- [x] Confirm silent fallback remains zero.
- [x] Report whether R1 reaches at least 3/6 and R2 remains at least 4/6.
- [x] Commit tracked protocol, scripts, lightweight results, and report only.
