# Try-3 FreeCAD amendment: Codex agent continuation

Approved by the user on 2026-09-05 after the configured GLM account exhausted
its available quota. This amendment changes the unfinished model-backed agent
stages; it does not change TrySet-5, the allowed input contract, the FreeCAD
backend, the no-GT rule, or the deterministic evaluator.

## Model and execution boundary

- Agent producer: interactive Codex session, GPT-5 family.
- Exact serving snapshot, temperature, top-p, response identifiers, and per-call
  token counts are not exposed to this local experiment. They are recorded as
  `UNAVAILABLE`, never as zero.
- Codex may read only the frozen multi-view images, engineering text, sanitized
  kinematic-only URDF, prompts, schemas, and non-GT crop artifacts while
  producing plans.
- GT meshes, original geometry-bearing URDF, STEP/CAD, segmentation, prior
  evaluator metrics, and case identity are evaluator-only and must not enter an
  agent artifact.
- Every Codex-authored artifact names its producer, source artifact hashes, UTC
  creation time, schema version, and the limitation that exact sampling replay
  is unavailable.

## Visual evidence continuation

The earlier GLM v2 scan/crop run is preserved as historical evidence but is not
used as the formal Codex visual packet. The formal Codex continuation uses the
existing deterministic, non-GT silhouette/link-order crops plus the six frozen
global views. Codex supplies semantic observations and carries ambiguous link
localization forward as uncertainty. It does not manufacture precise link
segmentation.

## Formal comparison

The new run namespace is `codex_agent_v1`. V0, V1, and V2 use the same Codex
producer and frozen inputs:

- V0: global images + engineering text + sanitized URDF; no local packet, MEP,
  or Interface Graph.
- V1: V0 inputs + Codex visual evidence; per-link planning without MEP or an
  explicit Interface Graph.
- V2: Codex visual evidence + MEP + Interface Graph + per-link feature/skill
  planning.

All five cases remain in every denominator. Generation/execution failures are
terminal for that formal cell and are not repaired in place. Development smoke
checks may use `dev_arm-ab15a75247` and `dev_arm-dcc2b0ce1e`; evaluator behavior
is frozen before the three other cases are executed/evaluated as holdout.

## Interpretation

Results from this run are reported as **Codex-agent Try-3 FreeCAD**, not as a
continuation of the GLM model condition. Historical GLM and Fusion API outputs
may inform implementation robustness but are not pooled with the new matrix.
The interactive model limitation lowers exact generation replayability; the
saved inputs, prompts, schemas, structured outputs, hashes, FreeCAD logs, and
deterministic metrics remain directly auditable.

