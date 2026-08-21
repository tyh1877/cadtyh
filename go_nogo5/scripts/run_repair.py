"""Failure-localized, bounded local CAD repair for Go/No-Go 5."""

from __future__ import annotations

import argparse
import json
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
from robot_blueprint import extract_json  # noqa: E402
from run_prototype import generic_validate  # noqa: E402


def repair_prompt(blueprint: dict, failure: dict) -> str:
    return """You are applying a bounded, failure-specific CAD repair. Return exactly one complete Robot CAD blueprint JSON. Do NOT add/delete/rename links or joints, change parent-child topology, joint type, joint axis, joint origin, limits, or scale units. Do NOT regenerate from a reference image. Only make minimal edits to existing per-link primitive centers/sizes/radii to address the supplied intrinsic engineering report. If the report cannot be safely fixed by those local primitive edits, return the blueprint unchanged.

SOURCE BLUEPRINT:
""" + json.dumps(blueprint, separators=(",", ":")) + "\nENGINEERING FAILURE REPORT:\n" + json.dumps(failure, separators=(",", ":"))


def run_one(case: Path, source: Path, verification: Path, destination: Path, client: Any, model: str, overwrite: bool) -> dict:
    if destination.exists() and overwrite: shutil.rmtree(destination)
    if (destination / "manifest.json").is_file() and not overwrite: return json.loads((destination / "manifest.json").read_text(encoding="utf-8"))
    destination.mkdir(parents=True, exist_ok=True)
    started, raw, error, request_id = time.perf_counter(), "", None, None
    usage = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
    try:
        source_manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
        if source_manifest["status"] != "SUCCESS": raise RuntimeError("source one-shot output is not executable")
        blueprint = json.loads((source / "blueprint.json").read_text(encoding="utf-8"))
        report = json.loads((verification / "failure.json").read_text(encoding="utf-8"))
        response = client.chat.completions.create(model=model, messages=[{"role": "system", "content": "Perform only failure-localized CAD repair; obey the supplied immutability constraints."}, {"role": "user", "content": repair_prompt(blueprint, report)}], response_format={"type": "json_object"}, temperature=0.0, top_p=1.0, max_tokens=32768)
        raw, request_id = response.choices[0].message.content or "", getattr(response, "id", None)
        api_usage = response.usage; usage = {"input_tokens": int(getattr(api_usage, "prompt_tokens", 0) or 0), "output_tokens": int(getattr(api_usage, "completion_tokens", 0) or 0), "total_tokens": int(getattr(api_usage, "total_tokens", 0) or 0)}
        repaired = generic_validate(extract_json(raw))
        if [link["name"] for link in repaired["links"]] != [link["name"] for link in blueprint["links"]] or repaired["joints"] != blueprint["joints"]:
            raise ValueError("repair violated frozen kinematic structure")
        (destination / "blueprint.json").write_text(json.dumps(repaired, indent=2), encoding="utf-8")
        compile_direct(repaired, destination); status = "SUCCESS"
    except Exception as exc:
        status, error = "FAILURE", f"{type(exc).__name__}: {exc}"
    (destination / "raw_response.txt").write_text(raw, encoding="utf-8")
    urdf = destination / "urdf" / "model.urdf"
    manifest = {"case_id": case.name, "variant": "verification_guided_repair", "status": status, "model": model, "latency_seconds": time.perf_counter() - started,
                "budget": {"api_calls": 1, "max_total_output_tokens": 32768, "max_total_model_tokens": 100000, **usage},
                "artifacts": {"prediction_urdf": "urdf/model.urdf" if urdf.is_file() else None, "raw_response": "raw_response.txt"},
                "source_run": str(source.resolve()), "verification": str(verification.resolve()), "error": error, "request_id": request_id}
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", required=True)
    parser.add_argument("--data-root", type=Path, default=ROOT / "go_nogo4/data/motion15")
    parser.add_argument("--baseline-root", type=Path, default=ROOT / "go_nogo4/runs/multiview_static")
    parser.add_argument("--verification-root", type=Path, default=ROOT / "go_nogo5/runs/verification")
    parser.add_argument("--output-root", type=Path, default=ROOT / "go_nogo5/runs/repair")
    parser.add_argument("--config", type=Path, default=ROOT / "go_nogo2/config/llm.local.toml")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(); case = args.data_root / args.case
    config = replace(load_shared_llm(args.config), model="qwen3.7-plus")
    result = run_one(case, args.baseline_root / args.case, args.verification_root / args.case, args.output_root / args.case, config.create_client(), config.model, args.overwrite)
    print(json.dumps({"case": args.case, "status": result["status"]}, indent=2))


if __name__ == "__main__": main()
