# Try-5B.1-A1 Frozen Scaffold Preservation Ablation

Status: **FORMAL_DEVELOPMENT_COMPLETE_HOLDOUT_UNACCESSED**

Independent validation: **PASS** (16/16 checks)

The experiment completed six one-shot development runs: L03/L04/L07 ×
S1/S0. Every run retained all 96 development configurations. No run failed or
retried, and the locked 32-case formal holdout remains `accessed=false`.

## Paired main results

| Link | Condition | BICR | Solids | JR3 | GCFR | Collisions | Intersection mm³ | Final IoU | Silhouette | nChamfer | nHD95 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| L03 | S1 preserved | 1.0 | 1 | 1.0 | 0.916667 | 31 | 12006.44 | 0.258783 | 0.612522 | 0.054416 | 0.214170 |
| L03 | S0 removed | 0.0 | 3 | 1.0 | 0.916667 | 31 | 12006.44 | 0.207170 | 0.553545 | 0.055928 | 0.231115 |
| L04 | S1 preserved | 1.0 | 1 | 1.0 | 0.916667 | 31 | 14953.64 | 0.094870 | 0.320063 | 0.125966 | 0.265327 |
| L04 | S0 removed | 0.0 | 3 | 1.0 | 0.916667 | 31 | 13207.81 | 0.083106 | 0.297599 | 0.125361 | 0.265209 |
| L07 | S1 preserved | 1.0 | 1 | N/A | 0.916667 | 33 | 12744.67 | 0.102382 | 0.268355 | 0.060296 | 0.222134 |
| L07 | S0 removed | 0.0 | 3 | N/A | 0.916667 | 31 | 12517.94 | 0.092706 | 0.264357 | 0.059548 | 0.222175 |

L07 has no relevant moving joint; JR3 is correctly reported as N/A rather than
filled with an asserted value. All six runs have the same eight failed
configuration IDs, and all preserve the full 96-case denominator.

## Aggregate S1−S0 deltas

| Metric | Mean delta | Median delta |
|---|---:|---:|
| BICR | +1.000000 | +1.000000 |
| Connected solid count | -2.000000 | -2.000000 |
| JR3, applicable links | 0 | 0 |
| GCFR | 0 | 0 |
| Collision events | +0.666667 | 0 |
| Intersection volume mm³ | +657.515627 | +226.722783 |
| Final voxel IoU | +0.024351 | +0.011764 |
| Final silhouette IoU | +0.028480 | +0.022464 |
| Final nChamfer | -0.000053 | +0.000605 |
| Final nHD95 | -0.005623 | -0.000041 |

Lower nChamfer/nHD95 is better. Body-only metrics are identical within every
S1/S0 link pair, confirming that the F2 body input is unchanged. They remain
paired diagnostics against full-link GT, not absolute body reconstruction
accuracy.

## FACTS

- Scaffold preservation raises BICR from 0 to 1 and changes the final link from
  three disconnected solids to one connected solid on all 3/3 links.
- Relevant JR3 remains 1.0 on L03 and L04; L07 has no relevant moving joint.
- GCFR remains 88/96 = 0.916667 for every run, with identical failed case IDs.
- Final-link voxel IoU and silhouette IoU improve on all three links under S1.
- L03 collision count/volume are unchanged. L04 intersection volume increases
  by 1745.82 mm³. L07 gains two collision events and 226.72 mm³.
- Raw body signatures and body-only STL hashes match within all three pairs;
  final STL hashes differ. The sole effective condition difference is scaffold
  preservation/fusion.

## INTERPRETATION

Frozen scaffold preservation is a stable attachment safeguard: it is necessary
for connected one-solid links in the current F2 implementation. It does not
change the coarse development motion-pass rate or relevant joint endpoints.

The observed trade-off is not “better mechanics versus worse geometry.” S1
improves IoU and silhouette on all pilots while also restoring attachment.
However, the added scaffold volume increases collision burden locally for L04
and L07 without changing GCFR. This is an attachment/shape benefit with a local
collision-cost trade-off.

At this stage the evidence supports describing the scaffold as an
**engineering safeguard**. Calling it a general paper-method contribution would
require the still-unaccessed holdout and broader transfer evidence.

## NOT_SUPPORTED

- No claim about 32-case formal holdout performance.
- No generalization claim beyond the three Robot-A pilots.
- No absolute body-only reconstruction claim.
- No protected-cut or auto-attachment-closure contribution claim.
- No claim that scaffold preservation universally improves collision metrics.
- No Direct VLM baseline or Metric Grounding conclusion.

The experiment stops here as required. The formal holdout remains locked and
unaccessed.
