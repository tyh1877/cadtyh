# Try-4 Phase 1 + 2 evidence checklist

Scope: try4.md sections 0–53 read completely (2,039 lines). Section 53
requires stopping after Phase 1+2 and user confirmation before Phase 3.
No T0/T1/T2 generation or full-robot reconstruction is authorized in this phase.

- [x] Freeze exactly 3 source robots and DEV_A/DEV_B/TRANSFER roles: robots/try4_robot_split.csv.
- [x] Preserve source URL, download date, SHA-256 and STEP/URDF provenance: robots/source_provenance.json.
- [x] Map all 40 imported leaves exactly once to 18 semantic Macro-Parts: robots/semantic_parts/*.json; results/phase12_validation.json.
- [x] Stable unique part IDs, 18 unique colors, role classes, descriptions and joint/interface annotations. Numerical STEP–URDF registration remains unverified and is disclosed.
- [x] Six global colored views per robot and four isolated views per part: 90 images, saved camera metadata, 90/90 automatic QA passes.
- [x] Inspect all 18 Macro-Part four-view sheets and record 56 expected features (46 critical): results/expected_features.csv and robots/feature_checklists/.
- [x] 18 sanitized packets contain renders, semantic context and permitted kinematics only; source CAD/body mapping remains offline.
- [x] RobotPart-LOD v1 SKILL.md defines exterior scope, omissions, critical feature exception and development-only threshold calibration. Skill validation passes.
- [x] Leakage audit checks all 18 packet dependency closures and forbidden CAD/feature dimensions: results/leakage_audit.json. This is not a runtime sandbox guarantee.
- [x] Report phase status and limitations: results/phase12_report.md. T0/T1/T2 have not started; stop before Phase 3 as requested.

Relevant validation: root .venv compilation, audit_references.py,
validate_phase12.py, and skill-creator quick_validate.py with Python UTF-8 mode.
Task-only diff review and local commit are recorded in Git; no push authorized.

Execution from repository root: .venv/Scripts/python.exe try4/scripts/prepare_phase12.py.
The FreeCAD native rendering helper is launched in the CAD application's bundled
Python runtime by the root .venv orchestrator. It is an offline reference renderer,
not an Agent or reconstructed CAD generator.
