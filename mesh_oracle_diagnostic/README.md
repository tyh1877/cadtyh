# Mesh Oracle Diagnostic

This is a 7-case development-only diagnostic, not a new benchmark track.
It tests whether kinematic errors remain after geometric evidence is supplied as
a deterministic surface-point representation derived from mesh files.

Input conditions are:

* `I`: existing static multi-view image reconstruction output.
* `M`: canonical merged-robot surface point cloud; no link labels.
* `L`: canonical per-link surface point clouds with anonymous part labels; no
  joints, URDF, link names, or manufacturer identifiers. Input geometry is an
  oracle, so geometry results for this condition are not a reconstruction score.

The Qwen Chat Completions endpoint used in this project has no documented raw
STL/OBJ semantic input type. Point clouds are therefore the explicit mesh
representation; the experiment must not be described as native STL-understanding.
