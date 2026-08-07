$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$paperRoot = Split-Path -Parent $projectRoot
$python = Join-Path $paperRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw "Paper-wide virtual environment not found: $python"
}

& $python (Join-Path $PSScriptRoot "equal_weight_v2.py") `
    --entities (Join-Path $projectRoot "results\robot_entities.csv") `
    --remesh-features (Join-Path $projectRoot "results\robustness\remesh_features_long.csv") `
    --brep-pairs (Join-Path $projectRoot "results\brep\mesh_brep_pairs.csv") `
    --output-dir (Join-Path $projectRoot "results\equal_weight_v2")

if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
