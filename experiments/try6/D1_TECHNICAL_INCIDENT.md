# D1 alignment technical incident (pre-results)

The first 5×13 alignment process exited before writing any complete alignment
table. The retained traceback is in `results/try6_0_d1/alignment/failure.json`:
`ValueError: Null shape` at `mutable.cut(allowed)` for the actual F0 coarse
geometry. The frozen allowed-region subtraction produces a Null mutable-added
BREP for F0. This is an exact zero-volume case and must remain one of the five
geometry denominators, not be omitted or converted to a CAD candidate.

Only the diagnostic worker's Null guard was added: Null mutable addition is
represented as an empty `Part.Shape`, yielding zero KFDE-added intersection.
The wrapper now permits exactly one recorded technical retry after this
specific incomplete attempt. The first failure artifact is retained and hashed
by `technical_retry_started.json`; no completed alignment rates were seen or
used to edit the method. Geometry sources, all 13 poses, URDF/FK, frozen KFDE,
allowed contact, thresholds, existing exact mechanical classifier, witness
rules, GT prohibition, and holdout lock are unchanged. If the recorded retry
fails, D1 is `DIAGNOSTIC_INCONCLUSIVE`; no further same-version retry.
