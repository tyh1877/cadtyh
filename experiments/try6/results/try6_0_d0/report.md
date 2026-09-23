# Try-6.0-D0 KFDE Feasible-Set Characterization — L04

**Decision: `DOMAIN_KFDE_INCOMPATIBLE`, in the protocol's finite-sampling sense.** No strict feasible point was observed in the exact frozen C1-v2 six-parameter domain after 5 canonical probes, 256 preregistered Sobol samples and 60 preregistered local violation-minimization proposals. The best observed `g_max` remained **66.60385593 mm³**, more than 66 million times the frozen **1e-6 mm³** feasibility epsilon. This does **not** mathematically prove that the continuous feasible set is empty. D0 does not modify the old C2 run or start C2-v2.

## A. Frozen-state / governance facts

The old C2 execution is documented here, without rewriting its artifacts, as **`NO_FEASIBLE_CANDIDATE_UNDER_FROZEN_SEARCH`**. The frozen C1 slot state remains `main_housing=PRESENT`, `visible_pocket=ABSENT`, `profile_transition=PRESENT`. Its six active parameter IDs, initial values and bounds were used exactly. The C1 KFDG and CAD compiler source, the 13-component C2 KFDE BREP keepout, neighbor geometry hashes, J03/J05 design sweep, L04 coordinate frame, scaffold/interface allowed-contact BREP, and 1e-6 mm³ numerical tolerance were hash-checked and unchanged. No VLM call, visual-objective score, GT file/metric, 96-case final mechanics row, C1 failed-case ID or formal holdout case entered D0 ranking. GT evaluations = **0**, final mechanics evaluations = **0**, formal holdout `accessed=false`, `evaluation_count=0`.

The fixed diagnostic budget was chosen before any D0 build: **256** seeded Sobol points (seed 20260923), then the **top five** by lexicographic (`g_max`, `g_sum`, ID), each with **12** bounded ±10%-range coordinate proposals; total ceiling **1800 s**. All 322 scheduled builds (P0–P4, one P3 technical repeat, 256 Sobol, 60 local) completed as valid single-solid CAD in about **427.36 s**, with **0 infrastructure failures**. The P3 repeat matched `g_sum=1402.26236702` and `g_max=281.97125918` exactly. The D0 component worker's P3 `g_max` also matched the independent frozen C2 checker on the same theta.

## B. Constraint decomposition

For each of the **321 distinct scheduled evaluations** (technical repeat excluded), D0 saved all **13 exact neighbor/pose intersection volumes** in `constraint_contribution_matrix.csv`; `g_sum` is their descriptive sum (overlapping swept poses can be double-counted), while **`g_max` is the frozen strict feasibility criterion**. On the 256 Stage-A Sobol points:

| Neighbor | Candidates with ≥1 violating pose | Rejection frequency |
|---|---:|---:|
| L03 / J03 sweep | 256/256 | 100% |
| L05 fixed J04 mount | 256/256 | 100% |
| L06 / J05 sweep | 256/256 | 100% |
| L07 fixed J06 child | 0/256 | 0% |

The L03 J03 samples `05` and `06`, L05 fixed pose, and L06 J05 poses `01`/`03` each violated all 256 Sobol candidates. L06 J05 poses `00`/`02` violated 255/256. Component-level mean/median/max volumes and pose IDs are in `constraint_summary.json`. Infeasibility is **not attributable to a single removable neighbor**: at least L03, L05 and L06 contribute broadly under the frozen semantics.

## C. Canonical probes

| Probe | Interpretation | `g_sum` mm³ | `g_max` mm³ | Dominant pose | Strict feasible? |
|---|---|---:|---:|---|---|
| P0 | all six at lower bounds | 356.170014 | 76.504853 | L06_J05_02 | no |
| P1 | all six at upper bounds | 5639.127365 | 1398.436698 | L05_FIXED_J04_00 | no |
| P2 | midpoint | 2330.034543 | 492.709355 | L06_J05_00 | no |
| P3 | frozen C1 initial theta | 1402.262367 | 281.971259 | L06_J05_00 | no |
| P4 | frozen C1 visual winner `candidate_031` | 3500.934642 | 727.970790 | L06_J05_03 | no |

