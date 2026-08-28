# Try-2 completion checklist

This checklist is the only completion gate for Try-2. A script ending, an F3D
file existing, or a partial aggregate does not establish completion.

| Requirement from `try2.md` | Evidence required | Current status |
|---|---|---|
| Frozen 15-case Image+Text v1 inputs reused | frozen manifest and packet hashes | PASS |
| Sanitized URDF removes geometry and identity leakage | 15 validator reports | PASS |
| A/C primitive runs retain every terminal case | manifests and evaluator outcomes | PASS |
| B/D use real Fusion API rather than primitive compiler | native F3D/STEP/STL plus Fusion execution log | PASS, subject to assembly checks |
| Fusion components assembled at canonical FK pose | Fusion-exported occurrence transform audit vs expected FK | PENDING |
| Fusion joints preserve type, axis, origin and limits | native joint audit vs skeleton/blueprint | FAIL: current layer creates Z-axis joints only |
| Native editability | component/feature/joint/rebuild/native-save audit | PARTIAL (rebuild audit pending) |
| All B/D geometry sent to evaluator comes from Fusion occurrence STL | per-component export manifest and mesh hashes | PENDING |
| Per-link geometry metrics | per-link Chamfer/IoU/HD95 table | PENDING |
| Joint-local geometry metrics | fixed-radius local metric table | PENDING |
| URDF-to-CAD preservation report | preservation rate and failures | PENDING |
| A/B/C/D effects and paired deltas | aggregate, effect, and interaction files | PARTIAL |
| Resource and Fusion operation accounting | calls/tokens/latency/Fusion operations | PARTIAL |
| Final report answers all 18 requested items with caveats | audited report | PENDING |
