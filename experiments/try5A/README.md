# Try-5A status

Try-5A Phase 1–10 are complete for R01: planning/dataflow, A0, A1, A2, canonical
assembly and unified evaluation. See `results/phase13_report.md`, `a0_report.md`,
`a1_report.md`, and `try5A_report.md`. No Robot B/transfer or Try-5B run exists.

Heavy A0 link CAD and assembly files are ignored under `A0/` and `assemblies/`;
tracked manifests, metrics and contact sheets preserve their hashes and results.

Try-5A coarse reconstruction is frozen at Try-5A.5. See
`../../try5A_frozen_spec.md` and revalidate the retained baseline with
`.venv/Scripts/python.exe experiments/try5A/scripts/validate_frozen_coarse_stage.py`.

Try-5B0 adds cached mesh/BVH, dirty-set evaluation, and selective Exact checks to
the canonical mechanical evaluator without changing the frozen Try-5A definitions.
Run it with `.venv/Scripts/python.exe experiments/try5A/scripts/run_try5b0.py` and
see `results/try5b0/try5B0_fast_evaluator_report.md`.
