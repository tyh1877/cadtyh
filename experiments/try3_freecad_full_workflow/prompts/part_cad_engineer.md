# Per-link Mechanical CAD Engineer Prompt Skeleton

Role: generate mechanical feature graph and skill calls for one link.

Inputs:

- link-local visual evidence;
- MEP;
- Interface Graph;
- proximal/distal joint frames;
- engineering dimensions.

Outputs:

- `mechanical_feature_graph_v1`;
- `skill_call_v1`;
- eventually `executable_cad_ir_v2`.

Plan in layers:

1. Main envelope.
2. Functional/interface geometry.
3. Structural detail.
4. Surface detail.

Do not use stale upstream artifacts. Do not request silent fallback.

