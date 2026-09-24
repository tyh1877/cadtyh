# Try-6.0-D1-W1 — Engineering-Scale Clearance Witness Validation

**Decision: `WITNESS_NUMERICALLY_UNSTABLE`; not `READY_FOR_D1_V3`.** All nine frozen subsets were constructed with both W0-declared paths, twice each, and reopened from BREP and FCStd. Eight satisfy every W1 gate. L07 produces valid, spatially contained, keepout-free, repeatable geometry, but its measured relief is negative beyond the W1 *preregistered* near-zero normalization rule. We retain that failed gate rather than changing it after observing L07.

## Frozen integrity and validation policy

C1-v2 geometry, KFDE components, allowed regions, D1 thresholds and nine subset IDs, T0 classifier, W0 result, and D1-v2 65-row alignment stayed unchanged. W1 did not rerun alignment. VLM, GT, final 96-case mechanics and formal-holdout evaluations were all zero; the holdout lock remains `accessed=false`, `evaluation_count=0`.

W1 is a new technical protocol, not a relabeling of W0's `BOOLEAN_ACCOUNTING_BLOCKED` result. The hard gates are valid exact BREP, `W\G` within W0's synthetic-calibrated source-exterior limit, `W∩K` within the frozen KFDE `1e-6 mm³` penetration limit, two-path/repeat/reopen stability, topology stability and unchanged frozen interfaces. `|[V(G)-V(W)]-V(G∩K)|` is recorded as diagnostic only. The paths and the additional 0.001 maximum relief-interval width were registered before this real run. The 5% and 15% category thresholds are the original D1 values.

## Nine-subset results

All PATH_A and PATH_B raw BREPs are valid. All memory/reopened source-exterior and keepout residuals are `0 mm³`; repeatability, BREP/FCStd parity and frozen interface signatures pass for all nine. Solid counts and topology classes are stable across paths, repeats and reopen.

| Subset | Solids A/B | Relief A / B | Numerical interval | Frozen category | W1 status |
|---|---:|---:|---:|---|---|
| FULL | 3 / 3 | 9.8982914% / 9.8982928% | 9.8982914–9.8982928% | Moderate, robust | PASS |
| L03 | 1 / 1 | 0.9794105% / 0.9794105% | 0.9794105–0.9794105% | Small, robust | PASS |
| L05 | 1 / 1 | 3.4985988% / 3.4985988% | 3.4985988–3.4985988% | Small, robust | PASS |
| L06 | 1 / 1 | 5.5341182% / 5.5341182% | 5.5341182–5.5341182% | Moderate, robust | PASS |
| L07 | 1 / 1 | −0.00000284% / −0.00000284% | −0.00000284–−0.00000284% | Not measurable under frozen rule | **NUMERICALLY UNSTABLE** |
| L03_L05 | 1 / 1 | 4.4780093% / 4.4780093% | 4.4780093–4.4780093% | Small, robust | PASS |
| L03_L06 | 1 / 1 | 6.5135289% / 6.5135289% | 6.5135289–6.5135289% | Moderate, robust | PASS |
| L05_L06 | 3 / 3 | 8.9188830% / 8.9188844% | 8.9188830–8.9188844% | Moderate, robust | PASS |
| L03_L05_L06 | 3 / 3 | 9.8982914% / 9.8982928% | 9.8982914–9.8982928% | Moderate, robust | PASS |

The intervals include both paths, two repeats and BREP/FCStd reopen values; they are **numerical sensitivity intervals, not statistical confidence intervals**. No interval among the eight usable subsets crosses 5% or 15%. None changes connected/disconnected classification. Full per-subset volumes, residuals, accounting errors, source-relative and relief-relative discrepancy ratios appear in `summary/witness_engineering_metrics.csv` and each `witnesses/<subset>/path_records.json`.

The W0-style volume-additivity discrepancy persists as a diagnostic: for FULL it is `0.007722 mm³` in PATH_A and `0.007540 mm³` in PATH_B. It does not alter FULL's 5%/15% category or three-solid topology. Optional `removeSplitter()` failed on several valid raw witnesses, including FULL, and succeeded on others; canonical validity never depended on cleanup.

## L07 limitation

Both paths report L07 witness volume **13,154.148555 mm³** versus source **13,154.148181 mm³**: a `+0.000374 mm³` measurement difference, or `2.84×10⁻⁸` of the source. Both path results are identical, valid, contained, keepout-free, repeatable and reopen-stable. Physically this is far from a 5% category boundary. But the preregistered W1 near-zero rule allowed a negative `V(G)-V(W)` only within the older W0 synthetic-calibrated volume stability limit (about `1.33×10⁻⁶ mm³` at this source scale). L07 exceeds that rule, so W1 cannot declare its relief ratio measurable or all nine usable.

The raw worker called this `WITNESS_CONSTRUCTION_BLOCKED` because the numeric guard raised an exception after all four valid L07 samples existed. The independent result audit corrected **the label only** to `WITNESS_NUMERICALLY_UNSTABLE`, preserving the raw status and every BREP. This is not a CAD-construction failure and no rerun occurred. The near-zero rule appears overconservative for W1's stated engineering-scale question; however, revising it now would be result-conditioned. A new preregistered W1 version would be required to test a scale-aware zero-relief rule.

## Evidence and unsupported conclusions

Pure category/topology unit tests: 7/7 pass. Named W1 gate ledger: 18/19 pass, with `all_nine_usable=false`. Independent result-integrity validation: 24/24 pass, confirming the blocked decision rather than technical readiness. This W1 result does **not** establish KFDE semantic correctness or misalignment as a final verdict, local relief need, topology insufficiency, C2 performance, Try-6.1/manufacturing readiness or formal-holdout performance. No localization or six-DOF expressibility analysis was performed.

Evidence: `summary/witness_engineering_metrics.csv`, `summary/relief_sensitivity_intervals.csv`, `summary/topology_stability.json`, `witnesses/L07/sensitivity.json`, `audit/raw_to_audited_status.json`, `failure_accounting.json`, and `audit/independent_validation.json`. Heavy BREP/FCStd files are kept under ignored `experiments/try6/artifacts/try6_0_d1_w1/` with hashes recorded in the path records.
