# FreeCAD MCP capability audit

Date: 2026-09-01

## Scope

This audit is deliberately separate from the formal FreeCAD backend acceptance.
The accepted pilot path is `FreeCADCmd + FreeCAD Python API`. MCP is assessed
only as a future adapter candidate and did not block or influence pass/fail.

## Current local MCP availability

No FreeCAD MCP tools are currently exposed to this Codex agent. Therefore no
MCP server was installed, connected, or used to execute CAD operations in this
pilot.

## Candidate repositories observed

The following public repositories were reachable during audit. HEAD commits
were recorded with `git ls-remote`; license and descriptions were queried from
GitHub metadata or README where available.

| Repository | HEAD commit | License | Observed character | Acceptance use |
|---|---:|---|---|---|
| <https://github.com/neka-nat/freecad-mcp> | `0ff3dd380f0deb13677aff4d9a0c94fae326c44a` | MIT | FreeCAD addon/workbench style; README mentions control, screenshot/RPC/inspection terms | not used |
| <https://github.com/contextform/freecad-mcp> | `de4fed2a7a4352fcb0de60d2b784063c54eeb812` | not declared in API response | natural-language FreeCAD automation server; README emphasizes AI-powered CAD workflow | not used |
| <https://github.com/ATOI-Ming/FreeCAD-MCP> | `5ee3f45468026344777a1a87a1ea185abec63e74` | MIT | plugin/server/client architecture; README mentions macro creation/running and view/report commands | not used |
| <https://github.com/sandraschi/freecad-mcp> | `03b0478372cfa3ac8ebad5340d46fe53077a169d` | MIT | headless document/export and tool endpoint style; README mentions STEP/STL and CFD-related tools | not used |
| <https://github.com/spkane/freecad-addon-robust-mcp-server> | `d9a37118a8331e8739ad45fd97d027437984296f` | MIT | addon/bridge workbench style; README mentions `execute_python`, screenshots, inspection, RPC | not used |

## Preliminary classification

- Typed CAD tool coverage is not yet accepted. README text suggests some
  servers expose tools, but this was not validated by local installation.
- Live desktop/session support is plausible for addon/workbench designs, but
  remains unverified locally.
- Some candidates appear closer to transport or macro execution than a strict
  typed CAD operation adapter.
- None currently proves it can replace the FreeCADCmd/API adapter without an
  installation and local smoke test.

## Recommendation

Keep the formal backend as `FreeCADCmd + FreeCAD Python API`. If an MCP is later
installed and stable, implement it only as `FreeCADMCPAdapter` behind the same
Executable CAD IR v1 contract. Do not let MCP-specific capabilities change the
upper RobotCAD IR / Skills / Agent interface.
