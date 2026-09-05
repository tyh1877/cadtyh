# Codex-agent Try-3 FreeCAD report

## Executive result

The formal Codex-agent matrix executed completely: 15/15 robot/version cells and 189/189 link/version cells exported editable FCStd plus STEP/STL with zero silent fallbacks. The architectural result is mixed: V1 clearly improves coarse geometry and connectivity over V0 on the three-case holdout, while V2 adds only a modest envelope/interface gain over V1 and increases the non-adjacent AABB-overlap interference proxy.

This is not a GLM continuation result. The producer change and interactive reproducibility limits are defined in `AMENDMENT_CODEX_AGENT_SUBSTITUTION.md`.

## Holdout results

| Metric | V0 | V1 | V2 |
| --- | ---: | ---: | ---: |
| Mean Chamfer | 0.004384 | 0.003120 | 0.002896 |
| Mean HD95 | 0.138036 | 0.108911 | 0.104910 |
| Mean voxel IoU | 0.231861 | 0.354844 | 0.373325 |
| Mean interface gap | 0.307947 | 0.222755 | 0.209830 |
| Mean disconnected-joint rate | 0.787500 | 0.233333 | 0.233333 |
| Mean non-adjacent AABB overlaps | 10.000000 | 17.000000 | 19.000000 |

V0→V1 reduces holdout Chamfer by 28.8% and HD95 by 21.1%, while voxel IoU rises by 53.0%. V1→V2 reduces Chamfer by 7.2% and interface gap by 5.8%; disconnected-joint rate is unchanged and non-adjacent overlap count worsens.

## Research questions

### RQ1: global-to-local visual grounding

Partially supported. V1 improves envelope-level geometry and joint-neighborhood connectivity over V0, including on holdout. It does not demonstrate fine visible-detail recovery: the pre-output visual labels reach the feature plans, but none are translated into an executed visible-detail operation.

### RQ2: MEP and interface-first planning

Not clearly supported as a distinct V2 effect. V2 modestly improves mean Chamfer, HD95, voxel IoU, and interface gap over V1, but it does not lower the disconnected-joint rate and increases the AABB interference proxy. The improvement is too small and mechanically incomplete to claim that full MEP/interface planning solved the assembly/detail gap.

### RQ3: RobotCAD skills and editable FreeCAD

Supported for the frozen basic skill subset, not for high-fidelity embodiment. Native Part::Box, Part::Loft, Part::Cylinder, and Part::Fuse features execute reliably, all assemblies reopen, and fallback count is zero. Shell, sweep, fillet, holes/recesses, feet, fingers, and other visible details are absent from the formal skill projection. V1/V2 avoid the V0 box-only proxy but remain coarse loft-and-cylinder assemblies.

## Coverage and failure accounting

- Formal execution: 15/15 cases and 189/189 links successful; 693 FreeCAD operations; zero fallback.
- Pre-holdout incident count: 1. The optional-URDF-origin parser failure occurred before any holdout agent output, was recorded, fixed generically, and the method was re-frozen before formal generation.
- No formal case was dropped or repaired after generation.
- Agent token counts, exact serving snapshot, sampling controls, and per-call latency are unavailable in the interactive Codex environment and are not represented as zero.

## Interpretation limits

- The five-case set is a method-development TrySet, not a large benchmark. The three-case holdout protects evaluator tuning within this continuation but is too small for a broad generalization claim.
- Visible-feature labels were authored by the same Codex agent from allowed images before formal outputs; they are not independent expert ground truth. Executed visible-feature recall is conservatively zero because those planned details have no mapped CAD operations.
- Interference is an AABB overlap proxy, not exact solid intersection volume. Axis equality is validated structurally against sanitized URDF/interface artifacts; native moving-joint behavior is outside the amended FreeCAD acceptance boundary.
- Global and per-link geometry use normalized deterministic surface sampling and rigid ICP; they measure shape similarity, not manufacturing correctness.

## Decision

The experiment supports continuing to a Try-3.x skill refinement, not claiming full Try-3 success. The next work should translate already planned visible details into robust FreeCAD hole/recess/shell/fillet/sweep operations and reduce non-adjacent interference without a case-specific repair loop. The same frozen five cases can be used for development; a new untouched set is required for a later confirmatory claim.
