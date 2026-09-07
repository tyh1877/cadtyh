# Try-4 Phase 8 report — T2 DEV_A/B full run

Status: the full 12-part T2 development matrix has completed through at most three
repair rounds. No Robot C execution or Phase-9 transfer freeze has started.

## Final combined Gate C

| Result | Parts |
| --- | ---: |
| PASS / FROZEN | 0 |
| UNRESOLVED after Round 3 | 12 |
| Repair-trigger rate | 100% |
| Average scheduled rounds | 3.0 |
| Contract execution | 32/36 (88.9%) |
| Parts entering REPLAN | 7/12 (58.3%) |
| Regression per built candidate | 15/32 (46.9%) |
| Declared protected-subgraph preservation | 100% |
| Early-pass rate | 0% |
| Calls saved versus three rounds for all | 0 |

Attempt 01 initially classified R02_P01, R02_P02 and R02_P04 as numeric PASS.
Manual inspection found major topology/LOD failures, so the method was corrected
on the development set to require structured post-review for Gate C. The numeric
evaluator and thresholds were not changed. All three then consumed their remaining
rounds and ended UNRESOLVED. Attempt-01 tables and method hashes are preserved.

## Accepted numeric artifacts

For each unresolved part, the blackboard retains the best candidate that did not
violate frozen regression rules. These are useful development artifacts, not PASS
models. Across the 12 paired parts:

| Metric | T1 mean | retained T2 mean | Direction |
| --- | ---: | ---: | --- |
| Voxel IoU ↑ | 0.2237 | 0.3402 | improved |
| Normalized Chamfer ↓ | 0.07967 | 0.04726 | improved |
| Normalized HD95 ↓ | 0.2654 | 0.1513 | improved |
| Mean silhouette IoU ↑ | 0.4256 | 0.5478 | improved |

Ten of 12 parts improve IoU, Chamfer and HD95; nine improve silhouette IoU. The
disagreement between these gains and 0/12 visual/LOD passes proves that the current
geometry metrics reward approximate envelopes but do not adequately enforce
mechanical topology and local detail.

## Free-form ablation

R02_P03 and R02_P05 received a separate one-round free-form review. Neither
free-form nor structured repair passed the combined gate. Structured repair had
higher IoU and lower Chamfer on both; free-form had slightly lower HD95 on R02_P03,
while structured repair was better on all three main geometry metrics for R02_P05.
Structured contracts additionally supplied locality, protected features and an
auditable action trace. With only two development parts, this is a diagnostic and
does not establish statistical superiority or convergence speed.

## Conclusion

Phases 6–8 establish a working, bounded and auditable repair loop, but the current
repair method does not solve the reconstruction task. Its bottleneck is the shared
shape/operation vocabulary and perceptual feature verification. Phase 9 must not
freeze this method for Robot C yet. The next development step should add region-
grounded visible-feature gates and richer generic profile/shell/web/fork/linkage
operations, then repeat DEV_A/B under a versioned protocol.
