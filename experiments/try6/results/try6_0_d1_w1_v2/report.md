# Try-6.0-D1-W1-v2 — Scale-Aware Zero-Relief Validation

**Technical decision: `READY_FOR_D1_V3`.** A fresh nine-subset run using the unchanged W1 FreeCAD worker and the same two exact-BREP paths passed the spatial, repeat/reopen, topology and interface gates. The only changed rule is a preregistered, per-measurement normalization of tiny **negative** relief after those hard gates pass. This is witness-infrastructure readiness, not a D1 scientific verdict; D1-v3 was not run.

## Frozen-state integrity and zero rule

W0 remains `BOOLEAN_ACCOUNTING_BLOCKED`; W1 remains `WITNESS_NUMERICALLY_UNSTABLE`. C1-v2 geometry, KFDE/allowed BREPs, nine witness subsets, PATH_A/PATH_B implementations, the D1 5%/15% category thresholds, and D1-v2's frozen 65-row alignment result were unchanged. No alignment, localization, capacity, GT, VLM, final 96-case mechanics or formal-holdout evaluation was run. Holdout remains `accessed=false`, `evaluation_count=0`.

Before the fresh real run, W1-v2 froze:

`epsilon_zero = max(epsilon_abs, 1e-6 × V_source)`, with `epsilon_abs = 1e-8 mm³` copied from W0's synthetic calibration. The negative boundary is inclusive: `-epsilon_zero ≤ V(G)-V(W) < 0` becomes zero, but a negative value below that band fails; **every nonnegative value is retained**. The `1e-6` relative factor is `0.0001%` of source volume—50,000 times below the first 5% relief boundary. Nine pre-run synthetic/threshold tests passed. For the frozen C1 mutable source, `epsilon_zero = 0.013154148181 mm³`.

Normalization was applied only after independent exact-BREP validity, `W\G`, `W∩K`, repeatability, BREP/FCStd reopen, topology and interface checks passed. It changed **zero geometry** and did not relax the KFDE `1e-6 mm³` keepout-penetration limit or the W0-calibrated source-exterior limit. Volume additivity discrepancy remains visible but diagnostic, as in W1.

## Nine fresh witness subsets

Both paths built valid BREPs for all nine; each path was repeated twice, and each result reopened from BREP and FCStd. Every source-exterior and keepout residual was `0 mm³`; all geometry states, solid counts, bbox/volume/remainder checks and frozen interface signatures were stable. All complete numerical relief intervals stay within one frozen category—none crosses 5% or 15%—and no connected/disconnected class changes.

| Subset | Raw relief A / B | Normalized relief A / B | Category | Solids A/B | Zero-normalized measurements |
|---|---:|---:|---|---:|---:|
| FULL | 9.8982914% / 9.8982928% | unchanged | Moderate, robust | 3/3 | 0/12 |
| L03 | 0.9794105% / 0.9794105% | unchanged | Small, robust | 1/1 | 0/12 |
| L05 | 3.4985988% / 3.4985988% | unchanged | Small, robust | 1/1 | 0/12 |
| L06 | 5.5341182% / 5.5341182% | unchanged | Moderate, robust | 1/1 | 0/12 |
| L07 | −0.00000284% / −0.00000284% | **0% / 0%** | Small, robust; engineering zero | 1/1 | **12/12** |
| L03_L05 | 4.4780093% / 4.4780093% | unchanged | Small, robust | 1/1 | 0/12 |
| L03_L06 | 6.5135289% / 6.5135289% | unchanged | Moderate, robust | 1/1 | 0/12 |
| L05_L06 | 8.9188830% / 8.9188844% | unchanged | Moderate, robust | 3/3 | 0/12 |
| L03_L05_L06 | 9.8982914% / 9.8982928% | unchanged | Moderate, robust | 3/3 | 0/12 |

L07's fresh raw `V(G)-V(W)` is about `−0.000374 mm³`, inside the preregistered `0.013154 mm³` zero band. The same general rule was applied to all 108 individual memory/reopen measurements; L07 alone met its negative-in-band condition. It is flagged `ZERO_RELIEF_WITHIN_ENGINEERING_TOLERANCE` so future D1-v3 work does not mistake its Small category for measured positive relief. The other eight W1-pass categories, ratios within frozen technical parity, solid counts, topology and occupancy residuals stayed unchanged.

The numerical sensitivity intervals are *not* statistical confidence intervals. Complete raw and normalized values, intervals, per-path accounting discrepancies and source-/relief-relative discrepancy ratios are in `summary/raw_vs_normalized_relief.csv`, `summary/engineering_witness_metrics.csv` and each `witnesses/<subset>/path_records.json`. W0's near-exact volume-additivity failure is **not** reversed by W1-v2.

## Validation and limits

The named technical ledger passed **22/22** checks; nine synthetic zero-rule unit tests passed; the separate independent validator recomputed hashes, the rule and all 108 measurements and passed **27/27** gates. The validation discipline prevented a geometric pass or a tiny-looking L07 number from being treated as permission to adjust thresholds after the run.

**Not supported:** final KFDE semantic verdict, local relief feature need, topology insufficiency, C2 performance, Try-6.1/manufacturing readiness, or formal-holdout performance. W1-v2 stops here and awaits authorization for D1-v3 science.

Evidence: `zero_rule/rule.json`, `zero_rule/synthetic_tests.json`, `summary/engineering_witness_metrics.csv`, `summary/raw_vs_normalized_relief.csv`, `summary/w1_comparison.json`, `audit/zero_rule_audit.json`, and `audit/independent_validation.json`. Heavy fresh BREP/FCStd artifacts remain in ignored `experiments/try6/artifacts/try6_0_d1_w1_v2/`, with hashes in the tracked path records.
