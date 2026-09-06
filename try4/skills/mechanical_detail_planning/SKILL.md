---
name: try4-mechanical-detail-planning
description: Convert Try-4 visual evidence, mechanical interpretation and RobotPart-LOD into a traceable Mechanical Feature Graph for one Macro-Part; does not emit FreeCAD code or perform repair.
---

# Try-4 mechanical detail planning

Create a stable feature for every expected requirement. Each feature cites exact
packet views and records region, shape family, dimensions with uncertainty,
dependencies, critical flag, confidence and intended native CAD strategy. Critical
functional/interface requirements must be executable. Mark ordinary unsupported
detail explicitly; do not silently drop it or call it complete.

Order features as primary envelope, functional/interface geometry, structural
detail, then surface treatment. Preserve open spaces and separate moving bodies.
Use a feature only when its evidence supports its location and role. The graph is
the authority for CAD IR: downstream operations must cite feature IDs and may not
invent unrelated geometry.

