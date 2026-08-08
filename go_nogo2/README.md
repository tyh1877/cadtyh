# Go/No-Go 2

This folder implements the frozen SOTA-gap pilot in `protocol.md`.

## Current stage

- Go/No-Go 1 is frozen at commit `7b01d43` (`17/20`, GO).
- The ten-case builder is deterministic and copies only complete cases.
- CADIR/SimpleCADAPI has a public repository and is pinned in
  `baseline_registry.json`.
- Direct LLM and CADIR/SimpleCAD use the same Alibaba Cloud Model Studio
  `qwen3.7-plus` configuration. Put the key only in the ignored
  `config/llm.local.toml`; secrets must never be committed.
- ArtiCAD and AssemCAD require official runnable implementations. Until those
  are available, the final pilot decision must remain `INCONCLUSIVE`.

The executed `cadir_simplecad` track is an SDK-conditioned baseline, not a full
reproduction of every component claimed in the CADIR paper. The public repository
contains SimpleCADAPI and its agent skill, but not the five-agent orchestrator,
learned retrieval encoders, or frozen indexed case library. See
`method_implementation.md` for the exact boundary.

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

## Reproduce the result summary

After both executable baselines finish, rebuild the tracked tables and execute
the result notebook:

```powershell
.\.venv\Scripts\python.exe go_nogo2\scripts\summarize_pilot.py
.\.venv\Scripts\python.exe go_nogo2\scripts\build_results_notebook.py
```

The concise decision report is `results/go_nogo_report.md`; the executed
analysis is `notebooks/02_executable_baseline_results.ipynb`.

## Configure the shared LLM

Edit the already-created, Git-ignored `go_nogo2/config/llm.local.toml` and put
your Model Studio key after `api_key =`. The default endpoint is the Beijing
DashScope OpenAI-compatible endpoint. If your key belongs to another region or
a workspace-specific endpoint, change `base_url` to the matching URL.

Validate without making a paid request:

```powershell
.\.venv\Scripts\python.exe go_nogo2\scripts\check_llm_config.py
```

After the offline check passes, make one minimal paid connectivity request:

```powershell
.\.venv\Scripts\python.exe go_nogo2\scripts\check_llm_config.py --live
```

Both baselines must call `load_shared_llm()` from `scripts/llm_config.py`; this
prevents either baseline from silently changing the model or sampling settings.

## Run the executable baselines

```powershell
.\.venv\Scripts\python.exe go_nogo2\scripts\run_baseline.py `
  --method direct_frontier_mllm
.\.venv\Scripts\python.exe go_nogo2\scripts\run_baseline.py `
  --method cadir_simplecad
```

Direct uses one model call per case. The SDK-conditioned CADIR track permits up
to three calls, where only schema or CAD execution errors are returned for
repair. Deterministic evaluation metrics and GT geometry are never fed back to
either generator.
