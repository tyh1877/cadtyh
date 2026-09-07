# Try-4 Phase 5 report — deterministic evaluator and Quality Gate

Status: Phase 5 is complete. The evaluator and global Gate B thresholds were
frozen before the first metric table. No review, repair, T2 or TRANSFER run was
started.

## Frozen method

Generated meshes are registered to GT with a deterministic rigid-only procedure:
surface-centroid translation, PCA with 24 proper axis rotations, best symmetric
Chamfer initialization and rigid ICP refinement. Scaling is prohibited. This
removes pose error because T0/T1 have no registered local frame, while preserving
dimension and shape error. Distances are normalized by the GT bbox diagonal.

Each evaluation uses 20,000 deterministic surface samples, a voxel pitch of GT
bbox diagonal / 64, and 256×256 front/side/top silhouette grids. The frozen
multi-criteria thresholds are IoU ≥ 0.35, normalized Chamfer ≤ 0.08, normalized
HD95 ≤ 0.18, trace MFR ≥ 0.80, critical trace recall = 1.0, plus valid/editable
native CAD. IoU < 0.15 or critical recall < 0.5 selects REPLAN; other failures
select LOCAL_REPAIR.

Trace MFR means an expected requirement maps to a planned Feature and at least
one successful native CAD operation without fallback. It measures executable
coverage, not whether the feature looks correct. That distinction is essential:
Phase 6 review is still needed for perceptual/mechanical correctness.

## Gate result

| Set | Evaluations | PASS | LOCAL_REPAIR | REPLAN |
| --- | ---: | ---: | ---: | ---: |
| DEV_A T0 | 5 | 0 | 5 | 0 |
| DEV_A T1 | 5 | 0 | 4 | 1 |
| DEV_B T1 | 7 | 0 | 4 | 3 |
| Total | 17 | 0 | 13 | 4 |

All 17 CAD artifacts remained valid and editable. T1 failed IoU on all 12 parts;
10 also failed HD95 and 4 failed normalized Chamfer. The REPLAN parts are
R01_P03, R02_P03, R02_P05 and R02_P06. These are scheduler decisions only; no
repair has been executed.

## DEV_A paired T0 → T1 result

| Metric | T0 mean | T1 mean | Mean Δ T1−T0 | Parts improved |
| --- | ---: | ---: | ---: | ---: |
| Voxel IoU ↑ | 0.2758 | 0.2394 | -0.0364 | 4/5 |
| Normalized Chamfer ↓ | 0.07118 | 0.07120 | +0.00002 | 3/5 |
| Normalized HD95 ↓ | 0.2254 | 0.2350 | +0.0096 | 1/5 |
| Mean silhouette IoU ↑ | 0.4251 | 0.4276 | +0.0025 | 4/5 |
| Trace MFR ↑ | 0.7833 | 1.0000 | +0.2167 | 4/5 |
| Critical trace recall ↑ | 0.9500 | 1.0000 | +0.0500 | 1/5 |

The paired evidence does not show an aggregate geometric improvement from T0 to
T1. Four parts improve slightly in IoU and silhouette, but R01_P03 regresses
strongly enough to lower mean IoU; HD95 improves on only one part. The clear gain
is trace coverage: T1 gives every declared feature an executable successful CAD
path. This supports pipeline completeness, while the geometric hypothesis remains
unsupported in this development run.

DEV_B T1 mean values are IoU 0.2126, normalized Chamfer 0.08572, normalized
HD95 0.2872 and silhouette IoU 0.4242. DEV_B has no T0 baseline, so no causal
T0→T1 comparison is made for it.

## Reliability and incidents

The final four primary CSV tables were regenerated from scratch and were
byte-identical. GT source STEP hashes and the final evaluator snapshot are
recorded. Three pre-table implementation failures and one protocol-conformance
failure are retained in `phase5_execution_incidents.csv`. The first metric table
used the wrong silhouette raster resolution and is archived under
`phase5_attempt_01/`; it is excluded from all conclusions. Thresholds were never
changed.

## Phase-5 conclusion

The deterministic comparator and Quality Gate are operational and sufficiently
strict to reject the visibly coarse models. Phase 4's 12/12 technical success did
not meet the initial-build quality bar. The current bottleneck is visual grounding
and CAD parameter/shape-family estimation, rather than FreeCAD execution.

The next authorized step is Phase 6, which should define the Structured Review
Contract using these frozen discrepancies. Phase 5 stops here without modifying
any model.
