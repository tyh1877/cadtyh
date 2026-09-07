# RobotCAD Try-4.1A report

## Main result

Try-4.1A completed the frozen four-part A0/A1/A2 matrix and stops before
Try-4.1B. A1 improves every aggregate geometry metric over A0 while making the
planned topology explicit. A2 further improves mean Chamfer, HD95 and silhouette,
but mean IoU falls slightly because R02_P04 and R02_P06 regress. The evidence
supports taking topology and shape-family representation into Try-4.1B, with the
translation/parameterization failures retained as the next target.

| Condition | IoU ↑ | nChamfer ↓ | nHD95 ↓ | silhouette IoU ↑ | Trace MFR |
| --- | ---: | ---: | ---: | ---: | ---: |
| A0 frozen | 0.1831 | 0.10310 | 0.34994 | 0.3665 | 1.000 |
| A1 + Topology Graph | 0.2777 | 0.06970 | 0.21112 | 0.4214 | 1.000 |
| A2 + Shape Families | 0.2683 | 0.05439 | 0.19047 | 0.4883 | 1.000 |

All 12 condition-part evaluations are CAD-valid/editable. The eight new A1/A2
plans produced FCStd/STEP/STL, four renders, native feature trees, reopen/recompute
and ±5% edit/restore evidence with zero silent fallback.

## Topology result

| Condition | Count accuracy | Branch/fork accuracy | Opening/gap recall | Relation F1 | Node-role F1 | Realized node fraction |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| A0 | 0.668 | 0.500 | 0.000 | 0.000 | 0.045 | 1.000 |
| A1 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| A2 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |

These are plan-realization metrics. Target graphs and A1/A2 graphs were authored
by the same current agent on the development images, and node realization means
their Feature references have successful native CAD operations. They prove that
the representation can encode and execute the declared topology; they do not
independently prove visual topology correctness. Contact-sheet findings remain
diagnostic rather than a main score.

## Per-part structural changes

| Part | A0 → A1 → A2 IoU | Interpretation |
| --- | --- | --- |
| R02_P02 | 0.311 → 0.400 → 0.404 | Topology Graph replaces parallel rods with a central web and terminal bifurcation; A2 rounds the fork ends. Geometry improves, although A2 HD95 is worse than A1. |
| R02_P04 | 0.193 → 0.359 → 0.234 | A1's explicit cover/channel/joint topology materially improves the housing. A2 chooses a reasonable stepped-housing family but translates it into a short block and regresses. |
| R02_P05 | 0.092 → 0.179 → 0.284 | A1 establishes branch/gap structure; A2's compact U/fork family produces the largest total improvement. It still misses accurate curved plates and flange placement. |
| R02_P06 | 0.136 → 0.173 → 0.152 | A1 adds explicit rail/jaw/link/pivot bodies. A2 still degenerates into boxes and bars and worsens IoU/HD95 versus A1. |

For all four parts, A1 topology changes the generated CAD: the operation plans
and resulting bodies differ from A0 and every declared node maps to successful
operations. R02_P02 is the clearest causal diagnostic. A2 selects plausible
generic families for all four, but family-to-profile and parameter translation is
reliable only for the central-web/fork case and directionally useful for R02_P05.

## Required conclusions

1. **A0/A1/A2 metrics:** shown above; A1 improves all aggregate geometry metrics,
   while A2 improves three of four geometry aggregates beyond A1.
2. **Four structural changes:** detailed in the per-part table and contact-sheet
   review.
3. **Topology Graph effectiveness:** supported as a representation and planning
   intervention. A0→A1 improves topology declarations and every mean geometry
   metric. Independent topology annotation is still missing.
4. **Shape-Family Vocabulary effectiveness:** mixed but positive enough for a
   larger pilot. It strongly helps R02_P05 and slightly helps R02_P02, while poor
   family translation/parameters regress R02_P04 and R02_P06.
5. **Current bottleneck:** mainly topology → shape family and shape family → CAD,
   especially profile parameterization and articulated gripper realization.
   Visual → topology is not ruled out because graph ground truth is not independent.
   FreeCAD execution is not the bottleneck in this matrix.
6. **Try-4.1B recommendation:** yes, as a Structural Replanning Pilot focused on
   stepped housing and gripper translation, with independently reviewed topology
   annotations and no expansion to Robot C.

The largest improvement is R02_P05. R02_P06 remains the strongest failure. Several
A2 outputs still rely on boxes/cylinders, most notably the gripper. Try-4.1A ends
here without implementing Try-4.1B.
