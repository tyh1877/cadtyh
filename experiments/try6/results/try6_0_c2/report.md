# Try-6.0-C2 KFDE — L04 frozen execution record

**Execution stopped with no feasible C2 candidate. The frozen protocol does not define an exact terminal decision label for this state.** Do not reclassify this as `GO_TRY6_1`, `KFDE_INACTIVE`, or a final geometry/mechanics comparison. The user's decision on categorical closure is pending; no KFDE tuning or C2-v2 was started.

## FACTS — C1 freeze and parity

C1-v2 remained frozen as `GO_C2`; its slot judgement was reused verbatim (`main_housing=PRESENT`, `visible_pocket=ABSENT`, `profile_transition=PRESENT`). C2 made **zero VLM calls** and did not vote/reclassify Pocket. Independent pre-run checks found the same canonical KFDG, six active theta variables, three inactive parameters, original bounds/initial values, raw-image hashes, right/top registration, 63 mm anchor, contour/profile visual objective and 0.5/0.5 weights, seeded bounded Sobol→coordinate-search configuration, 32 maximum proposals, unchanged FreeCAD compiler, and the same final evaluators. Frozen C1 exact geometry/mechanics values are preserved in `frozen_c1/c1_reference.json` for **post-lock comparison only**; KFDE construction and the C2 optimizer did not read that file or C1 failed-case IDs/collision locations.

## FACTS — KFDE construction

The keepout used the sanitized URDF/FK in **L04 local millimetres** and frozen physical L03/L05/L06/L07 FCStd geometries. L03 was transformed over seven inclusive J03 limit samples (−2.146755 to +1.745329 rad); L06 over four cardinal J05 continuous angles (0, π/2, π, 3π/2); L05 and L07 each have one fixed relative pose. These 13 per-neighbor relative poses are independent of the final 96-case development mechanics set. J02 upstream motion does not change L03's relative pose to L04 once J03 is fixed, so it was not an additional relative sweep axis.

The hard check operates on candidate mutable body **outside** the frozen L04 scaffold and exact proximal bore/mating-envelope shapes; frozen scaffold/interface occupancy itself is not automatically forbidden. Engineering clearance margin was **0 mm**; the predeclared numerical BREP-volume tolerance was **1e-6 mm³**. The 0.6 mm frozen J03/J04 interface clearance was **not** repurposed as a global KFDE margin. The keepout is non-empty (compound volume proxy 128564.11 mm³), all 13 component BREPs independently reopen/validate, J03/J05 pose changes alter BREP geometry, FK transforms were independently recomputed in L04 frame, and the frozen scaffold has 0 mm³ residual after the allowed-region subtraction. No GT or C1 final evaluator diagnostics entered construction.

## FACTS — C1 candidate replay and activity

All **32/32** frozen C1 solver CAD candidates were loaded as-is, not regenerated. Exact BREP feasibility rejected **32/32** (rejection rate 1.0); the original visual winner `candidate_031` was infeasible, with a maximum single-pose forbidden intersection of **727.97079 mm³**. This is a meaningful activity result, not numerical noise. Descriptively, maximum forbidden volume correlated most strongly in this 32-proposal sample with distal height (Spearman ρ≈0.858) and distal width (ρ≈0.744); all samples were infeasible, so these correlations do **not** distinguish feasible from infeasible designs or establish causality. The activity gate permitted a fresh formal C2 optimizer run; no old C1 candidate was chosen as C2.

## FACTS — formal C2 search and stop

The pre-registered C2 search used the **same C1 first 17 proposals**: frozen initial theta plus 16 seed-matched bounded Sobol samples, independently verified against C1. The C1 optimizer family stops after this block if no legal visual candidate exists. Consequently the maximum budget remained 32, but the actual search naturally terminated after **17 proposals**: 17 successful CAD builds, 17 exact KFDE checks, **17 hard rejections**, **0 feasible candidates**, **0 renders**, **0 visual objective evaluations**, **0 infrastructure-invalid builds**, and **no theta***. Rejected candidates never entered visual ranking; no kinematic penalty or mechanics/GT score was added to `L_visual`. Their maximum single-pose forbidden intersections ranged from **142.21303 to 756.60143 mm³**, far above the frozen 1e-6 mm³ tolerance. Recorded C2 solver runtime was about **29.19 s**, including **17.12 s** of KFDE checks; construction was **1.33 s** and 32-case replay **31.98 s**.

Because no feasible theta exists **among the frozen proposals**, there is no final C2 CAD/parameter table or `final_candidate_lock.json`. The experiment therefore correctly made **0 GT geometry evaluations**, **0 final 96-case mechanics evaluations**, and **0 formal holdout evaluations**. C1-v2 remains the only evaluated geometry/mechanics result; C2/C1 geometry-preservation, non-regression and ≥10% incremental-benefit gates are **not evaluable**. In particular, no claim that mechanics improved is supported. The result does not prove the entire continuous bounded design domain is empty—only that the unchanged C1 search policy found no feasible design within its first 17 proposals.

| Frozen final-link geometry reference | C1-v2 exact | C2 |
|---|---:|---:|
| voxel IoU | 0.1881884426368412 | not evaluated |
| silhouette IoU | 0.3462839613652157 | not evaluated |
| normalized Chamfer | 0.1010314900985874 | not evaluated |
| normalized HD95 | 0.29211681006226614 | not evaluated |

| Frozen mechanics reference | C1-v2 exact | C2 |
|---|---:|---:|
| BICR / connected solids | 1.0 / 1 | no final CAD |
| J03 JR3 | 1.0 | not evaluated |
| GCFR | 0.8020833333333334 | not evaluated |
| collision events | 42 | not evaluated |
| intersection volume, mm³ | 26456.388605736887 | not evaluated |
| failed coupled configurations | 19 | not evaluated |

## INTERPRETATION — protocol gap, not a post-hoc repair invitation

KFDE is active and auditable, but extremely restrictive for the frozen C1 proposal stream. The replay and formal search both show substantial exact overlaps, including L05 fixed-mount and L06 wrist neighbors; the allowed-region policy or domain geometry could be responsible, but the protocol forbids changing it after replay. No margin, joints, sweep density, neighbor set, bounds, optimizer, pocket state, or objective was retuned.

The allowed decision vocabulary lacks a category for “KFDE constructed and active, but **no feasible candidate before final evaluation**.” `KFDE_OVERCONSTRAINED` is explicitly defined only when **final mechanics improve and geometry preservation fails**; those metrics do not exist here. `KFDE_CONSTRUCTION_BLOCKED` would contradict the independently passing construction audit. Assigning either without a documented protocol amendment would fabricate an evaluation state. The exact execution outcome and this classification gap are frozen in `audit/independent_no_feasible_validation.json`; categorical direction has been requested from the user.

## NOT SUPPORTED / STOP

No C2 final GT or mechanical comparison, KFDE incremental benefit, geometry-preservation claim, search-efficiency superiority, Try-6.1 expansion, editability result, manufacturing readiness, three-link/Robot B/C generalization, or formal-holdout conclusion is supported. This turn stops without C2 retuning, final evaluation, C2-v2, or L03/L07 work.
