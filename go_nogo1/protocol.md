# Go/No-Go 1 — Mesh-Based Geometric Complexity Validity Audit

## Frozen question

Can geometric complexity of articulated robot CAD be measured reliably from the
visual meshes referenced by URDF, without requiring STEP as the main-entry format?

This audit is diagnostic. It does **not** test downstream CAD generation quality.

## Data and provenance

- Primary source: URDF Files Dataset.
- Frozen repository commit: `81f4cdac42c3a51ba88833180db5bf3697988c87`.
- Unit of sampling: a distinct robot model, not a URDF file or collision variant.
- Primary geometry: URDF visual meshes. Collision meshes are retained only for QC.
- Eligible types: `robotic arm`; `dual arm robot` and `mobile manipulator` are kept
  in inventory but excluded from the primary sample unless required as a stated
  sensitivity analysis.

## Stages

1. Build a complete URDF-level inventory and resolve all visual mesh references.
2. Collapse duplicate sources/variants to robot entities and assign QC grades.
3. Freeze Audit-30, stratified by manufacturer/family and preliminary complexity.
4. Compute mesh complexity features on canonicalized meshes and test sensitivity
   to remeshing/tessellation.
5. Obtain blinded expert ordinal ratings for Audit-30.
6. Compare a 10–15 model STEP/B-Rep calibration subset where lawful data exists.

## QC grades

- A: XML parses; kinematic graph is valid; at least 90% of visual mesh references
  resolve; at least 80% of non-fixed links have visual geometry.
- B: XML parses and graph is usable; at least 70% of visual references resolve;
  shortcomings are documented and do not erase the arm's main morphology.
- C: parse failure, invalid graph, under 70% visual resolution, or predominantly
  primitive/no visual geometry. C records are excluded from Audit-30.

## Pre-registered decision thresholds

Full Go requires all of the following:

- at least 24 valid robot entities after QC;
- at least 8 expert-rated high-complexity robots from at least 4 model families;
- expert agreement: weighted kappa >= 0.65 or ICC >= 0.75;
- mesh score versus expert median: Spearman rho >= 0.60;
- mesh score versus STEP/B-Rep score: Spearman rho >= 0.50 (target >= 0.60);
- remeshing robustness: rank rho >= 0.85;
- triangle-count confounding after canonicalization: |rho| < 0.30;
- no single upstream source supplies over 50% of Audit-30.

Conditional Go: the expert and mesh-validity thresholds pass but STEP calibration
or diversity is incomplete; proceed only with the limitation explicitly scoped.

No-Go: expert agreement fails, mesh score fails expert validity, or the score is
primarily tessellation/triangle-count driven after one allowed metric revision.

## Post-failure development revision: equal-weight v2

The original frozen score failed B-Rep validity. The following revision is therefore
explicitly **development-only** and cannot reverse the original result on Audit-30.

- Normalize every raw feature to a 0–1 percentile within the eligible development
  population, after aligning all directions so larger means more complex.
- Average features equally within their semantic module.
- Average semantic modules equally; do not let a module gain weight merely because
  it contains more raw indicators.
- Report geometry, assembly, and kinematic complexity separately. Geometry is the
  primary score; an equal three-way overall score is secondary only.
- Do not learn weights from experts or Audit-30. A new holdout must be frozen before
  v2 can be described as independently validated.

## Leakage controls

- Thresholds above are frozen before looking at correlations.
- Audit-30 membership is frozen before expert scoring.
- Experts do not see automated scores, source, triangle counts, or B-Rep results.
- One metric revision is allowed only on a separately recorded development subset;
  the frozen audit set is not reused for tuning.

## v3 objective-task amendment (2026-08-07)

This amendment replaces expert opinion as the primary development target. Expert
blind ratings remain an auxiliary construct-validity check and do not determine
feature weights.

- Freeze 142 eligible entities by product family into Development (80), Validation
  (32), and Final Holdout (30), using deterministic seed `20260807`.
- Frozen manifest SHA-256:
  `dbed8515b7af0ab5a577b037a5f99c7277b7239af2f2eb0ab3e0a98f7c786c63`.
- Fit every empirical percentile transform on Development only.
- Geometry v3 is the equal mean of three equal-weight modules: orientation
  distribution, local curvature, and multiscale curvature persistence. No learned
  weights and no triangle-count feature are permitted.
- The external objective target is approximation difficulty at nominal robot-level
  budgets of 1k, 5k, and 10k faces. At each budget, normalized Chamfer, normalized
  Hausdorff, and normal error receive equal weight; budgets then receive equal weight.
- Per-link simplification has a 20-face minimum, so achieved faces are recorded and
  may exceed the nominal robot-level budget.
- Go requires, on Validation: primary Spearman rho >= 0.60; remesh rank rho >= 0.85;
  |triangle-count rho| < 0.30; leave-one-module-out rho >= 0.80; and positive
  correlations at every budget.
- Final Holdout must not be read until a materially revised formula is frozen after
  passing Development diagnostics and the one-use Validation decision.
