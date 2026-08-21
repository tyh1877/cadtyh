# Mesh Oracle Diagnostic report

## Diagnostic decision: KINEMATIC_RESIDUAL_SUPPORTED

This is a point-cloud mesh representation diagnostic, not a native STL-understanding or main benchmark result.

| condition | executed | failed | Graph F1 | joint type | axis error | origin error | motion translation |
|---|---:|---:|---:|---:|---:|---:|---:|
| I_image_baseline | 7 | 0 | 0.4615384615384615 | 0.375 | 90.0 | 0.16628177251048046 | 0.1848394250002462 |
| M_monolithic_mesh | 5 | 2 | 0.0 | 0.0 | None | None | None |
| L_per_link_mesh_oracle | 5 | 2 | 0.6 | 0.5 | 22.5 | 0.19608970030442327 | 0.1936854244898613 |

I=image baseline; M=unlabeled merged surface points; L=anonymous per-link surface-point and mesh oracle. Geometry is not a reconstruction score for L. M motion metrics are omitted when only the root link matches.

M available on at least five cases: True; residual L kinematic gap: True.

Interpretation: if L remains poor in graph/origin/motion, kinematic recovery remains difficult even after geometry and part decomposition are supplied. If L is nearly correct, the bottleneck is primarily perception/decomposition.
