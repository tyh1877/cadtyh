# P0 paper-experiment governance requirement-to-evidence checklist

- [x] A tracked A1 configuration defines the sole condition variable and freezes all shared inputs, budgets, seeds, evaluators, and metrics.
- [x] The 128 frozen coupled configurations are deterministically split into a development set and a locked holdout with disjoint IDs and hashes.
- [x] An automatic parity audit rejects any C1/C2 difference outside the declared mechanical-policy fields.
- [x] Mechanical gates distinguish computed evidence from copied, asserted, or inferred values; asserted evidence cannot close a hard gate.
- [x] Candidate acceptance and rollback are runtime decisions with selected candidate, failed gates, and prior candidate recorded.
- [x] The B1 FreeCAD worker accepts policy flags while preserving existing constrained behavior by default.
- [x] An independent validator, not the experiment runner, verifies manifests, split counts, denominators, one-shot holdout use, and claim evidence.
- [x] Unit tests cover split determinism, parity, rollback, unconstrained acceptance, claim validation, denominator preservation, and holdout reuse rejection.
- [x] A governance dry-run materializes and validates the A1 split/parity without invoking FreeCAD or GT evaluation.
- [x] A project-level governance skill documents the mandatory workflow and artifact contract.
