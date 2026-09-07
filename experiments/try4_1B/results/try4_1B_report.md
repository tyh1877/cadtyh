# RobotCAD Try-4.1B report

## Main result

Try-4.1B completed B0/B1 and one triggered B2 structural replan for exactly
R02_P04 and R02_P06. It stops before Try-4.1C. Both B1 cases failed the frozen
Structure Realization Gate and therefore both received B2. Neither B2 passes the
final combined gate.

| Condition | mean IoU ↑ | mean nChamfer ↓ | mean nHD95 ↓ | mean silhouette IoU ↑ |
| --- | ---: | ---: | ---: | ---: |
| B0 frozen A1 | 0.2660 | 0.06170 | 0.19160 | 0.4041 |
| B1 executable family | 0.2614 | 0.06004 | 0.18177 | 0.4258 |
| B2 structural replan | 0.2494 | 0.05826 | 0.18078 | 0.4363 |

B1/B2 improve average distance and silhouette metrics but not IoU. Every new
FCStd is valid, reopenable, recomputable and editable; STEP/STL exports succeed and
silent fallback is zero. FreeCAD execution remains outside the main bottleneck.

## Independent-topology and realization metrics

| Condition | Node-role F1 | Relation F1 | Count accuracy | Gap recall | Symmetry accuracy | Substructure recall | Family realization |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| B0 | 0.143 | 0.059 | 0.883 | 0.000 | 0.143 | 1.000 | 0.000 |
| B1 | 1.000 | 0.293 | 1.000 | 1.000 | 0.833 | 1.000 | 1.000 |
| B2 | 0.958 | 0.278 | 0.909 | 1.000 | 0.786 | 1.000 | 1.000 |

Topology GT was frozen in evaluator-only files before B1 and was not read by the
generator. It is procedurally independent, but the offline rule/manual annotation
and generator decisions were both produced in the same interactive Codex session;
there is no independent human annotator. Relation F1 stays low because executable
instances encode many connections as generic `connected_to` rather than the more
specific attachment relations in topology GT.

## Per-part outcome

### R02_P04 complex stepped housing

| Condition | IoU | nChamfer | nHD95 | silhouette IoU |
| --- | ---: | ---: | ---: | ---: |
| B0 | 0.3588 | 0.06919 | 0.20178 | 0.4414 |
| B1 | 0.3317 | 0.07134 | 0.19181 | 0.4528 |
| B2 | 0.3435 | 0.06457 | 0.18996 | 0.4783 |

B1's executable schema changes the CAD materially: base, upper cover, boss,
transition, side walls, recess and mounting holes have separate operations. B2 is
a TRUE_STRUCTURAL_REPLAN from `stepped_housing` to
`compound_profile_housing`, retaining the proximal boss and replacing the short
stepped composition with low compound profiles and a transition loft. B2 improves
every geometry metric over B1 and visually reduces block degeneration, but IoU
remains below 0.35 and relation F1 below 0.8.

### R02_P06 gripper

| Condition | IoU | nChamfer | nHD95 | silhouette IoU |
| --- | ---: | ---: | ---: | ---: |
| B0 | 0.1733 | 0.05421 | 0.18142 | 0.3667 |
| B1 | 0.1911 | 0.04874 | 0.17172 | 0.3987 |
| B2 | 0.1553 | 0.05196 | 0.17160 | 0.3942 |

B1 explicitly realizes carriage, two rails, sliders, jaws, linkages, four pivot
features and a working gap. B2 is a TRUE_STRUCTURAL_REPLAN to
`articulated_plate_gripper`: it adds jaw adapters and replaces box linkage/jaw
strategies with polygon profiles while protecting the rail pair. The mechanism is
more explicit, but B2 regresses IoU, Chamfer and silhouette versus B1. It has not
escaped box/bar dominance sufficiently.

## Required answers

1. Main B0/B1/B2 geometry metrics are reported above.
2. Independent topology metrics improve strongly from B0 to B1 in node roles,
   count, gaps and symmetry; relation F1 remains weak and B2 does not improve it.
3. B1 executable schemas genuinely change CAD operations and substructure trees.
4. P04 substantially reduces short-block degeneration, especially in B2, but is
   still an approximate exterior.
5. P06 begins a real carriage/rail/slider/jaw/link/pivot/gap decomposition, yet
   still looks dominated by simple boxes/bars.
6. Declared Substructure Realization Recall is 1.0 for B1/B2; this proves operation
   realization, not visual correctness.
7. Hardest family parameters are P04 side/top profile stations and transition
   proportions, plus P06 jaw contour, rail-to-jaw orientation, pivot endpoints,
   linkage placement and working-gap scale.
8. The hardest substructures are the articulated jaw-linkage-pivot system, then
   the P04 cover/side-wall/rear-transition relationship.
9. TRUE_STRUCTURAL_REPLAN occurs for both cases.
10. P04 changes family and compound construction while preserving the boss; P06
    changes family, substructure graph and CAD strategy while preserving rails.
11. B2 is better than B1 for P04 and worse for P06; structural replanning is not
    uniformly beneficial.
12. FreeCAD remains reliable and is not the main bottleneck.
13. The bottleneck has narrowed to family parameterization → CAD for P04 and
    articulated mechanism representation/parameterization for P06. Relation typing
    also limits topology evaluation.
14. A three-robot Try-4.1C run is **not recommended yet**. First fix relation-typed
    compilation and obtain an independently reviewed P06 mechanism that improves
    rather than regresses geometry; keep Robot C frozen.

Executable Shape-Family realization is worth retaining, and the P04 structural
replan is encouraging. The mixed P06 result prevents a full-scale conclusion.
