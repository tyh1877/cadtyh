"""R1 VFP semantics and deterministic KFDG assembly; no GT or response repair."""

from __future__ import annotations

import hashlib
import json
import xml.etree.ElementTree as ET
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[3]
HERE = ROOT / "experiments/try6"
PROTOCOL = HERE / "protocol"
FORBIDDEN_VISUAL_TERMS = ("bearing", "motor", "bolt", "screw", "thread", "internal", "hidden", "fastener", "joint", "axis", "interface", "seat", "mount")


def load(path): return json.loads(Path(path).read_text(encoding="utf-8"))
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def canonical(value): return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


class SemanticError(ValueError):
    def __init__(self, code, detail):
        self.code = code
        super().__init__(f"{code}: {detail}")


def frozen_inputs():
    backbone = load(PROTOCOL / "r1_functional_backbone.json")
    registry = load(PROTOCOL / "r1_parameter_registry.json")
    rules = load(PROTOCOL / "r1_assembler_rules.json")
    return backbone, registry, rules


def audit_functional_authority(backbone=None):
    backbone = backbone or frozen_inputs()[0]
    for item in backbone["authority_sources"].values():
        if "sha256" in item and sha(ROOT / item["path"]) != item["sha256"]:
            raise SemanticError("AUTHORITY_SOURCE_DRIFT", item["path"])
    urdf = ET.parse(ROOT / backbone["authority_sources"]["sanitized_urdf"]["path"])
    joints = {j.get("name"): j for j in urdf.findall("joint")}
    j03, j04 = joints["J03"], joints["J04"]
    if j03.find("child").get("link") != "L04" or j04.find("parent").get("link") != "L04":
        raise SemanticError("URDF_LINK_DRIFT", "J03/J04 no longer bound to L04")
    j04_xyz = [1000*float(x) for x in j04.find("origin").get("xyz").split()]
    anchor = backbone["metric_anchor"]["distance_mm"]
    if j04_xyz != [anchor, 0.0, 0.0]:
        raise SemanticError("URDF_ANCHOR_DRIFT", str(j04_xyz))
    spec = load(ROOT / backbone["authority_sources"]["fixed_functional_parameter_spec"]["path"])["fixed_functional"]
    nodes = {n["id"]: n for n in backbone["functional_nodes"]}
    if nodes["proximal_joint_port"]["frame_xyz_mm"] != spec["J03_origin_L04_mm"] or nodes["proximal_joint_port"]["axis"] != spec["J03_axis_L04"]:
        raise SemanticError("PROXIMAL_FRAME_DRIFT", "local frame differs from frozen parameter spec")
    if nodes["distal_mount_port"]["frame_xyz_mm"] != spec["J04_origin_L04_mm"] or nodes["distal_mount_port"]["axis"] != [float(x) for x in j04.find("axis").get("xyz").split()]:
        raise SemanticError("DISTAL_FRAME_DRIFT", "local frame differs from frozen URDF/spec")
    contracts = load(ROOT / backbone["authority_sources"]["frozen_interfaces"]["path"])
    by_joint = {c["joint_id"]: c for c in contracts if c["joint_id"] in {"J03", "J04"}}
    if by_joint["J03"]["axis_child"] != nodes["proximal_joint_port"]["axis"] or by_joint["J04"]["axis_parent"] != nodes["distal_mount_port"]["axis"]:
        raise SemanticError("INTERFACE_AXIS_DRIFT", "axis differs from frozen contract")
    if by_joint["J04"]["origin_xyz_mm"] != nodes["distal_mount_port"]["frame_xyz_mm"]:
        raise SemanticError("INTERFACE_ORIGIN_DRIFT", "J04 differs from frozen contract")
    if not (ROOT / backbone["frozen_interface_geometry_source"]).is_file():
        raise SemanticError("FROZEN_SCAFFOLD_MISSING", backbone["frozen_interface_geometry_source"])
    return {"status":"PASS", "joint_ids":["J03","J04"], "anchor_mm":anchor,
            "urdf_sha256":sha(ROOT / backbone["authority_sources"]["sanitized_urdf"]["path"]),
            "interface_sha256":sha(ROOT / backbone["authority_sources"]["frozen_interfaces"]["path"])}


