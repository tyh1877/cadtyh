# Try-5B.1-A2a: Three-Link Same-Model Structured-vs-Direct VLM

Status: **FORMAL DEVELOPMENT COMPARISON COMPLETE WITH TWO STRUCTURED SCHEMA FAILURES**

Independent integrity audit: **PASS, 20/20 checks**. The 32-case formal
holdout remains `accessed=false`, `evaluation_count=0`.

## A. EXPERIMENT INTEGRITY

All six one-shot Qwen generations returned normally. Four candidates built
and received the full 96-case Exact and geometry evaluations. Structured-Qwen
on L04 and L07 returned an executable schema field of the wrong type and was
retained as a formal method failure. Each failure keeps the requested 96 cases
in failure accounting; no uncomputed metric is imputed.

Both conditions used `qwen3.7-plus`, temperature 0, top-p 1, seed 20260923,
one model call, zero refinement rounds, a 32768 output-token ceiling, a
300-second timeout, SDK retries 0, and manual intervention 0. All six returned
the requested model identifier. The provider supplied no `system_fingerprint`,
so an immutable backend snapshot is unavailable.

The L04 audited shared, Structured, and Direct prompt templates retain their
SHA-256 hashes; only the Link ID and Link-specific raw F0/interface evidence
were substituted. Within each Link, both methods received identical shared
text and 12 image attachments. Both used the same canonical FreeCAD worker,
protected-interface policy, frozen scaffold, 96 development configurations,
Link-specific joint sweeps, Exact evaluator, and geometry evaluator. GT entered
only the evaluator. There were no transport retries, result-conditioned
retries, model-output repairs, or CAD edits.

No generation infrastructure failure occurred. Two post-run analysis tools
needed mechanical corrections: one process aggregate had excluded the two
failed Structured runs, and the independent validator mistook
`no_overall_score` for `overall_score`. Both corrections used the already
frozen records; neither added a model, CAD, or evaluator run.

## B. PAIRED RESULTS

`—` denotes an uncomputed value after a one-shot method failure.

| Link | Method | Final IoU | Silhouette | nChamfer ↓ | nHD95 ↓ | BICR | Solids | JR3 | GCFR | Collisions | Intersection mm³ | Failed configs | Input tokens | Output tokens | Model latency s | End-to-end s | Build |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| L03 | Structured | 0.252802 | 0.579243 | 0.054152 | 0.135392 | 0 | 2 | 0 | 0.281250 | 122 | 73635.29 | 69 | 15725 | 2722 | 50.17 | 208.22 | yes |
| L03 | Direct | 0.427335 | 0.665299 | 0.043175 | 0.126408 | 1 | 1 | 0 | 0.093750 | 152 | 72144.66 | 87 | 15685 | 5947 | 104.48 | 270.58 | yes |
| L04 | Structured | — | — | — | — | — | — | — | — | — | — | — | 15715 | 4282 | 75.33 | 75.33 | no: schema |
| L04 | Direct | 0.124970 | 0.301745 | 0.116574 | 0.295043 | 1 | 1 | 1 | 0.729167 | 50 | 26393.01 | 26 | 15675 | 3867 | 69.77 | 220.09 | yes |
| L07 | Structured | — | — | — | — | — | — | — | — | — | — | — | 16526 | 3011 | 54.98 | 54.98 | no: schema |
| L07 | Direct | 0.089706 | 0.235298 | 0.095537 | 0.352333 | 1 | 1 | N/A | 0.916667 | 32 | 12266.58 | 8 | 16486 | 2389 | 44.17 | 178.55 | yes |

The full six-run table, including bbox/dimension errors and failure IDs, is
saved in `paired_main_table.csv` and `run_records.json`.

For the only fully evaluable pair, L03 Structured−Direct is: IoU −0.174533,
silhouette −0.086057, nChamfer +0.010977, nHD95 +0.008984, BICR −1,
GCFR +0.187500, collision events −30, and intersection volume +1490.63 mm³.
The geometry/mechanical mean and median deltas therefore both equal this one
L03 value and have **n=1 of 3 requested pairs**. Process token/latency deltas
are computed over all **n=3** call pairs. No overall score is defined.

## C. GEOMETRY FINDINGS

On L03, Direct outperformed Structured on all four frozen final-link geometry
metrics. L04 and L07 have no paired geometry result because Structured schema
validation failed. Therefore the L04 pilot observation of a Structured
geometry advantage did not replicate as a valid formal L04 pair, and the
three-link data cannot establish either method's cross-link geometry
superiority. Body-only/full-link-GT values remain diagnostic only.

## D. MECHANICAL FINDINGS

On L03, Direct formed one connected solid and reached BICR 1; Structured
produced two solids and BICR 0 despite receiving the same scaffold safeguard.
Both have aggregate relevant JR3 0. At J03 specifically, Structured reached
1/3 sampled poses and Direct 0/3. Structured had better 96-case GCFR
(27/96 versus 9/96) and fewer collision events (122 versus 152), while Direct
had slightly lower summed intersection volume. Thus neither method dominates
L03 mechanics. L04 and L07 Direct results have no paired mechanical comparator.

