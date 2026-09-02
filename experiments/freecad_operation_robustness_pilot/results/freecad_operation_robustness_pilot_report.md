# FreeCAD Operation Robustness Pilot Report

## Scope

This pilot replays the repaired IR from `mfg_to_ir_repair_pilot`. It does not call an LLM/VLM and does not change MFG semantics.

## Result summary

| Version | Previous success | Robust replay success | IR incomplete | Native failures | Exports |
|---|---:|---:|---:|---:|---:|
| R1 | 1/6 | 2/6 | 1 | 3 | 2/6 STEP |
| R2 | 0/6 | 4/6 | 2 | 0 | 4/6 STEP |

Operation smoke: `8/8` passed.
Silent fallback total: `0`.

## Failure codes

```json
{
  "NO_SAFE_EDGE": 3
}
```

## Failed operations

| Version | Case | Link | Operation | Code | Preflight | Context |
|---|---|---|---|---|---:|---:|
| R1 | dev_arm-dcc2b0ce1e | L2 | fillet | NO_SAFE_EDGE | True | True |
| R1 | dev_arm-dcc2b0ce1e | L3 | fillet | NO_SAFE_EDGE | True | True |
| R1 | dev_arm-ab15a75247 | L0 | fillet | NO_SAFE_EDGE | True | True |

## Interpretation

The backend robustness target did not fully pass. The report now separates explicit backend failure codes from upstream IR incompleteness, which is sufficient to decide the next repair target.
