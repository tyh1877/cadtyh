# Formal experiment artifact contract

A formal result directory must contain:

- `experiment_config_snapshot.json`: exact tracked configuration content.
- `case_split.json`: complete development/holdout IDs, counts, hashes, and lock policy.
- `condition_parity.json`: declared and observed condition differences.
- `manifest.json`: config file hash, canonical config hash, split hash, implementation hashes, environment, and inputs.
- `failure_accounting.json`: requested, completed, and failed cases for every condition.
- `holdout_evaluation_log.json`: one event per condition, with `followed_by_tuning=false`.
- `claim_ledger.json`: every paper-facing claim mapped to artifact, field, operator, expected value, and evidence type.
- `validation.json`: written only by the independent validator.

Claim evidence types:

- `computed`: produced by an evaluator from raw artifacts; allowed to close a hard gate.
- `copied`: transferred from another result; context only.
- `asserted`: written as a constant or policy declaration; cannot close a hard gate.
- `inferred`: interpretation from other values; cannot close a hard gate.

Tracked JSON must use repository-relative paths. Raw CAD, meshes, renders, caches, and downloaded data remain under ignored artifact/data locations with hashes recorded in the manifest.

Development results may guide repair. Holdout results must never be supplied to the generator, repair scheduler, candidate controller, or prompt. If holdout is rerun or followed by tuning, invalidate the formal bundle and create a new pre-registered experiment version.
