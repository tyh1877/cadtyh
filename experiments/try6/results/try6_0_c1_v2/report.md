# Try-6.0-C1-v2 — Real Visual Metric Grounding, L04 formal development run

**Decision: `GO_C2` under the preregistered one-link development gates.** This permits considering a later KFDE/C2 experiment; it does **not** start C2 or establish general performance. The one final C1-v2 candidate was chosen only by a raw-image visual objective, committed to `final_candidate_lock.json`, and evaluated against GT once afterward.

## FACTS — inputs and representation

- Frozen comparator: the existing A2a L04 `DIRECT_QWEN` C0 artifact, not a regenerated baseline. Its precise four geometry metrics and mechanics values were read only by final independent evaluation. This is a historical comparison, **not** a newly model-controlled paired trial.
- One fresh `qwen3.7-plus` call returned `main_housing=PRESENT`, `visible_pocket=ABSENT`, `profile_transition=PRESENT`. HTTP raw/SDK contents matched; exact three-slot contract and deterministic KFDG passed without repair/retry. The prior R1-v3 pocket warning (3 PRESENT, 2 ABSENT; modal agreement 0.6) was carried forward without majority voting. The final CAD accordingly **contains no Pocket**.
- Active theta had six pre-existing variables: `housing_width_mm`, `housing_height_mm`, `proximal_section_length_mm`, `transition_length_mm`, `distal_width_mm`, `distal_height_mm`. `recess_length_mm`, `recess_depth_mm`, and dormant `fillet_radius_mm` stayed frozen/inactive; functional joint frames, interface geometry, scaffold and the real 63 mm URDF anchor were never optimizer variables.

## FACTS — raw visual evidence and registration

No calibrated intrinsics/extrinsics or trustworthy full-link GT segmentation was available. The method used the raw robot's color-coded **visible teal L04 pixels**, selected by the frozen RGB/component rule. This is a raw-image visible-region mask, **not** a perfect L04 silhouette or GT mask. Right and top were the only usable solver views; front/rear lacked visible L04 pixels, while left/isometric were not selected for the frozen two-view objective. The central, joint-anchored ROI covers x=12–52 mm, excluding the most occluded interfaces. Profile widths were sampled at x=15, 30, 45 mm. Raw right-view visible widths were approximately 12.04/12.04/15.04 mm; top-view widths 25.04/25.04/18.78 mm after scale conversion.

Registration used approximate colored visible-envelope endpoints as landmarks, not manually annotated physical joint centers. The 63 mm J03–J04 URDF anchor converted right/top spans to 5.31746 and 5.11111 pixels/mm; cross-view relative scale discordance was 3.957%, below the frozen 10% gate. A two-endpoint fit has zero internal endpoint residual *by construction* and is not independent camera-accuracy evidence. Registration was then fixed for every candidate—camera pose/scale was never optimized together with theta. The raw-mask paths, hashes, ROIs, station measurements and explicit uncertainty are in `visual_metric_evidence/`.

## FACTS — objective and solver

The real visual objective was **0.5 × normalized central-ROI contour distance + 0.5 × normalized three-station profile-width error**, averaged over right/top. Contour distance is normalized by each ROI diagonal; profile width error by the 63 mm anchor. No full-link silhouette IoU, independent landmark term, prior-only target, GT term, or mechanical term was used. The approximate endpoint landmarks serve registration and are not double-counted as a separate loss. A preformal two-CAD non-GT smoke confirmed parameter sensitivity and that a synthetic 63→64 mm anchor perturbation changed raw-image metric width targets and the objective (0.05974859→0.06090206 for fixed CAD); this was diagnostic only, not the formal target.

The frozen optimizer was seeded bounded Sobol followed by deterministic coordinate search, with 32 maximum candidates, 240 s solver runtime cap, 90 s per-CAD timeout, and 0.0001 convergence tolerance. It evaluated **32/32 valid CAD/render candidates**, retained all in history, and exhausted the candidate budget. Initial visual loss 0.0597485900 fell to 0.0230483867 (**61.42%** relative improvement). Candidate `candidate_031` was the lowest legal visual-loss candidate; no GT or mechanics entered ranking. Selected theta (mm): housing width **24.0**, housing height **12.0380**, proximal section length **32.0**, transition length **16.0**, distal width **17.3818**, distal height **22.1409**. Width, proximal length and transition length touched frozen upper bounds; this is an important observability/objective warning, not a reason to retune this run.

## FACTS — final CAD and evaluation order

