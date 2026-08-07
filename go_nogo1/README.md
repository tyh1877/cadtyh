# Go/No-Go 1: Mesh+URDF prototype feasibility

Go/No-Go 1 now asks whether public data can support a 20-case high-quality Mesh+URDF
prototype with deterministic geometry and kinematic evaluation. At least 15 cases
must be complete. Complexity is not a selection variable or decision gate. See
`protocol.md` for the frozen v5 target and `STATUS.md` for the result.

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

4. Run the screenshot-defined 20-case prototype audit:

```powershell
.\.venv\Scripts\python.exe go_nogo1\scripts\prototype_feasibility.py `
  --candidate80 go_nogo1\results\benchmark_readiness\candidate_benchmark80.csv `
  --entities go_nogo1\results\robot_entities.csv `
  --dataset-root go_nogo1\sources\urdf_files_dataset\urdf_files `
  --output-dir go_nogo1\results\prototype_feasibility
```

Complete `visual_review.csv` from the generated six-view contact sheets, then rerun
the same command for the final decision. The current result is 17/20: Go.

## Complexity diagnostics

Earlier Audit-30, v2, and v3 scripts/results are retained for reproducibility. They
are optional post-hoc diagnostic analyses and do not select Benchmark-80 or determine
the primary Go/No-Go outcome.
