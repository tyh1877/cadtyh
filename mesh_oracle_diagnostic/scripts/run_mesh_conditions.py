"""Run monolithic and per-link mesh-oracle kinematic reconstruction conditions."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
import xml.etree.ElementTree as ET
from dataclasses import replace
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "go_nogo2" / "scripts"))
sys.path.insert(0, str(ROOT / "go_nogo3" / "scripts"))
from compile_blueprint import compile_direct  # noqa: E402
from llm_config import load_shared_llm  # noqa: E402
from robot_blueprint import BlueprintError, extract_json  # noqa: E402
from run_prototype import generic_validate  # noqa: E402

CONDITIONS = ("M_monolithic_mesh", "L_per_link_mesh_oracle")


def monolithic_prompt(payload: dict) -> str:
    return '''You receive a canonical articulated robot mesh represented as a normalized unordered surface-point cloud. It contains no part labels, no joints, no URDF, and no model identifier. The payload gives `millimeters_per_normalized_unit`; convert normalized coordinates to millimetres before writing CAD values. Reconstruct editable primitive CAD links plus a rooted URDF-equivalent joint graph. Infer all part boundaries, topology, joint type, axis, origin and limits from surface geometry only. Return exactly {"schema_version":"1.0","units":"mm","links":[{"name":"link_0","primitives":[PRIMITIVE]}],"joints":[JOINT]}. Do NOT use a `geometry` field. Each PRIMITIVE must be one of: {"type":"box","center":[x,y,z],"size":[x,y,z]}; {"type":"cylinder","center":[x,y,z],"radius":r,"height":h,"axis":[x,y,z]}; {"type":"sphere","center":[x,y,z],"radius":r}; {"type":"cone","center":[x,y,z],"bottom_radius":r1,"top_radius":r2,"height":h,"axis":[x,y,z]}. Every JOINT must include name,parent,child,type,origin_xyz,origin_rpy,axis,lower,upper.\nPOINT CLOUD JSON:\n''' + json.dumps(payload, separators=(",", ":"))


def per_link_prompt(payload: dict) -> str:
    return '''You receive anonymous per-link canonical mesh surface point clouds for one articulated robot. The list of part labels is complete, but there are no joints, URDF, manufacturer/model name, or motion annotations. The payload gives `millimeters_per_normalized_unit`; convert normalized point locations to millimetres before writing joint origins. Recover only a rooted kinematic graph: return JSON {"links":[{"name":"part_00"},...],"joints":[{"name":...,"parent":...,"child":...,"type":"fixed|revolute|continuous|prismatic","origin_xyz":[x,y,z],"origin_rpy":[r,p,y],"axis":[x,y,z],"lower":number,"upper":number}]}. Include every supplied part label exactly once, use a single rooted tree, and infer joints from the canonical mesh arrangement.\nPER-LINK POINT CLOUD JSON:\n''' + json.dumps(payload, separators=(",", ":"))


def canonicalize_fixed(joints: list[dict]) -> None:
    for joint in joints:
        if joint.get("type") == "fixed": joint.setdefault("lower", 0.0); joint.setdefault("upper", 0.0)


def write_oracle_urdf(joints: list[dict], names: list[str], source_parts: Path, output: Path) -> None:
    mesh_dir, urdf_dir = output / "meshes", output / "urdf"; mesh_dir.mkdir(parents=True, exist_ok=True); urdf_dir.mkdir(parents=True, exist_ok=True)
    for name in names: shutil.copy2(source_parts / f"{name}.stl", mesh_dir / f"{name}.stl")
    robot = ET.Element("robot", {"name": "per_link_mesh_oracle"})
    for name in names:
        link = ET.SubElement(robot, "link", {"name": name}); visual = ET.SubElement(link, "visual"); ET.SubElement(visual, "origin", {"xyz": "0 0 0", "rpy": "0 0 0"}); geometry = ET.SubElement(visual, "geometry"); ET.SubElement(geometry, "mesh", {"filename": f"../meshes/{name}.stl", "scale": "1 1 1"})
    for joint in joints:
        node = ET.SubElement(robot, "joint", {"name": joint["name"], "type": joint["type"]}); ET.SubElement(node, "parent", {"link": joint["parent"]}); ET.SubElement(node, "child", {"link": joint["child"]}); ET.SubElement(node, "origin", {"xyz": " ".join(str(float(x) / 1000.0) for x in joint["origin_xyz"]), "rpy": " ".join(str(float(x)) for x in joint["origin_rpy"])}); ET.SubElement(node, "axis", {"xyz": " ".join(str(float(x)) for x in joint["axis"])})
        if joint["type"] in {"revolute", "prismatic"}: ET.SubElement(node, "limit", {"lower": str(joint["lower"]), "upper": str(joint["upper"]), "effort": "1", "velocity": "1"})
    ET.indent(robot); ET.ElementTree(robot).write(urdf_dir / "model.urdf", encoding="utf-8", xml_declaration=True)


def run_one(condition: str, case: Path, output: Path, client: Any, model: str, overwrite: bool) -> dict:
    if output.exists() and overwrite: shutil.rmtree(output)
    manifest_path = output / "manifest.json"
    if manifest_path.is_file() and not overwrite: return json.loads(manifest_path.read_text(encoding="utf-8"))
    output.mkdir(parents=True, exist_ok=True); started, raw, error, request_id = time.perf_counter(), "", None, None; usage = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
    try:
        if condition == "M_monolithic_mesh": payload = json.loads((case / "monolithic_surface_points.json").read_text(encoding="utf-8")); prompt = monolithic_prompt(payload)
        else: payload = json.loads((case / "per_link_surface_points.json").read_text(encoding="utf-8")); prompt = per_link_prompt(payload)
        response = client.chat.completions.create(model=model, messages=[{"role": "system", "content": "Return a valid JSON object. Use only the supplied point-cloud mesh representation. Do not assume hidden CAD or URDF access."}, {"role": "user", "content": prompt}], response_format={"type": "json_object"}, temperature=0.0, top_p=1.0, max_tokens=32768)
        raw, request_id = response.choices[0].message.content or "", getattr(response, "id", None); api_usage = response.usage; usage = {"input_tokens": int(getattr(api_usage, "prompt_tokens", 0) or 0), "output_tokens": int(getattr(api_usage, "completion_tokens", 0) or 0), "total_tokens": int(getattr(api_usage, "total_tokens", 0) or 0)}
        value = extract_json(raw) if condition == "M_monolithic_mesh" else None
        if condition == "M_monolithic_mesh":
            canonicalize_fixed(value.get("joints", [])); blueprint = generic_validate(value); (output / "blueprint.json").write_text(json.dumps(blueprint, indent=2), encoding="utf-8"); compile_direct(blueprint, output)
        else:
            # Some models emit the requested joint array directly. This is a
            # syntax adaptation only: the anonymous oracle part set remains
            # fixed and no joint field is inferred by the adapter.
            try:
                value = extract_json(raw)
            except BlueprintError:
                parsed = json.loads(raw)
                if not isinstance(parsed, list): raise
                value = {"links": [], "joints": parsed}
            names = [part["part"] for part in payload["parts"]]; joints = value.get("joints", []); canonicalize_fixed(joints)
            skeleton = {"schema_version": "1.0", "units": "mm", "links": [{"name": name, "primitives": [{"type": "sphere", "center": [0, 0, 0], "radius": 1}]} for name in names], "joints": joints}; generic_validate(skeleton)
            listed = {entry.get("name") for entry in value.get("links", [])}
            if listed and listed != set(names): raise ValueError("per-link condition must list all anonymous parts exactly")
            (output / "kinematic_prediction.json").write_text(json.dumps({"links": names, "joints": joints}, indent=2), encoding="utf-8"); write_oracle_urdf(joints, names, case / "oracle_parts", output)
        status = "SUCCESS"
    except Exception as exc: status, error = "FAILURE", f"{type(exc).__name__}: {exc}"
    (output / "raw_response.txt").write_text(raw, encoding="utf-8")
    manifest = {"case_id": case.name, "condition": condition, "status": status, "model": model, "latency_seconds": time.perf_counter() - started, "budget": {"api_calls": 1, "max_total_output_tokens": 32768, "max_total_model_tokens": 100000, **usage}, "input_representation": "surface_point_mesh", "artifacts": {"prediction_urdf": "urdf/model.urdf" if (output / "urdf/model.urdf").is_file() else None, "raw_response": "raw_response.txt"}, "error": error, "request_id": request_id}
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8"); return manifest


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--condition", choices=CONDITIONS, required=True); parser.add_argument("--data-root", type=Path, default=ROOT / "mesh_oracle_diagnostic/data/cases"); parser.add_argument("--runs-root", type=Path, default=ROOT / "mesh_oracle_diagnostic/runs"); parser.add_argument("--case"); parser.add_argument("--overwrite", action="store_true"); args = parser.parse_args()
    config = replace(load_shared_llm(ROOT / "go_nogo2/config/llm.local.toml"), model="qwen3.7-plus"); client = config.create_client(); cases = sorted(args.data_root.glob("dev_arm-*"));
    if args.case: cases = [case for case in cases if case.name == args.case]
    results = []
    for case in cases:
        result = run_one(args.condition, case, args.runs_root / args.condition / case.name, client, config.model, args.overwrite); results.append({"case": case.name, "status": result["status"]}); print(f"{args.condition} {case.name}: {result['status']}", flush=True)
    print(json.dumps(results, indent=2))


if __name__ == "__main__": main()
