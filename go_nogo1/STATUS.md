# Go/No-Go 1 — current decision status

## Technical summary

**Full Go is not supported at this stage.** The URDF+mesh candidate pool is large,
diverse, parseable, and robust to tessellation, but the frozen mesh score fails the
current STEP/B-Rep calibration. Expert validity is still unmeasured because genuine
independent human ratings have not yet been supplied.

This is an interim experimental result, not a claim that Mesh+URDF is unsuitable as
the benchmark format. It says the present automated *complexity score* cannot yet be
used as a validated substitute for CAD/B-Rep or expert complexity.

## Evidence obtained

| Check | Evidence | Threshold | Status |
|---|---:|---:|---|
| URDF metadata match | 322/322 | complete provenance | pass |
| XML parse | 321/322 | diagnostic | pass with one exclusion |
| Independent eligible arm entities | 142, 16 manufacturers | >=24 | pass |
| Audit-30 source concentration | maximum 30% | <=50% | pass |
| Remesh rank stability, 50% faces | rho=0.875 | >=0.85 | pass |
| Remesh rank stability, 25% faces | rho=0.893 | >=0.85 | pass |
| Triangle-count confounding | rho=-0.068 | abs(rho)<0.30 | pass |
| URDF mesh vs independent STEP/B-Rep | n=9, rho=-0.05 | >=0.50 | fail |
| Same-geometry STEP tessellation vs B-Rep | n=10, rho=0.20 | >=0.50 | fail |
| Expert agreement | not yet measured | kappa>=0.65 or ICC>=0.75 | blocked |
| Mesh vs expert median | not yet measured | rho>=0.60 | blocked |

## Data and metric definitions

- Sampling unit: distinct manufacturer/model entity; URDF variants and duplicate
  sources are not counted as additional robots.
- Primary population: metadata type `robotic arm`, QC grade A/B, excluding three
  Pioneer mobile bases that are mislabeled as arms.
- Audit-30: 10 low, 10 medium, and 10 high preliminary-complexity entities, with a
  maximum of four models per manufacturer and no single source above 50%.
- Mesh score: mean robust-standardized rotationally invariant normal-distribution
  entropy, curvature entropy, 90th-percentile dihedral angle, and >30-degree sharp
  edge rate. Triangle count is not a score component.
- B-Rep score: mean robust-standardized log face count, non-planar surface-area
  fraction, freeform surface-area fraction, and edge/face ratio.

## Interpretation and limitations

The remeshing result is strong evidence that the current mesh ranking is not a
simple tessellation-density artifact. However, tessellation robustness is not the
same as semantic CAD validity. Both the independent-pair comparison and the
same-geometry comparison fail, so the B-Rep result cannot be dismissed solely as a
version mismatch.

The STEP subset is narrow: all ten files are official Interbotix/Trossen models.
This limits external validity and makes the correlation estimate unstable, but it
does not turn the observed failure into a pass. A cross-manufacturer STEP subset is
required before a final claim about general Mesh/B-Rep agreement.

## Required next steps

1. Have at least two CAD/robotics geometry experts independently score the 30 PNGs
   using `results/audit30/SCORING_INSTRUCTIONS.md` and separate copies of the blank CSV.
2. Run `scripts/analyze_expert_ratings.py`; do not tune the score on Audit-30.
3. Treat the current score as a development baseline. Develop a scale-aware,
   multiresolution surface descriptor on a disjoint set, then retest once on a new
   frozen audit set.
4. Add STEP pairs from at least three more manufacturers before claiming B-Rep
   agreement. The current official Trossen subset is calibration-only.
