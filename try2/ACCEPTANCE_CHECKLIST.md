# Try-2 completion checklist

This checklist is the only completion gate for Try-2. A script ending, an F3D
file existing, or a partial aggregate does not establish completion.

| Requirement from `try2.md` | Evidence required | Current status |
|---|---|---|
| Frozen 15-case Image+Text v1 inputs reused | frozen manifest and packet hashes | PASS |
| Sanitized URDF removes geometry and identity leakage | 15 validator reports | PASS |
| A/C primitive runs retain every terminal case | manifests and evaluator outcomes | PASS |
| B/D use real Fusion API rather than primitive compiler | native F3D/STEP/STL plus Fusion execution log | PASS, subject to assembly checks |
| Fusion components assembled at canonical FK pose | deterministic URDF/blueprint FK placement plus occurrence/component audit | PASS for successful B/D executions |
| C/D kinematic authority | sanitized URDF drives canonical placement and exported evaluator URDF | PASS |
| Fusion joints preserve type, axis, origin and limits | native joint audit vs skeleton/blueprint | NOT A GATE: optional demonstration only, by user-approved amendment |
| Native editability | component/feature/joint/rebuild/native-save audit | PARTIAL (rebuild audit pending) |
| All B/D geometry sent to evaluator comes from Fusion occurrence STL | per-component Fusion export manifest | PASS for successful B/D executions |
| Per-link geometry metrics | per-link Chamfer table | PASS |
| Joint-local geometry metrics | fixed-radius local metric table | PASS |
| URDF-to-CAD preservation report | external-URDF skeleton controls C/D evaluator and canonical FK | PASS |
| A/B/C/D effects and paired deltas | aggregate, effect, and interaction files | PASS |
| Resource and Fusion operation accounting | calls/tokens/latency/Fusion operations | PASS |
| Final report answers all 18 requested items with caveats | audited report | PENDING |
