from __future__ import annotations

import json
import subprocess
from pathlib import Path

from codex_agent_common import ROOT, RUNS, RESULTS, load_json, sha256, write_json


FREECAD_PYTHON = Path(r"D:\software\freeCAD\install\bin\python.exe")
HELPER = Path(__file__).with_name("freecad_codex_backend_smoke.py")


def main() -> int:
    output = RUNS / "backend_smoke"
    completed = subprocess.run([str(FREECAD_PYTHON), str(HELPER), str(ROOT), str(output)], cwd=str(ROOT), capture_output=True, text=True, timeout=180, check=False)
    result = load_json(output / "smoke_result.json") if (output / "smoke_result.json").exists() else {"status": "FAIL", "error": "missing smoke result"}
    tracked = {"status": result["status"], "helper_returncode": completed.returncode, "backend_sha256": sha256(ROOT / "robotcad/backends/freecad_api/FreeCADBackend.py"), "operations": [item for case in result.get("cases", []) for item in case.get("native_operations", [])], "fallbacks": sum(case.get("fallbacks", 0) for case in result.get("cases", [])), "heavy_artifact_root": output.relative_to(ROOT).as_posix()}
    write_json(RESULTS / "codex_agent_v1_backend_smoke.json", tracked)
    print(json.dumps(tracked, indent=2))
    return 0 if completed.returncode == 0 and result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

