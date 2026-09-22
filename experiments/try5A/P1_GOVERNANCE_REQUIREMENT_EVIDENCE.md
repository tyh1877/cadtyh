# P1 formal holdout governance: requirement-to-evidence checklist

P1 is a governance and readiness phase. It must not execute, deserialize for
evaluation, or report metrics from the 32-case formal holdout.

- [ ] The P0.5 development bundle independently validates as `PASS` with zero holdout events.
  Evidence: `results/try5b1_a1_development/validation.json` and the P1 readiness gate.
- [ ] The experiment config, split, development runner, worker, candidate manifest, and selected candidates are unchanged since P0.5.
  Evidence: hash checks in `results/try5b1_a1_development/p1_readiness.json`.
- [ ] Every frozen pilot and non-pilot FCStd used by the holdout evaluator exists and has a recorded SHA-256.
  Evidence: `results/try5b1_a1_development/p1_environment_manifest.json`.
- [ ] The evaluator-only GT inputs exist, are fingerprinted, and remain inaccessible to generator/repair code.
  Evidence: evaluator input inventory in `p1_environment_manifest.json` and static isolation checks.
- [ ] The Python and FreeCAD runtimes and required packages are available and recorded.
  Evidence: runtime inventory in `p1_environment_manifest.json`.
- [ ] Primary outcomes, estimands, comparison direction, denominator policy, and no-post-holdout-tuning rule are frozen before execution.
  Evidence: `protocol/try5b1_a1_p1_analysis_plan.json`.
- [ ] No one-shot lock or formal holdout output exists before P1 approval.
  Evidence: absence checks in `p1_readiness.json`.
- [ ] A failed or interrupted formal attempt consumes the allowance; deleting the lock or silently retrying is forbidden.
  Evidence: analysis plan, atomic-lock test, and holdout CLI confirmation gate.
- [ ] Formal execution requires a passing P1 record plus an explicit one-shot confirmation flag.
  Evidence: `evaluation/run_holdout.py` preflight enforcement.
- [ ] P1 governance is independently reproducible from the committed repository state without evaluating holdout cases.
  Evidence: committed readiness command, tests, and final `p1_governance_record.json`.
