"""Schema and leakage validation for a public Try-1 Image+Text packet."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas" / "image_text_input_v1.schema.json"
# The fixed template may explicitly say that URDF/mesh are unavailable.  Only
# terms that would disclose structure rather than deny access are rejected here.
FORBIDDEN = ("manufacturer", "brand", "joint count", "link count", "dh parameter", "xacro", "step", "b-rep")


def validate(packet: dict) -> dict:
    errors: list[dict] = []
    try:
        jsonschema.validate(packet, json.loads(SCHEMA.read_text(encoding="utf-8")))
    except jsonschema.ValidationError as exc:
        errors.append({"code": "SCHEMA", "path": list(exc.absolute_path), "message": exc.message})
    prompt = str(packet.get("rendered_prompt", "")).casefold()
    for token in FORBIDDEN:
        if token in prompt:
            errors.append({"code": "STRUCTURE_LEAK", "field": "rendered_prompt", "token": token})
    values = packet.get("images", {}).values() if isinstance(packet.get("images"), dict) else []
    if any(".." in str(path) or Path(path).suffix.casefold() != ".png" for path in values):
        errors.append({"code": "IMAGE_PATH", "message": "images must be local PNG paths without traversal"})
    return {"syntax_valid": not any(e["code"] == "SCHEMA" for e in errors), "semantic_valid": not errors, "errors": errors}


if __name__ == "__main__":
    value = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    report = validate(value)
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["semantic_valid"] else 1)
