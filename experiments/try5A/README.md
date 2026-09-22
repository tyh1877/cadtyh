# Try-5A status

Try-5A Phase 1–10 are complete for R01: planning/dataflow, A0, A1, A2, canonical
assembly and unified evaluation. See `results/phase13_report.md`, `a0_report.md`,
`a1_report.md`, and `try5A_report.md`. No Robot B/transfer or Try-5B run exists.

Heavy A0 link CAD and assembly files are ignored under `A0/` and `assemblies/`;
tracked manifests, metrics and contact sheets preserve their hashes and results.

## Formal experiment governance

Formal paper matrices use `skills/experiment-governance/SKILL.md` and the
deterministic helpers in `evaluation/experiment_governance.py`. A runner prepares
the tracked configuration snapshot, dev/holdout split, parity report, failure
accounting, holdout log, and claim ledger. After the runner exits, invoke
`evaluation/validate_experiment.py`; only that independent command may write the
final `validation.json`.

The Try-5B.1-A1 pre-registration and dry-run evidence are under `protocol/`.

P0.5 closes the A1 development phase without consuming the holdout. Run the
paired 96-case development experiment and its independent validation with:

```powershell
.venv/Scripts/python.exe experiments/try5A/scripts/run_try5b1.py --mechanical-ablation-development experiments/try5A/protocol/try5b1_a1_mechanical_ablation.json
.venv/Scripts/python.exe experiments/try5A/evaluation/validate_experiment.py --phase development --result-dir experiments/try5A/results/try5b1_a1_development --config experiments/try5A/protocol/try5b1_a1_mechanical_ablation.json
```

Only after the candidate manifest is frozen and formal execution is authorized,
run the one-shot holdout evaluator followed by the independent formal validator:

```powershell
.venv/Scripts/python.exe experiments/try5A/evaluation/run_holdout.py --result-dir experiments/try5A/results/try5b1_a1_development --config experiments/try5A/protocol/try5b1_a1_mechanical_ablation.json --confirm-one-shot
.venv/Scripts/python.exe experiments/try5A/evaluation/validate_experiment.py --phase formal --result-dir experiments/try5A/results/try5b1_a1_development --config experiments/try5A/protocol/try5b1_a1_mechanical_ablation.json
```

The holdout command creates an atomic lock before evaluation and refuses a
second run. Do not use it for smoke tests.

P1 freezes the formal analysis and runs a non-evaluating readiness gate. Run it
from a committed and pushed implementation state:

```powershell
.venv/Scripts/python.exe experiments/try5A/evaluation/p1_readiness.py --result-dir experiments/try5A/results/try5b1_a1_development --config experiments/try5A/protocol/try5b1_a1_mechanical_ablation.json --analysis-plan experiments/try5A/protocol/try5b1_a1_p1_analysis_plan.json
```

This fingerprints both runtimes, evaluator code, frozen CAD, and evaluator-only
GT inputs without evaluating a holdout configuration. Formal execution also
requires explicit user authorization and the `--confirm-one-shot` flag; a crash
after lock creation consumes the attempt.

The superseding A1 scaffold experiment uses a development-only input file and a
separate unaccessed holdout lock. Prepare, run the six development candidates,
and independently validate with:

```powershell
.venv/Scripts/python.exe experiments/try5A/scripts/run_try5b1.py --prepare-scaffold-ablation experiments/try5A/protocol/try5b1_a1_frozen_scaffold_ablation.json
.venv/Scripts/python.exe experiments/try5A/scripts/run_try5b1.py --run-scaffold-ablation-development experiments/try5A/protocol/try5b1_a1_frozen_scaffold_ablation.json
.venv/Scripts/python.exe experiments/try5A/evaluation/validate_scaffold_ablation.py --result-dir experiments/try5A/results/try5b1_a1_frozen_scaffold --config experiments/try5A/protocol/try5b1_a1_frozen_scaffold_ablation.json
```

These commands do not authorize or execute the 32-case formal holdout.

Try-5A coarse reconstruction is frozen at Try-5A.5. See
`../../try5A_frozen_spec.md` and revalidate the retained baseline with
`.venv/Scripts/python.exe experiments/try5A/scripts/validate_frozen_coarse_stage.py`.

Try-5B0 adds cached mesh/BVH, dirty-set evaluation, and selective Exact checks to
the canonical mechanical evaluator without changing the frozen Try-5A definitions.
Run it with `.venv/Scripts/python.exe experiments/try5A/scripts/run_try5b0.py` and
see `results/try5b0/try5B0_fast_evaluator_report.md`.
