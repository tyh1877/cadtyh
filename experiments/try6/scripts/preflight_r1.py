"""Freeze R1 source/protocol hashes before the five production-shaped calls."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tomllib
from datetime import datetime, timezone
from pathlib import Path

from experiments.try6.scripts.r1_contract import ROOT, HERE, audit_functional_authority, load, sha, validate_registry

RESULT = HERE / "results/try6_0_r1"


def save(path, obj):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def audit_frozen_result(directory):
    manifest = load(directory / "manifest.json")
    file_hashes = manifest.get("lightweight_result_sha256", manifest.get("result_file_sha256", {}))
    bad = [name for name, expected in file_hashes.items() if not (directory / name).is_file() or sha(directory / name) != expected]
    if bad: raise RuntimeError(f"frozen result hash mismatch: {directory.name}: {bad}")
    return {"manifest_sha256":sha(directory / "manifest.json"), "enumerated_files_checked":len(file_hashes), "unchanged":True}


def main():
    config_path = HERE / "protocol/r1_protocol.json"
    config = load(config_path)
    if (RESULT / "preflight.json").exists(): raise FileExistsError("R1 preflight already frozen")
    if config["starting_commit"] != subprocess.run(["git","rev-parse","HEAD"],cwd=ROOT,capture_output=True,text=True,check=True).stdout.strip():
        raise RuntimeError("starting commit drift")
    frozen = {"c1_v1":audit_frozen_result(HERE / "results/try6_0_c1"),
              "r0":audit_frozen_result(HERE / "results/try6_0_r0")}
    lock = load(ROOT / "experiments/try5A/results/try5b1_a1_frozen_scaffold/formal_holdout_lock.json")
    if lock.get("accessed") is not False or lock.get("evaluation_count") != 0: raise RuntimeError("formal holdout lock violated")
    authority = audit_functional_authority()
    registry = validate_registry()
    old_inputs = load(ROOT / config["source_input_manifest"])["inputs"]
    source_files = {}
    for name in ("engineering_text","sanitized_urdf","f0_fcstd","frozen_interface_contracts"):
        item = old_inputs[name]
        if sha(ROOT / item["path"]) != item["sha256"]: raise RuntimeError(f"input drift: {name}")
        source_files[name] = item
    images = []
    for view,item in old_inputs["images"].items():
        if sha(ROOT / item["path"]) != item["sha256"]: raise RuntimeError(f"image drift: {view}")
        images.append({"view":view,**item})
    for view in ("front","isometric","left","right","top","rear"):
        path = ROOT / config["f0_render_directory"] / f"{view}.png"
        if not path.is_file(): raise FileNotFoundError(path)
        images.append({"view":"f0_"+view,"path":str(path.relative_to(ROOT)).replace("\\","/"),"sha256":sha(path)})
    local = tomllib.loads((ROOT / config["model_config"]).read_text(encoding="utf-8"))
    if local["generation"]["model"] != config["requested_model"]: raise RuntimeError("model ID drift")
    if not local["provider"]["api_key"]: raise RuntimeError("API key absent")
    tracked = ["vfp_schema","kfdg_schema","prompt","functional_backbone","parameter_registry","assembler_rules"]
    frozen_hashes = {key:sha(ROOT / config[key]) for key in tracked}
    sys.path.insert(0,str(ROOT / "experiments/try5A/scripts"))
    from freecad_runtime import python_runtime
    version = subprocess.run([python_runtime(),"-c","import FreeCAD,json;print(json.dumps(FreeCAD.Version()))"],cwd=ROOT,capture_output=True,text=True,check=True).stdout.strip()
    output = {"schema_version":"robotcad_try6_r1_preflight_v1","timestamp_utc":datetime.now(timezone.utc).isoformat(),
        "starting_commit":config["starting_commit"],"protocol_sha256":sha(config_path),"frozen_hashes":frozen_hashes,
        "frozen_prior_results":frozen,"functional_authority_audit":authority,"parameter_registry_audit":registry,
        "source_files":source_files,"images":images,"prompt_text_sha256":frozen_hashes["prompt"],
        "model_requested":config["requested_model"],"api_base_url":local["provider"]["base_url"],
        "api_key_present":True,"api_key_recorded":False,"python_executable":sys.executable,
        "freecad_version":version,"formal_holdout_lock":{"accessed":False,"evaluation_count":0},
        "gt_evaluations":0,"target_calls":config["independent_calls"]}
    save(RESULT / "preflight.json", output)
    save(RESULT / "functional_backbone/backbone.json",load(ROOT / config["functional_backbone"]))
    save(RESULT / "functional_backbone/authority_audit.json",authority)
    save(RESULT / "parameter_registry/registry.json",load(ROOT / config["parameter_registry"]))
    save(RESULT / "parameter_registry/ownership_rules.json",load(ROOT / config["assembler_rules"]))
    save(RESULT / "vfp/schema.json",load(ROOT / config["vfp_schema"]))
    (RESULT / "vfp/prompt.txt").write_text((ROOT / config["prompt"]).read_text(encoding="utf-8"),encoding="utf-8")
    save(RESULT / "canonical_kfdg/assembler_rules.json",load(ROOT / config["assembler_rules"]))
    print(json.dumps({"status":"PREFLIGHT_FROZEN","image_count":len(images),"target_calls":config["independent_calls"]}))


if __name__ == "__main__": main()
