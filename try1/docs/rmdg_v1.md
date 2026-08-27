# Robot Mechanical Design Graph v1

RMDG is the predicted mechanical design state between Image+Text perception and
primitive CAD/URDF emission. It contains anonymous `L#` rigid links and `J#`
kinematic edges, functional roles, coarse envelope estimates, interfaces,
canonical/base-frame axes and origins in millimetres, and concise view evidence.
It intentionally does not contain mesh, B-Rep, CAD code, surface-detail plans,
commercial identity or chain-of-thought.

`validate_rmdg_v1.py` requires one rooted acyclic graph from `base_link_id` to
`end_effector_link_id`, checks bidirectional link/joint incidence, finite
coordinates, unit axes for movable joints and valid supplied limits. It saves no
automatic GT correction; only a separately stored normalized representation may
be passed downstream.
