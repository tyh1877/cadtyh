# Robot CAD benchmark paper experiments

This repository contains the complete paper experiment workspace. All sub-experiments
share one isolated Python environment at the repository root:

```powershell
cd D:\CADtest\papertest
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip check
```

Automation should call `D:\CADtest\papertest\.venv\Scripts\python.exe` directly.
Sub-experiments must not create their own virtual environments unless a documented,
incompatible dependency requires an explicit exception.

Current experiment: [Go/No-Go 1](go_nogo1/README.md).
