# Executable Shape-Family v1

`stepped_housing` requires a base body, upper stepped cover, proximal joint boss,
front/rear transition, side-wall structure, visible recess/opening and mounting
interface. Required parameters include overall envelope, ordered step stations and
heights, top/side profiles, rear taper, boss radius/depth and reference frame.

`compound_profile_housing` replaces a failed monolithic stepped body with separate
side-profile base, cover profile, transition loft and joint/mounting features.

`explicit_gripper_substructure` requires central carriage, left/right rails,
left/right sliders, left/right jaws, left/right linkages, pivot group and working
gap. Every substructure has a frame, approximate bbox, orientation, shape family,
connections and CAD strategy.

`articulated_plate_gripper` replaces a failed box/bar realization with profile
jaws, slider-to-jaw adapters, paired profile linkages and explicit pivot bosses.

Invalid configurations include a missing required substructure, absent required
gap, asymmetric declared pair without an uncertainty record, disconnected load
path, nonpositive dimensions, a gripper realized only as unnamed boxes/bars, or a
structural replan that changes only scalar parameters.
