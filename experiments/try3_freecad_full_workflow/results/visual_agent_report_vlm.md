# Visual Evidence Agent Stage Report

## Scope

This stage attempts VLM-backed global-to-local visual evidence for the fixed
TrySet-5.

Generation mode: `vlm`.

## Crop localization method

- VLM mode asks `glm-5.3-flash` for normalized per-link focus boxes and
  observable local evidence.
- It uses resized multi-view image inputs and sanitized URDF context.
- It does not use GT mesh, GT segmentation, STEP/CAD, product identity, or
  hidden part labels.

## Coverage

- Cases attempted: `1`.
- Successful cases: `0`.
- Links with VLM evidence packets: `0`.
- Crop records: `0`.
- Stage status: `FAILURE`.

## Failure

The smoke run for `dev_arm-ab15a75247` failed with `APITimeoutError` after a
120-second request timeout.

Failure manifest:

```text
experiments/try3_freecad_full_workflow/runs/visual_agent/vlm/dev_arm-ab15a75247/stage_manifest.json
```

## Gate decision

VLM-backed Visual Evidence Agent is not yet ready for MEP generation. The next
repair should reduce the VLM request granularity, for example one view or one
link group per request, before attempting the full TrySet-5.
