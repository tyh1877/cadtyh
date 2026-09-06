---
name: try4-freecad-part-modeling
description: Translate a frozen Try-4 Mechanical Feature Graph into explicit executable CAD IR for the generic FreeCAD backend; prohibits case-specific code, missing parameters and silent operation substitution.
---

# Try-4 FreeCAD part planning

Translate feature decisions into ordered native operations with explicit local
frames, dimensions, dependencies, modes and final objects. Choose operations by
geometry: oriented boxes for straight plates/rails, lofts for real taper, cylinders
for evidence-supported rotary forms, and Boolean cuts for visible openings. Use
multiple final bodies for separate plates or jaws. Do not fuse across working gaps.

Every planned feature needs at least one operation reference. All dependencies
must precede consumers; every final body names a real operation result. Select one
native Box or Cylinder parameter for the ±5% edit test. An unavailable or failed
required operation remains incomplete. Never replace Loft/Revolve/Shell failure
with a simpler primitive while reporting success, and never emit part-specific
Python. Review and repair are outside T1.

For the frozen Phase-4 reusable strategy names and their intended scope, read
[recipe_contract.md](references/recipe_contract.md). The recipe choice and every
dimension remain Agent decisions; the compiler may not choose them from case IDs.
