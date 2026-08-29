# Try-3 requirement-to-evidence checklist

| Requirement | Frozen / implementation evidence | Completion evidence | Status |
|---|---|---|---|
| TrySet-5-v1 is pre-registered and representative | `tryset5_v1.csv`, `tryset5_selection.md` | Hash and exactly five cases | pending |
| No prohibited input leakage | copied Try-1 image/text packets and Try-2 sanitized URDF validator | per-case input manifest + validator records | pending |
| V0 is Try-2 D baseline | source run manifest checksums | V0 provenance table | pending |
| V1 has non-GT global-to-local evidence | crop-generation source + crop manifest | image hashes; no GT mesh access assertion | pending |
| V2 uses MEP, interface graph, feature graph and generic skills | schemas + validators + skill logs | per-case generated plans and Fusion feature logs | pending |
| Fusion is real and editable | in-app Fusion script and saved artifacts | F3D/STEP/STL, feature/component/rebuild logs | pending |
| URDF joint frames are preserved in Fusion | Fusion audit script | axis/origin/limit preservation for all V1/V2 cases | pending |
| Full 5x3 matrix is accounted | run manifests | every case status, including failures | pending |
| Gap metrics are deterministic | evaluator + interface metric scripts | global/per-link/joint-local/interface/interference tables | pending |
| Visual diagnostics exist but are not AI judgement | deterministic render script | 5 x V0/V1/V2 contact sheets | pending |
| Resource accounting and report exist | aggregation script | token/call/Fusion-op/latency tables + `try3_report.md` | pending |
