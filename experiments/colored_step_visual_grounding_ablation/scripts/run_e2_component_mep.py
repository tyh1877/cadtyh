"""Run the same component-level MEP agent on successful A0/A1/A2 E1 packets."""

from __future__ import annotations

import argparse
import base64
import csv
import io
import json
import sys
import time
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from PIL import Image


ROOT = Path(__file__).resolve().parents[3]
EXP = Path(__file__).resolve().parents[1]
MANIFEST = EXP / "native_step5_v1.csv"
ARTIFACTS = EXP / "artifacts" / "native_step5"
E1_RUNS = EXP / "runs" / "e1_replicate_01"
RUNS = EXP / "runs" / "e2_replicate_01"
RESULTS = EXP / "results"
SCHEMA_PATH = EXP / "schemas" / "component_mechanical_embodiment_v1.schema.json"
PROMPT_PATH = EXP / "prompts" / "component_mep.md"
VIEWS = ["front", "rear", "left", "right", "top", "isometric"]
CONDITIONS = ["A0_controlled", "A1_color_only", "A2_color_legend"]

sys.path.insert(0, str(ROOT / "go_nogo2" / "scripts"))
from glm_config import load_glm  # noqa: E402
sys.path.insert(0, str(ROOT / "experiments" / "try3_freecad_full_workflow" / "scripts"))
from run_visual_agent_v2 import extract_json  # noqa: E402


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")


