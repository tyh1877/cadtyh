---
name: structured-part-repair
description: Apply a Try-4 structured repair contract to a prior CAD plan while preserving protected feature subgraphs, recording every change, and forbidding silent fallback.
---

# Structured Part Repair

Accept only a schema-valid contract and the immediately preceding generated plan.
Do not accept GT geometry. Apply actions in priority order and record the before
and after value or replacement strategy for each action.

For local repair, change only named targets. Byte-equivalent protected Feature
Graph nodes and their unaffected CAD-IR operations are mandatory. For replan,
replace the declared failing structure while retaining protected interfaces and
invariants. Never substitute a simpler primitive after an operation failure.

After execution, run the frozen evaluator. Roll back a repair when a previously
passing gate regresses or a protected subgraph changes. Escalate stagnant local
repair to replan. Stop at PASS/FROZEN or after Round 3 as UNRESOLVED.
