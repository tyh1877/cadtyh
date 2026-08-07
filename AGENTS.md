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

## Git finalization

- After Codex modifies project code or experiment configuration, run relevant
  validation, inspect the diff, and create a local Git commit containing only the
  current task's changes.
- Do not push unless a remote exists and the user has requested or authorized it.
- Never commit secrets, the virtual environment, downloaded third-party datasets,
  or large generated mesh/render caches.
