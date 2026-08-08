"""Run Direct LLM or CADIR/SimpleCAD on the frozen Go/No-Go 2 cases."""

from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import json
import mimetypes
import shutil
import time
from pathlib import Path
from typing import Any

from compile_blueprint import compile_cadir, compile_direct
from llm_config import DEFAULT_CONFIG_PATH, load_shared_llm
from robot_blueprint import BlueprintError, blueprint_contract, extract_json, validate_blueprint


ROOT = Path(__file__).resolve().parents[1]
VIEWS = ("front", "rear", "left", "right", "top", "iso")
METHODS = ("direct_frontier_mllm", "cadir_simplecad")
CADIR_IMPLEMENTATION = "SimpleCADAPI@6fee370 + SDK-conditioned generate/validate/repair"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def data_url(path: Path) -> str:
    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def case_metadata(case_dir: Path) -> tuple[int, int, int]:
    gt = json.loads((case_dir / "kinematic_gt.json").read_text(encoding="utf-8"))
    dof = sum(
        joint["type"] in {"revolute", "continuous", "prismatic"}
        for joint in gt["joints"]
    )
    return len(gt["links"]), len(gt["joints"]), int(dof)


def system_prompt(method: str) -> str:
    common = (
        "You reconstruct an articulated robot from a public prompt and six rendered views. "
        "This is a blinded experiment: do not request or invent access to hidden files. "
        "Use visible evidence, preserve curved housings with cylinders/cones/spheres, and "
        "make every dimension and transform internally consistent. Output JSON only.\n\n"
        + blueprint_contract()
    )
    if method == "direct_frontier_mllm":
        return common + (
            "\n\nDIRECT BASELINE: This is a single model call with no tools, API documentation, "
            "execution feedback, or repair. Produce your best final blueprint now."
        )
    return common + """

CADIR/SimpleCADAPI CONDITIONING:
The blueprint is deterministically lowered to the public CADIR/SimpleCADAPI
construction graph. Each primitive maps to one documented keyword-only call:
make_box_rsolid(width, height, depth, bottom_face_center),
make_cylinder_rsolid(radius, height, bottom_face_center, axis),
make_sphere_rsolid(radius, center), or
make_cone_rsolid(bottom_radius, height, top_radius, bottom_face_center, axis).
Each exposed size becomes a var(name=..., default=...), each link is captured by
@model(graph_id=...) and capture_result(value=...), and strict graph replay plus
STEP/STL export must succeed. Favor explicit compositional primitives and local
frames. This runner implements the public SDK-conditioned generation and
execution-repair portion; the paper's learned retrieval index is unavailable.
"""


def user_content(case_dir: Path, feedback: str | None = None) -> list[dict[str, Any]]:
    prompt = (case_dir / "prompt.txt").read_text(encoding="utf-8")
    if feedback:
        prompt += (
            "\n\nThe previous CADIR blueprint failed deterministic validation/execution. "
            "Return a complete corrected JSON object. Error feedback:\n" + feedback[:4000]
        )
    content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
    for view in VIEWS:
        content.append({"type": "text", "text": f"Reference view: {view}"})
        content.append({"type": "image_url", "image_url": {"url": data_url(case_dir / "renders" / f"{view}.png")}})
    return content


def call_model(client: Any, config: Any, method: str, case_dir: Path, feedback: str | None) -> Any:
    return client.chat.completions.create(
        model=config.model,
        messages=[
            {"role": "system", "content": system_prompt(method)},
            {"role": "user", "content": user_content(case_dir, feedback)},
        ],
        response_format={"type": "json_object"},
        temperature=config.temperature,
        top_p=config.top_p,
        max_tokens=config.max_output_tokens,
    )


