# Robot A selection

- **robot_id:** R01
- **source:** Interbotix PincherX-100
- **arm DOF:** 4 revolute arm joints, excluding gripper auxiliaries
- **URDF links/joints:** 12 links and 11 joints
- **movable URDF joints:** 7 entries: 4 arm revolute, 1 continuous gripper actuator and 2 opposed prismatic fingers (one mimic)
- **geometry difficulty:** easy-to-medium coarse reconstruction
- **surface character:** round joint housings, cylindrical bosses and rounded/forked arm ends provide curved geometry without the dense ViperX gripper complexity

R01 is selected because its complete URDF, native STEP provenance and six global
views already exist. It has a typical base/shoulder/upper-arm/forearm/wrist/end
chain but avoids R02's extreme multi-body dual-rail gripper. R03 is excluded
because it was the frozen Try-4 transfer robot.
