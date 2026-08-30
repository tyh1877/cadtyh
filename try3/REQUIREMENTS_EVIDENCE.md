# Try-3 requirement-to-evidence checklist

| Requirement | Frozen / implementation evidence | Completion evidence | Status |
|---|---|---|---|
| TrySet-5-v1 is pre-registered and representative | `tryset5_v1.csv`, `tryset5_selection.md` | Hash and exactly five cases | pass |
| No prohibited input leakage | copied Try-1 image/text packets and Try-2 sanitized URDF validator | per-case input manifest + validator records | partial — planning pipeline only |
| External Kinematic Authority | frozen sanitized URDF and `AMENDMENT_EXTERNAL_KINEMATIC_AUTHORITY.md` | URDF hashes unchanged; topology/frame/limits/FK remain external evaluation authority | pass — native Fusion fields are not scientific ground truth |
| CAD–Kinematic Consistency | deterministic URDF FK occurrence placement and interface/joint-local geometry evaluators | link-component correspondence, canonical transforms, joint-centered geometry, no disconnected geometry, URDF-driven motion | pending — formal V1/V2 Fusion execution and evaluation required |
| Native Fusion Joint Semantics | `fusion_mcp_joint_capability_audit.md`; optional tiny validator if connected | semantic origin/axis/limits/motion/persistence report | environment limitation — no Fusion MCP is connected; existing API enum test is non-blocking |
| V0 is Try-2 D baseline | source run manifest checksums | V0 provenance table | pass — five source manifests successful |
| V1 has non-GT global-to-local evidence | crop-generation source + crop manifest | image hashes; no GT mesh access assertion | partial — 4/5 plans generated; 1 model-JSON failure retained |
| V2 uses MEP, interface graph, feature graph and generic skills | schemas + validators + skill logs | per-case generated plans and Fusion feature logs | partial — 5/5 plans generated; no Fusion skill execution |
| Fusion is real and editable | in-app Fusion script and saved artifacts | F3D/STEP/STL, feature/component/rebuild logs | pending — proceeds independently of optional native-joint semantics |
| Full 5x3 matrix is accounted | run manifests | every case status, including failures | partial — V0 5/5; V1 4 success + 1 planning failure; V2 5/5; formal Fusion jobs pending |
| Gap metrics are deterministic | evaluator + interface metric scripts | global/per-link/joint-local/interface/interference tables | pending — formal V1/V2 outputs required |
| Visual diagnostics exist but are not AI judgement | deterministic render script | 5 x V0/V1/V2 contact sheets | pending — formal V1/V2 outputs required |
| Resource accounting and report exist | aggregation script | token/call/Fusion-op/latency tables + `try3_report.md` | partial — planning token/call manifests available; formal execution pending |
