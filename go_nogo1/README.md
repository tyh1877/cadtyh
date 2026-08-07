# Go/No-Go 1 experiment project

## Environment

The project uses the repository-local Python 3.12 environment at `.venv`.

```powershell
cd D:\CADtest\papertest\go_nogo1
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -c "import sys; print(sys.executable)"
```

All automated experiment commands must call `.venv\Scripts\python.exe` directly so
they do not depend on shell activation state.

## Data regeneration

Downloaded datasets are intentionally excluded from Git.

1. Clone `https://github.com/utecrobotics/urdf_files_dataset` into
   `sources/urdf_files_dataset` and checkout commit
   `81f4cdac42c3a51ba88833180db5bf3697988c87`.
2. Run `scripts/download_trossen_step.py` to obtain the official public STEP
   calibration files and their checksums.
3. Run the inventory, entity-feature, sample-selection, robustness, rendering, and
   B-Rep scripts in that order. Exact thresholds are in `protocol.md`.

## Current status

See `STATUS.md`. The original mesh descriptor passes tessellation robustness but
fails the current B-Rep validity gate. The next experiment revision uses normalized,
hierarchically equal-weighted metric groups; experts remain an auxiliary validation.
