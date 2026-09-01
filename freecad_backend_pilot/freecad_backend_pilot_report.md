# FreeCAD Backend Pilot Report

Date: 2026-09-01

## Decision

Current state: **pass for the scoped backend pilot**.

FreeCADCmd + FreeCAD Python API is a viable strict RobotCAD backend candidate.
It executed the required native operation smoke tests and the six frozen-link
Executable CAD IR batch without silent fallback.

Important boundary: this pilot validates backend executability and
reproducibility, not visual resemblance to a full industrial robot arm. The
current generated links are deliberately simple operation-bearing solids.

## Environment

- FreeCADCmd: `D:\software\freeCAD\install\bin\freecadcmd.exe`
- FreeCAD version: `1.1.1`
- Revision: `20260414 (Git shallow)`
- Embedded Python: `3.11.14`
- Repository Python: `.venv\Scripts\python.exe`
- Current local FreeCAD MCP: none exposed to this agent
- Formal acceptance path: `FreeCADCmd + FreeCAD Python API`
- MCP status: capability audit only; not used for pass/fail

## Original six-link plan check

The frozen six `operation_plan_pilot` link plans were first checked directly.
They remain non-executable vague plans:

- Links total: `6`
- Directly ready links: `0`
- IR-incomplete links: `6`
- Operations total in old plans: `65`
- IR-complete operations in old plans: `0`

This result is retained because it explains why the upstream LLM must emit
Executable CAD IR rather than natural-language operation plans.

## Executable CAD IR generation

A new Qwen-based generation script regenerated Executable CAD IR v1 for the
same six frozen links. It uses the existing Alibaba/Qwen configuration and does
not use GT mesh, STEP, CAD, or product identity.

Result:

- Provider/model: `qwen3.7-plus`
- Links total: `6`
- Output links: `6`
- Schema-valid links: `6`
- IR-complete links: `6`
- Operations total: `30`

The generator performs deterministic alias canonicalization only and adds a
geometry sanity gate for FreeCAD-native revolve: with the current XY profile
construction, the revolution axis must lie in the profile plane. This prevented
the earlier invalid Z-axis revolve failure from being counted as backend
success.

## Operation-level smoke results

All required operation-level smoke tests passed through FreeCADCmd + FreeCAD
Python API:

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

## Six-link FreeCAD execution

Only schema-valid and IR-complete generated IRs were executed. All six completed
under strict native operation mapping.

- Links total: `6`
- Successful links: `6`
- Failed/incomplete links: `0`
- Operations total: `30`
- Native-successful operations: `30`
- Semantic-match operations: `30`
- Silent fallbacks: `0`
- Batch Execution Success Rate: `6/6`
- FCStd Save/Reopen Rate: `6/6`
- STEP Export Rate: `6/6`
- STL Export Rate: `6/6`
- Feature Introspection Coverage: `6/6`

The initial 5/6 result exposed two real issues:

1. `Part::Fuse` was incorrectly used with a `Tools` property. This was a backend
   bug and was fixed by using `Part::Fuse.Tool` for one tool and
   `Part::MultiFuse.Shapes` for multiple tools.
2. One regenerated IR used a Z-axis revolve with an XY profile, producing an
   invalid FreeCAD shape. This was fixed by making the generator reject that
   invalid geometry pattern before backend execution.

Neither fix introduced a silent fallback.

## Reproducibility

Two reproducibility checks were run:

- Native revolve smoke: 3 trials, reproducible.
- Complex generated link `dev_arm-dcc2b0ce1e/L2`: 3 trials, reproducible.

For the complex link, all three trials produced the same feature type sequence:

`Part::Extrusion -> Part::Revolution -> Part::Loft -> Part::MultiFuse -> Part::Fillet`

The bbox, volume, face count, edge count, and export status were also stable.

## MCP audit

FreeCAD MCP was not available locally, so it was not part of formal acceptance.
Candidate repositories were recorded in `freecad_mcp_audit.md`. The current
recommendation is to keep MCP as a future adapter only:

`Executable CAD IR v1 -> FreeCADMCPAdapter`

It must not alter the upper RobotCAD IR / Skills / Agent interface.

## Recommendation

Move the next Try-3 backend direction from Fusion-script execution to
FreeCADCmd/API. The engineering reason is concrete: FreeCAD is batch-callable
from CLI, supports the required native operations, preserves feature/object
introspection, exports FCStd/STEP/STL, and is reproducible under the scoped
pilot.

Do not claim that this proves high-quality robot-arm reconstruction yet. It
proves that the backend can strictly execute richer CAD operations if the
upstream planner emits complete Executable CAD IR.