def write_manifest(
    run_dir: Path, case_dir: Path, method: str, status: str, attempts: int,
    latency: float, model: str, request_id: str | None, error: str | None,
) -> None:
    urdf = run_dir / "urdf" / "model.urdf"
    manifest = {
        "schema_version": "1.0", "method": method, "case_id": case_dir.name,
        "status": status, "prompt_sha256": sha256(case_dir / "prompt.txt"),
        "image_sha256": {view: sha256(case_dir / "renders" / f"{view}.png") for view in VIEWS},
        "attempts": attempts, "latency_seconds": latency,
        "artifacts": {
            "raw_response": "raw_response.txt" if (run_dir / "raw_response.txt").is_file() else None,
            "prediction_urdf": "urdf/model.urdf" if urdf.is_file() else None,
            "link_mesh_directory": "meshes" if (run_dir / "meshes").is_dir() else None,
            "editable_cad": (
                "cadir_graphs" if method == "cadir_simplecad" and (run_dir / "cadir_graphs").is_dir()
                else "blueprint.json" if (run_dir / "blueprint.json").is_file() else None
            ),
        },
        "provenance": {
            "implementation_version": CADIR_IMPLEMENTATION if method == "cadir_simplecad" else "direct-blueprint-v1",
            "model": model, "request_id": request_id,
            "output_sha256": sha256(urdf) if urdf.is_file() else None,
            "llm_provider": "alibaba_model_studio",
            "sampling": {"temperature": 0.0, "top_p": 1.0},
        },
        "error": error,
    }
    (run_dir / "prediction_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def run_case(method: str, case_dir: Path, run_dir: Path, config_path: Path, overwrite: bool) -> str:
    if run_dir.exists() and overwrite:
        shutil.rmtree(run_dir)
    if (run_dir / "prediction_manifest.json").is_file() and not overwrite:
        return "SKIP"
    run_dir.mkdir(parents=True, exist_ok=True)
    config = load_shared_llm(config_path)
    client = config.create_client()
    expected_links, expected_joints, expected_dof = case_metadata(case_dir)
    max_attempts = 1 if method == "direct_frontier_mllm" else 3
    feedback, raw_history, request_id, error = None, [], None, None
    started = time.perf_counter()
    for attempt in range(1, max_attempts + 1):
        print(
            f"{method} {case_dir.name}: attempt {attempt}/{max_attempts} started",
            flush=True,
        )
        try:
            response = call_model(client, config, method, case_dir, feedback)
            request_id = response.id
            raw = response.choices[0].message.content or ""
            raw_history.append({"attempt": attempt, "request_id": request_id, "response": raw})
            blueprint = validate_blueprint(
                extract_json(raw), expected_links=expected_links,
                expected_joints=expected_joints, expected_dof=expected_dof,
            )
            (run_dir / "blueprint.json").write_text(
                json.dumps(blueprint, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            if method == "cadir_simplecad":
                compile_cadir(blueprint, run_dir)
            else:
                compile_direct(blueprint, run_dir)
            (run_dir / "raw_response.txt").write_text(
                json.dumps(raw_history, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            write_manifest(
                run_dir, case_dir, method, "SUCCESS", attempt,
                time.perf_counter() - started, config.model, request_id, None,
            )
            return "SUCCESS"
        except Exception as caught:
            error = f"{type(caught).__name__}: {caught}"
            if raw_history and raw_history[-1].get("attempt") == attempt:
                raw_history[-1]["deterministic_error"] = error
            else:
                raw_history.append({
                    "attempt": attempt, "request_id": request_id,
                    "response": None, "deterministic_error": error,
                })
            print(
                f"{method} {case_dir.name}: attempt {attempt} failed: {error}",
                flush=True,
            )
            feedback = error
            if method == "direct_frontier_mllm":
                break
    (run_dir / "raw_response.txt").write_text(
        json.dumps(raw_history, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    write_manifest(
        run_dir, case_dir, method, "FAILURE", len(raw_history),
        time.perf_counter() - started, config.model, request_id, error,
    )
    return "FAILURE"


def selected_cases(data_root: Path, only_case: str | None, limit: int | None) -> list[Path]:
    cases = sorted(path for path in data_root.glob("case_*") if path.is_dir())
    if only_case:
        cases = [path for path in cases if path.name == only_case]
        if not cases:
            raise SystemExit(f"unknown case: {only_case}")
    return cases[:limit] if limit is not None else cases


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--method", choices=METHODS, required=True)
    parser.add_argument("--data-root", type=Path, default=ROOT / "data" / "pilot10")
    parser.add_argument("--runs-root", type=Path, default=ROOT / "runs")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--case")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    rows = []
    for case_dir in selected_cases(args.data_root.resolve(), args.case, args.limit):
        run_dir = args.runs_root.resolve() / args.method / case_dir.name
        status = run_case(args.method, case_dir, run_dir, args.config, args.overwrite)
        rows.append((case_dir.name, status))
        print(f"{args.method} {case_dir.name}: {status}", flush=True)
    print(json.dumps(dict(rows), indent=2))


if __name__ == "__main__":
    main()
