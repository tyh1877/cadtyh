# FreeCAD Backend Pilot Report

Date: 2026-08-31

## Decision

Current state: **partial pass**.

FreeCAD itself is a strong backend candidate: the local `FreeCADCmd` runtime
successfully executed the required operation-level native smoke tests without
silent fallback.

However, the existing six `operation_plan_pilot` link plans cannot be executed
under the strict pilot rules because they are vague semantic plans, not
Executable CAD IR v1. Link execution is therefore blocked at `IR_VALIDATION`,
not at FreeCAD native operation execution.

## Environment

- FreeCADCmd: `D:\software\freeCAD\install\bin\freecadcmd.exe`
- FreeCAD version: `1.1.1`
- Revision: `20260414 (Git shallow)`
- Embedded Python: `3.11.14`
- Current FreeCAD MCP: none exposed to the current agent
- MCP classification: `NO_FREECAD_MCP_AVAILABLE_IN_CURRENT_AGENT`

## Operation-level smoke results

All required operation-level smoke tests passed through FreeCADCmd + FreeCAD
Python API helper:

| Operation | Native type | Result |
|---|---|---:|
| Revolve | `Part::Revolution` | pass |
| Loft | `Part::Loft` | pass |
| Sweep / Pipe | `Part::Sweep` | pass |
| Shell / Thickness | `Part::Thickness` | pass |
| Boolean Union | `Part::Fuse` | pass |
| Boolean Cut | `Part::Cut` | pass |
| Fillet | `Part::Fillet` | pass |
| Chamfer | `Part::Chamfer` | pass |
| Pattern | Draft Array proxy object | pass |
| Mirror | `Part::Mirroring` | pass |

Aggregate:

- Native Operation Execution Rate: `10/10`
- Semantic Execution Fidelity: `10/10`
- Silent Fallback Rate: `0/10`
- Recompute Success Rate: `10/10`
- FCStd Save/Reopen Success Rate: `10/10`
- STEP Export Success Rate: `10/10`
- STL Export Success Rate: `10/10`

## Six-link plan execution

The frozen six existing link plans were checked for Executable CAD IR v1
completeness.

Result:

- Links total: `6`
- Ready executable links: `0`
- IR-incomplete links: `6`
- Operations total: `65`
- IR-complete operations: `0`
- IR-incomplete operations: `65`

This is the correct strict outcome. The old plans contain statements such as
`"operation": "Revolve"` and natural-language descriptions, but do not provide
required executable fields such as sketch plane, closed profile, axis, angle,
operation mode, dependencies, edge selectors, or face selectors.

The backend did not guess missing geometry and did not replace complex
operations with primitive approximations.

## Reproducibility

Native revolve smoke was repeated 3 times:

- success consistency: pass
- bbox consistency: pass
- volume consistency: pass
- topology count consistency: pass

Complex link reproducibility was not run because the selected link plan is
`IR_INCOMPLETE`.

## Required questions

1. Current FreeCAD version: `1.1.1`.
2. Current FreeCAD MCP: none exposed to this agent.
3. Is the MCP a typed CAD tool MCP: not currently testable; no MCP is connected.
4. Operations possible purely through MCP: none in the current environment.
5. Operations needing FreeCAD API helper: all tested operations currently use
   the FreeCAD API helper path.
6. Revolve native execution: yes, `Part::Revolution`.
7. Loft native execution: yes, `Part::Loft`.
8. Sweep/Pipe native execution: yes, `Part::Sweep`.
9. Shell/Thickness native execution: yes, `Part::Thickness`.
10. Boolean/Fillet/Chamfer/Pattern stability: passed in deterministic smoke.
11. Silent fallback: no; observed fallback rate is `0`.
12. Six links complete execution: `0/6`, because all six plans are
    `IR_INCOMPLETE`.
13. FCStd batch save/reopen: yes for `10/10` smoke tests.
14. STEP/STL export: yes for `10/10` smoke tests.
15. Feature tree/object properties inspection: basic feature type/name and
    shape stats are inspectable; deeper dependency/constraint introspection is
    still partial.
16. Per-operation failure localization: yes for smoke execution and link IR
    validation.
17. Repeated-run stability: native revolve smoke is stable across 3 runs.
18. Is FreeCAD better than the current Fusion-script pipeline for research
    experiments: yes as a backend candidate, because it is batch-callable from
    CLI and supports native strict operations without manual GUI execution.
19. Recommend migrating Try-3 now: migrate the backend direction to FreeCAD,
    but do not rerun full Try-3 until the upstream planner emits Executable CAD
    IR v1.
20. Missing backend capabilities: executable IR generation, Sketcher constraint
    smoke tests, deeper feature dependency introspection, full link execution,
    and optional evaluation of a third-party FreeCAD MCP.

## Recommendation

Use FreeCADCmd + FreeCAD Python API helper as the next primary backend path.
Treat third-party FreeCAD MCP as optional infrastructure to evaluate later. The
immediate blocker is not FreeCAD; it is the upstream output format. The next
RobotCAD revision should make the LLM emit Executable CAD IR v1 with complete
operation parameters.

