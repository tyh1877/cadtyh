# RobotCAD Skill Catalog v1

Formal executable CAD operation skills: `CreateSketchProfile`, `Extrude`,
`Loft`, `ApplyFillet`, `ApplyChamfer`, `CreateHole`, `BooleanCut`,
`CircularPattern`.

`CreateCompositeLinkGeometry` is retained only for legacy compatibility.
Current Try-3 formal jobs should prefer explicit operation sequences:
sketch profiles, extrudes, lofts, and then modifying operations. Every CAD
operation must map to the named Fusion operation in the backend and smoke logs;
no operation may silently degrade to a different formal Skill name.

Historical mechanical-template names are accepted only by the Try-3 Feature
Graph projection as aliases into operation skills. They are not valid formal
`SkillCall` execution skills.

Assembly/verification skills: `PlaceComponentFromURDF`,
`CreateSharedJointReference`, `CheckInterfaceGap`, `CheckAxisAlignment`,
`CheckInterference`, `CheckCanonicalPlacement`, `RebuildAndValidate`,
`ExportFusionArtifacts`.

The V1/V2 planner never emits Fusion API objects or Python. A deterministic
projection maps its frozen geometric plan and feature graph into these calls.
