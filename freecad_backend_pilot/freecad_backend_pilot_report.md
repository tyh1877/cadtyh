# FreeCAD Backend Pilot Report

Date: 2026-08-31

## Decision

Current state: **BLOCKED before formal pilot execution**.

Reason: the current Agent CLI environment cannot call FreeCAD. No `FreeCADCmd`
executable, FreeCAD Python modules, or FreeCAD MCP typed tools are available.

This is not a FreeCAD backend failure and not a RobotCAD method failure. It is
an environment blocker discovered during the required capability audit.

## Required questions

1. Current FreeCAD version: unavailable; FreeCAD is not currently callable.
2. Current FreeCAD MCP: none exposed to the current agent.
3. Is the MCP a typed CAD tool MCP: not applicable; no FreeCAD MCP available.
4. Operations possible purely through MCP: none in current environment.
5. Operations needing FreeCAD API helper: all operations would need API helper
   unless a typed MCP is later installed.
6. Revolve native execution: not tested; blocked by missing FreeCAD runtime.
7. Loft native execution: not tested; blocked by missing FreeCAD runtime.
8. Sweep/Pipe native execution: not tested; blocked by missing FreeCAD runtime.
9. Shell/Thickness native execution: not tested; blocked by missing FreeCAD runtime.
10. Boolean/Fillet/Chamfer/Pattern stability: not tested; blocked.
11. Silent fallback: none executed; no fallback-based success is reported.
12. Six-link execution: 0/6 executed; blocked before formal execution.
13. FCStd save/reopen: not tested; blocked.
14. STEP/STL export: not tested; blocked.
15. Feature tree/object property inspection: not tested; blocked.
16. Per-operation failure localization: logging schema defined, but not executed.
17. Repeated-run stability: not tested; blocked.
18. Is FreeCAD currently better than Fusion-script pipeline: not yet proven.
19. Recommend migrating Try-3 to FreeCAD now: **no**; first install/connect
    FreeCAD and pass native operation smoke tests.
20. Missing backend capabilities: current environment needs a real FreeCAD
    runtime, then native implementations for Revolve, Loft, Sweep/Pipe,
    Thickness/Shell, Boolean operations, Fillet, Chamfer, Pattern, Mirror,
    feature introspection, FCStd save/reopen, and STEP/STL export.

## Next required user/environment action

Install FreeCAD or expose a FreeCAD MCP/API server to this Codex environment.
After that, rerun the audit and proceed to operation-level smoke tests.

