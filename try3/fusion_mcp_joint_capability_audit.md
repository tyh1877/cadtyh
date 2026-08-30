# Fusion MCP joint-capability audit — Try-3

Audit date: 2026-08-30. This document inventories the **currently callable**
MCP tool set in this Codex session, rather than assuming capabilities from the
Autodesk Python API.

## Environment

| Item | Observed state |
|---|---|
| Local Fusion executable | `Fusion360.exe` product/file version `2704.1.36` |
| Fusion MCP server registered in Codex config | none |
| Callable tool names containing `fusion` | none |
| Callable tool names for joint/assembly/axis/transform/motion | none |
| Native Fusion Python API | installed inside Fusion; callable only by a user-run in-app script |

The active Codex MCP configuration contains `node_repl` and disabled
`cua_repl`; it contains no Fusion MCP server entry. Therefore there is no
actual connected official Fusion MCP to enumerate, query, or invoke.

## Capability matrix: current MCP, not API documentation

| Requested capability | Callable MCP tool | Set | Read/query | Result |
|---|---|---:|---:|---|
| Create component/occurrence | none | no | no | unavailable |
| Joint / as-built joint | none | no | no | unavailable |
| Joint origin / reference axis/frame | none | no | no | unavailable |
| Revolute axis / arbitrary axis | none | no | no | unavailable |
| Limits | none | no | no | unavailable |
| Drive joint / motion pose | none | no | no | unavailable |
| Component occurrence transform | none | no | no | unavailable |
| Inspect/query/rebuild | none | no | no | unavailable |
| Save/reopen and re-query | none | no | no | unavailable |

## Consequences

1. A MCP-only minimal smoke test cannot be truthfully performed in this
   session. There is no MCP request to send.
2. The existing in-app Python scripts are **not Fusion MCP**, and must not be
   described as such.
3. A tiny in-app API helper is permitted only for introspection/validation if
   needed. It must not replace the formal CAD generation executor.
4. The previously observed `ZAxisJointDirection` is an internal native-joint
   representation, not sufficient evidence by itself of a world-Z motion axis.
   Its semantic axis/frame/motion requires a separate validator.

## Required next integration condition

To perform MCP-first execution, connect an official Fusion MCP server to this
Codex session and rerun this audit. Until then, the formal experiment uses the
already approved external-authoritative URDF for topology, frames, limits and
FK, and treats native Fusion joints as a non-blocking optional capability.
