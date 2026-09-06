---
name: robot-part-modeling-standard
description: Apply RobotPart-LOD v1 to Try-4 semantic Macro-Part exterior reconstruction, feature planning, review and selective repair; not whole-robot assembly or recovery of hidden manufacturing geometry.
---

# RobotPart-LOD v1 — Engineering Exterior Reconstruction

Use only the supplied PartInputPacket in the generator context. Offline STEP,
component membership, exact B-Rep dimensions, original URDF visual meshes and
reviewer-only data are not generation inputs. Related joint origins/axes/limits
and global kinematic scale anchors are permitted; do not confuse the supplied
URDF frame with the unregistered STEP rendering frame.

## Required exterior content

For each part, explicitly assess and record:

1. Primary shape: envelope, major proportions, section family, dominant taper,
   major curvature, and the primary structural body.
2. Joint regions: evidence-supported proximal/distal housing, neck, rotary bulge,
   joint-centered transition and attachment boundaries.
3. Functional exterior: flange, mounting face, boss, visible hole/hole pattern,
   recess, slot, cutout, local opening and mounting structure where supported.
4. Structural exterior: shell-like wall layout, rib/web, cover region, strengthening
   bulge, lightening cut and cavities visible from outside.
5. Surface geometry: rounded section, tapered/lofted/revolved/sweep-like regions,
   major fillets/chamfers and blended transitions supported by the reference.

These are assessment categories, not instructions to add every feature to every
part. Read that part's expected feature checklist. Each included feature must
cite its actual views and region; never distribute whole-robot labels by index.
Use multiple solids for clearly separate members or jaws; do not fuse across a
visible working opening. A Macro-Part may be a subassembly, not one solid.

## Inclusion and permitted simplification

Critical functional/interface features are mandatory whenever explicit semantic
or joint/interface context requires them, regardless of size. Mark an uncertain
geometry parameter as uncertain; do not invent a hole where evidence does not
establish a hole. Distinguish circular cover outlines from through holes.

Ordinary details are required only when clearly visible in a high-quality view,
material to silhouette/local shape, and larger than the development-calibrated
relative scale threshold. Phase 2 sets a **provisional 0.02 ratio** of projected
feature extent to projected part extent in the same unscaled view. It is not an
exact B-Rep dimension and not yet a validated Quality Gate threshold. Freeze the
final ratio using DEV_A/B only before TRANSFER reconstruction. Record candidates
below/near this threshold separately; no threshold tuning from TRANSFER results.

Threads, logos/text, tiny chamfers, exact screw heads, invisible fasteners,
motors, reducers, bearings, internal cables and unsupported hidden manufacturing
details may be omitted. Major silhouette curvature and required exterior details
may not be replaced with box/cylinder placeholders merely to make export pass.

## Feature-to-CAD obligations

Each planned feature records a stable ID, semantic type, evidence, region/frame,
estimated dimensions with uncertainty, shape family, native CAD strategy,
dependencies, critical flag and confidence. IR must consume these decisions.
Missing required operation parameters yield PLAN_INCOMPLETE before execution.
Unsupported/failed required features remain failures; no hidden operation
substitution, proxy success or skipped-feature success is allowed.

## Completion and selective repair

Export success alone is insufficient. Assess valid B-Rep, geometry discrepancy,
critical and ordinary feature coverage/precision, semantic role, exterior LOD,
reopen/recompute and an isolated ±5% parameter-edit test. Numerical Quality Gate
thresholds remain unset in Phase 2 and must be calibrated on DEV_A/B.

After evaluation, freeze passed features and record do-not-change parameters.
Modify only failed features unless an explicit replan is required. Stop on PASS;
at most three repair rounds. Stagnation triggers replan, then UNRESOLVED if still
unsuccessful; detect/rollback regression of protected features. No unconditional
fixed number of repairs. Keep each part's generation/review/repair in its own
Codex CLI context when Phase 3 is approved.
