# RobotCAD Skill Catalog v1

Atomic operation skills: `CreateSketch`, `CreateReferencePlane`,
`CreateReferenceAxis`, `Extrude`, `Revolve`, `Loft`, `Sweep`, `Shell`,
`Fillet`, `Chamfer`, `Hole`, `Pattern`, `BooleanUnion`, `BooleanCut`.

Operation-grounded modeling skills: `CreateCompositeLinkGeometry`,
`ApplyFillet`, `ApplyChamfer`, `CreateHole`, `CreatePocket`, `CreateSlot`,
`CreateGroove`, `CreateRib`, `CircularPattern`, `LinearPattern`,
`MirrorFeature`.

Historical mechanical-template names are accepted only by the Try-3 Feature
Graph projection as aliases into operation skills. They are not valid formal
`SkillCall` execution skills.

Assembly/verification skills: `PlaceComponentFromURDF`,
`CreateSharedJointReference`, `CheckInterfaceGap`, `CheckAxisAlignment`,
`CheckInterference`, `CheckCanonicalPlacement`, `RebuildAndValidate`,
`ExportFusionArtifacts`.

The V1/V2 planner never emits Fusion API objects or Python. A deterministic
projection maps its frozen geometric plan and feature graph into these calls.
