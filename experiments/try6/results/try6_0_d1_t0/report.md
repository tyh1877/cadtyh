# Try-6.0-D1-T0 — Empty / Zero-Volume BREP Handling Audit

Decision: **READY_FOR_D1_V2**, technical readiness only. The independent validator passed 17/17 gates after 29/29 FreeCAD technical checks. This is not a D1-v2 alignment result and does not authorize automatic scientific rerun.

## Facts

- Historical D1-v1 remains `DIAGNOSTIC_INCONCLUSIVE`. Its incomplete alignment rows were not reused. Frozen C1-v2, C2, D0, D1 manifest hashes and all five source FCStd hashes remained unchanged. KFDE, CAD, exact mechanics, and evaluator code were not modified.
- Canonical states: `VALID_SINGLE_SOLID`, `VALID_MULTI_SOLID`, `EFFECTIVELY_EMPTY`, `NONVOLUMETRIC_ONLY`, `INVALID_BREP`. Missing/invalid fails closed. A Null or no-solid, at-most-1e-6 mm³ result is empty only with verified subtraction provenance. Shell/face-only geometry without that provenance is nonvolumetric. An actual valid solid remains volumetric even at or below 1e-6 mm³. This is the frozen C2/D1 tolerance, not a tuned replacement.
- State/volume/solid counts recomputed from exact frozen FCStd sources:

| Source | Full mm³ | Mutable mm³ | Mutable solids | Mutable state |
|---|---:|---:|---:|---|
| G1 C1 final | 22852.281154 | 18772.872456 | 1 | VALID_SINGLE_SOLID |
| G2 D0 P0 | 10180.039430 | 4053.216334 | 1 | VALID_SINGLE_SOLID |
| G3 D0 P3 | 17276.751262 | 13541.354554 | 1 | VALID_SINGLE_SOLID |
| G4 historical Direct | 17506.171013 | 7808.035067 | 6 | VALID_MULTI_SOLID |
| G5 actual F0 | 9698.134201 | 0 | 0 | EFFECTIVELY_EMPTY |

- All five full shapes are valid volumetric FreeCAD shapes. All five mutable states match their previously serialized frozen BREPs. G1, G4, G5, synthetic derived-empty, and normal-solid state/solid-count/volume pass serialize/reopen parity. Repeated classification within each path is deterministic. G1/G4 serialization changes the final floating digits of volume (at most 2.1e-11 mm³), far below the frozen tolerance; exact floating equality is not asserted.
- G5's full F0 is one valid solid, 9698.134201 mm³. The frozen allowed region is valid with two solids. Independently recomputed `full.cut(allowed)` has 0 solids and 0 volume; its in-memory and frozen serialized forms are valid, non-Null, no-solid shapes. Thus G5's *mutable scope*, not its full link, is legitimately empty. `full.common(allowed)` reports 0.000114894 mm³ more than `full.Volume`, a numerical inconsistency greater than the frozen epsilon. We do **not** call that an exact volume-conservation proof, nor increase epsilon; the provenance conclusion rests on the direct zero-solid/zero-volume subtraction residual and valid frozen inputs. The discrepancy is preserved in the audit as a caveat.
- A verified empty A returns the actual empty shape without calling OCC `.cut`; an empty B returns A unchanged. Invalid and unproven nonvolumetric shapes fail closed. No dummy solid, surrogate, or inflated geometry was created. For the 13 frozen KFDE component IDs, the technical row helper retains 13 explicit zero-intersection, non-violation rows with `EMPTY_MUTABLE_GEOMETRY`. This is a row-contract check, **not** the 65-row scientific alignment computation. Empty mutable witness volume/removal are zero; ratio and mutable-carrier connectivity are `NOT_APPLICABLE_EMPTY_MUTABLE`, not numeric zero.
- Synthetic fixtures include Null (with and without derivation provenance), single solid, multi-solid compound, exact subtraction-empty, face-only, positive solids at 0.5/1/2 × epsilon, and corrupt BREP text. FreeCAD reads the corrupt text into an invalid/no-content shape rather than necessarily throwing; the classifier rejects it. The preliminary 27/29 technical attempt is retained under ignored artifacts; its two failures led to corrected test expectations, not a tolerance or geometry adjustment. One explicit technical retry passed 29/29.
- VLM calls, GT evaluations, 96-case final mechanics evaluations, D1-v2 alignment rows, and scientific witness runs: all 0. Formal holdout lock remains `accessed=false`, `evaluation_count=0`.

## Interpretation

The old G5 crash can be avoided through a general, provenance-aware empty-state classifier and central safe Boolean path. G5 can remain in a future complete D1-v2 denominator without inventing geometry. The `READY_FOR_D1_V2` label means only that this technical obstruction has a tested handling contract; D1-v2 must be separately authorized and run unchanged scientifically.

## Not supported

No conclusion is supported here about KFDE alignment or false-positive rate, F0 authority contradiction, local relief, topology insufficiency, C2 performance, Try-6.1 readiness, manufacturing, or formal holdout performance.

Evidence: `geometry_state/g1_g5_states.json`, `provenance/g5_provenance_audit.json`, `boolean_safety/operation_results.json`, `roundtrip/parity_report.json`, `tests/test_report.json`, and `audit/independent_validation.json`. Heavy roundtrip BREPs and raw FreeCAD logs remain in ignored `experiments/try6/artifacts/try6_0_d1_t0/`.
