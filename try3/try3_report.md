# RobotCAD Try-3 report — Fusion API Skill-Layer pilot

## Protocol and architecture

TrySet-5-v1, Image/Text/sanitized-URDF inputs, GLM planning outputs, and the
no-GT policy remained frozen. The official Fusion MCP endpoint was unavailable,
so the user-approved executor was `RobotCAD Skill Layer -> FusionAPIBackend ->
Fusion API`. The sanitized URDF remained the authoritative topology, frame,
limit and FK source.

## Coverage

The generic six-skill smoke created real Fusion Revolve, Loft, Fillet, Extrude
and Shell features and passed rebuild/F3D/STEP/STL export. Formal coverage is
V1 4/5 successful (one malformed-JSON planning failure retained) and V2 5/5
successful. Every successful run has F3D, STEP, assembly STL and one component
STL per URDF link.

## Objective diagnostics

Distances are normalized by each robot's global diagonal after fixed
deterministic alignment.

| Metric | V1 | V2 |
|---|---:|---:|
| Whole-robot voxel IoU range | 0.079–0.133 | 0.079–0.155 |
| Whole-robot Chamfer range | 0.0228–0.0381 | 0.0228–0.0381 |
| Per-link median voxel IoU | 0.0089 | 0.0094 |
| Per-link median Chamfer | 0.0852 | 0.0797 |
| Valid joint-local median Chamfer | 0.00178 | 0.00180 |
| Median joint-centre surface gap range | 0.102–0.346 | 0.102–0.346 |

Component correspondence and planned canonical placements are exact, but
joint-neighborhood gaps are large and conservative bbox overlap counts are
10–210 pairs. V1 defaults to rounded housings; V2 adds only five extra fillet
calls across successful cases. V2 has no persuasive general gain.

## Decision

This pilot proves the reusable backend abstraction is executable, but it is
**not positive evidence** that Mechanical Embodiment + Interface-first planning
improves geometry, details or interfaces. Do not make that paper claim.

Proceed to **Try-3.x refinement**, not Try-4 repair: develop semantic composite
SkillCall parameters (housings, flanges, transitions, recesses and bosses) on a
separate development split. Do not tune using TrySet-5-v1.

## Evidence

- `results/fusion_api_skill_smoke.md`
- `results/fusion_api_case_geometry.csv`
- `results/fusion_api_per_link_geometry.csv`
- `results/fusion_api_joint_local_geometry.csv`
- `results/fusion_api_interface_consistency.csv`