## E. PROCESS FINDINGS

Model responses succeeded in 6/6 calls, but CAD/evaluation completion was
Structured 1/3 and Direct 3/3. The two Structured failures happened before
FreeCAD execution: `major_recess` was an object where the frozen schema
validator requires a Boolean. Direct code execution failures, FreeCAD build
failures, invalid built CAD attempts, transport failures, and manual edits were
all zero. Actual input/output token use and per-run latency are in the main
table. Structured's shorter average end-to-end time is caused by its two early
failures and is not evidence of a faster successful workflow.

Across all three call pairs, Structured−Direct input-token delta has mean and
median +40; output-token delta has mean −729.33 and median +415. Model latency
delta has mean −12.64 s and median +5.56 s. These process statistics include
the two Structured outputs that failed schema validation. End-to-end runtime
comparisons must retain that failure context.

## F. FAILURE MODES

- **L03 Structured:** Qwen selected `central_web` with `span_mm=126` and no
  lateral offset. The compiler consumed that schema, and the final assembly
  had two solids. Exact rows show many L03–L04 (55) and L02–L03 (34)
  collision events; J02 JR3=0, J03 JR3=1/3. The generated load path and
  motion envelope remain insufficiently constrained.
- **L03 Direct:** The verbatim generated code used a rectangular bar and two
  cylinder rings with FreeCAD's default cylinder axis, while the frozen joint
  axes are Y. The body was large (about 67,256 mm³); Exact rows include
  L03–L04 (82) and L02–L03 (38) collisions. It achieved stronger geometry
  and BICR but J02/J03 JR3=0 and GCFR 9/96.
- **L04 Structured:** Qwen chose `compound_profile_housing` but supplied
  `major_recess` as a nested location/diameter/depth object. The frozen
  compiler contract expects a Boolean. No Structured CAD or mechanical metric
  exists for this run. The prompt exposed the field name without its Boolean
  type, which is a concrete IR-interface weakness.
- **L04 Direct:** The generated FreeCAD code used a beam and cylindrical hubs.
  It built and reopened; BICR=1, J03 JR3=1, GCFR=70/96, with 50 Exact
  collisions. Geometry remains coarse (IoU 0.124970), but no execution
  failure occurred.
- **L07 Structured:** Qwen again chose `compound_profile_housing` and returned
  a nested `major_recess` object. The same frozen schema contract rejected
  it before CAD. The family choice and schema were preserved as response
  evidence, not rewritten to a gripper family.
- **L07 Direct:** The code built a spool from cylinders and end disks; the raw
  body had two solids, while the shared scaffold yielded a valid final
  one-solid link. Its final IoU is 0.089706 and silhouette 0.235298,
  consistent with a coarse primitive representation. GCFR is 88/96; L07 has
  no relevant moving joint, so JR3 is N/A.

## G. CROSS-LINK PATTERN

**MIXED / INCONCLUSIVE.** Direct had stronger execution stability (3/3 versus
1/3), and it won all four geometry metrics on the sole complete L03 pair.
Structured had better L03 GCFR and collision count but worse L03 BICR and
intersection volume. Two failed Structured schemas leave no L04/L07 paired
geometry or mechanics. The evidence does not establish Patterns A, B, C, or D
as a general cross-link performance law.

## H. FACTS

Six frozen calls returned the same model identifier with no retry. Four
candidates were fully evaluated over 96 development cases each. Structured
failed schema validation on L04 and L07. Direct built and evaluated all three
Links. Only L03 permits a numerical paired geometry/mechanics comparison. The
formal holdout lock remains untouched.

## I. INTERPRETATION

The current Structured IR plus compiler pathway has a reliability bottleneck
at the typed schema boundary. Its L03 parameterization also lacks sufficient
motion-aware constraints. Direct generation can represent L03's visible shape
well, yet its unconstrained hub construction caused severe motion collisions.
The present data support improving both schema contract reliability and
kinematic design-space control before drawing an algorithmic superiority
claim.

## J. NOT_SUPPORTED

This experiment does not support a formal holdout conclusion, Robot B/C
generalization, manufacturing conclusions, Try-6 superiority, universal
Structured superiority, or a three-link geometry/mechanics mean over failed
pairs. The provider returned no immutable backend fingerprint.

## Try-6 DESIGN IMPLICATIONS

1. Retain frozen interface authority, the shared scaffold safeguard, explicit
   input/provenance manifests, and independent Exact evaluation.
2. Treat the current narrow typed Body Family schema as a likely execution
   bottleneck; `major_recess` object failures show the prompt–validator
   contract is underspecified.
3. Geometry and mechanics conflict at the joint motion envelope: L03 Direct
   has the better outer shape while both methods fail relevant JR3, and
   Structured L03 still has disconnected solids.
4. First improve typed IR validation and motion-aware parameter bounds. Do
   not enlarge the old family taxonomy solely on this incomplete comparison.

Historical Frozen Try-5 remains a separate context record. It is not included
in this same-model comparison. No Try-6 code was changed.
