# Try-6.0-D0 requirement-to-evidence checklist

D0 is a standalone no-GT/no-VLM/no-final-mechanics diagnosis. C1-v2 and C2
remain immutable, including the historical C2 execution label documented
here as `NO_FEASIBLE_CANDIDATE_UNDER_FROZEN_SEARCH`.

- [ ] Hash-audit frozen C1/C2 domain, KFDG, CAD compiler, KFDE artifact/sweep/allowed-region/tolerance and holdout lock; record no GT/VLM/final mechanics inputs.
- [ ] Freeze 5 canonical probes (P0–P4), P5 exact-mapping exclusion, Sobol 256 seed, top-5 local seeds, 12 coordinate proposals each, 1800 s ceiling, strict epsilon and counterfactual subsets before any D0 CAD build.
- [ ] For each evaluated theta, build CAD and compute exact 13-component BREP intersections, `g_sum`, `g_max`, component/neighbor/pose counts and feasibility; preserve every failed build.
- [ ] Verify same-theta deterministic repeat, same result as frozen C2 KFDE checker and counterfactual subset arithmetic.
- [ ] Run P0–P4 first, then all 256 Sobol points and frozen 60 local proposals without visual loss or result-conditioned tuning.
- [ ] Compute empirical Stage-A feasible density, near-feasible counts, feasible parameter ranges/distances and descriptive Spearman correlations.
- [ ] Derive full/minus-one-neighbor counterfactuals from frozen component vector only; do not change KFDE or select CAD.
- [ ] Audit fixed/interface occupancy and F0 exact-mapping availability; independently validate final D0 decision, C1/C2 immutability, GT=0, mechanics=0, VLM=0 and holdout lock.
