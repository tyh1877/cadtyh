---
name: structured-part-review
description: Diagnose a Try-4 Macro-Part against allowed GT renders and frozen deterministic metrics, then emit a schema-valid repair contract with bounded actions and protected features.
---

# Structured Part Review

Consume every required review input. Identify WHAT is wrong from rendered visual
evidence and use deterministic discrepancies only for HOW MUCH. Never inspect or
copy GT STEP/B-Rep, exact GT dimensions, sketches, or feature trees.

Choose `LOCAL_REPAIR` only when the main shape family and topology are credible.
Choose `REPLAN` for wrong main family, missing critical structure, or structurally
wrong multi-body layout. Use only the action enum in the contract schema.

Each violation names a region, feature, type, severity, requirement, evidence
views and numeric discrepancy. Every action names executable parameters. List
features that are already credible as `protected_features`; repair must preserve
their CAD-IR subgraph. State invariant dimensions/interfaces in `do_not_change`.

Do not declare feature correctness solely from execution-trace MFR. Record visual
uncertainty rather than inventing evidence.
