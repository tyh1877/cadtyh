# Try-4 source split and semantic granularity

Selection precedes all Try-4 generated outputs. Native STEP imports, not mesh-to-
STEP conversions, supply references. Source URLs, ZIP/STEP/URDF hashes, download
dates and FreeCAD version are in source_provenance.json. Exact native filenames
and body labels remain offline, outside generator packets.

| ID | Source | Role | Arm DOF (excludes gripper) | Macro-Parts | STEP leaves/solids |
| --- | --- | --- | ---: | ---: | ---: |
| R01 | PincherX-100 | DEV_A | 4 | 5 | 7/9 |
| R02 | ViperX-300s | DEV_B | 6 | 7 | 24/24 |
| R03 | ReactorX-200 | TRANSFER | 5 | 6 | 9/16 |

DEV_A provides a compact exterior with fork plates, slots and a two-jaw gripper.
DEV_B has more axes, separate roll/pitch regions, offset forearm plates, web
openings and a dense dual-rail gripper. It is relatively hard within the available
native STEP cohort; it does not cover arbitrary freeform industrial castings.
TRANSFER was not in the preceding five-case colored STEP experiment. Its local
references may be annotated now as explicitly required by Phase 1, but no Try-4
reconstruction/evaluation or threshold tuning is allowed on it before Phase 9.
All three sources are Trossen/Interbotix: future transfer evidence is same-family,
not independent cross-manufacturer generalization. Earlier general access to
source assets must not be described as a pristine benchmark holdout.

Grouping is a curated partition of all imported leaves. Every leaf appears once,
including compound leaves; there is no body dropping or GT-dimension extraction
for the generator. Gripper assemblies deliberately include multiple bodies and
moving jaws: future generation must retain visible gaps and constituent bodies.
This granularity is not a BOM/manufacturing partition and is not asserted to be
one rigid kinematic link per group.

Semantic joint associations use source component names and the supplied URDF.
Anonymous local frames preserve origins, RPY, axes and limits. A numerical rigid
registration between STEP coordinates and URDF coordinates is not established;
packets disclose this and prohibit treating those frames as calibrated image
projections. External contact boundaries with no joint have null joint IDs and
explicit semantic region descriptions.

Color IDs are stable and unique across all 18 Macro-Parts. Membership is stored
in semantic_parts/*.json; colors are presentation cues, never evidence of
manufacturability or automatically correct CAD decomposition.
