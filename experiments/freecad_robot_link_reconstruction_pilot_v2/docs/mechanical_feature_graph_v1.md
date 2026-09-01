# Mechanical Feature Graph v1

Mechanical Feature Graph v1 is an intermediate structured representation
between visual/URDF/text evidence and Executable CAD IR. Its nodes are
mechanical design semantics, not CAD operations.

Each graph must include:

- `link_id`
- `functional_role`
- `kinematic_context`
- `primary_features`
- `functional_features`
- `structural_features`
- `surface_features`
- `feature_dependencies`
- `visual_evidence_refs`
- `interface_refs`

Each feature node must record:

- `feature_id`
- `feature_type`
- `priority`
- `role`
- `evidence`
- `reference_frame`
- `approx_dimensions`
- `shape_family`
- `cad_strategy`
- `dependencies`
- `confidence`

The graph must not contain chain-of-thought. It must contain only structured,
auditable conclusions. GT mesh, GT CAD, GT STEP, GT feature tree, and GT part
segmentation are forbidden as planner inputs.
