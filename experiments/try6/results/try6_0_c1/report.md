# Try-6.0-C1 — KFDG + Metric Grounding Pilot, L04

Decision: **REPRESENTATION_FAILURE**. The formal one-shot attempt stopped at
the typed KFDG response boundary. This is a valid terminal outcome under the
frozen protocol; it is not a geometry or motion result.

Independent failure-path validation: **PASS, 12/12 integrity checks**.
Formal holdout: `accessed=false`, `evaluation_count=0`.

## A. IMPLEMENTATION

The new `experiments/try6/` namespace contains a versioned L04 KFDG schema,
strict parser, parameter table, image/URDF metric objective, and native FreeCAD
feature-history builder. Frozen Try-5 files were only read as inputs or reused
as evaluator utilities; they were not modified.

The canonical KFDG has four kinds of data: two URDF-fixed functional ports,
VLM-proposed visible feature nodes, nine continuous parameter nodes, and typed
relations. A complete formal KFDG was **not materialized**, because the VLM
response failed the top-level type check. The read-only postmortem found a
schema-valid object inside the returned one-element array; that object was not
used for generation.

The nine bounded visual parameters are `housing_width_mm`,
`housing_height_mm`, `proximal_section_length_mm`, `transition_length_mm`,
`distal_width_mm`, `distal_height_mm`, `recess_length_mm`, `recess_depth_mm`,
and `fillet_radius_mm`. Frozen functional values include J03/J04 frames,
the J03 axis, and their 63 mm separation. Every parameter has a value, mm
unit, bounds, provenance, and confidence in `parameter_bounds.json`.

The VLM was asked only for visible feature topology, relations, evidence views,
uncertainty, and dimensionless ratio cues. Final millimetre values were reserved
for the metric solver. One `qwen3.7-plus` call returned normally with request ID
`chatcmpl-9f9da69d-98d1-995d-8f2b-dafe5fe2c51f`: 15,821 input tokens,
7,070 output tokens, 124.20 seconds, zero retries, and zero manual edits.
The API returned no system fingerprint.

All six raw PNGs contain FreeCAD MIBA view matrices. They do not provide a
complete calibrated pixel projection or the exact articulated source pose.
The pre-registered objective therefore selected the visible right/top L04
color masks and fixed view-specific scale/translation using the URDF J03→J04
63 mm separation. Joint pixel endpoints are approximate; this limitation is
recorded in `camera_or_view_registration.json`.

## B. METRIC SOLVER

The frozen objective was

`0.45 L_silhouette + 0.30 L_edge/profile + 0.15 L_landmark + 0.10 L_prior`.

The optimizer was seeded Sobol followed by local random search, maximum 32
candidate evaluations, seed 20260923, tolerance 0.0001, and 240-second runtime
limit. Two nonformal smoke points produced finite objective values (0.265774
and 0.250540) with valid FreeCAD builds. Changing the URDF anchor from 63 to
60 mm changed the fixed-CAD objective from 0.265774 to 0.260306 and the
right-view metric height estimate from 15.421 to 14.687 mm. This proves the
anchor is consumed in the prepared solver.

**Formal solver evaluations: 0.** There is no theta*, convergence curve, or
claim that metric grounding improved geometry. No GT or motion metric entered
the smoke objective.

## C. CAD

The nonformal infrastructure builder generated a real FreeCAD history with
Sketch/Pad, Fillet, Pocket, three Sketch-based Loft sections, frozen proximal
bore and mating-envelope cuts, and scaffold fusion. A spreadsheet binds all
nine parameter aliases. The resulting FCStd reopened and recomputed; a small
`recess_depth_mm` edit changed final volume. A separate width-edit smoke
invalidated the Fillet's Edge1 reference, exposing a topology-naming
limitation. This was not hidden or counted as formal editability success.

**Formal C1 CAD artifacts: none.** No feature mapping or final geometry can be
claimed for this one-shot response. The smoke tree is infrastructure evidence
only.

## D. RESULTS

The precise frozen C0 Direct-Qwen values were read from
`experiments/try5A/results/try5b1_a2a_three_link/paired_main_table.json`:

| Frozen C0 metric | Value |
|---|---:|
| Final voxel IoU | 0.12496993987975952 |
| Silhouette IoU | 0.3017446993510538 |
| nChamfer | 0.11657432624731785 |
| nHD95 | 0.2950432532379807 |
| BICR / connected solids | 1.0 / 1 |
| J03 JR3 | 1.0 |
| GCFR | 0.7291666666666666 |
| Collision events | 50 |
| Intersection volume, mm³ | 26393.013813899426 |

The pre-registered C1 IoU requirement would be
`1.10 × 0.12496993987975952 = 0.13746693386773548`. **C1 IoU, other
geometry metrics, BICR, JR3, GCFR, and collision metrics are all uncomputed.**
The 96 development mechanical cases were requested by protocol and all 96
remain uncomputed because execution stopped before CAD. They were not dropped
from a reported success denominator.

Process totals: one successful transport response; one schema failure; zero
formal solver evaluations, CAD rebuilds, GT evaluations, retries, manual
interventions, and formal-holdout evaluations.

## E. DECISION

**REPRESENTATION_FAILURE.** The request used the provider's `json_schema`
response format with `strict=true` and a top-level object schema. The model
content was a JSON array containing one object. The strict local validator
rejected it before KFDG assembly. The exact provider-side reason for the
envelope mismatch is unknown; neither the VLM content nor the array wrapper
was edited to make this attempt pass. The official Qwen documentation lists
Qwen3.7-Plus support for JSON Schema output:
<https://help.aliyun.com/en/model-studio/qwen-structured-output>.

Under the frozen C1 stop rule, KFDE/C2 cannot begin from this result. A future
version would need a newly pre-registered response-envelope contract and a
fresh independent one-shot run. This attempt must remain frozen.

## F. FACTS / INTERPRETATION / NOT_SUPPORTED

**Facts:** Six KFDG contract tests passed; two CAD/objective smoke points
passed; the URDF anchor affected the metric objective; the one formal VLM
response had the wrong top-level JSON type; formal execution stopped before
solver, CAD, GT evaluation, and holdout access.

**Interpretation:** The first bottleneck in this attempt is the API-to-KFDG
response contract. The inner object being locally valid suggests the failure
was at the response envelope, but does not establish whether the cause lies in
the provider, SDK, multimodal JSON Schema handling, or prompt interaction.
The width-edit smoke separately identifies a FreeCAD topological-reference
risk that should be handled before claiming broad editability.

**Not supported:** C1 geometry improvement, C1 BICR, motion trade-off,
metric-grounding convergence, formal PRS, C2 readiness, Robot B/C transfer,
manufacturing detail, or a formal-holdout conclusion.
