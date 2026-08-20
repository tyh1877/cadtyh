# Go/No-Go 3 protocol

## Name and question

**Joint Frame Recovery + CAD-URDF Consistency Prototype.** Given six blind
reference renders of an articulated robot, does recovering a visual joint-frame
hypothesis and preserving it in emitted CAD/URDF improve kinematics and motion
without degrading geometry?

## Development-only data

The set is 15 robots that passed the Go/No-Go 1 mesh, URDF, multi-pose and
evaluator gates. It is a development set, not a final benchmark test set. Model
prompts contain no model name, link count, DOF, joint type, axis, origin,
limits, or URDF. Ground truth is loaded only after generation by the evaluator.

## Variants and compute

| Variant | Calls | Maximum output tokens | Maximum total tokens | Repair |
|---|---:|---:|---:|---:|
| V0 Direct | 1 | 32,768 | 100,000 | 0 |
| SimpleCAD-style | 1 | 32,768 | 100,000 | 0 |
| V1 Joint Frame Recovery | 2 | 8,192 + 24,576 | 100,000 | 0 |
| V2 + CAD-URDF consistency | 2 | 8,192 + 24,576 | 100,000 | 0 |

V1/V2 have the same total output cap as baselines. The additional first call is
the explicit mechanism under test, not a retry. All calls use the same model,
temperature 0, six views, and API timeout from the repository-local configuration.

## Measurement and decision

All outputs use the deterministic Go/No-Go 2 evaluator. V2 additionally checks
the equality of its predicted joint-frame draft and compiled CAD/URDF joint
frames. A GO requires 15-case execution for every variant, directional V2 gains
over V0 in graph F1, axis error, origin error, and motion translation error,
non-worse Chamfer distance, and exact CAD-URDF consistency. No threshold is
tuned on these development outputs.

The prototype claims neither connector planning, port matching, generic assembly
agents, nor novelty over the related ArtiCAD/AssemCAD lines.
