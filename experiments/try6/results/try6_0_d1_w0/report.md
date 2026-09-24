# Try-6.0-D1-W0 — Clearance Witness Boolean Reliability Audit

**Decision: `BOOLEAN_ACCOUNTING_BLOCKED`.** Synthetic calibration passed, but the first frozen real subset (`FULL`) failed the previously frozen Boolean accounting tolerance. The prescribed fail-closed rule stopped the remaining eight subsets. W0 does **not** establish `READY_FOR_D1_V3`.

## Facts

- C1-v2 CAD, D1-v2 65-row table, KFDE component/allowed-region BREPs, URDF, Exact taxonomy, T0 classifier, D1 thresholds and nine subset definitions remained frozen. No alignment recomputation, GT, VLM, final 96-case mechanics or formal-holdout access occurred. Holdout remains `accessed=false`, `evaluation_count=0`.
- Before opening a real witness, eight synthetic exact-BREP cases were run for two preregistered paths, three identical repeats each (48 records). Maximum absolute error was `2.274e-13 mm³`; serialize/reopen and repeatability passed. The independent Boolean accounting rule was frozen as **`1e-8 mm³ + 1e-10 × max(1, source volume in mm³)`**. This is not the frozen KFDE feasibility epsilon of `1e-6 mm³` and was not changed after the real failure.
- The canonical path was selected before real data: exact OCC union of the relevant frozen components in frozen order, followed by one cut of the *mutable-only* C1 BREP. Ordered sequential cuts were declared as an independent corroboration path. Neither path uses `removeSplitter()` to define the witness.
- For FULL, the exact keepout union is valid and BREP round-trip stable: **79,381.321501 mm³**. The sum of individual component volumes is **128,564.108977 mm³**; that sum was never used as removed volume, avoiding overlap double counting.

| FULL technical path | Source mutable mm³ | Witness mm³ | Unique `G∩K_union` removed mm³ | `W∩K` mm³ | Accounting error mm³ | Frozen limit mm³ |
|---|---:|---:|---:|---:|---:|---:|
| Union then single cut | 13,154.148181 | 11,852.112266 | 1,302.043637 | 0 | 0.007722 | 0.000001325 |
| Ordered sequential cut | 13,154.148181 | 11,852.112084 | 1,302.043637 | 0 | 0.007540 | 0.000001325 |

Both paths produced valid three-solid exact BREPs, zero material outside the source, zero residual keepout intersection, identical results across two repeats, and passing BREP and FCStd reopen parity. Both exceed the frozen accounting limit; the canonical error is about 5,826× the limit. The two mathematically intended-equivalent paths also disagree in witness volume by about `0.000182 mm³`, above the same limit. These are technical failures, not reasons to switch paths or increase tolerance.

`removeSplitter()` again raised `Bnd_Box is void` on valid raw multi-solid witnesses. Its failure is isolated to optional cleanup and does not by itself invalidate the raw BREP. Nevertheless, raw BREP validity and serialization stability do **not** cure the failed volume invariant. The exact internal OCC/topological cause is not established. The discrepancy is systematic across repeats and both paths; it is not explained by summing overlapping components or by serialization. D1-v2's earlier accounting also mixed pre-allowed source with a re-fused preserved/mutable assembly; W0 removed that scope mixture, yet a smaller material inconsistency remains.

## Nine-subset accounting

`FULL` was attempted and failed Boolean accounting. `L03`, `L05`, `L06`, `L07`, `L03_L05`, `L03_L06`, `L05_L06`, and `L03_L05_L06` were **not run after the fail-closed stop**. No technical witness from W0 is accepted for D1-v3 science. Frozen scaffold/interface BREP signatures and the source FCStd hash remained unchanged. No dummy or surrogate geometry was introduced.

The named technical test ledger records **18/20** passing checks; the failing checks are removed-volume consistency and exact nine-subset completion. An independent audit passed **20/20 evidence-integrity checks** and confirmed the blocked decision, not technical readiness.

## Interpretation and limits

W0 establishes that exact OCC BREP generation, union serialization, optional cleanup handling and state classification can be stable while Boolean volume additivity still fails on the real FULL input. It does not establish why the discrepancy arises inside OCC, and it does not support changing the frozen tolerance. A new preregistered technical investigation would be needed before any D1-v3 rerun.

**Not supported:** KFDE semantic alignment or false-positive cause; local relief need; topology insufficiency; C2 performance; Try-6.1, manufacturing or formal-holdout readiness.

Evidence: `calibration/tolerance_calibration.json`, `union/union_report.json`, `construction_paths/path_comparison.csv`, `witness_technical/FULL/path_records.json`, `failure_audit/volume_consistency_analysis.json`, `failure_accounting.json`, `tests/test_report.json`, and `audit/independent_validation.json`. Heavy BREP/FCStd artifacts and raw FreeCAD logs remain under ignored `experiments/try6/artifacts/try6_0_d1_w0/` with hashes in the manifest.
