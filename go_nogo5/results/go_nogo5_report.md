# Go/No-Go 5 report

## FINAL DECISION: NO-GO

## A. Dataset summary

15 audited real robots reused as a development set. The one-shot source is the fixed Go/No-Go 4 static-multiview output; only 14 executable sources enter repair eligibility.

## B. Baseline generation results

One-shot executable outputs: 14/15.

## C. Verification statistics

Engineering failures common: True. Collision uses a deterministic sampled non-adjacent surface-clearance proxy (not exact FCL penetration); GT workspace IoU is evaluation-only.

## D. Repair results

Paired repair outputs: 12/14. Repair froze links, topology, joint type, axis, origin and limits, permitting only local primitive geometry edits. Therefore a motion-score shift is not counted as trajectory repair evidence.

| flow | collision mean | workspace IoU median | Graph F1 median | motion translation median | Chamfer median |
|---|---:|---:|---:|---:|---:|
| one_shot_all | 0.09709821428571429 | 0.0 | 0.5 | 0.16348276443624046 | 0.004535546004547449 |
| one_shot_paired_subset | 0.11328125 | 0.0 | 0.4807692307692307 | 0.16504334317732366 | 0.004535546004547449 |
| verification_guided_repair_paired | 0.1015625 | 0.0 | 0.4807692307692307 | 0.16441492726960832 | 0.004535546004547449 |

## E. Ablation

No-feedback is the frozen one-shot output; mechanical feedback is the bounded local repair. Geometry-only feedback is not claimed because meaningful geometry-error feedback would require hidden GT or an AI judge. The absence of an extra-call matched non-feedback repair control prevents causal attribution of any apparent change to feedback.

## F. Failure analysis

Case-level results are in `case_results.csv`. The structured repair inputs are retained under ignored raw runs as `failure.json`.

## G. Research decision

Collision improved: True; workspace improved: False; motion improved: False; graph improved: False; geometry non-degradation: True; feedback isolated from extra call: False.
Do not advance RobotCAD-Agent. Verification exposes common engineering failures, but bounded local repair does not establish two engineering gains or feedback-specific causal value.
