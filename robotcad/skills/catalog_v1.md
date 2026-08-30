# RobotCAD Skill Catalog v1

Atomic skills: `CreateSketch`, `CreateReferencePlane`, `CreateReferenceAxis`,
`Extrude`, `Revolve`, `Loft`, `Sweep`, `Shell`, `Fillet`, `Chamfer`, `Hole`,
`Pattern`, `BooleanUnion`, `BooleanCut`.

Composite skills: `CreateCompositeLinkGeometry`, `CreateRotaryJointHousing`, `CreateRoundedLinkHousing`,
`CreateLoftedLinkHousing`, `CreateJointTransition`, `CreateFlangeInterface`,
`CreateShellHousing`, `CreateRecess`, `CreateBoss`, `ApplyFilletGroup`,
`CreateInterfacePort`.

Assembly/verification skills: `PlaceComponentFromURDF`,
`CreateSharedJointReference`, `CheckInterfaceGap`, `CheckAxisAlignment`,
`CheckInterference`, `CheckCanonicalPlacement`, `RebuildAndValidate`,
`ExportFusionArtifacts`.

The V1/V2 planner never emits Fusion API objects or Python. A deterministic
projection maps its frozen geometric plan and feature graph into these calls.
