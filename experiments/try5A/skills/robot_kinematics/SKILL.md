---
name: robot-kinematics
description: Deterministically parse sanitized URDF frames and compute canonical transforms, FK, world joint axes, joint-limit samples and lightweight workspace diagnostics for Try-5A.
---

# Robot Kinematics

Treat sanitized URDF as kinematic authority. Compose homogeneous transforms using
`T_parent_link @ T_joint_origin @ T_joint_motion(q)`. Interpret URDF RPY as fixed
roll-pitch-yaw with rotation `Rz(yaw) @ Ry(pitch) @ Rx(roll)`. Rotate revolute or
continuous joints about the declared local axis; translate prismatic joints along
that axis. Fixed joints add no motion.

Use zero as canonical value for revolute/continuous joints. Use the limit midpoint
for a prismatic joint whose interval excludes zero, and apply mimic relations from
the source joint. Normalize every non-fixed axis. Preserve raw URDF values and
never change a frame from visual evidence.

Validate tree connectivity, orthonormal rotations, determinant +1, parent-child
relative reconstruction and multiple deterministic joint-limit samples.
