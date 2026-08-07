# Go/No-Go 1: unified Mesh+URDF benchmark feasibility

Go/No-Go 1 now asks whether the public candidate pool can support one fair,
traceable, uniformly evaluated 80-robot benchmark. It does not require complexity
strata or a validated composite complexity score. See `protocol.md` for the frozen
v4 target and `STATUS.md` for the current decision.

## Paper-wide environment

All experiments use the repository-wide isolated Python 3.12 environment:

```powershell
cd D:\CADtest\papertest
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip check
```

## Data regeneration

Downloaded datasets are excluded from Git.

1. Clone `https://github.com/utecrobotics/urdf_files_dataset` into
   `sources/urdf_files_dataset` and checkout commit
   `81f4cdac42c3a51ba88833180db5bf3697988c87`.
2. Run the inventory and entity-feature scripts to regenerate
   `results/robot_entities.csv`.
3. Run the v4 readiness audit:

```powershell
.\.venv\Scripts\python.exe go_nogo1\scripts\benchmark_readiness.py `
  --entities go_nogo1\results\robot_entities.csv `
  --output-dir go_nogo1\results\benchmark_readiness
```

The generated Benchmark-80 manifest proves that a compliant set exists. It remains
a review candidate until license, leakage, normalization, and evaluator checks are
complete.

## Complexity diagnostics

Earlier Audit-30, v2, and v3 scripts/results are retained for reproducibility. They
are optional post-hoc diagnostic analyses and do not select Benchmark-80 or determine
the primary Go/No-Go outcome.
