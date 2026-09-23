# Try-6.0-R1-v3 Closed-Set Evidence Slot Reliability

**Decision: `READY_FOR_C1_V2` — infrastructure readiness only.** The pre-registered closed-set representation gate and one fresh non-GT end-to-end dataflow smoke passed. This is not evidence that Metric Grounding improves reconstruction geometry. A visible-pocket perception warning remains material for the next formal experiment.

## A. Architecture and frozen semantics

The system now supplies exactly three L04 visual slots: `main_housing`, `visible_pocket`, `profile_transition`. Qwen reports only `PRESENT`/`ABSENT`/`UNCERTAIN`, evidence-view IDs, and confidence for each slot. It does **not** output local feature names, parameter roles/IDs, free relations, joints/frames, final dimensions, CAD code, or a full KFDG. The frozen Slot Registry deterministically maps only PRESENT slots to feature IDs, feature types, existing parameter refs, and relation rules. ABSENT and UNCERTAIN slots instantiate no visual feature; their decision and evidence remain in `slot_provenance`, with associated parameter nodes explicitly inactive.

Functional nodes, interface context, and the real 63 mm metric anchor come from the unchanged sanitized URDF/frozen interfaces. The R1 Parameter Registry was not expanded: its actual axial variables are `proximal_section_length_mm` and `recess_length_mm`, not the illustrative `housing_depth_mm`/`recess_width_mm` names in the request. `fillet_radius_mm` remains dormant. CAD compilation added only conditional *omission* of the existing Pocket/transition when their slots are not PRESENT; no new feature, fillet, chamfer, or manufacturing logic was introduced. A separate non-GT compiler self-test passed for both PRESENT and UNCERTAIN pocket, including one solid, export/reopen, and unchanged protected interface signatures.

The canonical slot Schema is the single source of truth. The deterministic API projection removed exactly one `uniqueItems` constraint from `evidence_views`, with path/reason/local replacement recorded in `schema/projection_report.json`. The local canonical validator still rejects duplicate evidence and enforces exact slot completeness/status-dependent evidence. The single non-denominator production preflight returned HTTP 200 and a raw transport-valid response.

## B. Five-call contract reliability

Five fresh production-shaped requests used byte-identical prompt/model/budget/engineering text and the same 12 hashed image inputs. The independent validator decoded the actual HTTP request bodies to recheck image bytes and confirmed exact request-body parity. All five attempts and raw outputs were retained; no retries, response repair, manual intervention, selection, or majority-vote KFDG occurred.

| Gate | Result |
|---|---:|
| API transport valid | 5/5 |
| Exact three-slot local contract valid | 5/5 |
| Deterministic graph assembly | 5/5 |
| Canonical KFDG valid | 5/5 |
| Repair / manual intervention | 0 / 0 |
| Missing/unknown/duplicate slots, invalid status/evidence, dangling/duplicate refs, ownership/functional violations | all 0 |

Different slot statuses led to different valid graphs. In particular, ABSENT pocket decisions did not create a pocket feature; the graph kept provenance and inactive pocket parameters. These are not contract failures.

## C. Perception stability — separate warning

| Slot | PRESENT | ABSENT | UNCERTAIN | Modal agreement | Confidence agreement |
|---|---:|---:|---:|---:|---:|
| main_housing | 5 | 0 | 0 | 1.0 | 1.0 |
| visible_pocket | 3 | 2 | 0 | **0.6** | 0.8 |
| profile_transition | 5 | 0 | 0 | 1.0 | 1.0 |

`visible_pocket` triggers the pre-registered **`PERCEPTION_STABILITY_WARNING`** (<0.8). Its status entropy is about 0.971 bits. The warning is descriptive, not a hard contract failure. No GT feature labels exist, so PRESENT is not presumed correct. The five responses were **not voted** into a formal CAD candidate; future C1-v2 must use one new call and report whichever status it returns.

## D. One fresh end-to-end no-GT smoke

After the independently checked 5/5 gate, one additional Qwen call was made outside the reliability denominator. It returned `main_housing=PRESENT`, `visible_pocket=ABSENT`, `profile_transition=PRESENT`. Its raw response passed transport and full local contract; deterministic assembly produced a valid KFDG with **no pocket entity**. The status-aware version of the existing feature-history compiler built this graph without a Pocket, then applied the frozen proximal opening and F0 scaffold.

The tiny solver used **three primary CAD candidates plus one predefined anchor-sensitivity candidate** (four builds total; no GT). Its synthetic normalized-width target was derived from the frozen 17 mm registry width divided by the real 63 mm URDF J04 anchor. All objectives were finite. The selected `housing_width_mm` theta was 17.0 mm. Perturbing only the **synthetic objective anchor** to 64 mm changed the fixed-theta objective from 0 to about 1.78×10⁻⁵, moved the corresponding theta to 17.269841 mm, changed the Pad's width/bounding box and final assembled volume (17276.75→17361.20 mm³). CAD jobs continued to use the **real 63 mm functional anchor**, so the interface did not move. The independent validator recomputed the objective and theta values, reopened the copied final FCStd in FreeCAD, and verified one solid, invariant proximal bore/mating-envelope/scaffold BREP signatures across all four builds, STEP/STL exports, and FCStd reopen.

This is a **synthetic wiring test**: its target ratio is constructed from the frozen baseline, not estimated from visual evidence. Therefore it demonstrates anchor→objective→theta→CAD dataflow and parameter editability, **not** that the paper's real Metric Grounding objective works or improves geometry.

## E. Freeze, decision and unsupported claims

C1-v1, R0, R1-v1, and R1-v2 result files passed independent hash rechecks. GT evaluation count remained **0**; formal holdout lock metadata remained `accessed=false`, `evaluation_count=0`, and no holdout cases were read. The frozen future C1-v2 C0 IoU and geometry gate were not changed or evaluated. The result supports `READY_FOR_C1_V2` under the R1-v3 **infrastructure** gates, with the pocket perception warning carried forward. No C1-v2, C2, KFDE, 96-case mechanics, manufacturing, or formal-holdout run followed.

Not supported: KFDG outperforming Direct, Metric Grounding improving geometry, Try-6 outperforming Try-5, KFDE effectiveness, manufacturing readiness, or formal-holdout performance.
