# Go/No-Go 3 report

## FINAL DECISION: NO-GO

## A. Dataset summary

Development set: 15 audited real robots. Input text is structurally blind; GT was not sent to any model call.

## B-D. Baselines, prototype, ablation

| variant | executed | failed | calls | tokens | Graph F1 | axis error | origin error | motion translation | Chamfer |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| direct | 11 | 4 | 11 | 80036 | 0.5333333333333333 | 45.0 | 0.21808095977767092 | 0.19379827079078132 | 0.0034002789177019007 |
| simplecad | 15 | 0 | 15 | 109668 | 0.5 | 45.0 | 0.24989452995225211 | 0.23047986171690443 | 0.00458167651966956 |
| v1_joint_frame | 15 | 0 | 30 | 227398 | 0.5 | 0.0 | 0.2271452046765881 | 0.24786126809905568 | 0.004393849366329337 |
| v2_consistency | 14 | 1 | 30 | 238188 | 0.5 | 0.0 | 0.1959887193387817 | 0.30054100639165116 | 0.0032136869232028747 |

V0=Direct; V1=Joint Frame Recovery soft conditioning; V2=Joint Frame Recovery + hard CAD-URDF consistency. SimpleCAD is an execution-constrained baseline.

## E. Failure analysis

See `failure_breakdown.csv` and `case_results.csv`; all categories are produced by the deterministic evaluator. Transport timeouts are separated from invalid-CAD failures.

## F. Novelty assessment

The prototype only tests recovery of reference-conditioned joint frames and consistency between those *predicted* frames and emitted CAD/URDF. It does not claim a connector planner, port matcher, generic assembly agent, or novelty over ArtiCAD/AssemCAD.

## Decision logic

Coverage complete: True; all requested kinematic/motion directions improved: False; geometry did not decline: True; hard-frame CAD-URDF consistency exact: True; mechanism isolated from extra prompt/token use: False.
Do not proceed with the method route yet. Redirect to benchmark/evaluation work or revise the mechanism before expansion.
