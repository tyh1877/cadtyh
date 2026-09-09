# Project working rules

## Python environment

- Run every paper experiment with the repository-wide `.venv/Scripts/python.exe`.
- Do not install experiment dependencies into the system Python environment.
- When adding or changing a direct dependency, update the root `requirements.txt`.

## Experiment reproducibility

- Treat `go_nogo1/protocol.md` as the frozen Go/No-Go 1 protocol.
- Keep downloaded datasets and generated heavy geometry outside Git; preserve their
  source URLs, versions, checksums, and regeneration scripts in tracked files.
- Do not tune metrics on a frozen audit/test set. Metric development must use a
  declared development split and must be evaluated once on a separate holdout.

## Experiment development structure

- Keep Try5, Try5.1, Try5.2, and other incremental Try5 work inside
  `experiments/try5A/`.
- Modify the canonical `scripts/`, schemas, and evaluators directly. Do not keep
  parallel implementations that add no lasting value.
- Commit every runnable development milestone. Tag formal results or freeze them
  with a manifest that records the exact commit and result provenance.
- Preserve older results through input hashes, script commit identifiers, and
  result tables. Do not duplicate the entire implementation merely to retain
  history.
- Create a new top-level experiment directory only when the research object,
  inputs, or architecture changes fundamentally, such as a Try5-to-Try6
  transition.

## Git finalization

- After Codex modifies project code or experiment configuration, run relevant
  validation, inspect the diff, and create a local Git commit containing only the
  current task's changes.
- Do not push unless a remote exists and the user has requested or authorized it.
- Never commit secrets, the virtual environment, downloaded third-party datasets,
  or large generated mesh/render caches.
- The user has authorized pushing Codex's completed code and experiment-
  configuration changes to the configured GitHub remote after validation and a
  focused local commit. Preserve and exclude unrelated user changes.
