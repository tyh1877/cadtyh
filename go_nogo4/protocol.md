# Go/No-Go 4 protocol

## Question

Does multi-pose image evidence provide independent mechanical information for
blind CAD + URDF reconstruction, beyond spatial multi-view evidence and beyond
simply supplying more images?

## Data and secrecy

The development set contains the 15 Go/No-Go 3 audited robots. For each, three
joint configurations are deterministically rendered from the source Mesh+URDF,
with front, side, top and iso views. The model receives rendered images and pose
labels only. Robot names, count information, GT URDF, joint values, axes,
origins, limits and trajectories are withheld until deterministic evaluation.

## Conditions

| ID | Variant | Images | Motion mechanism |
|---|---|---:|---|
| A | single_view | 3, pose_0 | none |
| B | multiview_static | 4, pose_0 | none |
| D | multipose_concat | 12, three poses | images concatenated; no explicit motion inference |
| C | motion_aware | 12, three poses | cross-pose link/joint hypothesis hard-constrains emitted CAD/URDF |

Every condition uses Qwen3.7-Plus, temperature 0, one API call, no repair,
32,768 maximum output tokens, and 100,000 maximum total tokens. C and D have
identical image count and call count; C's extra structured output remains under
the same output cap and actual usage is reported.

## Evaluation

The deterministic RobotCAD evaluator reports geometry, part/graph, joint and
multi-pose motion metrics. It uses hidden GT trajectories only after generation.

GO requires terminal coverage for all 15 cases, C improving over B in graph F1,
joint-type accuracy and motion translation, C improving over D in graph F1 and
motion translation, and non-worse C Chamfer relative to D. The pilot makes no
connector/port/mate/retrieval claim.