The final editable tree contains `MainHousingPad`, `ProfileTransitionLoft`, `HousingWithTransition`, frozen proximal bore/mating-envelope cuts, and scaffold fusion. Pocket and fillet are absent. The final `RigidGroup` is a valid **one connected solid**, with frozen protected BREP signatures unchanged, parameter table matching theta*, STEP/STL export and FCStd reopen passing. The final CAD and all generation/evidence/solver hashes were locked in `evaluation/final_candidate_lock.json` **before** the first GT evaluator event. The final assembled-link GT geometry was evaluated once; same-development-protocol exact mechanics used all 96 coupled configurations plus J03 sweep only afterward. Formal holdout remained untouched.

| Final-link geometry metric | Frozen C0 Direct-Qwen | C1-v2 | Relative change |
|---|---:|---:|---:|
| voxel IoU ↑ | 0.12496993987975952 | 0.1881884426368412 | **+50.59%** |
| silhouette IoU ↑ | 0.3017446993510538 | 0.3462839613652157 | **+14.76%** |
| normalized Chamfer ↓ | 0.11657432624731785 | 0.1010314900985874 | **−13.33%** |
| normalized HD95 ↓ | 0.2950432532379807 | 0.29211681006226614 | **−0.99%** |

The primary C1 IoU threshold was **0.13746693386773548**. C1 exceeded it; silhouette ≥0.98×C0, Chamfer/HD95 ≤1.05×C0, and at least one strict distance improvement all passed. Final C1 bbox error was 32.60057 mm and major-dimension error 10.04958 mm; no exact C0 counterparts were available in the frozen comparison row, so no bbox delta is claimed. Body-only-versus-full-link-GT scores are retained solely as a paired diagnostic, not absolute body reconstruction accuracy.

| Mechanics (diagnostic only) | Frozen C0 | C1-v2 |
|---|---:|---:|
| BICR / connected solids | 1.0 / 1 | **1.0 / 1** |
| J03 JR3 | 1.0 | **1.0** |
| GCFR | 0.7291666666666666 | **0.8020833333333334** |
| exact collision events | 50 | **42** |
| exact intersection volume, mm³ | 26393.013813899426 | **26456.388605736887** |
| failed coupled configurations | 26 | **19** |

C1 failed configuration IDs (all retained): `sobol_011, sobol_014, sobol_018, sobol_020, sobol_021, sobol_025, sobol_035, sobol_046, sobol_047, sobol_050, sobol_053, sobol_056, sobol_076, sobol_077, sobol_090, sobol_095, sobol_107, sobol_118, sobol_123`. The intersection burden rose slightly despite fewer collision events; motion results did not affect C1 selection or the geometry gate.

## FACTS — process, dataflow and leakage discipline

One VLM call used 13,366 input and 4,013 output tokens (71.95 s latency); 32 solver evaluations, 33 CAD builds including final, 64 two-view candidate renders, zero invalid CAD candidates and zero manual interventions were recorded. Solver runtime was 24.90 s; geometry evaluator 1.88 s; exact mechanics diagnostic 183.59 s. Original evidence-extraction and orchestration times were **not instrumented**; `process_metrics.json` reports a sum of measured components as a lower bound, not a fabricated total runtime.

Three chains were audited: (A) fresh slot status→PRESENT-only KFDG nodes/active parameters→Pocket-free CAD; (B) hashed raw color-visible measurements→frozen contour/profile objective→visual-minimum theta→CAD parameter table/body shape; (C) sanitized URDF 63 mm→per-view pixel/mm scale and metric profile targets→objective→theta→CAD. The synthetic anchor perturbation proves the metric relation and fixed-CAD objective are sensitive; it does **not** establish a full counterfactual formal optimizer theta under a changed physical URDF. Generator/solver source and job paths contain no GT input and the one GT evaluation start marker follows the candidate lock. This is an artifact/code-path leakage audit, not an OS-level filesystem-read trace. GT evaluation count = 1 final candidate only; formal holdout `accessed=false`, `evaluation_count=0`.

## INTERPRETATION

For this single L04 development case, the preregistered geometry and base assembly gates support `GO_C2`: real raw-image contour/profile grounding selected a parameterized CAD that outperformed the frozen Direct-Qwen result on all four reported final-link geometry metrics. The decrease in visual loss and improvement in GT metrics point in the same direction, so the frozen severe-misalignment rule did not trigger. This is encouraging but not a causal proof of which individual component—slot representation, registration, optimization, or scaffold—produced the gain. The camera registration is approximate, the top-view observed width partly exceeds the frozen parameter range, and three theta coordinates hit upper bounds. The pocket decision is unstable across R1-v3 repeats and happened to be ABSENT here. Those are material limitations for C1-v2 interpretation and for any later C2 design.

## NOT SUPPORTED / STOP

This run does **not** support general superiority over Direct or Try-5, three-link or Robot B/C generalization, KFDE effectiveness, manufacturing readiness, hidden engineering completion, or formal-holdout performance. `GO_C2` is a gate outcome, not authorization to automatically start KFDE. C1-v2 stops here pending user confirmation.
