# Try-5B.1-A1 Protection Effect Audit

This audit inspects geometry effects only. It must not run the 96-case
mechanical matrix, access formal holdout cases, change F2 geometry, or add an
evaluator/controller.

- [x] Use only frozen F2 inputs for L03, L04, and L07; verify their hashes against the dry-run freeze.
- [x] Record A: proximal/interface protected bore/corridor cut as a separate operation.
- [x] Record B: proximal mating-envelope cut as a separate operation.
- [x] Record C: distal rotary/interface clearance cut as a separate operation.
- [x] Record D: frozen scaffold preservation/fusion as a separate operation.
- [x] Record E: auto attachment closure only if it is reached by the current execution path.
- [x] For every link/operation record applicability, execution, before/after B-Rep hash, volume, solid count, bbox, deltas, and computed `geometry_changed`.
- [x] Classify every executed operation as `EXECUTED_BUT_NO_OP` or `GEOMETRY_EFFECTIVE` from geometry evidence, never from call-site execution alone.
- [x] Save one `protection_trace.json` per link plus a complete summary table.
- [x] Rename the generic per-joint result key from `holdout_samples` to `sample_count` without changing evaluator behavior.
- [x] Prove that no GT evaluator, 96-case mechanical evaluation, formal holdout, repair, rejection, or rollback path ran.
- [x] Independently validate trace completeness and issue exactly one recommendation: `GO_BUNDLE_ABLATION`, `REFRAME_AS_SCAFFOLD_ABLATION`, or `STOP_A1_WEAK_EFFECT`.
- [x] Stop after the audit; do not launch the three-link formal run.

Final result: `PASS`; recommendation: `REFRAME_AS_SCAFFOLD_ABLATION`.
Protected cuts are effective on 0/3 links, scaffold fusion is effective on 3/3,
and auto attachment closure executes on 0/3. Formal execution remains stopped.
