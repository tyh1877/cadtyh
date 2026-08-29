# Fusion world-transform smoke gate

Status: **PASSED for the selected D smoke case**. This gate was added after inspecting
`runs/D/dev_arm-3ce41d3c31/model.f3d`: its visible model and exported root STL
showed overlapping components rather than a FK-expanded assembly.

| Requirement | Evidence | Status |
|---|---|---|
| Smoke uses one frozen D blueprint and does not overwrite formal matrix artifacts | wrapper-generated `fusion_assembly_smoke_job.json` and `smoke_runs/` | PASS |
| All required L0--L9 occurrences are created | `smoke_runs/D/dev_arm-3ce41d3c31/fusion_execution.json` (`component_count == 10`) | PASS |
| Every occurrence records an actual translation equal to its deterministic FK translation | `occurrence_transforms` in the execution JSON | PASS |
| Root STL contains the FK-expanded assembly rather than overlapped local components | root STL bounds `1145 x 190 x 535 mm` (`model.stl`) | PASS |
| Native F3D and STEP exports exist | smoke execution JSON and files | PASS |
| Fusion UI visual inspection shows a spatially expanded multi-link assembly | user screenshot plus L0--L9 browser entries | PASS |

Only after all rows pass may the repaired executor be applied to the remaining
formal B/D cases and the old results be invalidated and regenerated.
