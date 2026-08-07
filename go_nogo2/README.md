# Go/No-Go 2

This folder implements the frozen SOTA-gap pilot in `protocol.md`.

## Current stage

- Go/No-Go 1 is frozen at commit `7b01d43` (`17/20`, GO).
- The ten-case builder is deterministic and copies only complete cases.
- CADIR/SimpleCADAPI has a public repository and is pinned in
  `baseline_registry.json`.
- Direct GPT execution requires `OPENAI_API_KEY` supplied through the process
  environment. Secrets must never be stored in this repository.
- ArtiCAD and AssemCAD require official runnable implementations. Until those
  are available, the final pilot decision must remain `INCONCLUSIVE`.

## Build the fixed ten-case dataset

```powershell
.\.venv\Scripts\python.exe go_nogo2\scripts\build_pilot_dataset.py `
  --audit go_nogo1\results\prototype_feasibility\case_audit.csv `
  --dataset-root go_nogo1\sources\urdf_files_dataset\urdf_files `
  --go1-results go_nogo1\results\prototype_feasibility `
  --output-dir go_nogo2\data\pilot10 `
  --manifest go_nogo2\manifests\pilot10_manifest.csv
```

The generated `data/`, downloaded `external/`, and raw `runs/` folders are
ignored by Git. Lightweight manifests, protocols, evaluator code, and summary
tables are tracked.