def validate_registry(registry=None, rules=None):
    registry = registry or frozen_inputs()[1]
    rules = rules or frozen_inputs()[2]
    source = load(ROOT / registry["source"])["optimizable"]
    source_by_id = {p["id"]: p for p in source}
    items = registry["parameters"]
    ids = [p["id"] for p in items]
    if len(ids) != len(set(ids)) or set(ids) != set(source_by_id):
        raise SemanticError("REGISTRY_IDENTITY", "registry differs from frozen parameter source")
    owners = [(p["owner_feature_type"],p["semantic_role"]) for p in items]
    if len(owners) != len(set(owners)):
        raise SemanticError("REGISTRY_ROLE_COLLISION", "owner-role pair repeated")
    for p in items:
        src = source_by_id[p["id"]]
        if any(p[key] != src[key] for key in ("value","lower_bound","upper_bound")):
            raise SemanticError("REGISTRY_BOUNDS_DRIFT", p["id"])
        if p.get("unit", registry["unit"]) != "mm":
            raise SemanticError("REGISTRY_UNIT", p["id"])
        if p["allowed_orphan"] and (p["owner_feature_type"] != "deferred_fillet" or p["optimizable"]):
            raise SemanticError("REGISTRY_ORPHAN_POLICY", p["id"])
        if not p["allowed_orphan"] and p["owner_feature_type"] not in rules["feature_signatures"]:
            raise SemanticError("REGISTRY_UNKNOWN_OWNER", p["id"])
        if not p["lower_bound"] <= p["value"] <= p["upper_bound"]:
            raise SemanticError("REGISTRY_VALUE_BOUNDS", p["id"])
    expected_pairs = {(kind,role) for kind,sig in rules["feature_signatures"].items() for role in sig["required_roles"]}
    if expected_pairs != {pair for pair,p in zip(owners,items) if not p["allowed_orphan"]}:
        raise SemanticError("REGISTRY_SIGNATURE_MISMATCH", "active registry roles do not cover signatures exactly")
    return {"status":"PASS", "active_parameter_count":sum(not p["allowed_orphan"] for p in items),
            "dormant_parameter_count":sum(p["allowed_orphan"] for p in items)}


def validate_vfp(raw):
    schema = load(PROTOCOL / "r1_vfp.schema.json")
    Draft202012Validator(schema).validate(raw)
    rules = frozen_inputs()[2]
    features = raw["visual_features"]
    names = [f["local_name"] for f in features]
    types = [f["feature_type"] for f in features]
    if len(names) != len(set(names)) or len(types) != len(set(types)):
        raise SemanticError("DUPLICATE_VISUAL_FEATURE", "duplicate local name or feature class")
    if set(types) != set(rules["required_feature_types"]):
        raise SemanticError("MISSING_OR_EXTRA_VISIBLE_FEATURE", str(types))
    for f in features:
        kind = f["feature_type"]
        if any(term in f["local_name"] for term in FORBIDDEN_VISUAL_TERMS):
            raise SemanticError("UNSUPPORTED_HIDDEN_FEATURE", f["local_name"])
        signature = rules["feature_signatures"][kind]
        roles = f["parameter_roles"]
        if len(roles) != len(set(roles)) or set(roles) != set(signature["required_roles"]):
            raise SemanticError("FEATURE_ROLE_SIGNATURE", kind)
        if f["relations"] != signature["required_relations"]:
            raise SemanticError("VISUAL_RELATION_SIGNATURE", kind)
        if any(r["target_feature_type"] == kind for r in f["relations"]):
            raise SemanticError("SELF_RELATION", kind)
    return json.loads(canonical(raw))


def assemble(vfp, backbone=None, registry=None, rules=None):
    vfp = validate_vfp(vfp)
    backbone, registry, rules = (backbone or frozen_inputs()[0], registry or frozen_inputs()[1], rules or frozen_inputs()[2])
    audit_functional_authority(backbone)
    validate_registry(registry, rules)
    proposals = {f["feature_type"]:f for f in vfp["visual_features"]}
    features = []
    for kind in rules["required_feature_types"]:
        f = proposals[kind]; signature = rules["feature_signatures"][kind]
        refs = [p["id"] for role in signature["required_roles"] for p in registry["parameters"] if p["owner_feature_type"] == kind and p["semantic_role"] == role]
        if len(refs) != len(signature["required_roles"]) or len(refs) != len(set(refs)):
            raise SemanticError("ASSEMBLY_REFERENCE_FAILURE", kind)
        features.append({"id":signature["canonical_id"],"type":signature["canonical_type"],"parameter_refs":refs,
                         "source_local_name":f["local_name"],"evidence_views":sorted(f["evidence_views"]),"confidence":f["confidence"]})
    owners = {kind: rules["feature_signatures"][kind]["canonical_id"] for kind in rules["required_feature_types"]}
    parameters = [{"id":p["id"],"value":p["value"],"unit":registry["unit"],"lower_bound":p["lower_bound"],"upper_bound":p["upper_bound"],
                   "provenance":p["provenance"],"confidence":p["confidence"],"owner_feature_id":owners.get(p["owner_feature_type"],"deferred_fillet"),
                   "semantic_role":p["semantic_role"],"optimizable":p["optimizable"],"functional_frozen":p["functional_frozen"],"allowed_orphan":p["allowed_orphan"]} for p in registry["parameters"]]
    graph = {"schema_version":"robotcad_kfdg_r1","link_id":backbone["link_id"],"functional_nodes":backbone["functional_nodes"],
             "geometric_features":features,"parameters":parameters,"constraints":rules["canonical_relations"],
             "metric_anchor":backbone["metric_anchor"],"authority":{"functional_backbone_sha256":sha(PROTOCOL / "r1_functional_backbone.json"),
             "parameter_registry_sha256":sha(PROTOCOL / "r1_parameter_registry.json"),"assembler_rules_sha256":sha(PROTOCOL / "r1_assembler_rules.json"),
             "vfp_sha256":hashlib.sha256(canonical(vfp).encode("utf-8")).hexdigest()}}
    validate_kfdg(graph, vfp=vfp)
    return json.loads(canonical(graph))


