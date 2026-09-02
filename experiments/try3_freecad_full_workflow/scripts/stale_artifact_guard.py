from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Iterable


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_stage_manifest(
    path: Path,
    *,
    stage: str,
    status: str,
    schema_version: str,
    producer: str,
    input_paths: Iterable[Path],
    stale_downstream_artifacts_allowed: bool = False,
) -> None:
    manifest = {
        "stage": stage,
        "status": status,
        "schema_version": schema_version,
        "producer": producer,
        "input_hashes": {
            str(p): file_sha256(p) for p in input_paths if p.exists()
        },
        "stale_downstream_artifacts_allowed": stale_downstream_artifacts_allowed,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def assert_current_stage(manifest_path: Path, required_status: str = "SUCCESS") -> None:
    if not manifest_path.exists():
        raise RuntimeError(f"missing upstream manifest: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != required_status:
        raise RuntimeError(
            f"upstream stage is not current: {manifest_path} status={manifest.get('status')}"
        )
    if manifest.get("stale_downstream_artifacts_allowed") is not False:
        raise RuntimeError(f"stale downstream artifacts are not forbidden: {manifest_path}")

