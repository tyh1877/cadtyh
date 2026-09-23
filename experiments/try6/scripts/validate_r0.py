"""Independent post-run R0 evidence audit; reads no GT or holdout cases."""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

from jsonschema import Draft202012Validator

from experiments.try6.scripts.kfdg_v1_contract import parse_raw

ROOT = Path(__file__).resolve().parents[3]
HERE = ROOT / "experiments/try6"
RESULT = HERE / "results/try6_0_r0"


def load(path): return json.loads(Path(path).read_text(encoding="utf-8"))
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def main():
    c1_dir = HERE / "results/try6_0_c1"
    c1_manifest = load(c1_dir / "manifest.json")
    frozen = {name: sha(c1_dir / name) == expected for name, expected in c1_manifest["lightweight_result_sha256"].items()}
    if not all(frozen.values()): raise RuntimeError("frozen C1-v1 artifact hash mismatch")
    holdout_lock = load(ROOT / "experiments/try5A/results/try5b1_a1_frozen_scaffold/formal_holdout_lock.json")
    holdout_intact = holdout_lock.get("accessed") is False and holdout_lock.get("evaluation_count") == 0
    if not holdout_intact: raise RuntimeError("formal holdout lock no longer intact")
    schema = load(HERE / "protocol/kfdg_v1.schema.json")
    contract_dir = RESULT / "kfdg_contract"
    save(contract_dir / "kfdg_v1.schema.json", schema)
    valid = load(HERE / "fixtures/kfdg_v1_valid_full.json")
    save(contract_dir / "valid_fixture.json", valid)
    invalids = {
        "missing_required": lambda x: x.pop("constraints"),
        "unknown_field": lambda x: x.update(unexpected=1),
        "wrong_enum": lambda x: x["parameters"][0].update(provenance="MANUFACTURING_RULE"),
        "wrong_parameter_type": lambda x: x["parameters"][0].update(value="40"),
        "invalid_unit": lambda x: x["parameters"][0].update(unit="inch"),
        "duplicate_id": lambda x: x["parameters"][0].update(id="port_01"),
        "dangling_parameter_ref": lambda x: x["geometric_features"][0].update(parameter_refs=["missing"]),
    }
    for name, mutate in invalids.items():
        item = copy.deepcopy(valid); mutate(item)
        save(contract_dir / "invalid_fixtures" / f"{name}.json", item)
    save(contract_dir / "invalid_fixtures/wrong_root_type.json", [valid])
    duplicate_ref = copy.deepcopy(valid)
    duplicate_ref["geometric_features"][0]["parameter_refs"].append("housing_width")
    save(contract_dir / "invalid_fixtures/duplicate_parameter_ref.json", duplicate_ref)
    suite = unittest.defaultTestLoader.loadTestsFromName("experiments.try6.tests.test_kfdg_v1_contract")
    test_result = unittest.TestResult(); suite.run(test_result)
    contract_tests = {"run": test_result.testsRun, "failures": len(test_result.failures), "errors": len(test_result.errors),
                      "pass": test_result.wasSuccessful() and test_result.testsRun >= 12,
                      "fixture_hashes": {p.name: sha(p) for p in (HERE / "fixtures").glob("kfdg_v1_*.json")}}
    save(contract_dir / "contract_test_report.json", contract_tests)
    if not contract_tests["pass"]: raise RuntimeError("contract test gate failed")
    transport = load(RESULT / "schema_transport/transport_report.json")
    levels = load(HERE / "protocol/r0_schema_levels.json")["levels"]
    specs = {s["level"]: s["schema"] for s in levels}; specs[4] = schema
    transport_checks = []
    for level in range(5):
        record = next(x for x in transport["levels"] if x["level"] == level)
        if record["classification"] != "RAW_RESPONSE_VALID":
            transport_checks.append({"level":level,"pass":False,"classification":record["classification"]}); continue
        request = load(RESULT / "schema_transport" / f"level{level}_request.json")
        http = load(RESULT / "schema_transport" / f"level{level}_http_response.json")
        sdk = load(RESULT / "schema_transport" / f"level{level}_response.json")
        raw = (RESULT / "schema_transport" / f"level{level}_raw_response.txt").read_text(encoding="utf-8")
        sent = request["response_format"]["json_schema"]
        valid = sent["schema"] == specs[level] and sent["strict"] is True and raw == http["choices"][0]["message"]["content"] == sdk["choices"][0]["message"]["content"]
        try:
            value = json.loads(raw); Draft202012Validator(specs[level]).validate(value)
            if level == 4: parse_raw(raw)
        except Exception:
            valid = False
        transport_checks.append({"level":level,"pass":valid,"classification":record["classification"]})
    rebuild = load(RESULT / "parametric_rebuild/rebuild_report.json")
    baseline_volume = rebuild["baseline"]["builder_result"]["final_volume_mm3"]
    rebuild_checks = []
    for edit in rebuild["edits"]:
        entry = edit["result"]
        protected = entry["protected_shape_signatures_before"] == entry["protected_shape_signatures_after"]
        volume_changed = abs(entry["final_volume_mm3"] - baseline_volume) > 1e-6
        output = HERE / "artifacts/try6_0_r0/parametric_rebuild" / f"edit_{edit['id']}"
        files_present = all((output / name).is_file() for name in ("edited.FCStd","edited.step","edited.stl"))
        check = entry["pass"] and protected and volume_changed and files_present and entry["connected_solid_count"] == 1
        rebuild_checks.append({"edit":edit["id"],"pass":check,"protected_shapes_same":protected,"final_volume_changed":volume_changed,"artifacts_present":files_present})
    raw = (RESULT / "end_to_end_smoke/raw_model_response.json").read_text(encoding="utf-8")
    raw_value = json.loads(raw)
    schema_valid = Draft202012Validator(schema).is_valid(raw_value)
    try:
        parse_raw(raw)
        semantic_valid = True; semantic_error = None
    except Exception as error:
        semantic_valid = False; semantic_error = f"{type(error).__name__}: {error}"
    refs = [{"feature_id": f["id"], "parameter_refs": f["parameter_refs"]} for f in raw_value["geometric_features"] if len(f["parameter_refs"]) != len(set(f["parameter_refs"]))]
    request = load(RESULT / "end_to_end_smoke/request.json")
    http = load(RESULT / "end_to_end_smoke/http_response.json")
    sdk = load(RESULT / "end_to_end_smoke/response.json")
    same_raw = raw == http["choices"][0]["message"]["content"] == sdk["choices"][0]["message"]["content"]
    schema_sent = request["response_format"]["json_schema"]["schema"] == schema
    decision = "SCHEMA_TRANSPORT_BLOCKED" if not semantic_valid else ("READY_FOR_C1_V2" if all(x["pass"] for x in rebuild_checks) else "PARAMETRIC_ROBUSTNESS_BLOCKED")
    if decision == "READY_FOR_C1_V2":
        raise RuntimeError("no end-to-end success artifact exists; cannot award READY")
    audit = {"schema_version":"robotcad_try6_r0_independent_validation_v1", "timestamp_utc":datetime.now(timezone.utc).isoformat(),
             "frozen_c1_v1_artifacts_unchanged":all(frozen.values()), "frozen_c1_v1_hash_check":frozen,
             "formal_holdout_lock_intact":holdout_intact,"contract_tests":contract_tests,
             "transport_level_rechecks":transport_checks,"parametric_rebuild_rechecks":rebuild_checks,
             "end_to_end":{"raw_json_schema_valid":schema_valid,"raw_semantic_contract_valid":semantic_valid,
                "raw_semantic_error":semantic_error,"duplicate_parameter_refs":refs,"http_sdk_raw_equal":same_raw,
                "schema_actually_sent":schema_sent,"vlm_calls":1,"candidate_evaluations":0},
             "gt_evaluations":0,"formal_holdout_evaluations":0,"decision":decision}
    save(RESULT / "validation.json", audit)
    sys.path.insert(0, str(ROOT / "experiments/try5A/scripts"))
    from freecad_runtime import python_runtime  # noqa: E402
    freecad_version = subprocess.run([python_runtime(), "-c", "import FreeCAD,json;print(json.dumps(FreeCAD.Version()))"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    branch = subprocess.run(["git", "branch", "--show-current"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    sdk = load(RESULT / "schema_transport/sdk_config.json")
    artifact_hashes = {str(p.relative_to(RESULT)).replace("\\", "/"): sha(p) for p in RESULT.rglob("*") if p.is_file() and p.name != "manifest.json"}
    manifest = {"schema_version":"robotcad_try6_r0_manifest_v1", "decision":decision,
        "starting_commit":load(HERE / "protocol/r0_transport_protocol.json")["starting_commit"],
        "implementation_head_at_validation":head,"branch":branch,"model_requested":"qwen3.7-plus",
        "model_returned":sdk["model"],"sdk_version":sdk["openai_version"],"api_base_url":sdk["api_base_url"],
        "api_key_recorded":False,"kfdg_schema_sha256":sha(HERE / "protocol/kfdg_v1.schema.json"),
        "fixture_hashes":contract_tests["fixture_hashes"],"freecad_version":freecad_version,
        "python_executable":str(Path(sys.executable).resolve()),"venv_required":".venv/Scripts/python.exe",
        "c1_v1_manifest_sha256":sha(c1_dir / "manifest.json"),"frozen_c1_v1_unchanged":True,
        "formal_holdout_accessed":False,"formal_holdout_evaluation_count":0,"gt_evaluation_count":0,
        "solver_candidate_count":0,"result_file_sha256":artifact_hashes}
    save(RESULT / "manifest.json", manifest)
    print(json.dumps({"decision":decision,"transport_pass":all(x["pass"] for x in transport_checks),"rebuild_pass":all(x["pass"] for x in rebuild_checks),"e2e_semantic_valid":semantic_valid}))
    return audit


if __name__ == "__main__": main()
