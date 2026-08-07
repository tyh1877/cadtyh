# Go/No-Go 1 — Unified Mesh+URDF Benchmark Feasibility

## Frozen primary question (v4, 2026-08-07)

Can the public Mesh+URDF candidate pool support one technically valid, traceable,
and uniformly evaluated 80-robot benchmark for robot-arm CAD generation?

This gate tests **benchmark feasibility**, not whether a hand-designed robot
complexity score agrees with experts, STEP topology, or mesh simplification error.

## Benchmark design implied by the gate

- One benchmark and one case manifest; no Easy/Medium/Hard tracks.
- No G1/G2/G3 × A1/A2/A3 benchmark matrix.
- Direct, CADIR, ArtiCAD, AssemCAD, and the proposed method must be evaluated on
  exactly the same cases, inputs, geometry normalization, and evaluator versions.
- Input-modality comparison (Text, Image, Text+Image), geometry/surface evaluation,
  assembly/kinematics evaluation, and ablations are experiments on the same benchmark,
  not separate complexity tracks.
- STEP is an optional diagnostic/calibration subset. It is not an entry requirement.

## Technical eligibility for one robot case

A candidate is technically eligible only when all of the following hold:

1. It is a distinct robot-arm entity rather than a duplicate URDF variant.
2. Source URL and local URDF path are recorded.
3. URDF parses and its kinematic graph is valid.
4. It has at least one actuated joint and a recorded kinematic depth.
5. At least 90% of visual mesh references resolve and at least 80% of non-fixed
   links have visual geometry.
6. At least one visual mesh loads and yields finite mesh features.

## Automated Go/No-Go criteria

Technical Go requires that a complexity-blind selection procedure can construct a
candidate Benchmark-80 satisfying all of these conditions:

- exactly 80 technically eligible, distinct robot entities;
- at least 10 manufacturers;
- no manufacturer supplies more than 25% of Benchmark-80;
- no upstream source supplies more than 50% of Benchmark-80;
- every selected case has both mesh geometry and URDF kinematic structure available.

The caps are diversity safeguards, not difficulty strata. The selection procedure
must not read preliminary complexity scores, expert ratings, B-Rep scores, or method
performance.

No-Go is issued only if an 80-case set satisfying these technical conditions cannot
be constructed from the current public candidate pool.

## Release prerequisites outside the automated gate

Technical Go does not by itself authorize dataset publication or a benchmark claim.
Before release, the project must additionally:

- complete a file-level license and redistribution audit;
- manually review and freeze the final Benchmark-80 manifest;
- canonicalize units, coordinate frames, link naming, and train/test leakage rules;
- implement one versioned evaluator used unchanged for all methods;
- verify geometry metrics (Validity, IoU, CD, HD95, normal error, high-curvature CD);
- verify assembly metrics (PartMatch F1, Graph F1, joint type, axis/origin error,
  and multi-pose error);
- run every baseline on the identical frozen cases and modalities.

## Complexity is a post-hoc diagnostic

Complexity does not affect case inclusion, the primary leaderboard, or fairness.
After the main results are frozen, inexpensive objective attributes may be reported:

- assembly: link count, joint count, DOF, kinematic depth, joint-axis diversity;
- geometry: normal/curvature variation, surface-area-to-bounding-box-volume ratio,
  local curvature distribution, and high-curvature area ratio;
- STEP-only optional attributes: B-spline/Bezier/freeform surface proportions.

Permitted analyses include performance versus continuous geometry attributes,
Graph F1 versus joint count, and improvement over the strongest baseline versus
complexity. Expert ratings and composite complexity weights are optional validation,
not Go/No-Go requirements.

## Historical note

The original audit and v2/v3 revisions tested whether an automated complexity score
could be validated against experts, B-Rep structure, or fixed-budget approximation.
Those results remain reproducible diagnostics. Their No-Go decisions apply to the
respective complexity metrics only and no longer determine Benchmark feasibility.
