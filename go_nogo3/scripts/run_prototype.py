"""Blind Go/No-Go 3 runs for Joint Frame Recovery + CAD-URDF Consistency.

V0 is direct blind reconstruction. V1 uses a separately predicted joint-frame
draft as a soft conditioning signal. V2 hard-freezes that *predicted* draft
when assembling the CAD geometry. No ground-truth kinematic field is exposed
to model calls; GT is read only by the separate deterministic evaluator.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import mimetypes
import shutil
import time
from dataclasses import replace
from pathlib import Path
from typing import Any
import sys

import jsonschema

ROOT = Path(__file__).resolve().parents[2]
sys_path = ROOT / "go_nogo2" / "scripts"
sys.path.insert(0, str(sys_path))
from llm_config import DEFAULT_CONFIG_PATH, load_shared_llm  # noqa: E402
from compile_blueprint import compile_cadir, compile_direct  # noqa: E402
from robot_blueprint import BlueprintError, extract_json, load_schema  # noqa: E402

VIEWS = ("front", "rear", "left", "right", "top", "iso")
VARIANTS = ("direct", "simplecad", "v1_joint_frame", "v2_consistency")
MODELS = ("qwen3.7-plus", "qwen3.7-max-2026-06-08")


def sha256(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def image_url(path: Path) -> str:
    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"


def image_content(case_dir: Path, text: str) -> list[dict[str, Any]]:
    content: list[dict[str, Any]] = [{"type": "text", "text": text}]
    for view in VIEWS:
        content.extend(({"type": "text", "text": f"view={view}"}, {"type": "image_url", "image_url": {"url": image_url(case_dir / 'renders' / f'{view}.png')}}))
    return content


def contract() -> str:
    return '''Return exactly JSON: {"schema_version":"1.0","units":"mm","links":[{"name":"base_link","primitives":[PRIMITIVE]}],"joints":[JOINT]}.
Each PRIMITIVE is box {"type":"box","center":[x,y,z],"size":[x,y,z]}, cylinder {"type":"cylinder","center":[x,y,z],"radius":r,"height":h,"axis":[x,y,z]}, sphere, or cone. A JOINT has name,parent,child,type (fixed|revolute|continuous|prismatic),origin_xyz,origin_rpy,axis,lower,upper. Infer the unknown number of links and joints from the views. Names must be unique, links and joints must form one rooted tree, all non-fixed axes nonzero, units millimetres.'''


FRAME_SYSTEM = '''You are a mechanical perception module. From six robot views only, infer a conservative articulated skeleton. Do not use brand/model memorization. Return JSON only: {"links":[{"name":"base_link"}],"joints":[{"name":"joint_1","parent":"base_link","child":"link_1","type":"revolute|continuous|prismatic|fixed","origin_xyz":[x,y,z],"origin_rpy":[r,p,y],"axis":[x,y,z],"lower":number,"upper":number}]}. Use an inferred rooted tree. This is a visual hypothesis, not a request for CAD geometry.'''


def generic_validate(blueprint: dict[str, Any]) -> dict[str, Any]:
    jsonschema.validate(blueprint, load_schema())
    links, joints = blueprint["links"], blueprint["joints"]
    names = [entry["name"] for entry in links]
    if len(names) != len(set(names)) or len(joints) > len(links) - 1:
        raise BlueprintError("invalid unique link/joint cardinality")
    known, child = set(names), set()
    for joint in joints:
        if joint["parent"] not in known or joint["child"] not in known or joint["parent"] == joint["child"] or joint["child"] in child:
            raise BlueprintError("joint graph is not a rooted tree")
        child.add(joint["child"])
        norm = sum(float(value) ** 2 for value in joint["axis"]) ** 0.5
        if joint["type"] != "fixed" and norm < 1e-9:
            raise BlueprintError("non-fixed joint has zero axis")
        if norm >= 1e-9:
            joint["axis"] = [float(value) / norm for value in joint["axis"]]
        if joint["type"] in {"revolute", "prismatic"} and joint["lower"] >= joint["upper"]:
            raise BlueprintError("invalid motion limit")
    if len(known - child) != 1:
        raise BlueprintError("expected exactly one root")
    return blueprint


def validate_frame(frame: dict[str, Any]) -> dict[str, Any]:
    links = frame.get("links")
    joints = frame.get("joints")
    if not isinstance(links, list) or not links or not isinstance(joints, list):
        raise BlueprintError("invalid joint-frame draft")
    blueprint = {"schema_version": "1.0", "units": "mm", "links": [{"name": item["name"], "primitives": [{"type": "sphere", "center": [0, 0, 0], "radius": 1}]} for item in links], "joints": joints}
    generic_validate(blueprint)
    return {"links": [{"name": item["name"]} for item in links], "joints": joints}


def call(client: Any, model: str, system: str, content: list[dict[str, Any]], max_tokens: int) -> tuple[str, dict[str, int], str | None]:
    response = client.chat.completions.create(model=model, messages=[{"role": "system", "content": system}, {"role": "user", "content": content}], response_format={"type": "json_object"}, temperature=0.0, top_p=1.0, max_tokens=max_tokens)
    usage = response.usage
    return response.choices[0].message.content or "", {"input_tokens": int(getattr(usage, "prompt_tokens", 0) or 0), "output_tokens": int(getattr(usage, "completion_tokens", 0) or 0), "total_tokens": int(getattr(usage, "total_tokens", 0) or 0)}, getattr(response, "id", None)


def build_system(variant: str, frame: dict[str, Any] | None) -> str:
    common = "You reconstruct an unknown articulated robot from six blind reference views. " + contract()
    if variant == "direct":
        return common + " Produce the complete final CAD and kinematic model in one pass."
    if variant == "simplecad":
        return common + " Use only robust compositional primitives suitable for strict CAD API replay."
    assert frame is not None
    serialized = json.dumps(frame, separators=(",", ":"))
    if variant == "v1_joint_frame":
        return common + " A separate visual joint-frame hypothesis follows. Use it as a soft mechanical cue; you may correct it only if contradicted by the reference views. " + serialized
    return common + " A separate visual joint-frame hypothesis follows. It is a hard CAD-URDF consistency constraint: retain exactly its link names, parent-child topology, joint types, origins, axes, and limits; only infer the per-link body primitives from the views. " + serialized


def run_case(variant: str, case_dir: Path, run_dir: Path, client: Any, model: str, overwrite: bool) -> dict[str, Any]:
    if run_dir.exists() and overwrite:
        shutil.rmtree(run_dir)
    if (run_dir / "manifest.json").is_file() and not overwrite:
        return json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    run_dir.mkdir(parents=True, exist_ok=True)
    started, history, total = time.perf_counter(), [], {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
    prompt = (case_dir / "prompt.txt").read_text(encoding="utf-8")
    frame = None
    request_id, error = None, None
    try:
        if variant.startswith("v"):
            raw, usage, request_id = call(client, model, FRAME_SYSTEM, image_content(case_dir, prompt), 8192)
            history.append({"stage": "joint_frame_recovery", "response": raw, "usage": usage})
            for key in total: total[key] += usage[key]
            frame = validate_frame(extract_json(raw))
            (run_dir / "joint_frame_draft.json").write_text(json.dumps(frame, indent=2), encoding="utf-8")
        max_tokens = 24576 if variant.startswith("v") else 32768
        raw, usage, request_id = call(client, model, build_system(variant, frame), image_content(case_dir, prompt), max_tokens)
        history.append({"stage": "cad_reconstruction", "response": raw, "usage": usage})
        for key in total: total[key] += usage[key]
        blueprint = generic_validate(extract_json(raw))
        if variant == "v2_consistency":
            blueprint["links"] = [{"name": link["name"], "primitives": next(item["primitives"] for item in blueprint["links"] if item["name"] == link["name"])} for link in frame["links"]]
            blueprint["joints"] = frame["joints"]
            blueprint = generic_validate(blueprint)
        (run_dir / "blueprint.json").write_text(json.dumps(blueprint, indent=2), encoding="utf-8")
        if variant == "simplecad":
            compile_cadir(blueprint, run_dir)
        else:
            compile_direct(blueprint, run_dir)
        status = "SUCCESS"
    except Exception as exc:
        status, error = "FAILURE", f"{type(exc).__name__}: {exc}"
    (run_dir / "raw_history.json").write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")
    urdf = run_dir / "urdf" / "model.urdf"
    manifest = {"case_id": case_dir.name, "variant": variant, "status": status, "model": model, "latency_seconds": time.perf_counter() - started,
                "budget": {"api_calls": len(history), "max_total_output_tokens": 32768, "max_total_model_tokens": 100000, **total},
                "artifacts": {"prediction_urdf": "urdf/model.urdf" if urdf.is_file() else None, "raw_history": "raw_history.json", "joint_frame_draft": "joint_frame_draft.json" if frame else None},
                "error": error, "request_id": request_id, "prompt_sha256": sha256(case_dir / "prompt.txt"), "image_sha256": {view: sha256(case_dir / "renders" / f"{view}.png") for view in VIEWS}}
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--variant", choices=VARIANTS, required=True)
    parser.add_argument("--data-root", type=Path, default=ROOT / "go_nogo3/data/dev15")
    parser.add_argument("--runs-root", type=Path, default=ROOT / "go_nogo3/runs")
    parser.add_argument("--config", type=Path, default=ROOT / "go_nogo2/config/llm.local.toml")
    parser.add_argument("--model", choices=MODELS, default="qwen3.7-plus")
    parser.add_argument("--case")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    config = replace(load_shared_llm(args.config), model=args.model)
    client = config.create_client()
    cases = sorted(path for path in args.data_root.glob("dev_arm-*") if path.is_dir())
    if args.case:
        cases = [path for path in cases if path.name == args.case]
    results = []
    for case_dir in cases:
        result = run_case(args.variant, case_dir, args.runs_root / args.variant / case_dir.name, client, config.model, args.overwrite)
        results.append({"case": case_dir.name, "status": result["status"]})
        print(f"{args.variant} {case_dir.name}: {result['status']}", flush=True)
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
