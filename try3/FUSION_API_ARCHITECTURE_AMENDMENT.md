# Try-3 amendment: RobotCAD Skill Layer -> Fusion API Backend

Approved by the user on 2026-08-30. The official Fusion MCP endpoint is not
available in this environment. Try-3 therefore freezes the execution boundary
as `RobotCAD Skill Layer -> FusionAPIBackend -> Fusion API`.

Agents are mechanical planners only. They emit or deterministically project to
validated `robotcad.skill_call.v1` records; they never generate Fusion Python
or use Fusion API objects. The backend is a generic deterministic adapter that
does not inspect images, robot names, GT geometry, evaluator scores, or modify
MEP/interface/URDF decisions. A future Fusion MCP adapter must consume the
same SkillCall schema.

The historical `Try3FusionBatch.py` is retained as an audit artifact and is
deprecated for formal execution. Formal execution begins only after the six
generic composite-skill smoke tests have produced editable F3D, STEP and STL
artifacts with a successful rebuild.

Repair note, 2026-08-30: the first formal Fusion API batch is invalidated for
geometry evaluation because the projection layer collapsed each planner link
to a single envelope skill and let missing primitives become a universal
20 mm rounded placeholder. The formal batch gate now requires
`CreateCompositeLinkGeometry` with explicit planner-authored primitives for
each link before a case can enter `READY`.