P0 is still strongly infeasible, so simply shrinking every current visual variable to its lower bound does not clear KFDE. **P5 was omitted**: the frozen coarse/F0 FCStd has no exact auditable mapping to the six current parameter-table dimensions. It has no `ParameterTable` and only one coarse object; D0 did not invent approximate F0 theta. Consequently `KFDE_AUTHORITY_INCONSISTENCY_SUSPECTED` cannot be tested from an exact P5 and is not claimed.

## D. Feasible-set search

Stage A found **0/256** strict feasible samples (empirical feasible-sample density **0**, not a continuous-volume estimate). Its best `g_max` was **103.00088594 mm³**; counts within descriptive near-feasible thresholds ≤0.1, ≤1 and ≤10 mm³ were all **0**. The fixed local search also found **0/60** strict feasible proposals. The best observed point was `L1_5_N`, with `g_max=66.60385593` and `g_sum=406.19137835` mm³. The minimum observed `g_sum` was instead P0's **356.17001439** mm³; the two diagnostics need not choose the same point, and neither changes strict feasibility. No empirical feasible theta ranges or nearest-feasible distances exist to report.

In the 256 new Sobol samples, descriptive Spearman ρ versus `g_max` was highest for distal height (**0.686**) and distal width (**0.665**); versus `g_sum`, about **0.684** and **0.635** respectively. Other six-parameter correlations are in `parameter_sensitivity.json`. They were recomputed from D0 data, were not used to pick samples, and are not causal evidence.

## E. Frozen counterfactual and interface audit

The per-component vectors were recombined *without altering or rerunning the KFDE* for `FULL`, `MINUS_L05`, `MINUS_L07`, `MINUS_L06`, and `MINUS_L03`. Across all **321** evaluated non-repeat candidates, strict feasible counts were **0 in every subset**. No single neighbor's removal satisfies the preregistered ≥3-distinct-theta `SEMANTIC_MISMODEL_SUSPECT` criterion. This does not prove every neighbor's semantics are correct: multiple constraints may jointly overconstrain the domain, and these are diagnostic counterfactuals only.

The frozen topology confirms J04–L05 and J06–L07 are fixed connections. J04's contract permits **0 mm³ volumetric contact**; L05 intersections outside the frozen scaffold/interface allowance are therefore forbidden by the current KFDE, not automatically legitimate mating contact. The independent C2 allowed-region audit showed the frozen scaffold itself was exempt. Whether more distal interface volume should have been allowed is a **future semantic question**, not an adjustment authorized by D0; moreover deleting L05 alone does not create a feasible sample. No exact F0-equivalent parameterized body was available for an authority-inconsistency verdict.

## F. Decision, interpretation and limits

Under the frozen decision priority: full feasibility **0**, no single-neighbor removal creates feasible samples, no exact F0 authority test exists, and best `g_max=66.60` exceeds the preregistered “material” threshold of **10 mm³**. Therefore the independent validator assigned **`DOMAIN_KFDE_INCOMPATIBLE`**: the current domain and current KFDE show no **observable** intersection under this broad, completed diagnostic plan. The result points toward a separately versioned design-domain/KFDE semantics audit, **not** an automatic margin relaxation or C2-v2 search. A thin feasible island outside these finite samples is not ruled out.

**NOT SUPPORTED:** C2 geometry superiority, C2 mechanical improvement, KFDE incremental benefit, Try-6.1 expansion, manufacturing readiness, F0 authority inconsistency, or formal-holdout performance. D0 ends here; no KFDE/bounds/objective/search changes, GT evaluation, final mechanics evaluation, C2-v2, L03 or L07 experiment followed.
