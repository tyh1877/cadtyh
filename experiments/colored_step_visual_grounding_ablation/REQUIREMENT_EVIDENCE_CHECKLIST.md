# Colored STEP Visual Grounding Ablation Checklist

Audited 2026-09-05. See `CLOSEOUT.md` for the requirement-to-evidence map.
Checked means directly supported at the stated scope; unchecked gates prevent
scientific completion. The original protocol remains unchanged.

## Provenance and assets

- [x] Five native STEP cases preserved, with source URLs, hashes and regeneration script in `results/source_provenance.csv`.
- [x] Oracle-only interpretation retained; historical mesh cohort not pooled.
- [x] Actual denominator established: 58 STEP leaf components (7/9/24/8/10), 66 solids; old checklist's 63-link count was incorrect.
- [x] Five native STEP assemblies exported/reopened, leaf and solid counts retained in `results/native_step_asset_summary.csv`.
- [x] Five FCStd files and colored STEP files exist; hashes in `results/closeout_evidence_inventory.csv`.
- [x] Six renders per condition and case; 30 silhouette IoUs equal 1; A1/A2 byte parity passes in `results/asset_parity_by_view.csv`.
- [ ] Independent serialized camera/geometry transform parity proof (not recorded historically).
- [ ] Reopened per-object color-value validation (only STEP color entities and previews recorded).
- [ ] Authoritative STEP-component-to-URDF-link mapping (not available).

## E1

- [x] All 45 cells retained; 43 successes and two explicit API failures in `results/closeout_failures.csv`.
- [x] Successful API manifests identify model and six images; implementations use real inline image data.
- [x] Historical metrics recomputed from unchanged scans/masks by `scripts/finalize_existing_results.py`.
- [x] Failure-inclusive component table has 522 rows; paired case and aggregate macro/micro tables exported.
- [x] 43 successful contact sheets regenerated locally and excluded from Git.
- [ ] Visible target-pixel purity and categorical wrong-link crop rate (historical masks include occluded geometry; wrong-link column is a contamination proxy).
- [ ] Proximal/distal joint localization availability and evaluated feature crops (not implemented/labeled).
- [ ] Pre-repeat pipeline/evaluator freeze provenance (not available; repeats treated as exploratory).

## E2

- [x] Common prompt/schema/model implementation; 14 plans revalidated against JSON schema and recorded metrics.
- [x] All 15 case-condition cells retained, including one upstream failure.
- [x] 174 component/condition plan rows exported through E1 matching, with absent plans retained.
- [x] Predicted-region completeness and syntactic reference traceability reported with correct limitations.
- [x] Feature and joint-region counts explicitly treated as diagnostics, not accuracy.
- [ ] GT-link completeness, joint-housing coverage and semantic evidence support (no frozen labels/mapping).
- [ ] Blinded feature-correctness annotation (pending as allowed by protocol).

## Closeout

- [x] Source protocol re-read; deviations and unmet promotion gates recorded in `CLOSEOUT.md` without retroactive amendment.
- [x] Successful-call resources summarized; missing failure usage remains unknown.
- [x] Heavy artifacts/raw outputs excluded via experiment-local `.gitignore`.
- [x] Relevant scripts compile with root `.venv/Scripts/python.exe`.
- [x] Offline integrity/asset audits pass; integrity success does not imply scientific gate success.
- [ ] Frozen-protocol scientific completion: blocked; NO-GO for promotion.

Local commit and diff review are recorded by the task's Git commit. No push is authorized.
