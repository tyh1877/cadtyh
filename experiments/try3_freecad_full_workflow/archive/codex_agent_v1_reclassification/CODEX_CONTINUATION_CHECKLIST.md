# Codex-agent Try-3 continuation: requirement-to-evidence checklist

This checklist is frozen before formal `codex_agent_v1` execution. A checked
item requires the named direct evidence; script exit alone is insufficient.

## Freeze and provenance

- [x] Input snapshot covers five manifest rows, 30 images, five engineering-text
  packets, and five sanitized URDFs: `results/codex_agent_v1_input_snapshot.csv`.
- [x] Prompt/schema/config hashes and producer limitation are recorded:
  `results/codex_agent_v1_method_snapshot.csv`.
- [x] Planner-input audit finds no GT geometry, product identity, original URDF,
  STEP/CAD, segmentation, or evaluator result paths:
  `results/codex_agent_v1_planner_input_audit.csv`.
- [x] Development and holdout cases match `codex_agent_v1_config.json`.

## Agent stages

- [x] Codex Visual Observer covers all five cases and 63 links with evidence
  references, explicit uncertainty, and no placeholder observations:
  `results/codex_agent_v1_stage_summary.csv` plus local run artifacts.
- [x] V2 MEP covers each sanitized URDF link and passes the frozen schema.
- [x] V2 Interface Graph covers every sanitized URDF joint, inherits its origin
  and axis, and passes deterministic equality checks.
- [x] V0/V1/V2 per-link feature graphs, SkillCalls, and executable IR cover all
  189 version/link cells or retain an explicit terminal failure.
- [x] Every stage manifest contains stage, status, input hashes, schema version,
  created-at time, and producer; downstream failure states are explicit.

## FreeCAD execution and integration

- [x] Generic operation smoke passes before the formal matrix; no TrySet metric
  is used to tune it.
- [x] All 15 version/case cells are attempted once after method freeze. One
  parser preflight incident before holdout output is retained separately.
- [x] Successful links export editable FCStd plus STEP and STL; native feature
  types and operation outcomes are logged with zero silent fallbacks.
- [x] Successful cases export full assembly FCStd, STEP, and STL with one named
  component per sanitized URDF link and canonical URDF placements.
- [x] Reopening validates assembly component count, shape validity, and export
  existence.

## Deterministic evaluation

- [x] Evaluator code/hash is frozen before holdout execution.
- [x] Global, per-link, and joint-local Chamfer/HD95/voxel-IoU tables include
  every formal case/version or explicit failure rows.
- [x] Interface gap, structural axis/origin equality, constraint satisfaction,
  disconnected/floating component, and interference diagnostics are reported.
- [x] Primitive-proxy degeneration, native feature use, rebuild/export success,
  and visible-feature diagnostics are reported without using AI Judge scores.
- [x] Resource table records agent calls as interactive with token fields
  `UNAVAILABLE`, plus measured wall time and FreeCAD operation/runtime counts.
- [x] Development, holdout, and all-case aggregates are reported separately.

## Completion

- [x] `results/codex_agent_v1_try3_report.md` answers RQ1, RQ2, and RQ3 and
  distinguishes this run from historical GLM/Fusion evidence.
- [x] Protocol, amendment, and this checklist are reread against the workspace.
- [x] Relevant validation passes under `.venv/Scripts/python.exe`; generated
  geometry/raw agent artifacts remain ignored.
- [x] Task-only diff is inspected and committed locally without push.
