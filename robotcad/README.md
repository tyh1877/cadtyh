# RobotCAD Skill Abstraction

This directory is the stable boundary between mechanical reasoning and CAD
execution. Agents emit only schema-validated `SkillCall` records. Backends
consume those records deterministically and return feature IDs, timing and
failures. No skill or backend is permitted to branch on a robot/case name or
inspect ground-truth geometry.

Current adapter: `backends/fusion_api/FusionAPIBackend.py` (run inside Fusion).
A future Fusion MCP adapter must consume the same `SkillCall` JSON.
