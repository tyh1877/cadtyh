# Try-5B.1-A1 Mechanical Geometry Protection Ablation — L04 dry run

Status: **DRY_RUN_COMPLETE_FORMAL_NOT_RUN**
Independent integrity review: **PASS_WITH_DISCLOSED_LIMITATIONS**

## A. Baseline reproduction

The original C1/F2 three-link baseline reproduced at commit
`1c50c96f5bb57da2c50b5bf6d32b309ee3ac054a`. L03/L04/L07 raw-body and
interface signatures, attachment state, solid counts, and STL SHA-256 values
matched exactly. All 96 Exact rows and per-joint results matched; both runs had
88/96 valid configurations and GCFR 0.9166667.

## B. Modified files and execution design

The canonical FreeCAD refinement worker now accepts a four-field
`mechanical_geometry_policy`, emits execution traces and body-only STL, and can
stop after frozen-candidate generation. The existing independent FreeCAD
evaluator then measures both frozen conditions. A small evaluator-only geometry
entrypoint evaluates body-only and final-link STL with the unchanged metric
implementation. No pipeline, body-family compiler, or mechanical evaluator was
copied, and no runtime acceptance/rollback controller is used.

## C–D. Evaluator integrity

Real computed main metrics are BICR/connected-solid attachment validity,
relevant JR3, GCFR, Exact collision events/intersection volume, and failed
configuration IDs. Legacy `swept_clearance_preserved`,
`forbidden_fusion_count`, `virtual_solid_count`, and
`meaningless_patch_count` values are declarative or non-primary and are removed
from A1 quantitative analysis.

## E. Geometry scopes

Both conditions use the same deterministic evaluator and seed for:

1. `refined_body_only`: the post-cut executable F2 body exported separately;
2. `final_assembled_link`: the actual final link group placed in the robot.

No evaluator-only GT body segmentation exists, so both predictions are scored
against the same full-link GT mesh. Body-only values are therefore paired
diagnostics, not absolute body-segmentation accuracy.

## F. Input parity

Parity is **PASS**. Images, URDF, pilot set, L04 F2 family/schema,
VisualEvidencePack, Semantic Inventory, Mechanical Topology, seed, evaluator,
96 coupled configurations, and J03 sweeps have shared hashes. There are zero
unexpected differences and zero serialized holdout IDs. Only the four declared
`mechanical_geometry_policy` flags differ.

## G. L04 raw results

| Metric | C1 constrained | C2 unprotected |
|---|---:|---:|
| BICR / attachment | 1.0 / pass | 0.0 / fail |
| Connected solids | 1 | 3 |
| J03 JR3 (3 samples) | 1.0 | 1.0 |
| GCFR | 0.916667 | 0.916667 |
| Exact collision events | 31 | 31 |
| Exact intersection volume mm³ | 14953.6387 | 13207.8146 |
| Failed configurations | 8 | 8 |
| Body-only voxel IoU | 0.089439 | 0.089439 |
| Body-only silhouette IoU | 0.255422 | 0.255422 |
| Body-only nChamfer | 0.119873 | 0.119873 |
| Body-only nHD95 | 0.265131 | 0.265131 |
| Final-link voxel IoU | 0.094870 | 0.083106 |
| Final-link silhouette IoU | 0.320063 | 0.297599 |
| Final-link nChamfer | 0.125966 | 0.125361 |
| Final-link nHD95 | 0.265327 | 0.265209 |

C1 executed the proximal protected-cut path and scaffold preservation. C2
skipped both. L04 has no applicable rotary distal interface; C1 auto attachment
closure was not reached because scaffold preservation was selected.

## H. Confounds and limitations

The L04 body-only STL hash and volume are exactly equal between conditions.
Thus, although the proximal cut path was invoked, it was a geometric no-op for
this link; the observed final-link difference is primarily the frozen scaffold.
The distal-clearance flag is not exercised by L04. The ablation must therefore
be interpreted as a bundled protection treatment, not as an estimate of each
individual cut.

There was no retry, candidate repair, acceptance filtering, GT generator access,
or formal holdout access. The reused independent evaluator's legacy JSON key
`holdout_samples` means generic per-joint sample count in this dry run; it does
not indicate that the formal holdout was read.

## I. Formal-run recommendation

**CONDITIONAL GO**, not an unconditional go. Before the three-link formal run,
record per-link pre/post-operation volume or shape-hash deltas so an invoked
operation is distinguished from an effective geometry change. Preserve the
bundled-treatment interpretation and the body-only scoring limitation. No
formal three-link execution or paper conclusion is made at this stage.
