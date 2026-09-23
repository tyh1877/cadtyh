"""Strict, versioned L04 KFDG contract and topology assembly."""

from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

HERE = Path(__file__).resolve().parents[1]
FUNCTIONAL_IDS = ("proximal_joint_port", "distal_mount_port")
REQUIRED_FEATURE_TYPES = {"housing", "profile_transition", "pocket", "fillet"}


def load(path): return json.loads(Path(path).read_text(encoding="utf-8"))
def canonical(value): return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def validate_vlm(payload):
    schema = load(HERE / "protocol/kfdg_vlm_response_schema.json")
    Draft202012Validator(schema).validate(payload)
    ids = [item["id"] for item in payload["geometric_features"]]
    if len(ids) != len(set(ids)) or set(ids).intersection(FUNCTIONAL_IDS): raise ValueError("duplicate or reserved feature ID")
    nodes = set(ids) | set(FUNCTIONAL_IDS)
    for relation in payload["relations"]:
        if relation["source"] not in nodes or relation["target"] not in nodes: raise ValueError("relation references unknown node")
    cues = [item["parameter_id"] for item in payload["parameter_cues"]]
    if len(cues) != len(set(cues)): raise ValueError("duplicate parameter cue")
    types = {item["type"] for item in payload["geometric_features"]}
    if not REQUIRED_FEATURE_TYPES <= types: raise ValueError("missing required visible feature type")
    if any(sum(item["type"] == kind for item in payload["geometric_features"]) != 1 for kind in REQUIRED_FEATURE_TYPES): raise ValueError("minimal L04 KFDG needs one node per built feature type")
    return json.loads(canonical(payload))


def build_kfdg(vlm, parameter_spec):
    validated = validate_vlm(vlm)
    fixed = parameter_spec["fixed_functional"]
    graph = {"schema_version": "robotcad_kfdg_l04_v1", "link_id": "L04", "functional_nodes": [
        {"id": "proximal_joint_port", "type": "joint_port", "frame_xyz_mm": fixed["J03_origin_L04_mm"], "axis": fixed["J03_axis_L04"], "source": "KINEMATIC_REQUIREMENT"},
        {"id": "distal_mount_port", "type": "mount_port", "frame_xyz_mm": fixed["J04_origin_L04_mm"], "axis": [1.0, 0.0, 0.0], "source": "URDF_METRIC_ANCHOR"}
    ], "geometric_features": validated["geometric_features"], "parameter_nodes": parameter_spec["optimizable"], "relations": validated["relations"], "metric_anchor": {"source": "sanitized_urdf_and_frozen_interface_contract", "joint_ids": ["J03", "J04"], "distance_mm": fixed["anchor_distance_mm"]}}
    validate_kfdg(graph)
    return json.loads(canonical(graph))


def validate_kfdg(graph):
    Draft202012Validator(load(HERE / "protocol/kfdg_schema.json")).validate(graph)
    functional = {item["id"] for item in graph["functional_nodes"]}
    features = {item["id"] for item in graph["geometric_features"]}
    if functional != set(FUNCTIONAL_IDS) or len(features) != len(graph["geometric_features"]): raise ValueError("node identity mismatch")
    nodes = functional | features
    if any(item["source"] not in nodes or item["target"] not in nodes for item in graph["relations"]): raise ValueError("relation references unknown node")
    parameters = graph["parameter_nodes"]
    ids = [item["id"] for item in parameters]
    if len(ids) != len(set(ids)) or len(ids) != 9: raise ValueError("expected nine unique visual parameters")
    for item in parameters:
        if not item["lower_bound"] <= item["value"] <= item["upper_bound"] or item["lower_bound"] >= item["upper_bound"]: raise ValueError("parameter outside bounds")
    if abs(graph["metric_anchor"]["distance_mm"] - 63.0) > 1e-9: raise ValueError("frozen metric anchor mismatch")
    return True
