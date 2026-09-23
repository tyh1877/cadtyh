"""One synthetic Qwen→KFDG v1→2-candidate CAD dataflow smoke; no GT."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import shutil
import subprocess
import sys
import time
import tomllib
import xml.etree.ElementTree as ET
from pathlib import Path

import httpx
import openai

from experiments.try6.scripts.kfdg_v1_contract import parse_raw

ROOT = Path(__file__).resolve().parents[3]
HERE = ROOT / "experiments" / "try6"
RESULT = HERE / "results/try6_0_r0/end_to_end_smoke"
ARTIFACT = HERE / "artifacts/try6_0_r0/end_to_end_smoke"
sys.path.insert(0, str(ROOT / "experiments/try5A/scripts"))
from freecad_runtime import python_runtime  # noqa: E402


def load(path): return json.loads(Path(path).read_text(encoding="utf-8"))
def save(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def urdf_anchor_mm(path):
    tree = ET.parse(path)
    joint = next(j for j in tree.findall("joint") if j.get("name") == "J04")
    xyz = [float(v) for v in joint.find("origin").get("xyz").split()]
    return math.sqrt(sum(v*v for v in xyz))*1000.0


def main():
    if not load(HERE / "results/try6_0_r0/schema_transport/transport_report.json")["all_pass"]:
        raise RuntimeError("R0-A gate not passed")
    if not load(HERE / "results/try6_0_r0/parametric_rebuild/rebuild_report.json")["pass"]:
        raise RuntimeError("R0-B three-edit gate not passed")
    cfg = load(HERE / "protocol/r0_end_to_end_protocol.json")
    param_spec = load(HERE / "protocol/parameter_bounds.json")
    source_params = param_spec["optimizable"]
    expected_ids = {p["id"] for p in source_params}
    urdf_path = ROOT / "experiments/try5A/inputs/sanitized_urdf/px100_sanitized.urdf"
    anchor = urdf_anchor_mm(urdf_path)
    if abs(anchor - 63.0) > 1e-9: raise RuntimeError("URDF J04 anchor differs from frozen 63 mm")
    local = tomllib.loads((ROOT / "go_nogo2/config/llm.local.toml").read_text(encoding="utf-8"))
    if local["generation"]["model"] != cfg["model"]: raise RuntimeError("model config mismatch")
    RESULT.mkdir(parents=True, exist_ok=True)
    ARTIFACT.mkdir(parents=True, exist_ok=True)
    schema = load(HERE / "protocol/kfdg_v1.schema.json")
    prompt = ("This is ONLY a synthetic CAD dataflow test, not visual reconstruction. Return one KFDG v1 JSON object for link L04. "
              "Use functional_nodes [{id: proximal_joint_port, type: joint_port}, {id: distal_mount_port, type: mount_port}]. "
              "Use exactly four geometric_features with ids housing_main (housing), transition_main (profile_transition), recess_main (pocket), fillet_main (fillet). "
              "Each feature must have parameter_refs: housing_main references housing_width_mm and housing_height_mm; transition_main references proximal_section_length_mm, transition_length_mm, distal_width_mm, distal_height_mm; recess_main references recess_length_mm and recess_depth_mm; fillet_main references fillet_radius_mm. "
              "Use a connected_to constraint from housing_main to proximal_joint_port and another from transition_main to distal_mount_port. "
              "Use exactly these nine parameters, preserving IDs, numeric values and bounds; set each unit mm, provenance SOLVER_ESTIMATED, confidence MEDIUM: "
              + json.dumps([{k:p[k] for k in ("id","value","lower_bound","upper_bound")} for p in source_params], separators=(",", ":"))
              + ". No GT, no images, no geometry performance claim.")
    messages = [{"role": "system", "content": "Return only one JSON object that strictly conforms to the supplied schema. No wrapper array or markdown."}, {"role": "user", "content": prompt}]
    captured = {}

    def request_hook(request):
        captured["request"] = json.loads(request.content)

    def response_hook(response):
        response.read()
        captured["http_status"] = response.status_code
        captured["http_response"] = response.json()

    started = time.perf_counter()
    with httpx.Client(timeout=cfg["timeout_seconds"], event_hooks={"request": [request_hook], "response": [response_hook]}) as transport:
        client = openai.OpenAI(api_key=local["provider"]["api_key"], base_url=local["provider"]["base_url"], timeout=cfg["timeout_seconds"], max_retries=0, http_client=transport)
        response = client.chat.completions.create(model=cfg["model"], messages=messages,
            response_format={"type":"json_schema", "json_schema":{"name":"r0_e2e_kfdg_v1", "strict":True, "schema":schema}},
            temperature=cfg["temperature"], top_p=cfg["top_p"], max_tokens=cfg["max_output_tokens"], seed=cfg["seed"])
    latency = time.perf_counter() - started
    sdk = response.model_dump(mode="json")
    save(RESULT / "request.json", captured["request"])
    save(RESULT / "response.json", sdk)
    save(RESULT / "http_response.json", captured["http_response"])
    raw = captured["http_response"]["choices"][0]["message"]["content"]
    (RESULT / "raw_model_response.json").write_text(raw, encoding="utf-8")
    if raw != sdk["choices"][0]["message"]["content"]: raise RuntimeError("SDK changed raw model content")
    if captured["request"].get("response_format",{}).get("json_schema",{}).get("schema") != schema: raise RuntimeError("schema not actually sent")
    kfdg = parse_raw(raw)
    if kfdg["link_id"] != "L04": raise RuntimeError("model returned wrong link identity")
    params = {p["id"]:p for p in kfdg["parameters"]}
    if set(params) != expected_ids: raise RuntimeError("model parameter set differs from frozen nine-parameter table")
    if {f["type"] for f in kfdg["geometric_features"]} != {"housing","profile_transition","pocket","fillet"}: raise RuntimeError("model feature set incomplete")
    for source in source_params:
        returned = params[source["id"]]
        if any(abs(returned[key]-source[key]) > 1e-9 for key in ("value","lower_bound","upper_bound")):
            raise RuntimeError("synthetic parameter copying failed; no local repair allowed")
    save(RESULT / "validated_kfdg.json", kfdg)
    values = {p["id"]: p["value"] for p in kfdg["parameters"]}
    graph_path = RESULT / "validated_kfdg.json"
    candidates = [dict(values), dict(values)]
    candidates[1]["housing_width_mm"] *= cfg["candidate_width_multiplier"]
    history = []
    for i, theta in enumerate(candidates):
        folder = ARTIFACT / f"candidate_{i}"
        job = {"mode":"R0_SYNTHETIC_DATAFLOW", "parameters":theta, "anchor_distance_mm":anchor,
               "kfdg_path":str(graph_path), "frozen_interface_contracts":str(ROOT / "experiments/try5A/results/try5a5/motion_interface_contracts.json"),
               "f0_fcstd":str(ROOT / "experiments/try5A/artifacts/try5a5/round3_verified/links/L04/model.FCStd"), "output_root":str(folder)}
        job_path = ARTIFACT / f"candidate_{i}_job.json"
        save(job_path, job)
        tick = time.perf_counter()
        proc = subprocess.run([python_runtime(), str(HERE / "scripts/freecad_c1_builder.py"), str(job_path)], cwd=ROOT, capture_output=True, text=True, timeout=180)
        (RESULT / f"candidate_{i}_stdout.txt").write_text(proc.stdout, encoding="utf-8")
        (RESULT / f"candidate_{i}_stderr.txt").write_text(proc.stderr, encoding="utf-8")
        if proc.returncode: raise RuntimeError(f"candidate {i} CAD build failed: {proc.stderr[-1000:]}")
        cad = load(folder / "build_result.json")
        if cad["final_solid_count"] != 1 or not cad["reopen"]["valid"]: raise RuntimeError(f"candidate {i} invalid CAD")
        width = theta["housing_width_mm"]
        objective = (width / anchor - cfg["synthetic_normalized_width_target"])**2 + 0.01*((width-values["housing_width_mm"])/values["housing_width_mm"])**2
        if not math.isfinite(objective): raise RuntimeError("non-finite objective")
        history.append({"candidate":i, "objective":objective, "housing_width_mm":width, "anchor_mm":anchor,
                        "final_volume_mm3":cad["final_volume_mm3"], "cad_seconds":time.perf_counter()-tick,
                        "cad_valid":True, "connected_solids":cad["final_solid_count"]})
    if abs(history[0]["final_volume_mm3"]-history[1]["final_volume_mm3"]) < 1e-6:
        raise RuntimeError("candidate parameter change did not alter final CAD")
    mutated_anchor = cfg["anchor_mutation_test_mm"]
    mutated_objective = (values["housing_width_mm"] / mutated_anchor - cfg["synthetic_normalized_width_target"])**2
    if abs(mutated_objective-history[0]["objective"]) < 1e-8: raise RuntimeError("URDF anchor not consumed by objective")
    best = min(history, key=lambda item:item["objective"])
    with (RESULT / "solver_smoke_history.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(history[0]))
        writer.writeheader(); writer.writerows(history)
    save(RESULT / "parameter_table.json", {"source":"validated raw KFDG v1", "candidate_theta":candidates, "selected_candidate":best["candidate"]})
    save(RESULT / "dataflow_audit.json", {"status":"PASS", "mode":"synthetic infrastructure only", "raw_kfdg_valid":True,
        "no_response_repair":True, "vlm_calls":1, "model_requested":cfg["model"], "model_returned":sdk.get("model"),
        "token_usage":sdk.get("usage"), "vlm_latency_seconds":latency,
        "urdf_path":str(urdf_path.relative_to(ROOT)).replace("\\","/"), "urdf_sha256":hashlib.sha256(urdf_path.read_bytes()).hexdigest(),
        "urdf_anchor_mm":anchor, "mutated_anchor_mm":mutated_anchor,
        "baseline_objective":history[0]["objective"], "mutated_anchor_objective":mutated_objective,
        "normalized_width_relation_at_urdf_anchor":values["housing_width_mm"]/anchor,
        "normalized_width_relation_at_mutated_anchor":values["housing_width_mm"]/mutated_anchor,
        "candidate_count":len(history), "selected_candidate":best["candidate"], "gt_evaluations":0, "formal_holdout_evaluations":0})
    selected = ARTIFACT / f"candidate_{best['candidate']}"
    for source,target in (("final.FCStd","final.FCStd"),("final.step","final.step"),("final.stl","final.stl")):
        shutil.copy2(selected/source, ARTIFACT/target)
    print(json.dumps({"status":"PASS", "candidate_count":len(history), "selected_candidate":best["candidate"], "gt_evaluations":0}))
    return True


if __name__ == "__main__": sys.exit(0 if main() else 2)
