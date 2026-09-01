# FreeCAD Backend Pilot — Capability Audit

Date: 2026-09-01

## Audit question

Can the current environment run a strict FreeCAD backend for the
`freecad_backend_pilot` experiment, and should MCP block the pilot?

## Current result

Status: **PASS for local FreeCADCmd/API runtime; MCP audited separately and not
used for acceptance**.

The current repository Python environment is:

- Python executable: `D:\CADtest\papertest\.venv\Scripts\python.exe`
- Python version observed: `3.12.13`
- Platform observed: `Windows-11-10.0.26200-SP0`

The usable FreeCAD executable is:

- `D:\software\freeCAD\install\bin\freecadcmd.exe`

FreeCADCmd audit command:

```powershell
& 'D:\software\freeCAD\install\bin\freecadcmd.exe' --version
& 'D:\software\freeCAD\install\bin\freecadcmd.exe' -c "import FreeCAD; print(FreeCAD.Version()); import Part, Mesh, Import"
```

Observed FreeCAD runtime:

- FreeCAD version: `1.1.1`
- Revision: `20260414 (Git shallow)`
- Embedded Python: `3.11.14`
- `FreeCAD`, `Part`, `Mesh`, and `Import` imported successfully inside
  FreeCADCmd.

The repository `.venv` does not directly import FreeCAD modules. This is
expected; FreeCAD execution is performed through FreeCADCmd.

## MCP audit

Tool discovery found no callable FreeCAD MCP tools in the current Codex agent.
Public candidate repositories were recorded separately in
`freecad_mcp_audit.md`.

Current MCP classification: **MCP_AUDITED_NOT_USED_FOR_ACCEPTANCE**.

The pilot therefore uses this formal execution stack:

`Executable CAD IR v1 -> RobotCAD FreeCADBackend -> FreeCADCmd -> FreeCAD Python API`

## Operation capability matrix

| Capability | Current evidence | Status |
|---|---|---:|
| create document | `FreeCAD.newDocument()` used in smoke and link execution | pass |
| create Part object | `Part::Feature`, `Part::Extrusion`, `Part::Revolution`, `Part::Loft`, etc. | pass |
| create Sketch / Sketcher constraints | not part of this scoped pilot | not tested |
| Pad / Extrude | `Part::Extrusion` in smoke and link batch | pass |
| Pocket / Cut | `Part::Cut` smoke test | pass |
| Revolve | `Part::Revolution` smoke and link batch | pass |
| Loft | `Part::Loft` smoke and link batch | pass |
| Sweep / Pipe | `Part::Sweep` smoke test | pass |
| Shell / Thickness | `Part::Thickness` smoke test | pass |
| Boolean Union | `Part::Fuse` and `Part::MultiFuse` tested | pass |
| Boolean Cut | `Part::Cut` smoke test | pass |
| Fillet | `Part::Fillet` smoke and link batch | pass |
| Chamfer | `Part::Chamfer` smoke test | pass |
| Pattern | Draft array smoke test | pass |
| Mirror | `Part::Mirroring` smoke test | pass |
| placement / transform | placement used in smoke setup | pass |
| recompute | 10/10 smoke and 6/6 link batch recomputed | pass |
| inspect object tree | object name/type and shape stats logged | pass |
| inspect feature type | native feature type recorded for each operation | pass |
| read parameters/properties | object properties and shape stats recorded | pass for scoped pilot |
| export FCStd | 10/10 smoke and 6/6 link batch saved/reopened | pass |
| export STEP | 10/10 smoke and 6/6 link batch exported | pass |
| export STL | 10/10 smoke and 6/6 link batch exported | pass |

## Experimental implication

FreeCAD is no longer just a smoke-test candidate. Under the scoped pilot, it can
strictly execute generated Executable CAD IR for the six frozen links with no
silent fallback. The remaining research risk shifts upward: the planner must
produce semantically meaningful and sufficiently detailed CAD IR, rather than
vague operation descriptions or visually generic solids.
