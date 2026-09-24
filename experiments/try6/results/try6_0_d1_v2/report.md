# Try-6.0-D1-v2 — L04 KFDE–Exact Alignment & Clearance Witness Audit

**Decision: `DIAGNOSTIC_INCONCLUSIVE`.** Phase A completed all 65 frozen geometry/pose rows. The preregistered nine-subset clearance-witness phase completed **0/9**, so the D1-v2 completeness gate and representation-capacity question remain open. Do not promote the Phase A signal to a final KFDE-method verdict.

## Facts — frozen-state integrity

- Exact G1–G5 sources, 13 KFDE components/poses, sanitized URDF, allowed-contact/keepout BREPs, frozen 1e-6 mm³ tolerance, original D1 thresholds and witness subsets were used. C1-v2, C2, D0, D1-v1, and T0 historical result manifests remained unchanged. No incomplete D1-v1 row was reused.
- The same-geometry/same-pose mapping was frozen before execution and checked per row against FK-relative transforms and mutable overlap parity. The Exact classifier source was unchanged; T0 supplied the provenance-aware empty-BREP path. G5 full F0 remained a valid solid; its mutable-added scope was `EFFECTIVELY_EMPTY` and retained all 13 denominator rows without dummy geometry.
- VLM calls, GT evaluations, final 96-case mechanics, and formal-holdout evaluations were 0. The formal holdout remains `accessed=false`, `evaluation_count=0`.

## Facts — complete Phase A, descriptive only

| Neighbor | Cases | Aligned unsafe | Aligned safe | KFDE false-positive suspects | Non-ambiguous KFDE violations | Unsafe alignment rate |
|---|---:|---:|---:|---:|---:|---:|
| L03 / J03 | 35 | 5 | 23 | 7 | 12 | 5/12 = 41.7% |
| L05 fixed J04 | 5 | 0 | 1 | 4 | 4 | 0/4 = 0% |
| L06 / J05 | 20 | 0 | 4 | 16 | 16 | 0/16 = 0% |
| L07 fixed J06 | 5 | 0 | 5 | 0 | 0 | undefined |
| **Overall** | **65** | **5** | **33** | **27** | **32** | **5/32 = 15.625%** |

False-negative suspects: 0. Ambiguous rows: 0. The frozen descriptive `ALIGNMENT_HIGH ≥ 0.90` criterion is not met. This rate is not a general statistical precision estimate. The 27 suspects are row-level classifier outputs, not a final causal attribution while witness execution is incomplete.

For G5, the mutable KFDE state is empty and reports zero violation in 13/13 rows. The independent Exact full-link taxonomy reports `EXPECTED_INTERFACE_CONTACT` in 13/13 rows and no unintended collision, including positive full-link common volumes in some poses. Empty mutable scope is **not** a full-link authority contradiction; no `KFDE_AUTHORITY_INCONSISTENCY` claim is established.

## Facts — witness failure and denominator

The first FULL witness attempt reached a valid fused BREP but OCC's optional `removeSplitter()` failed with `Bnd_Box is void`. The first failure was preserved. A single explicit, recorded technical retry retained the valid raw fused BREP if splitter cleanup failed; it then failed the frozen removed-volume Boolean consistency check for FULL. No witness metric, STEP/STL result, localization, per-neighbor witness, or combined-subset conclusion was accepted. Failure accounting keeps all nine requested subsets as incomplete/failed; none is silently dropped or converted to a favourable zero.

The raw-fuse fallback is **not** accepted as a validated scientific witness. The second failure means its occupancy/Boolean consistency is unresolved. No third retry or threshold adjustment was made. Further technical work requires a separately frozen plan before D1 scientific rerun.

## Interpretation

The complete Phase A table raises a strong, specific concern about KFDE/Exact semantic alignment, especially L05 and L06 fixed/swept contacts. Because the required witness stage did not pass, D1-v2 does **not** settle whether D0's observed domain incompatibility is due to KFDE semantics, a localized clearance feature, or deeper parametric topology. The only admissible final decision under the frozen completeness rule is `DIAGNOSTIC_INCONCLUSIVE`.

## Not supported

This result does not establish a valid relief magnitude, connectedness, interface invariance after relief, six-theta expressibility, a `KINEMATIC_RELIEF_FEATURE_CANDIDATE`, C2 geometry/mechanics improvement, KFDE incremental benefit, Try-6.1 readiness, manufacturing readiness, or formal-holdout performance.

Evidence: `alignment/alignment_65_rows.csv`, `alignment/raw_alignment.json`, `alignment/alignment_summary.json`, `alignment/per_neighbor_alignment.json`, `authority/authority_summary.json`, `witness/failure.json`, `failure_accounting.json`, and `audit/independent_validation.json`. First-failure evidence is retained in commit `5a89ad1` and ignored technical artifact logs.
