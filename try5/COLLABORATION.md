# Try5 collaboration quick start

1. Clone the repository and create a feature branch.
2. Use the repository `.venv/Scripts/python.exe`; do not install into system Python.
3. Start with [ASSET_INDEX.md](ASSET_INDEX.md) and the matching protocol in this directory.
4. Generated FCStd, STEP, STL and raw collision caches are intentionally excluded from Git. Regenerate them from the tracked CAD IR, contracts and scripts instead of committing them.
5. Keep D0/C0 baselines immutable. Put a new repair result under the relevant active Try5-A experiment directory, with a contract, CAD IR, evaluator result and concise report.
6. Before sharing a change, run the relevant evaluator, inspect the diff, commit only task files and push your branch.

The current active shared implementation is `experiments/try5A/`; `experiments/try5A_1/` is the preserved Try5-A.1 evidence set.
