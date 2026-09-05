# Try-3 FreeCAD Full Workflow

This is the clean formal Try-3 experiment workspace.

The experiment restores the full Try-3 workflow from `try3/try3.md` and replaces
only the execution backend:

```text
Fusion MCP/API -> FreeCADCmd + FreeCAD Python API
```

It is not a continuation of the simplified link-level FreeCAD pilots. Those
pilots showed that FreeCAD can execute CAD IR, but they did not preserve the
full Try-3 architecture required for robot-like mechanical embodiment.

Current implementation status (2026-09-05): the GLM-backed run stopped after
visual scan/crop generation. The user-approved Codex continuation has now
completed a separate `codex_agent_v1` V0/V1/V2 FreeCAD matrix. All 15
case/version cells and 189 link/version cells executed and exported with zero
silent fallback. The architectural result is mixed: V1 improves coarse geometry
and connectivity over V0; V2 provides only a modest further gain and worsens the
non-adjacent overlap proxy. See
`results/codex_agent_v1_try3_report.md` and
`AMENDMENT_CODEX_AGENT_SUBSTITUTION.md`.
