# Try-6.0-C1 L04 KFDG structural reasoning prompt

You are given six raw views of one articulated robot, neutral renders of the
frozen coarse L04 CAD, engineering text, a sanitized URDF, and numerical
interface frames. Identify the visible structural topology of L04 only.

Return exactly the supplied JSON Schema. Your response contains:

- visible feature nodes, each with one canonical type and source views;
- relations between those nodes and the fixed `proximal_joint_port` and
  `distal_mount_port` identifiers;
- dimensionless cues for relevant parameter IDs, if the views support them;
- explicit uncertainty for obscured or unobservable details.

The visible L04 contour supports a main housing, a profile transition, a
visible recess, and rounded exterior edges. Include each only where you find
support in the attached views. A valid L04 feature history requires one node
of each of those four types. The proximal bore and distal mount frames come
from URDF/interface data and will be inserted deterministically.

Do not output millimetre dimensions, CAD code, a body-family label, a Boolean
feature switch, a manufacturing feature, or a final PASS judgment. The solver
will determine metric dimensions from the raw images and URDF anchor. Do not
invent a camera calibration. Do not use historical Try-5 structured results,
GT meshes, evaluator metrics, or motion feedback.
