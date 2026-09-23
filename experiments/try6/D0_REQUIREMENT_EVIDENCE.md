# Try-6.0-D0 requirement-to-evidence checklist

D0 is a standalone no-GT/no-VLM/no-final-mechanics diagnosis. C1-v2 and C2
remain immutable, including the historical C2 execution label documented
here as `NO_FEASIBLE_CANDIDATE_UNDER_FROZEN_SEARCH`.

- [x] Hash-audit frozen C1/C2 domain, KFDG, compiler, KFDE artifact/sweep/allowance/tolerance and holdout (`pre_run_manifest.json`, independent validation); no GT/VLM/final mechanics inputs.
- [x] Freeze P0–P4, P5 exact-mapping exclusion, Sobol 256 seed, top-5×12 local search, 1800 s ceiling, epsilon and counterfactual subsets before D0 (`1999132`, `1698070`).
- [x] Build all 322 requested CAD points (including technical P3 repeat), compute all 13 exact BREP component volumes, `g_sum`, `g_max` and strict feasibility; 0 infrastructure failures (`all_candidate_records.json`, contribution matrix).
- [x] Verify same-theta repeat exactly, technical P3 match with frozen C2 checker, and every full/minus-one-neighbor counterfactual vector (`canonical_probes/reproducibility_check.json`, `audit/independent_validation.json`).
- [x] Complete P0–P4 then all 256 Sobol and all 60 local proposals under fixed budget; no visual ranking or result-conditioned tuning.
- [x] Compute Stage-A feasible density 0/256, near-threshold counts, unavailable feasible ranges/nearest distances, and D0-only descriptive Spearman correlations.
- [x] Derive frozen full/minus-one-neighbor counterfactuals without changing KFDE or selecting CAD; all strict feasible counts 0/321.
- [x] Audit J04/J06 fixed ownership, allowed region and missing exact F0 mapping; independent decision `DOMAIN_KFDE_INCOMPATIBLE`, prior hashes unchanged, GT/mechanics/VLM/holdout 0. Stop before C2-v2.
