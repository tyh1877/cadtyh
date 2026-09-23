"""R0 flat KFDG v1 contract; no coercion or response repair."""

from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "protocol" / "kfdg_v1.schema.json"


def canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def validate(payload: object) -> dict:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(payload)
    assert isinstance(payload, dict)
    identifiers = [item["id"] for key in ("functional_nodes", "geometric_features", "parameters") for item in payload[key]]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("duplicate KFDG ID")
    parameter_ids = {item["id"] for item in payload["parameters"]}
    node_ids = {item["id"] for key in ("functional_nodes", "geometric_features") for item in payload[key]}
    for feature in payload["geometric_features"]:
        if len(feature["parameter_refs"]) != len(set(feature["parameter_refs"])):
            raise ValueError("duplicate parameter reference")
        if not set(feature["parameter_refs"]) <= parameter_ids:
            raise ValueError("dangling parameter reference")
    for relation in payload["constraints"]:
        if relation["source"] not in node_ids or relation["target"] not in node_ids:
            raise ValueError("dangling constraint reference")
    for parameter in payload["parameters"]:
        if not parameter["lower_bound"] <= parameter["value"] <= parameter["upper_bound"]:
            raise ValueError("parameter outside bounds")
        if parameter["lower_bound"] >= parameter["upper_bound"]:
            raise ValueError("inverted parameter bounds")
    return json.loads(canonical(payload))


def parse_raw(raw: str) -> dict:
    return validate(json.loads(raw))