def validate_kfdg(graph, vfp=None):
    schema = load(PROTOCOL / "r1_kfdg.schema.json")
    Draft202012Validator(schema).validate(graph)
    backbone, registry, rules = frozen_inputs()
    if graph["functional_nodes"] != backbone["functional_nodes"] or graph["metric_anchor"] != backbone["metric_anchor"]:
        raise SemanticError("FUNCTIONAL_AUTHORITY_VIOLATION", "graph differs from frozen backbone")
    auth = graph["authority"]
    for key,path in (("functional_backbone_sha256","r1_functional_backbone.json"),("parameter_registry_sha256","r1_parameter_registry.json"),("assembler_rules_sha256","r1_assembler_rules.json")):
        if auth[key] != sha(PROTOCOL / path): raise SemanticError("AUTHORITY_HASH_DRIFT", key)
    if vfp is not None and auth["vfp_sha256"] != hashlib.sha256(canonical(vfp).encode("utf-8")).hexdigest():
        raise SemanticError("VFP_PROVENANCE_DRIFT", "VFP hash mismatch")
    all_ids = [x["id"] for key in ("functional_nodes","geometric_features","parameters") for x in graph[key]]
    if len(all_ids) != len(set(all_ids)):
        raise SemanticError("DUPLICATE_ID", "KFDG node/parameter ID")
    feature_ids = {f["id"] for f in graph["geometric_features"]}
    node_ids = feature_ids | {n["id"] for n in graph["functional_nodes"]}
    parameter_by_id = {p["id"]:p for p in graph["parameters"]}
    if set(parameter_by_id) != {p["id"] for p in registry["parameters"]}:
        raise SemanticError("PARAMETER_REGISTRY_DRIFT", "parameter ID set")
    refs = []
    for f in graph["geometric_features"]:
        if len(f["parameter_refs"]) != len(set(f["parameter_refs"])):
            raise SemanticError("DUPLICATE_REFERENCE", f["id"])
        if not set(f["parameter_refs"]) <= set(parameter_by_id):
            raise SemanticError("DANGLING_PARAMETER_REFERENCE", f["id"])
        refs.extend(f["parameter_refs"])
        kind = next(k for k,v in rules["feature_signatures"].items() if v["canonical_id"] == f["id"])
        expected = [p["id"] for role in rules["feature_signatures"][kind]["required_roles"] for p in registry["parameters"] if p["owner_feature_type"] == kind and p["semantic_role"] == role]
        if f["parameter_refs"] != expected:
            raise SemanticError("OWNERSHIP_VIOLATION", f["id"])
    for p in graph["parameters"]:
        source = next(item for item in registry["parameters"] if item["id"] == p["id"])
        expected_owner = rules["feature_signatures"].get(source["owner_feature_type"],{}).get("canonical_id","deferred_fillet")
        if p["owner_feature_id"] != expected_owner or p["allowed_orphan"] != source["allowed_orphan"]:
            raise SemanticError("PARAMETER_OWNER_DRIFT", p["id"])
        if p["id"] not in refs and not p["allowed_orphan"]:
            raise SemanticError("UNAPPROVED_ORPHAN_PARAMETER", p["id"])
        if p["id"] in refs and p["allowed_orphan"]:
            raise SemanticError("DORMANT_PARAMETER_CLAIMED", p["id"])
    if len(graph["constraints"]) != len({canonical(c) for c in graph["constraints"]}):
        raise SemanticError("DUPLICATE_RELATION", "constraint repeated")
    for c in graph["constraints"]:
        if c["source"] not in node_ids or c["target"] not in node_ids:
            raise SemanticError("DANGLING_RELATION_REFERENCE", str(c))
        if c["source"] == c["target"]:
            raise SemanticError("SELF_RELATION", str(c))
    if graph["constraints"] != rules["canonical_relations"]:
        raise SemanticError("RELATION_AUTHORITY_DRIFT", "not deterministic assembly rules")
    return True
