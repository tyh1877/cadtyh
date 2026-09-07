# Try-4 Phase 5 requirement-to-evidence checklist

- [x] Deterministic evaluator protocol and global thresholds were written and hashed before the first metric run.
- [x] GT STEP hashes were verified and DEV_A/B Macro-Part meshes were exported by frozen source-component mapping.
- [x] Alignment is rigid only; scaling is prohibited and GT bbox diagonal is the distance normalizer.
- [x] Voxel IoU, Chamfer, normalized Chamfer, HD95, normalized HD95, bbox error, centroid error and three-view silhouette IoU are reported.
- [x] Deterministic trace MFR, precision and critical recall are reported with their non-perceptual limitation explicit.
- [x] CAD validity, silent fallback, reopen, recompute and ±5% edit/restore evidence feed the gate.
- [x] Multi-criteria Gate B produces PASS, LOCAL_REPAIR or REPLAN without a scalar aggregate score.
- [x] DEV_A has paired T0/T1 evaluation; DEV_B has T1 absolute evaluation only.
- [x] All failed implementation attempts and the superseded nonconformant metric table remain archived.
- [x] A complete rerun produced byte-identical result tables.
- [x] No reviewer, repair, T2 or R03 TRANSFER execution was started.
