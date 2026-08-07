# Go/No-Go 2 — SOTA Gap Validation Pilot (frozen protocol v1)

## Question

On the same ten robot-arm inputs, can any existing baseline jointly recover
geometry, assembly structure, and kinematics, or is there a stable gap between
these three objectives?

This is a feasibility pilot, not a leaderboard. Evaluation is deterministic;
LLMs may generate predictions but never judge them.

## Frozen dataset

- Start from the 17 complete Go/No-Go 1 cases in commit `7b01d43`.
- Sort by the frozen prototype index, retain the first case from each
  manufacturer, and stop at ten manufacturers.
- The denominator remains ten even when a baseline crashes or emits invalid CAD.
- Each generated case contains a rewritten local URDF, copied visual meshes,
  `kinematic_gt.json`, the common prompt, and six common renders.

## Inputs

Every method receives exactly the same prompt and the same six PNG views. The
prompt states the robot family, link/joint counts, DOF, and required output
contract. It does not include the GT URDF, mesh files, transforms, axes, or
joint origins.

## Baselines

1. `direct_frontier_mllm`: one frontier multimodal model call producing the
   common prediction contract.
2. `cadir_simplecad`: the same base model with the public SimpleCADAPI/CADIR
   representation and API documentation available.
3. `articad`: official implementation only; do not substitute an imitation.
4. `assemcad`: official implementation only; do not substitute an imitation.

Unavailable code, missing credentials, and runtime incompatibility are reported
as `NOT_RUN`, never converted to zero scores and never presented as method
performance. A four-baseline comparison is complete only when every method has
ten terminal records (`SUCCESS` or genuine generation/execution `FAILURE`).

## Common prediction contract

Each successful run must preserve raw model output and produce:

- one mesh per predicted link;
- a machine-readable link list;
- parent/child joint edges;
- joint type, normalized axis, origin transform, and limits;
- an executable or replayable CAD artifact when the method supports it;
- provenance: method version, model snapshot, prompt hash, image hashes,
  request ID, attempts, latency, and output hashes.

## Deterministic evaluation

Geometry is evaluated after deterministic similarity normalization and rigid
registration because the inputs do not expose a calibrated physical scale.
Report whole-robot and per-link Chamfer distance, HD95 (the robust Hausdorff
statistic used by Go/No-Go 1), and voxel IoU. Do not call HD95 simply
"Hausdorff Distance" in tables.

The frozen geometry implementation samples 3,000 whole-robot and 600 per-link
surface points with recorded seeds. Chamfer is the symmetric mean squared
nearest-neighbor distance; HD95 is the 95th percentile of bidirectional nearest
distances; maximum Hausdorff is retained as a diagnostic. Voxel pitch is 0.05
in normalized robot coordinates. Global registration uses deterministic ICP.

Assembly reports part precision/recall/F1 and directed assembly-graph F1.
Part correspondence first accepts identical link identifiers and then applies a
deterministic Hungarian assignment using normalized shape distance, tree depth,
and incoming-joint type, with maximum assignment cost 0.35.
Kinematics reports joint-type accuracy, sign-invariant axis angular error, and
origin position error normalized by GT robot diagonal. Motion uses fixed joint
samples at fractions `[-0.75, -0.375, 0, 0.375, 0.75]` and reports per-link and
end-effector translation/rotation error.

Random sampling uses recorded seeds. Invalid outputs stay in the denominator and
are listed in failure analysis.

## Pilot-level simultaneous-success thresholds

Thresholds are frozen before any baseline output is inspected. A case is a
simultaneous success only if all are true:

- normalized whole-robot Chamfer <= 0.05;
- whole-robot HD95 <= 0.10;
- voxel IoU >= 0.50;
- part F1 >= 0.90 and graph F1 >= 0.90;
- joint-type accuracy >= 0.90;
- median axis error <= 10 degrees;
- median normalized joint-origin error <= 0.05;
- median normalized moving-link translation error <= 0.05;
- median moving-link rotation error <= 10 degrees.

A baseline is "jointly strong" only when at least 8/10 fixed cases are
simultaneous successes. These are operational pilot thresholds, not claims of
manufacturing readiness.

## Decision

- `GO`: the four-baseline comparison is complete, no baseline is jointly strong,
  and at least one failure pattern recurs in >=3/10 cases for at least two
  methods.
- `NO-GO`: the four-baseline comparison is complete and at least one baseline is
  jointly strong.
- `INCONCLUSIVE`: fewer than four baselines are runnable/comparable, provenance
  is incomplete, or evaluator validation fails.

Paper-reported metrics on other datasets may motivate the experiment but cannot
replace predictions on this fixed ten-case set.
