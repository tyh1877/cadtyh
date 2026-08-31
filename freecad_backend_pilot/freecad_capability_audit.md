# FreeCAD Backend Pilot — Capability Audit

Date: 2026-08-31

## Audit question

Can the current Codex/CLI environment directly run FreeCAD or a FreeCAD MCP/API
backend for the `freecad_backend_pilot` experiment?

## Current result

Status: **PASS for local FreeCADCmd/API runtime; FreeCAD MCP still unavailable**

The current repository Python environment is:

- Python executable: `D:\CADtest\papertest\.venv\Scripts\python.exe`
- Python version observed: `3.12.13`
- Platform observed: `Windows-11-10.0.26200-SP0`

After the user installed FreeCAD, the following executable was found:

- `D:\software\freeCAD\install\bin\freecadcmd.exe`

The following checks were run from `D:\CADtest\papertest`:

```powershell
where.exe FreeCADCmd
where.exe freecadcmd
where.exe FreeCAD
```

Result: no executable was found on `PATH`, but recursive local search found
`D:\software\freeCAD\install\bin\freecadcmd.exe`.

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

The following Python module import availability check was run with the project
virtual environment:

```python
import importlib.util
for module in ["FreeCAD", "Part", "PartDesign", "Sketcher", "Draft", "Mesh", "Import", "ImportGui"]:
    print(module, importlib.util.find_spec(module))
```

Observed result from the repository `.venv`:

| Module | Availability |
|---|---:|
| `FreeCAD` | missing |
| `Part` | missing |
| `PartDesign` | missing |
| `Sketcher` | missing |
| `Draft` | missing |
| `Mesh` | missing |
| `Import` | missing |
| `ImportGui` | missing |

## MCP audit

Tool discovery was queried for FreeCAD MCP / CAD typed tools.

Observed result: no FreeCAD MCP tools are exposed to the current agent. No
typed tools such as `create_sketch`, `pad`, `revolve`, `loft`, `fillet`, or
`inspect_object` are currently callable.

Current MCP classification: **NO_FREECAD_MCP_AVAILABLE**

Because no FreeCAD MCP is available, the pilot cannot yet determine from local
execution whether a third-party FreeCAD MCP would be a typed CAD tool server or
merely an `execute_python` transport. This must be re-audited after a specific
MCP repository is installed/connected.

## Operation capability matrix

The prompt requires all capabilities below to be checked by current-environment
execution, not assumed from documentation. FreeCADCmd is callable, so native
capability checks can be performed through the FreeCAD Python API helper path.
MCP-specific checks remain blocked.

| Capability | Current evidence | Status |
|---|---|---:|
| create document | `FreeCAD.newDocument()` used in smoke runner | pass |
| create Part / Body | `Part::Box`, `Part::Cylinder`, `Part::Feature` used | pass |
| create Sketch | not exercised as Sketcher-native constrained sketch | not tested |
| constraints | not exercised as Sketcher constraints | not tested |
| Pad / Extrude | native type exists; not in the 10-operation smoke matrix | available |
| Pocket / Cut | `Part::Cut` smoke test | pass |
| Revolve | `Part::Revolution` smoke test | pass |
| Loft | `Part::Loft` smoke test | pass |
| Sweep / Pipe | `Part::Sweep` smoke test | pass |
| Shell / Thickness | `Part::Thickness` smoke test | pass |
| Boolean Union | `Part::Fuse` smoke test | pass |
| Boolean Cut | `Part::Cut` smoke test | pass |
| Fillet | `Part::Fillet` smoke test | pass |
| Chamfer | `Part::Chamfer` smoke test | pass |
| Pattern | Draft array smoke test, stored as `Part::FeaturePython` with Array proxy | pass |
| Mirror | `Part::Mirroring` smoke test | pass |
| placement / transform | placement used in smoke setup | pass |
| recompute | 10/10 smoke tests recomputed | pass |
| inspect object tree | object type/name and shape stats logged | pass |
| inspect feature type | 10/10 executed native types recorded | pass |
| read parameters/properties | basic object properties and shape stats recorded | partial |
| export FCStd | 10/10 smoke tests saved FCStd | pass |
| export STEP | 10/10 smoke tests exported STEP | pass |
| export STL | 10/10 smoke tests exported STL | pass |

## Experimental implication

The FreeCAD native operation smoke test is successful through FreeCADCmd/API.
The six existing link plans are not executed because they are vague semantic
plans and fail Executable CAD IR completeness checks. This is an upstream IR
blocker, not a FreeCAD native-operation blocker.
