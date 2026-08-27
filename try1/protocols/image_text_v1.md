# Image+Text Input Protocol v1

Each model call receives exactly six anonymous PNG renders (`front`, `rear`,
`left`, `right`, `top`, `isometric`) from the Go/No-Go 3 canonical/home pose,
and the fixed text template below. Camera metadata, meshes, depth, URDF,
manufacturer/model identity, link labels and all hidden ground-truth fields are
not included in the model packet.

The text is rendered only from `semantic_category`, `units`, two deterministic
global anchors, and the template. The anchors are (A) the home-pose vertical
extent of the reference visual geometry (`overall_height_home_mm`) and (B) a
deterministic nominal maximum end-effector reach (`max_reach_mm`). The latter is
the maximum base-to-deepest-link-origin distance over 256 fixed-seed Sobol joint
samples within URDF limits; continuous joints are sampled over [-pi, pi]. It is
an explicit, reproducible approximation to reachable radius, not a manually
entered robot specification.

Fixed template:

> Reconstruct the articulated industrial robot arm shown in the six reference
> images as an editable parametric CAD assembly and an explicit kinematic model.
> Use millimeters. In the shown canonical/home configuration, the overall height
> is {overall_height_home_mm} mm. The nominal maximum reach from the base
> reference to the end-effector reference is {max_reach_mm} mm. Infer the
> rigid-link decomposition, parent-child topology, joint types, joint axes,
> joint origins, and detailed link geometry from the references. Do not assume
> access to original CAD, mesh, URDF, product identity, or hidden part labels.

The template supplies category, units and global scale only; it explicitly does
not disclose link/joint count, topology, axes, origins, limits, per-link size or
commercial identity. Packets are schema-validated and generated only by
`scripts/build_inputs.py`.
