# Mechanical Embodiment Plan v1

The MEP maps an already-known anonymous URDF link to an externally observable
mechanical embodiment. It must not repeat topology, axes, origins or limits;
those fields remain authoritative in the sanitized URDF. Each link records a
functional role, a broad geometry family, a surface strategy and protected
joint-interface regions. It is generated from image evidence and sanitized
kinematics only; it may not use GT mesh/CAD labels.
