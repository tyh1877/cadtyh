# Go/No-Go 1 — current status under the v4 target

## Current decision

**Technical Go: the candidate pool can support a unified Mesh+URDF Benchmark-80.**

This decision concerns data and evaluation feasibility. It does not claim that the
benchmark is release-ready, nor that the current complexity score is valid.

## Automated evidence

| Check | Current evidence | Gate |
|---|---:|---:|
| Strictly eligible robot entities | 142 | at least 80 |
| Manufacturers in eligible pool | 16 | candidate diversity |
| URDF parse and graph validity | 142/142 | required per selected case |
| Visual mesh resolution >=90% | 142/142 | required per selected case |
| Non-fixed-link visual coverage >=80% | 142/142 | required per selected case |
| Actuated joint and kinematic depth present | 142/142 | required per selected case |
| Loadable visual mesh and finite features | 142/142 | required per selected case |
| Complexity-blind candidate manifest | 80 entities | exactly 80 |
| Manufacturers in candidate Benchmark-80 | 16 | at least 10 |
| Maximum manufacturer share | 17.5% | at most 25% |
| Maximum upstream-source share | 50.0% | at most 50% |

The machine-readable result is written to
`results/benchmark_readiness/readiness_summary.json`. The candidate manifest is an
existence proof and review draft, not the final frozen paper test set.

## What is no longer a gate

- Complexity low/medium/high balance.
- Expert agreement on a composite complexity score.
- Mesh-complexity correlation with STEP/B-Rep.
- Mesh-complexity correlation with fixed-budget simplification error.
- Remesh rank stability of a composite complexity score.

These can inform a post-hoc sensitivity section but cannot turn an otherwise fair
same-case SOTA comparison into No-Go.

## Release readiness

The benchmark is **not yet release-ready**. Remaining work includes license audit,
manual manifest review, canonical normalization, evaluator implementation, leakage
review, and same-case baseline execution. These are tracked separately from the
technical feasibility decision.

## Historical complexity diagnostics

The original descriptor was stable under remeshing but failed Mesh/B-Rep agreement.
The equal-weight v2 descriptor also failed B-Rep agreement. Objective-task v3 reached
Validation rho=0.367 against fixed-budget approximation difficulty, below its 0.60
target. Therefore v3 remains No-Go **as a validated complexity metric**, while the
Mesh+URDF benchmark feasibility decision is Technical Go.
