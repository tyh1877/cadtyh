# Try-5B.1-A1 Mechanical Geometry Protection Ablation

## Current-stage requirement-to-evidence checklist

This stage ends after baseline reproduction, evaluator integrity, the minimal
policy implementation, and the L04 paired dry run. It must not execute the
three-link formal matrix or consume the previously reserved formal holdout.
The earlier `try5b1_a1_mechanical_constraint_ablation` P1 record is retained as
history but is superseded for future execution by this redesigned protocol; its
one-shot command must not be used for the new A1.

- [x] Re-run the current original C1/F2 pipeline before implementing C2 and demonstrate reproducibility.
  Evidence: `results/try5b1_a1_geometry_protection/baseline_reproduction.json`.
- [x] Freeze the baseline commit, Python/FreeCAD versions, input image hashes, URDF, F2 schema, Interface Contract, VisualEvidencePack, seed, and evaluator settings.
  Evidence: `results/try5b1_a1_geometry_protection/reproducibility_manifest.json`.
- [x] Classify every proposed main mechanical metric as evaluator-computed or declarative/hard-coded.
  Evidence: `results/try5b1_a1_geometry_protection/evaluator_integrity.json`.
- [x] Exclude hard-coded swept-clearance, forbidden-fusion, virtual-solid, and meaningless-patch fields from the main quantitative analysis.
  Evidence: frozen analysis schema and evaluator-integrity audit.
- [x] Use one shared F2 generation path controlled only by `mechanical_geometry_policy`; do not add runtime rejection, rollback, acceptance, repair, family, inventory, or topology logic.
  Evidence: config parity report, source audit, and L04 execution traces.
- [x] Compute body-only and final assembled-link geometry metrics with the same evaluator definition in both conditions.
  Evidence: L04 dry-run geometry result tables and metric-equivalence test.
- [x] Before generation, prove all listed inputs are identical and that the only condition difference is `mechanical_geometry_policy`.
  Evidence: canonical parity report and shared-input hash manifest.
- [x] Run only L04 for C1_CONSTRAINED and C2_UNPROTECTED and retain failures without repair, deletion, or rerun.
  Evidence: dry-run failure accounting and raw worker outputs.
- [x] Record `EXECUTED`/`SKIPPED` traces for protected cuts, distal clearance, scaffold preservation, and attachment closure.
  Evidence: `results/try5b1_a1_geometry_protection/l04_execution_trace.json`.
- [x] Run identical build/export/reopen, BICR/attachment, relevant JR3, GCFR, Exact collision, body-only geometry, and final-link geometry evaluation for both L04 candidates.
  Evidence: `results/try5b1_a1_geometry_protection/l04_dry_run_summary.json`.
- [x] Confirm zero GT access from generation and zero holdout evaluation.
  Evidence: leakage audit, empty formal lock/output checks, and job manifests.
- [x] Stop after the paired L04 dry run and make no formal three-link claim.
  Evidence: stage status `DRY_RUN_COMPLETE_FORMAL_NOT_RUN`.

Final stage audit: `PASS_WITH_DISCLOSED_LIMITATIONS`. L04's invoked proximal
cut is a geometric no-op (identical body-only STL hash and volume), so formal
three-link suitability is `CONDITIONAL_GO`; see
`results/try5b1_a1_geometry_protection/post_run_integrity_review.json`.
