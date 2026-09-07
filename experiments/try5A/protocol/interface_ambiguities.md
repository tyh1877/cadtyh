# Interface design ambiguities at the Phase 3 stop

- J02 is assigned `fork_pin_interface` from the upper-arm `dual_side_plate`
  family, but images do not determine exact pin/bearing geometry.
- J05 is a continuous gripper actuator attached through a short virtual spacer;
  only a coaxial coarse interface is justified.
- J06 and J07 are fixed, partly co-located gripper-frame branches. Later geometry
  must avoid interpreting zero translation as duplicated solid material.
- J08/J09 are opposed prismatic fingers and J09 mimics J08 with multiplier -1.
  Their shared interface family is a linear slider; exact guide profile is unknown.
- J10 is a fixed tool-center marker. It may remain an interface-only link rather
  than a substantial CAD body.

These uncertainties concern interface appearance. URDF origin, axis, topology and
limits remain authoritative and are not ambiguous.
