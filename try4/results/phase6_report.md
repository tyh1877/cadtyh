# Try-4 Phase 6 report — Structured Review Contract

Phase 6 implemented and validated a bounded Repair Contract schema and a shared
Structured Review Skill. Round 1 produced one schema-valid contract for every one
of the 12 DEV_A/B parts; Round 2 and 3 produced contracts only for parts still
actionable in the blackboard. Across the formal run, 36 contracts were scheduled.

Every contract records failed gates, region and Feature ID, error type, severity,
render evidence, deterministic discrepancy, finite repair action, executable
parameter changes, protected features, invariants and history. Review inputs use
GT renders and Phase-5 discrepancies. No GT STEP/B-Rep, exact sketch, feature tree
or copied GT dimension enters a decision or executor artifact.

The phase also exposed a limitation in the original Phase-5 trace MFR: successful
CAD operations do not prove visible feature correctness. Post-repair review was
therefore added to Gate C after three numeric false positives were found. The
development amendment and superseded attempt remain archived.

Three early contracts and one Round-2 contract incorrectly protected features
whose parameterized operation would change. The repair preflight rejected all
four before CAD execution. They remain counted as contract-execution failures.
This shows the contract check works, but also shows that Feature-to-operation
ownership needs a better automated authoring aid.
