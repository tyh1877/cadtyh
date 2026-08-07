# Go/No-Go 1 — Dataset and Evaluation-Protocol Feasibility

## Frozen primary question (v5, 2026-08-08)

Can public data be used to build a small, high-quality Mesh+URDF robot-arm set
and support deterministic geometric and kinematic evaluation of generated results?

This is a **20-case prototype feasibility gate**, not a 100-case benchmark and not
a complexity-ranking experiment.

## Frozen denominator and selection

- Start from the complexity-blind candidate Benchmark-80 manifest.
- Select exactly 20 cases: one per manufacturer in stable order, then a second per
  manufacturer until 20 is reached.
- Never use complexity features, expert scores, STEP/B-Rep results, or method
  performance for selection.
- Failed cases remain in the denominator of 20.

## Required output for each case

Every complete case must contain:

- URDF links and joints with type, parent/child, axis, origin, limits, and a
  deterministic canonical pose;
- link-level visual meshes;
- six deterministic views: front, rear, left, right, top, and isometric;
- a deterministic text description and bundles for Text, Image, and Text+Image;
- callable deterministic geometry, assembly, and multi-pose evaluators.

## Five checks

### 1. Mesh quality

- At least 90% of visual mesh references resolve and load for the case.
- At least 80% of actuated child links have visual meshes.
- The assembled mesh is finite, has non-zero extent, and contains at least 1,000 faces.
- Any empty/unloadable referenced mesh fails the case.
- Six-view review must find no obvious missing, exploded, severely broken, or
  box/cylinder-only proxy geometry.

### 2. URDF quality

- Link and joint names are present and unique.
- Joint types belong to the supported URDF set.
- Parent and child links exist and form one rooted tree.
- Actuated joint axes are finite and non-zero.
- Revolute and prismatic joints have finite ordered limits.

### 3. Mesh–URDF consistency

- Every loaded visual mesh remains attached to its declared link.
- Visual origins, joint origins, and Collada scene-node transforms are applied.
- At least 90% of checked joint origins lie within 0.25 robot-diagonal of both
  adjacent-link AABBs; this is a conservative connection-region diagnostic.
- Neutral, lower-quarter, and upper-quarter poses produce finite forward kinematics,
  non-zero articulated motion, and no unbounded transform explosion.

### 4. Deterministic evaluator loop

The smoke test must expose and execute:

- geometry: normalized CD, HD95, whole-geometry similarity, per-link CD, and
  quantized surface-occupancy IoU;
- assembly: link/part match F1, kinematic graph F1, joint-type accuracy, joint-axis
  error, and joint-origin error;
- dynamics: multi-pose link-transform error.

Identity input must return exact zero distance/error and unit similarity/F1/IoU.
A deterministic synthetic corruption must worsen geometry, per-link, and multi-pose
metrics. This proves callability and directionality, not production-level validity.

### 5. Multimodal input construction

Each case must have a non-empty text prompt, six images, and an explicit modality
bundle supporting Text, Image, and Text+Image.

## Frozen decision rule

Go requires all of the following:

- at least 15 of the fixed 20 candidates are complete cases;
- aggregate link visual-mesh readability is at least 90%;
- 100% of complete cases pass URDF parse and graph construction;
- 100% of complete cases have no clear multi-pose GT error under the checks above;
- geometry and kinematic evaluators run for 100% of complete cases;
- multimodal inputs exist for 100% of complete cases;
- all 20 six-view reviews are completed, including failed cases.

No-Go applies if any global criterion fails. Thresholds may not be relaxed after
seeing results. Parser defects may be repaired, but the inventory and experiment
must then be rebuilt from source and rerun with the same denominator rule.

## Scope of a Go decision

Go authorizes the next engineering stage: evaluator hardening, controlled-set design,
and baseline integration. It does not establish license/redistribution clearance,
Benchmark-80 release readiness, train/test leakage safety, or SOTA superiority.

Complexity remains an optional post-hoc sensitivity analysis and is not part of
this decision.
