"""Blind input-condition runs for Go/No-Go 4 multi-pose reconstruction."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import mimetypes
import shutil
import sys
import time
from dataclasses import replace
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "go_nogo2" / "scripts"))
sys.path.insert(0, str(ROOT / "go_nogo3" / "scripts"))
from compile_blueprint import compile_direct  # noqa: E402
from llm_config import load_shared_llm  # noqa: E402
from robot_blueprint import BlueprintError, extract_json  # noqa: E402
from run_prototype import generic_validate, sha256  # noqa: E402

VARIANTS = ("single_view", "multiview_static", "multipose_concat", "motion_aware")
MODELS = ("qwen3.7-plus", "qwen3.7-max-2026-06-08")
STATIC_VIEWS = ("front", "side", "top", "iso")


def url(path: Path) -> str:
    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"


def selected_images(case: Path, variant: str) -> list[tuple[str, Path]]:
    root = case / "rendered_images"
    if variant == "single_view":
        return [(f"pose_0/{view}", root / "pose_0" / f"{view}.png") for view in ("front", "side", "iso")]
    if variant == "multiview_static":
        return [(f"pose_0/{view}", root / "pose_0" / f"{view}.png") for view in STATIC_VIEWS]
    return [(f"{pose}/{view}", root / pose / f"{view}.png") for pose in ("pose_0", "pose_1", "pose_2") for view in STATIC_VIEWS]


def content(case: Path, variant: str) -> list[dict[str, Any]]:
    prompt = (case / "prompt.txt").read_text(encoding="utf-8")
    items: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
    for label, path in selected_images(case, variant):
        items.extend(({"type": "text", "text": f"observation={label}"}, {"type": "image_url", "image_url": {"url": url(path)}}))
    return items


def contract() -> str:
    return '''Return exactly one CAD blueprint JSON: {"schema_version":"1.0","units":"mm","links":[{"name":"base_link","primitives":[PRIMITIVE]}],"joints":[JOINT]}. Every primitive uses a local-frame `center`, never `origin_xyz` or `origin_rpy`: box={"type":"box","center":[x,y,z],"size":[x,y,z]}; cylinder={"type":"cylinder","center":[x,y,z],"radius":r,"height":h,"axis":[x,y,z]}; sphere={"type":"sphere","center":[x,y,z],"radius":r}; cone={"type":"cone","center":[x,y,z],"bottom_radius":r1,"top_radius":r2,"height":h,"axis":[x,y,z]}. JOINT={"name":...,"parent":...,"child":...,"type":"fixed|revolute|continuous|prismatic","origin_xyz":[x,y,z],"origin_rpy":[r,p,y],"axis":[x,y,z],"lower":number,"upper":number}. Infer all counts and all joint fields only from observations. Output one rooted tree and use nonzero axes for non-fixed joints.'''


def system(variant: str) -> str:
    core = "You reconstruct a blind articulated robot from rendered observations. " + contract()
    if variant == "single_view":
        return core + " These are one pose with sparse views. Return the best single-pass reconstruction."
    if variant == "multiview_static":
        return core + " These views depict one static pose. Use only spatial multi-view evidence."
    if variant == "multipose_concat":
        return core + " Several images may depict different poses. Treat them as an unordered collection of visual observations; do not explicitly infer motion correspondence or joint constraints."
    return core + ''' Images are labelled by pose index. First reason from changes across poses: identify persistent link identities and infer relative motion constraints. Return exactly {"motion_hypothesis":{"links":[{"name":...}],"joints":[JOINT]},"blueprint":BLUEPRINT}. The blueprint must use exactly the hypothesis link names and exactly the hypothesis joints; infer only each link's body primitives after estimating motion. This is not a connector, port, mate, retrieval, or generic assembly-agent task.'''


def parse_motion(raw: str) -> tuple[dict, dict]:
    value = extract_json(raw)
    if not isinstance(value.get("motion_hypothesis"), dict) or not isinstance(value.get("blueprint"), dict):
        raise BlueprintError("motion-aware response must contain motion_hypothesis and blueprint")
    hypothesis = value["motion_hypothesis"]
    links, joints = hypothesis.get("links"), hypothesis.get("joints")
    if not isinstance(links, list) or not isinstance(joints, list):
        raise BlueprintError("motion hypothesis lacks links/joints")
    # Validate the predicted structure without accessing target GT.
    canonicalize_fixed_limits(joints)
    skeleton = {"schema_version": "1.0", "units": "mm", "links": [{"name": entry["name"], "primitives": [{"type": "sphere", "center": [0, 0, 0], "radius": 1}]} for entry in links], "joints": joints}
    generic_validate(skeleton)
    blueprint = value["blueprint"]
    blueprint["links"] = [{"name": item["name"], "primitives": next(candidate["primitives"] for candidate in blueprint.get("links", []) if candidate.get("name") == item["name"])} for item in links]
    blueprint["joints"] = joints
    return generic_validate(blueprint), {"links": [{"name": item["name"]} for item in links], "joints": joints}


def canonicalize_fixed_limits(blueprint_or_joints: dict | list) -> None:
    """Canonicalize only semantically fixed limits; never invent moving-joint data."""
    joints = blueprint_or_joints if isinstance(blueprint_or_joints, list) else blueprint_or_joints.get("joints", [])
    for joint in joints:
        if joint.get("type") == "fixed":
            joint.setdefault("lower", 0.0)
            joint.setdefault("upper", 0.0)


def invoke(client: Any, model: str, variant: str, case: Path) -> tuple[str, dict[str, int], str | None]:
    response = client.chat.completions.create(model=model, messages=[{"role": "system", "content": system(variant)}, {"role": "user", "content": content(case, variant)}], response_format={"type": "json_object"}, temperature=0.0, top_p=1.0, max_tokens=32768)
    usage = response.usage
    return response.choices[0].message.content or "", {"input_tokens": int(getattr(usage, "prompt_tokens", 0) or 0), "output_tokens": int(getattr(usage, "completion_tokens", 0) or 0), "total_tokens": int(getattr(usage, "total_tokens", 0) or 0)}, getattr(response, "id", None)


def run_one(variant: str, case: Path, run: Path, client: Any, model: str, overwrite: bool) -> dict:
    if run.exists() and overwrite:
        shutil.rmtree(run)
    manifest_path = run / "manifest.json"
    if manifest_path.is_file() and not overwrite:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    run.mkdir(parents=True, exist_ok=True)
    started, raw, request_id, error, hypothesis = time.perf_counter(), "", None, None, None
    usage = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
    try:
        raw, usage, request_id = invoke(client, model, variant, case)
        if variant == "motion_aware":
            blueprint, hypothesis = parse_motion(raw)
            (run / "motion_hypothesis.json").write_text(json.dumps(hypothesis, indent=2), encoding="utf-8")
        else:
            blueprint = extract_json(raw)
            canonicalize_fixed_limits(blueprint)
            blueprint = generic_validate(blueprint)
        (run / "blueprint.json").write_text(json.dumps(blueprint, indent=2), encoding="utf-8")
        compile_direct(blueprint, run)
        status = "SUCCESS"
    except Exception as exc:
        status, error = "FAILURE", f"{type(exc).__name__}: {exc}"
    (run / "raw_response.txt").write_text(raw, encoding="utf-8")
    urdf = run / "urdf" / "model.urdf"
    manifest = {"case_id": case.name, "variant": variant, "status": status, "model": model, "latency_seconds": time.perf_counter() - started,
                "budget": {"api_calls": 1, "max_total_output_tokens": 32768, "max_total_model_tokens": 100000, **usage},
                "artifacts": {"prediction_urdf": "urdf/model.urdf" if urdf.is_file() else None, "motion_hypothesis": "motion_hypothesis.json" if hypothesis else None},
                "error": error, "request_id": request_id,
                "input_observations": [label for label, _ in selected_images(case, variant)],
                "input_hashes": {label: sha256(path) for label, path in selected_images(case, variant)}}
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--variant", choices=VARIANTS, required=True)
    parser.add_argument("--data-root", type=Path, default=ROOT / "go_nogo4/data/motion15")
    parser.add_argument("--runs-root", type=Path, default=ROOT / "go_nogo4/runs")
    parser.add_argument("--config", type=Path, default=ROOT / "go_nogo2/config/llm.local.toml")
    parser.add_argument("--model", choices=MODELS, default="qwen3.7-plus")
    parser.add_argument("--case")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    config = replace(load_shared_llm(args.config), model=args.model)
    client = config.create_client()
    cases = sorted(path for path in args.data_root.glob("dev_arm-*") if path.is_dir())
    if args.case: cases = [path for path in cases if path.name == args.case]
    output = []
    for case in cases:
        result = run_one(args.variant, case, args.runs_root / args.variant / case.name, client, config.model, args.overwrite)
        output.append({"case": case.name, "status": result["status"]}); print(f"{args.variant} {case.name}: {result['status']}", flush=True)
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
