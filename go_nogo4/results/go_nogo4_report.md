# Go/No-Go 4 report

## FINAL DECISION: NO-GO

## A. Dataset summary

15 audited real robots; each has three deterministically rendered joint states and four views per state. GT URDF is withheld from model calls.

## B-C. Input setting comparison and quantitative results

| variant | images/case | executed | calls | tokens | Graph F1 | joint type | axis error | origin error | motion translation | Chamfer |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| single_view | [3] | 15 | 15 | 55660 | 0.5 | 0.3333333333333333 | 45.0 | 0.17710434859689697 | 0.22005146184856425 | 0.004893616033422668 |
| multiview_static | [4] | 14 | 15 | 102088 | 0.5 | 0.3333333333333333 | 22.5 | 0.20039142249753528 | 0.16348276443624046 | 0.004535546004547449 |
| multipose_concat | [12] | 15 | 15 | 119482 | 0.5 | 0.3333333333333333 | 22.5 | 0.15124078636323982 | 0.263740818928748 | 0.00424869685545895 |
| motion_aware | [12] | 11 | 15 | 138871 | 0.3636363636363636 | 0.2222222222222222 | 0.0 | 0.20265833284912127 | 0.2630468736339496 | 0.003969945668192169 |

A=single-view, B=multi-view static, D=multi-pose images concatenated without explicit motion reasoning, C=motion-aware prototype with an in-response cross-pose motion hypothesis that constrains CAD/URDF.

## D. Ablation

D and C receive the same 12 labelled images and one model call with identical output-token caps. Their difference is whether motion correspondence/constraints are explicitly inferred and imposed. Actual token usage is reported because C's structured hypothesis may consume more output even under equal caps.

## E. Failure analysis

See `failure_breakdown.csv` and `case_results.csv`; all failure labels are deterministic evaluator outputs.

## F. Novelty assessment

The tested mechanism is multi-pose motion constraints from image changes, not connector, port, mate, retrieval, or generic assembly-agent planning.

## Decision logic

Terminal coverage complete: True; A→B multi-view signal: True; B→C motion signal: False; D→C same-image-count motion-reasoning signal: False; geometry non-degradation C vs D: True; actual C/D total-token matched: False.
Do not advance this motion-aware method route. The pilot does not establish independent mechanical value beyond static/more-image evidence.
