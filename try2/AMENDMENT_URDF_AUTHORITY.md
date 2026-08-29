# Try-2 amendment: external authoritative kinematics

Approved by the user on 2026-08-28. For C/D, the sanitized URDF is the
external authoritative kinematic representation. Fusion is required to create
and save editable parameterized link/component geometry and to place components
at canonical URDF FK transforms. CAD–URDF consistency is evaluated by link
correspondence, canonical transforms, joint-centered geometry, and URDF-driven
multi-pose geometry/motion. Native Fusion joints are retained as an optional
demonstration and are not a round-trip gate for axis/origin/limit fields.

This does not lower the CAD requirement: geometry metrics, per-link geometry,
joint-local geometry, editability, and deterministic URDF-driven motion remain
the primary evidence.
