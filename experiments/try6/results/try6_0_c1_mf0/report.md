# Try-6.0-C1-MF0 — L04 Metric Factorization Feasibility

**Decision: `FACTOR_REFACTOR_TOO_LARGE`.** MF0 stopped at its preregistered *pre-implementation* anti-sunk-cost gate. The existing C1-v2 scientific path cannot be turned into a clean `C(theta_shape, s)` through a bounded extraction of one scale variable: all seven audited core layers require a semantic change, and wrapping the legacy builder would retain the exact metric prior inside the supposedly scale-free shape path. This is a scope judgment about the **current** method, not a proof that scale-factorized CAD is impossible in a new architecture.

## Historical diagnosis and refactor scope

C1-v2's frozen 63 mm J03–J04 relation remains in its KFDG metric anchor and distal `frame_xyz_mm`, the round3 F0/FrozenScaffold, absolute-mm interface contracts, six-parameter registry/bounds, FreeCAD compiler guard and distal loft placement, camera px/mm registration, mm-domain ROI/profile stations and visual-objective normalization. C1-A1 correctly stopped its NoAnchor ablation because these paths would contaminate the control condition. None of those historical sources or results was modified in MF0.

| Core layer | Why a local wrapper is insufficient |
|---|---|
| KFDG/functional frames | Schema, validator and authority graph encode a metric distal frame and `distance_mm=63`; canonical `u=1` needs a new scale-free contract. |
| F0/scaffold generator | Actual F0 is built from URDF-origin placement plus fixed-mm body, interface radii and clearance primitives. Dividing the final F0 BREP by 63 would preserve anchor-derived proportions and is not a provenance-clean normalized functional scaffold. |
| FreeCAD compiler | It rejects `s≠63`, consumes mm theta, opens/fuses exact-metric F0 and uses fixed-mm bore/mating cuts. Its feature tree and interface instantiation would need coordinated scale semantics. |
| Parameter registry | Active values/bounds and functional anchor are in mm; renaming them “ratios” without new dimensionless provenance would not separate factors. |
| Interface geometry/contract | Distal placement, clearance, radii and depths must move together to the explicit metric boundary while retaining joint identity and axes. |
| Visual objective | Projection, profile target widths and loss normalization use px/mm and the anchor; a unit-shape image-domain objective is a different implementation. |
| View registration/evidence | Cached scales and 12–52 mm ROI/15–30–45 mm stations derive from the anchor; raw masks must be re-extracted into preregistered dimensionless positions. |

The budget sheet identifies **7/7 semantic replacements**, with a **665–1280 changed-line** engineering estimate across these layers and affected historical KFDG, interface, compiler, registration, objective and parity tests. The exact count is not a measured diff. The preregistered budget rule classifies ≥5/7 layer replacement—or a wrapper that retains 63 mm in shape—as `MAJOR_METHOD_REWRITE`. Current C1 would cease to be the same recognizable method. The right response is to stop, not to accumulate a second, nominally factorized pipeline merely to obtain PASS-looking screenshots.

## Desired representation versus achieved implementation

A future architecture could, in principle, represent proximal/distal functional identity at canonical `u=0/1`, use dimensionless housing/transition ratios, generate a normalized scaffold and all interfaces, and introduce physical millimetres through one explicit `s` boundary. Joint identity, axes, parent/child ownership, feature ordering and topology may remain scale-free. **MF0 did not implement or validate these objects.** `representation/*.json` deliberately labels each specification `DESIGN_ONLY_NOT_IMPLEMENTED`; there is no provenance-after audit or single metric-entry proof.

No technical builds were made at `s=1,60,63,70`. Consequently MF0 has **no** evidence for canonical BREP validity, scale equivariance, normalized-shape invariance, topology/interface invariance, image-objective scale independence or historical `s=63` parity. Simply isotropically scaling a frozen final FCStd could show a geometric transform; it would not show that image-derived `theta_shape` and functional scaffold were independent of the URDF metric prior. No GT was used to define ratios or assess parity.

## Validation and next implication

Of the 24 named MF0 checks, five prohibited-activity/holdout guards pass and 19 implementation/build checks are explicitly **not run because of the budget gate**. Independent validation passes **20/20 evidence-integrity checks** and confirms the fail-closed decision—not factorization readiness. GT, VLM, optimizer, KFDE and formal-holdout calls are all zero; holdout remains `accessed=false`, `evaluation_count=0`.

`READY_FOR_MF1` is **not** supported. Under the current C1 architecture, the kinematic-metric contribution cannot be defended through a bounded factorization refactor. Pursuing it would require explicitly authorizing and evaluating a new scientific method architecture, with new provenance and parity criteria, rather than continuing MF1/A1 by default. MF0 does **not** establish anchor benefit, reconstruction improvement, L03/L07 generalization, SOTA/benchmark readiness, editability superiority or mechanical superiority.

Evidence: `refactor_budget/scope.json`, `refactor_budget/changed_modules.json`, `refactor_budget/budget_decision.json`, `provenance/metric_provenance_before.json`, `provenance/hidden_scale_search.json`, `tests/test_report.json` and `audit/independent_validation.json`.
