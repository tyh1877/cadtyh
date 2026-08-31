# FreeCAD Backend Pilot — Capability Audit

Date: 2026-08-31

## Audit question

Can the current Codex/CLI environment directly run FreeCAD or a FreeCAD MCP/API
backend for the `freecad_backend_pilot` experiment?

## Current result

Status: **BLOCKED — FreeCAD runtime unavailable in current Agent CLI environment**

The current repository Python environment is:

- Python executable: `D:\CADtest\papertest\.venv\Scripts\python.exe`
- Python version observed: `3.12.13`
- Platform observed: `Windows-11-10.0.26200-SP0`

The following checks were run from `D:\CADtest\papertest`:

```powershell
where.exe FreeCADCmd
where.exe freecadcmd
where.exe FreeCAD
```

Result: no executable was found on `PATH`.

The following Python module import availability check was run with the project
virtual environment:

```python
import importlib.util
for module in ["FreeCAD", "Part", "PartDesign", "Sketcher", "Draft", "Mesh", "Import", "ImportGui"]:
    print(module, importlib.util.find_spec(module))
```

Observed result:

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

Observed result: no FreeCAD MCP tools were exposed to the current agent. No
typed tools such as `create_sketch`, `pad`, `revolve`, `loft`, `fillet`, or
`inspect_object` are currently callable.

Current MCP classification: **NO_FREECAD_MCP_AVAILABLE**

Because no FreeCAD MCP is available, the pilot cannot yet determine whether a
FreeCAD MCP would be a typed CAD tool server or merely an `execute_python`
transport. This must be re-audited after a FreeCAD MCP is installed/connected.

## Operation capability matrix

The prompt requires all capabilities below to be checked by current-environment
execution, not assumed from documentation. Since FreeCAD is not currently
callable, all native capability checks are blocked.

| Capability | Current evidence | Status |
|---|---|---:|
| create document | FreeCAD module/executable missing | blocked |
| create Part / Body | FreeCAD module/executable missing | blocked |
| create Sketch | FreeCAD module/executable missing | blocked |
| constraints | FreeCAD module/executable missing | blocked |
| Pad / Extrude | FreeCAD module/executable missing | blocked |
| Pocket / Cut | FreeCAD module/executable missing | blocked |
| Revolve | FreeCAD module/executable missing | blocked |
| Loft | FreeCAD module/executable missing | blocked |
| Sweep / Pipe | FreeCAD module/executable missing | blocked |
| Shell / Thickness | FreeCAD module/executable missing | blocked |
| Boolean Union | FreeCAD module/executable missing | blocked |
| Boolean Cut | FreeCAD module/executable missing | blocked |
| Fillet | FreeCAD module/executable missing | blocked |
| Chamfer | FreeCAD module/executable missing | blocked |
| Pattern | FreeCAD module/executable missing | blocked |
| Mirror | FreeCAD module/executable missing | blocked |
| placement / transform | FreeCAD module/executable missing | blocked |
| recompute | FreeCAD module/executable missing | blocked |
| inspect object tree | FreeCAD module/executable missing | blocked |
| inspect feature type | FreeCAD module/executable missing | blocked |
| read parameters/properties | FreeCAD module/executable missing | blocked |
| export FCStd | FreeCAD module/executable missing | blocked |
| export STEP | FreeCAD module/executable missing | blocked |
| export STL | FreeCAD module/executable missing | blocked |

## Experimental implication

Formal `operation_smoke_results.csv`, `link_execution_results.csv`, and
`reproducibility_results.csv` must not be reported as successful until a real
FreeCAD runtime is available and the native operations are executed without
silent fallback.