def image_item(path: Path, max_side: int = 1000) -> dict[str, Any]:
    image = Image.open(path).convert("RGB"); image.thumbnail((max_side, max_side))
    stream = io.BytesIO(); image.save(stream, format="PNG")
    data = base64.b64encode(stream.getvalue()).decode("ascii")
    return {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{data}"}}


def all_refs(component: dict) -> list[dict]:
    refs = list(component.get("main_envelope", {}).get("evidence_refs", []))
    refs += list(component.get("body_transition", {}).get("evidence_refs", []))
    for item in component.get("joint_regions", []): refs += list(item.get("evidence_refs", []))
    for item in component.get("visible_structural_features", []): refs += list(item.get("evidence_refs", []))
    return [item for item in refs if isinstance(item, dict)]


def evaluate(plan: dict, scan: dict) -> dict:
    valid_regions = {item["region_id"] for item in scan["regions"]}
    expected = len(valid_regions); components = plan.get("components", [])
    output_ids = [item.get("evidence_region_id") for item in components]
    refs = [ref for item in components for ref in all_refs(item)]
    valid_refs = [ref for ref in refs if ref.get("region_id") in valid_regions and ref.get("view") in VIEWS]
    joint_count = sum(len(item.get("joint_regions", [])) for item in components)
    feature_count = sum(len(item.get("visible_structural_features", [])) for item in components)
    unknown_roles = sum(str(item.get("functional_role", "unknown")).lower() in {"unknown", "uncertain", ""} for item in components)
    return {
        "expected_regions": expected,
        "output_components": len(components),
        "complete_region_rate": len(set(output_ids) & valid_regions) / expected if expected else 0.0,
        "duplicate_region_ids": len(output_ids) - len(set(output_ids)),
        "total_evidence_refs": len(refs),
        "evidence_traceability_rate": len(valid_refs) / len(refs) if refs else 0.0,
        "unsupported_reference_rate": 1.0 - len(valid_refs) / len(refs) if refs else 1.0,
        "joint_region_count": joint_count,
        "joint_region_per_component": joint_count / expected if expected else 0.0,
        "visible_feature_count": feature_count,
        "visible_feature_per_component": feature_count / expected if expected else 0.0,
        "unknown_role_rate": unknown_roles / expected if expected else 1.0,
    }


def call(case_id: str, condition: str, scan: dict, component_manifest: dict, timeout: float) -> tuple[dict, dict, str]:
    cfg=load_glm(); client=cfg.create_client().with_options(timeout=timeout,max_retries=0)
    contract=json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    prompt={
        "task_instructions": PROMPT_PATH.read_text(encoding="utf-8"),
        "case_id": case_id, "condition": condition,
        "component_grounding_packet": scan,
        "output_schema": contract,
        "interpretation_guard": "GT-derived color is oracle diagnostic input. Do not claim formal Try-3 validity.",
    }
    if condition == "A2_color_legend":
        prompt["color_legend"]=[{"component_id":x["component_id"],"rgb":x["color_rgb"]} for x in component_manifest["components"]]
    content=[{"type":"text","text":json.dumps(prompt,ensure_ascii=False)}]
    root=ARTIFACTS/case_id/condition/"renders"
    for view in VIEWS: content.extend([{"type":"text","text":f"view={view}"},image_item(root/f"{view}.png")])
    started=time.time(); response=client.chat.completions.create(
        model=cfg.model,messages=[{"role":"system","content":"You are a mechanical embodiment architect. Return schema-valid JSON only."},{"role":"user","content":content}],
        temperature=0,top_p=1,max_tokens=8192,response_format={"type":"json_object"},extra_body={"reasoning_effort":"low"})
    elapsed=time.time()-started; raw=response.choices[0].message.content or ""; usage=getattr(response,"usage",None)
    return extract_json(raw),{"model":cfg.model,"actual_image_inputs":len(VIEWS),"elapsed_seconds":elapsed,"input_tokens":int(getattr(usage,"prompt_tokens",0) or 0),"output_tokens":int(getattr(usage,"completion_tokens",0) or 0),"total_tokens":int(getattr(usage,"total_tokens",0) or 0)},raw


def main() -> int:
    parser=argparse.ArgumentParser();parser.add_argument("--case");parser.add_argument("--condition",choices=CONDITIONS);parser.add_argument("--timeout",type=float,default=180.0);args=parser.parse_args()
    rows=list(csv.DictReader(MANIFEST.open("r",encoding="utf-8")))
    if args.case: rows=[r for r in rows if r["case_id"]==args.case]
    conditions=[args.condition] if args.condition else CONDITIONS
    validator=Draft202012Validator(json.loads(SCHEMA_PATH.read_text(encoding="utf-8")))
    summary=[]
    for row in rows:
        component_manifest=json.loads((ARTIFACTS/row["case_id"]/"component_manifest.json").read_text(encoding="utf-8"))
        for condition in conditions:
            e1_path=E1_RUNS/condition/row["case_id"]/"component_grounding_v1.json"; out=RUNS/condition/row["case_id"];out.mkdir(parents=True,exist_ok=True)
            if not e1_path.exists():
                summary.append({"case_id":row["case_id"],"condition":condition,"status":"UPSTREAM_FAILURE","schema_valid":0,"expected_regions":0,"output_components":0,"complete_region_rate":0,"duplicate_region_ids":0,"total_evidence_refs":0,"evidence_traceability_rate":0,"unsupported_reference_rate":1,"joint_region_count":0,"joint_region_per_component":0,"visible_feature_count":0,"visible_feature_per_component":0,"unknown_role_rate":1,"input_tokens":0,"output_tokens":0,"total_tokens":0,"elapsed_seconds":0,"error_type":"E1_FAILURE","error":"component grounding artifact missing"});continue
            scan=json.loads(e1_path.read_text(encoding="utf-8"))
            try:
                plan,api,raw=call(row["case_id"],condition,scan,component_manifest,args.timeout);(out/"raw_response.txt").write_text(raw,encoding="utf-8")
                errors=sorted(validator.iter_errors(plan),key=lambda e:list(e.path));write_json(out/"schema_validation.json",{"valid":not errors,"errors":[e.message for e in errors]})
                if errors: raise ValueError("SCHEMA_INVALID: "+errors[0].message)
                if plan.get("case_id")!=row["case_id"] or plan.get("condition")!=condition: raise ValueError("CASE_OR_CONDITION_MISMATCH")
                write_json(out/"component_mechanical_embodiment_v1.json",plan);write_json(out/"api_manifest.json",api);metrics=evaluate(plan,scan)
                summary.append({"case_id":row["case_id"],"condition":condition,"status":"SUCCESS","schema_valid":1,**metrics,**{k:api[k] for k in ["input_tokens","output_tokens","total_tokens","elapsed_seconds"]},"error_type":"","error":""})
            except Exception as exc:
                write_json(out/"failure.json",{"error_type":type(exc).__name__,"error":str(exc)})
                summary.append({"case_id":row["case_id"],"condition":condition,"status":"FAILURE","schema_valid":0,"expected_regions":len(scan["regions"]),"output_components":0,"complete_region_rate":0,"duplicate_region_ids":0,"total_evidence_refs":0,"evidence_traceability_rate":0,"unsupported_reference_rate":1,"joint_region_count":0,"joint_region_per_component":0,"visible_feature_count":0,"visible_feature_per_component":0,"unknown_role_rate":1,"input_tokens":0,"output_tokens":0,"total_tokens":0,"elapsed_seconds":0,"error_type":type(exc).__name__,"error":str(exc)[:500]})
    RESULTS.mkdir(parents=True,exist_ok=True);path=RESULTS/"e2_case_condition_summary.csv"
    with path.open("w",encoding="utf-8",newline="") as handle:
        writer=csv.DictWriter(handle,fieldnames=list(summary[0]));writer.writeheader();writer.writerows(summary)
    print(json.dumps({"rows":len(summary),"successes":sum(r["status"]=="SUCCESS" for r in summary),"upstream_failures":sum(r["status"]=="UPSTREAM_FAILURE" for r in summary)},indent=2))
    return 0 if all(r["status"] in {"SUCCESS","UPSTREAM_FAILURE"} for r in summary) else 1


if __name__=="__main__": raise SystemExit(main())

