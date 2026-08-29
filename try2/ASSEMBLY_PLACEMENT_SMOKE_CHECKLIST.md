# Fusion world-transform smoke gate

Status: **RUNNING**. This gate was added after inspecting
`runs/D/dev_arm-3ce41d3c31/model.f3d`: its visible model and exported root STL
showed overlapping components rather than a FK-expanded assembly.

| Requirement | Evidence | Status |
|---|---|---|
| Smoke uses one frozen D blueprint and does not overwrite formal matrix artifacts | wrapper-generated `fusion_assembly_smoke_job.json` and `smoke_runs/` | PENDING |
| All required L0--L9 occurrences are created | Fusion execution JSON `component_count == 10` | PENDING |
| Every occurrence records an actual translation equal to its deterministic FK translation | `occurrence_transforms` in execution JSON | PENDING |
| Root STL contains the FK-expanded assembly rather than overlapped local components | deterministic STL bounds audit: X max > 900 mm and Z max > 450 mm for this selected case | PENDING |
| Native F3D and STEP exports exist | smoke execution JSON and files | PENDING |
| Fusion UI visual inspection shows a spatially expanded multi-link assembly | user-visible Fusion document screenshot/inspection | PENDING |

Only after all rows pass may the repaired executor be applied to the remaining
formal B/D cases and the old results be invalidated and regenerated.
