---
name: robot-assembly-planning
description: Build a coarse whole-robot link plan by consuming the frozen kinematic skeleton together with allowed multi-view morphology evidence.
---

# Robot Assembly Planning

Plan every URDF link before any CAD. Copy parent/child joint identities and frame
constraints from L0. Use images only for coarse envelope, principal direction,
mechanical role and broad body family. Do not add detailed holes, internal gripper
mechanisms or exact GT dimensions.

Each link record must include the L0 source hash and the exact skeleton fields it
consumed. Neighboring link scales should be coherent with joint-origin distances.
