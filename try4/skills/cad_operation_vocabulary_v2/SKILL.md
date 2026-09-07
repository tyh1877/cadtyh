---
name: cad-operation-vocabulary-v2
description: Plan Try-4 Macro-Part geometry with profile, loft, terminal-fork, housing, web and linkage families when primitive proxy geometry cannot satisfy visible mechanical topology.
---

# CAD Operation Vocabulary v2

Select a shape family from visible evidence before estimating dimensions. Use a
closed polygon profile extrusion for non-rectangular side plates and housings; use
multi-section loft only where two or more observed sections change; create a
terminal fork from one load-carrying web that splits near the end; preserve fork
and jaw openings as explicit negative space.

Represent a joint housing with a revolved/cylindrical interface joined to its
supporting profile. Represent ribs and webs as separate, traceable features.
Represent a gripper as carriage, rails, jaws, link bars and pivots, retaining
moving-body separation. Use mirror only for evidence-supported symmetry.

Every visible Feature owns at least one native CAD operation. Keep dimensions in
the agent-authored blueprint. The compiler may dispatch on the declared generic
shape family, never robot or part ID. Do not consume GT STEP/B-Rep, exact GT
profiles, copied dimensions or a GT feature tree.

Reject a plan that uses two full-length bars for a single web with a terminal
fork, straight rods for visibly curved fork plates, or a generic box for an
integrated housing. Record unsupported detail explicitly.
