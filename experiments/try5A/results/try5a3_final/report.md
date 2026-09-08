# Try-5A.3 final report

Status: **COMPLETE_WITH_NEGATIVE_WHOLE_ROBOT_RESULT**

The requested mechanism experiment is complete. This is a valid negative whole-robot result, not a claim that the robot is mechanically acceptable.

- Knowledge retrieval coverage: 100%; family change rate: 36.4%; CUSTOM rate: 0%.
- K0 -> K1 strict BICR: 0% -> 0%.
- K0 -> K1 exact collision events: 130 -> 181.
- K0 -> K1 spurious virtual geometry: 1 -> 0.
- Scope accuracy: 100%; physical repair success: 100%; MGR: 100%.

R0, R1, R2, R3 and R4 each have a real baseline/candidate FreeCAD B-Rep pair and passed Mechanical Meaningfulness, Interface/Attachment, Collision and Coarse Morphology acceptance gates. No whole-robot three-round repair loop was run, as required by A.3.

Conclusion: the knowledge base and scope arbiter are functional, but knowledge-guided family selection alone does not make the current whole robot acceptable. The next experiment must integrate accepted design-level repairs into the coarse reconstruction loop.
