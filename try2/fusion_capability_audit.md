# Fusion capability audit — Try-2

Date: 2026-08-28

## Observed local installation

- Fusion launcher: `C:\Users\Administrator\AppData\Local\Autodesk\webdeploy\production\6a0c9611291d45bb9226980209917c3d\FusionLauncher.exe`
- Fusion executable: `C:\Users\Administrator\AppData\Local\Autodesk\webdeploy\production\9c5312dfff2e4569cd1d269973ddf11cb999f782\Fusion360.exe`
- Embedded Python/API directories: present under the Fusion production directory.

## Capability status

| Capability | Status | Evidence |
|---|---|---|
| Fusion installed | available | launcher configuration points to `Fusion360.exe` |
| Native Fusion Python API | available in application | embedded Python/API directories present |
| Document/components/features/joints | API-supported | Autodesk API documentation |
| STEP/STL export | API-supported | Autodesk ExportManager API documentation |
| Fusion MCP server/tool | **not connected** | no callable Fusion MCP tool in this Codex session |
| Headless/script command-line execution | not established | no verified official launcher interface available |

## Decision

Try-2 condition B/D must not be replaced by the primitive backend. A real
Fusion API or MCP connection is required before the 2x2 experiment can run.
The next executable action is either (1) connect a Fusion MCP server to this
Codex session, or (2) open Fusion and run an in-application Python script via
Scripts and Add-Ins, with its results exported for verification.
