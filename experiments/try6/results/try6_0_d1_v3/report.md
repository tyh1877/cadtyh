# Try-6.0-D1-v3 — Final L04 KFDE Semantics and Representation Attribution

**Final decision: `KFDE_SEMANTICS_MISALIGNED`. Immediate next direction: KFDE semantic redesign, not yet implemented.** The frozen finite D0 search found no feasible 6D candidate; D1-v3 now attributes the *primary* obstruction to KFDE occupancy that independent Exact mechanics did not classify as unintended collision. A smaller, mechanically supported local proximal clearance issue also exists, but under the frozen decision priority it is secondary and does not justify diagnosing the full ~9.90% witness removal as necessary CAD redesign.

## Facts — immutable evidence

- D1-v2's 65/65 row categories remain **33 ALIGNED_SAFE, 5 ALIGNED_UNSAFE, 27 KFDE_FALSE_POSITIVE_SUSPECT**, with no false negatives or ambiguous rows. The preregistered descriptive unsafe alignment is **5/32 = 15.625%**, below the frozen 90% `ALIGNMENT_HIGH` criterion. Across all five geometries: L03 5/12 KFDE violations aligned unsafe, L05 0/4, L06 0/16, L07 no violations. This is not a general statistical precision estimate.
- Witness attribution uses **only C1-final geometry's own 13 frozen rows**, not the other four geometries' labels: C1 has 1 aligned-unsafe L03 pose, 6 false-positive-suspect poses (1 L03, 1 L05, 4 L06), and 6 aligned-safe poses. Frozen W1-v2 nine-subset BREP/FCStd validity, containment, keepout clearance, repeatability, topology and interface invariance remained accepted and unchanged.
- FULL's normalized W1-v2 relief is **9.8983% (Moderate)**; it is a KFDE-demanded diagnostic removal, not automatically a mechanical requirement. The frozen C1 mutable body's unique removed-region BREP is about **1302.044 mm³**. Exact union/intersection of the frozen C1-labeled components yields:

| C1-frozen component class | Unique relief mm³ | Fraction of FULL removed region |
|---|---:|---:|
| Exact-supported-only | 66.604 | 5.12% |
| False-positive-suspect-only | 1235.441 | 94.88% |
| Spatially shared | 0 | 0% |

These are geometric unions, never sums of overlapping component volumes. OCC reports a **0.001727 mm³** difference between the class partition sum and FULL total, so exact volume additivity is **not** asserted. The fractions are descriptive at that numerical precision. The supported/suspect BREP artifacts and hashes are retained.

## Localization and neighbor attribution

The original L04-local x stations (21 and 42 mm) and frozen ≥80% one-region rule were used; no secondary axes were invented. FULL removed volume is about **90.105% DISTAL** and **9.895% PROXIMAL**. Its three-region volume sum differs from its total by about **0.001727 mm³**, slightly above the old worker's 0.001 mm³ sanity check. The first failed attempt was preserved; one documented technical retry retained the raw discrepancy and tested a conservative dominant-fraction bound **without changing the 21/42 mm stations or 80% criterion**. FULL remains robustly distal-localized under that bound. No region volume was adjusted to make it sum exactly.

| Neighbor | C1 supported / suspect poses | W1-v2 normalized relief | Removed-region location | Mechanically required CAD interpretation |
|---|---:|---:|---|---|
| L03 | 1 / 1 | 0.9794%, Small | 100% proximal | Only the supported component's 66.604 mm³ is mechanically evidenced; it is local. The remaining L03 suspect component must not be counted as required. |
| L05 | 0 / 1 | 3.4986%, Small | 100% distal | KFDE-demanded, but unsupported by Exact in C1; not CAD-capacity evidence. |
| L06 | 0 / 4 | 5.5341%, Moderate | 100% distal | KFDE-demanded, but unsupported by Exact in C1; not CAD-capacity evidence. |
| L07 | 0 / 0 | 0%, engineering zero | Not applicable | No measurable relief; its Small category is not positive evidence. |

Combined frozen subsets are also recorded: L03_L05 is ~78.13% distal and does **not** meet the 80% localization rule; L03_L06 is ~84.96% distal, L05_L06 is 100% distal, and L03_L05_L06 matches FULL's ~90.11% distal localization. These labels do not override the underlying component semantics.

## Representation-capacity axis — secondary

The exact-supported-only C1 relief is a valid two-piece removed-region BREP of **66.604 mm³**, entirely proximal; its bbox spans local x ≈ **11.78–15.79 mm** (about 4.01 mm) within the selected 32 mm proximal pad. W1-v2's L03 witness remains a connected single solid with frozen interfaces intact. The six frozen active parameters control the full proximal width/height/length or broader transition/distal loft sections; the frozen KFDG has no local pocket node. On this code-and-BREP evidence the supported L03 region is labeled **`REQUIRES_LOCAL_FEATURE`**, and the secondary representation axis is **`LOCAL_CAPACITY_MISSING`**. No parameter perturbation, optimization or new CAD feature was run; this is a bounded expressibility assessment, not a measured performance gain.

Critically, the three-solid FULL and L05_L06 witnesses are largely driven by suspect L05/L06 occupancy. Their disconnected topology **cannot** justify `PARAMETRIC_TOPOLOGY_INSUFFICIENT` for real mechanics. L05/L06 expressibility is therefore `UNKNOWN` rather than inferred from their false-positive relief.

## Causal decision and limits

The frozen F0 full link remains valid and Exact found no unintended collision in its 13 authority rows; its empty mutable scope alone does not establish `KFDE_AUTHORITY_INCONSISTENCY`. With low frozen overall alignment and a dominant **94.88% suspect-only** share of C1 FULL relief, the first applicable non-authority decision under the frozen priority is **`KFDE_SEMANTICS_MISALIGNED`**. The supported L03 local-capacity signal is recorded as secondary; `MIXED_KFDE_AND_REPRESENTATION_ISSUE` is not selected because the preregistered priority places substantial semantic misalignment first. The immediate method direction is **KFDE semantic redesign**; only after revalidating corrected mechanical constraints should local CAD freedom be considered.

No KFDE, KFDG, CAD, theta, C2 candidate or relief feature was changed. No new exact sweep, GT, VLM, final 96-case mechanics or formal-holdout evaluation occurred; holdout remains `accessed=false`, `evaluation_count=0`. D1-v3 does **not** establish improved C2 geometry/mechanics, Try-6.1 generalization, manufacturing readiness or formal-holdout performance.

Evidence: `frozen_evidence/parity_audit.json`, `localization/localization_summary.csv`, `semantic_decomposition/decomposition_summary.json`, `capacity/six_theta_geometry_support.json`, `attribution/neighbor_attribution.csv`, `attribution/decision_trace.json` and `audit/independent_validation.json`. Heavy diagnostic BREPs and raw FreeCAD logs remain in ignored `experiments/try6/artifacts/try6_0_d1_v3/` with recorded hashes.
