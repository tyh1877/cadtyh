# Try-5B.1-A1 Protection Effect Audit

Status: **AUDIT_COMPLETE_FORMAL_NOT_RUN**

Validation: **PASS**

Recommendation: **REFRAME_AS_SCAFFOLD_ABLATION**

No 96-case mechanical evaluation, GT evaluation, formal holdout access, repair,
rejection, rollback, or three-link formal run occurred.

## 1–3. Per-link effects

| Link | Operation | Applicable | Executed | Result | ΔVolume mm³ | Symmetric difference mm³ |
|---|---|---|---|---|---:|---:|
| L03 | Proximal protected bore/corridor cut | yes | yes | EXECUTED_BUT_NO_OP | 0 | 0 |
| L03 | Proximal mating-envelope cut | yes | yes | EXECUTED_BUT_NO_OP | 0 | 0 |
| L03 | Distal rotary/interface clearance cut | yes | yes | EXECUTED_BUT_NO_OP | 0 | 0 |
| L03 | Frozen scaffold preservation/fusion | yes | yes | GEOMETRY_EFFECTIVE | +11448.2198 | 11448.2197 |
| L03 | Auto attachment closure | no | no | NOT_APPLICABLE | 0 | 0 |
| L04 | Proximal protected bore/corridor cut | yes | yes | EXECUTED_BUT_NO_OP | 0 | 0 |
| L04 | Proximal mating-envelope cut | yes | yes | EXECUTED_BUT_NO_OP | 0 | 0 |
| L04 | Distal rotary/interface clearance cut | no | no | NOT_APPLICABLE | 0 | 0 |
| L04 | Frozen scaffold preservation/fusion | yes | yes | GEOMETRY_EFFECTIVE | +6567.3066 | 6567.3072 |
| L04 | Auto attachment closure | no | no | NOT_APPLICABLE | 0 | 0 |
| L07 | Proximal protected bore/corridor cut | no | no | NOT_APPLICABLE | 0 | 0 |
| L07 | Proximal mating-envelope cut | no | no | NOT_APPLICABLE | 0 | 0 |
| L07 | Distal rotary/interface clearance cut | no | no | NOT_APPLICABLE | 0 | 0 |
| L07 | Frozen scaffold preservation/fusion | yes | yes | GEOMETRY_EFFECTIVE | +1321.4811 | 1321.4811 |
| L07 | Auto attachment closure | no | no | NOT_APPLICABLE | 0 | 0 |

## 4–5. No-op and effective operations

Five operations were `EXECUTED_BUT_NO_OP`: all three applicable cuts on L03
and both applicable proximal cuts on L04. L03's first bore/corridor cut changed
the serialized B-Rep hash, but exact symmetric-difference volume, total volume,
bbox, solid count, and face/edge/vertex counts remained unchanged. It is
therefore a representation rewrite, not a geometric effect.

Exactly three operations were `GEOMETRY_EFFECTIVE`: frozen scaffold fusion on
L03, L04, and L07.

## 6–8. Mechanism-level conclusions

Frozen scaffold preservation is the only consistently effective mechanism and
is effective on 3/3 links. Protected cuts are effective on 0/3 links, not at
least 2/3. Auto attachment closure participates on 0/3 links because the
current constrained path selects scaffold preservation first; it is not an
active component of the current C1 treatment.

## 9. New confound

The previous `C1_CONSTRAINED` label bundled four flags, but in the frozen F2
geometry only scaffold preservation changes the solid region. Calling the
experiment a general mechanical-geometry-protection ablation would therefore
misattribute the observed effect to inactive cut and closure mechanisms.

The historical L04 dry-run JSON retains its original field names for immutable
provenance. The canonical evaluator now emits `sample_count` and
`all_samples_pass`; no current evaluator code emits `holdout_samples`.

## 10. Recommendation

**REFRAME_AS_SCAFFOLD_ABLATION**.

If the paper experiment proceeds later, the independent variable should be
described narrowly as frozen scaffold preservation/fusion. It should not claim
to estimate protected-cut or auto-attachment-closure effects under the current
F2 schemas. This audit does not authorize or execute the formal run.
