---
name: experiment-governance
description: Govern formal RobotCAD paper experiments and ablations before execution, including dev/holdout locking, condition parity, runtime candidate decisions, claim evidence, failure accounting, and independent validation. Use for a formal paper matrix or when final metrics will support a paper claim; do not use for ordinary exploratory debugging.
---

# RobotCAD Experiment Governance

Use this after the general paper-experiment discipline has identified the protocol and evidence requirements.

Before a formal matrix:

1. Put all shared variables and condition policies in one tracked configuration. Do not encode condition differences only in Python branches.
2. Materialize a deterministic development/holdout split before candidate generation. Generator and repair code may consume development IDs only; holdout is one-shot final evaluation.
3. Run the condition-parity audit. Any difference outside the declared self-variable is a hard stop.
4. Use `CandidateController` only when the pre-registered protocol actually has runtime accept/reject/rollback decisions. For a generation-then-independent-evaluation ablation, do not introduce a controller: freeze every generated candidate and record failures without repair, deletion, acceptance filtering, or rerun.
5. Keep FAST and Exact evaluators active in every condition. An unconstrained condition disables their rejection authority, not measurement.
6. Preserve all cases in failure accounting, including build, export, reopen, parse, and evaluator failures.

Before claiming completion:

- Build a claim ledger. A hard claim requires `computed` evidence from a named artifact and field; copied, asserted, or inferred evidence cannot close it.
- Run `evaluation/validate_experiment.py` as a separate command after the runner exits. The runner must not author its own final PASS.
- Reject a result bundle if holdout was evaluated more than once per condition or followed by tuning.

Read [references/artifact-contract.md](references/artifact-contract.md) when creating a formal result directory or claim ledger.
