# Try-6.0-D1 KFDE–Exact Alignment & Clearance Witness Audit — L04

**Decision: `DIAGNOSTIC_INCONCLUSIVE`.** The frozen five-geometry/13-pose exact-mechanics alignment matrix could not be completed because the actual F0 coarse geometry has a zero-volume mutable-added BREP that the FreeCAD/OCC Boolean path treated as a non-cuttable Null shape. No alignment rate, false-positive rate, clearance-witness relief, or representation-capacity verdict is supported by this run.

## FACTS — frozen state and geometry availability

C1-v2 (`GO_C2`), C2 (`NO_FEASIBLE_CANDIDATE_UNDER_FROZEN_SEARCH`) and D0 (`DOMAIN_KFDE_INCOMPATIBLE`) results passed hash rechecks and were not modified. The exact FreeCAD classifier implementation, sanitized URDF, 13 KFDE component BREPs, allowed-contact BREP, tolerance, six-dimensional parameter domain and CAD compiler were frozen. D1 made **0 VLM calls**, **0 GT geometry evaluations**, **0 final 96-case mechanical evaluations**, and **0 formal holdout accesses**.

Five exact FCStd sources were present and opened during pre-run inspection: G1 C1 final, G2 D0 all-lower-bound P0, G3 D0 C1-initial P3, G4 historical Direct-Qwen L04, and G5 actual frozen F0/coarse L04. Their full/mutable volumes (mm³) were approximately G1 22852.28/18772.87, G2 10180.04/4053.22, G3 17276.75/13541.35, G4 17506.17/7808.04, and G5 9698.13/**0**. G4 and G5 mutable scope is derived by exact subtraction of the frozen allowed region from the full link, rather than by an original parametric body object; this scope ambiguity was preregistered. No six-parameter F0 theta was fabricated.

The protocol preregistered 65 geometry/pose comparisons, a descriptive ≥0.9 alignment threshold, material false-positive criteria, and nine fixed witness subsets with 5%/15% relief and 80% localization thresholds. Those thresholds were not modified after attempting execution.

## FACTS — retained technical incident and stop

The first alignment process exited at `mutable.cut(allowed)` on G5 with `ValueError: Null shape` before a complete 65-row result table existed. Its traceback was committed in `3a33ca3`. A narrowly scoped code guard for `mutable.isNull()` was recorded along with a **single** permitted technical retry; the retry also failed at G5 because the deserialized F0 mutable BREP was *not* reported as Null yet had no cuttable volumetric solid. Its traceback remains in `alignment/failure.json`; `technical_retry_started.json` hashes the first failure. The scientific geometry set, URDF poses, existing exact classifier, KFDE/allowed region and thresholds were unchanged. There was **no third same-version retry**.

No complete alignment table, per-neighbor/pose rates, or F0 exact-mechanics authority comparison was written. The process may have computed earlier cases internally, but without a complete retained denominator they cannot substantiate an alignment claim. Because this critical same-geometry/pose mapping failed, the preregistered witness phase was **not run**. Thus original/witness mutable volume ratio, connectivity, interface effects, localization, per-neighbor relief and six-DOF expressibility are all **not evaluable**. No STEP/STL diagnostic witness or C2 candidate was created.

## INTERPRETATION

This is an implementation/auditability failure, **not** evidence that KFDE is mechanically aligned, misaligned, or that a local relief feature/topology redesign is needed. The actual F0 coarse body was available, but its mutable-added part is exactly zero after the frozen scaffold/interface exemption; FreeCAD represented that empty result in a way the D1 diagnostic Boolean path did not safely handle. An independently versioned technical audit would need to treat both `isNull()` and zero-volume/no-solid BREPs as empty without changing KFDE or exact taxonomy. D1 itself stops at the preregistered retry limit.

## NOT SUPPORTED / STOP

D1 does **not** establish C2 geometry or mechanical improvement, KFDE incremental benefit, Try-6.1 readiness, a KFDE semantics verdict, representation-capacity verdict, manufacturing readiness or formal-holdout performance. No KFDE redesign, relief feature, KFDG edit, C2-v2, GT geometry, full 96-case mechanics, L03/L07 experiment or formal-holdout access followed.
