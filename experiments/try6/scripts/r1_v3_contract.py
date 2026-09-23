"""Closed-set slot validation and deterministic, status-aware KFDG assembly."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

from jsonschema import Draft202012Validator

from experiments.try6.scripts.r1_contract import ROOT, HERE, audit_functional_authority, canonical, load, sha, validate_registry

PROTOCOL = HERE / "protocol"


class SlotError(ValueError):
    def __init__(self,code,detail):
        self.code = code
        super().__init__(f"{code}: {detail}")


def registry(): return load(PROTOCOL/"r1_v3_slot_registry.json")
def slot_schema(): return load(PROTOCOL/"r1_v3_slot.schema.json")


def validate_slot_registry(reg=None):
    reg = reg or registry()
    params = load(PROTOCOL/"r1_parameter_registry.json")
    by_id = {p["id"]:p for p in params["parameters"]}
    ids = [s["slot_id"] for s in reg["slots"]]
    if ids != ["main_housing","visible_pocket","profile_transition"] or len(ids)!=len(set(ids)):
        raise SlotError("SLOT_SET_DRIFT",str(ids))
    expected_owner = {"main_housing":"main_housing","visible_pocket":"pocket","profile_transition":"profile_transition"}
    refs = []
    for slot in reg["slots"]:
        if len(slot["parameter_refs"])!=len(set(slot["parameter_refs"])):
            raise SlotError("DUPLICATE_REGISTRY_REF",slot["slot_id"])
        for ref in slot["parameter_refs"]:
            if ref not in by_id or by_id[ref]["owner_feature_type"]!=expected_owner[slot["slot_id"]]:
                raise SlotError("PARAMETER_OWNER_DRIFT",f"{slot['slot_id']}:{ref}")
        refs += slot["parameter_refs"]
    if len(refs)!=len(set(refs)):
        raise SlotError("CROSS_SLOT_PARAMETER_CLAIM",str(refs))
    if set(refs)!={p["id"] for p in params["parameters"] if not p["allowed_orphan"]}:
        raise SlotError("ACTIVE_PARAMETER_COVERAGE",str(refs))
    feature_ids = {s["feature_id"] for s in reg["slots"]}
    functional_ids = {n["id"] for n in load(PROTOCOL/"r1_functional_backbone.json")["functional_nodes"]}
    if len(feature_ids)!=3: raise SlotError("DUPLICATE_FEATURE_ID",str(feature_ids))
    for rule in reg["deterministic_relation_rules"]:
        if not set(rule["if_present"])<=set(ids) or rule["source"] not in feature_ids|functional_ids or rule["target"] not in feature_ids|functional_ids:
            raise SlotError("RELATION_RULE_DRIFT",str(rule))
    audit_functional_authority()
    validate_registry()
    return {"status":"PASS","slot_count":3,"active_parameter_count":len(refs),"dormant_legacy_count":1}


def validate_slots(raw):
    Draft202012Validator(slot_schema()).validate(raw)
    expected = [s["slot_id"] for s in registry()["slots"]]
    ids = [slot["slot_id"] for slot in raw["slots"]]
    if len(ids)!=len(set(ids)): raise SlotError("DUPLICATE_SLOT_ID",str(ids))
    if set(ids)!=set(expected): raise SlotError("SLOT_COMPLETENESS",str(ids))
    for item in raw["slots"]:
        if len(item["evidence_views"])!=len(set(item["evidence_views"])):
            raise SlotError("DUPLICATE_EVIDENCE",item["slot_id"])
        if item["status"] in ("PRESENT","UNCERTAIN") and not item["evidence_views"]:
            raise SlotError("EVIDENCE_REQUIRED",f"{item['slot_id']}:{item['status']}")
    return json.loads(canonical(raw))


def make_kfdg_schema():
    schema = copy.deepcopy(load(PROTOCOL/"r1_kfdg.schema.json"))
    schema["title"] = "Try-6 R1-v3 status-aware canonical KFDG"
    schema["properties"]["schema_version"]["enum"] = ["robotcad_kfdg_r1_v3"]
    features = schema["properties"]["geometric_features"]
    features["minItems"] = 0
    features["items"]["required"] = ["id","type","parameter_refs","source_slot_id","evidence_views","confidence"]
    features["items"]["properties"].pop("source_local_name")
    features["items"]["properties"]["source_slot_id"] = {"type":"string","enum":["main_housing","visible_pocket","profile_transition"]}
    parameters = schema["properties"]["parameters"]["items"]
    parameters["required"] += ["owner_slot_id","active"]
    parameters["properties"]["owner_slot_id"] = {"type":"string","enum":["main_housing","visible_pocket","profile_transition","deferred_fillet"]}
    parameters["properties"]["active"] = {"type":"boolean"}
    schema["properties"]["constraints"]["minItems"] = 0
    schema["required"] += ["slot_provenance"]
    schema["properties"]["slot_provenance"] = {"type":"array","minItems":3,"maxItems":3,
        "items":{"type":"object","additionalProperties":False,
            "required":["slot_id","status","evidence_views","confidence"],
            "properties":{"slot_id":{"type":"string","enum":["main_housing","visible_pocket","profile_transition"]},
                "status":{"type":"string","enum":["PRESENT","ABSENT","UNCERTAIN"]},
                "evidence_views":{"type":"array","uniqueItems":True,"items":{"type":"string"}},
                "confidence":{"type":"string","enum":["HIGH","MEDIUM","LOW"]}}}}
    authority = schema["properties"]["authority"]
    authority["required"].remove("assembler_rules_sha256")
    authority["required"].remove("vfp_sha256")
    authority["properties"].pop("assembler_rules_sha256")
    authority["properties"].pop("vfp_sha256")
    authority["required"] += ["slot_registry_sha256","slot_response_sha256"]
    authority["properties"]["slot_registry_sha256"]={"type":"string"}
    authority["properties"]["slot_response_sha256"]={"type":"string"}
    Draft202012Validator.check_schema(schema)
    return schema


def freeze_kfdg_schema():
    path = PROTOCOL/"r1_v3_kfdg.schema.json"
    if path.exists(): raise FileExistsError("R1-v3 KFDG schema already frozen")
    path.write_text(json.dumps(make_kfdg_schema(),indent=2,sort_keys=True,ensure_ascii=False)+"\n",encoding="utf-8")
    return path


def assemble(raw):
    decisions = validate_slots(raw)
    validate_slot_registry()
    reg = registry()
    backbone = load(PROTOCOL/"r1_functional_backbone.json")
    parameter_registry = load(PROTOCOL/"r1_parameter_registry.json")
    by_id = {x["slot_id"]:x for x in decisions["slots"]}
    present = {slot_id for slot_id,item in by_id.items() if item["status"]=="PRESENT"}
    features=[]
    for slot in reg["slots"]:
        item = by_id[slot["slot_id"]]
        if slot["slot_id"] in present:
            features.append({"id":slot["feature_id"],"type":slot["engineering_feature_type"],
                "parameter_refs":slot["parameter_refs"],"source_slot_id":slot["slot_id"],
                "evidence_views":sorted(item["evidence_views"]),"confidence":item["confidence"]})
    slot_for_owner = {"main_housing":"main_housing","pocket":"visible_pocket","profile_transition":"profile_transition","deferred_fillet":"deferred_fillet"}
    slot_map = {s["slot_id"]:s for s in reg["slots"]}
    params=[]
    for p in parameter_registry["parameters"]:
        owner_slot = slot_for_owner[p["owner_feature_type"]]
        active = owner_slot in present and not p["allowed_orphan"]
        params.append({"id":p["id"],"value":p["value"],"unit":parameter_registry["unit"],
            "lower_bound":p["lower_bound"],"upper_bound":p["upper_bound"],
            "provenance":p["provenance"],"confidence":p["confidence"],
            "owner_feature_id":slot_map[owner_slot]["feature_id"] if owner_slot in slot_map else "deferred_fillet",
            "owner_slot_id":owner_slot,"semantic_role":p["semantic_role"],
            "optimizable":p["optimizable"] and active,"functional_frozen":p["functional_frozen"],
            "allowed_orphan":not active,"active":active})
    constraints=[{"source":r["source"],"target":r["target"],"type":r["type"]}
        for r in reg["deterministic_relation_rules"] if set(r["if_present"])<=present]
    graph={"schema_version":"robotcad_kfdg_r1_v3","link_id":"L04",
        "functional_nodes":backbone["functional_nodes"],"geometric_features":features,
        "parameters":params,"constraints":constraints,"metric_anchor":backbone["metric_anchor"],
        "slot_provenance":[by_id[s["slot_id"]] for s in reg["slots"]],
        "authority":{"functional_backbone_sha256":sha(PROTOCOL/"r1_functional_backbone.json"),
            "parameter_registry_sha256":sha(PROTOCOL/"r1_parameter_registry.json"),
            "slot_registry_sha256":sha(PROTOCOL/"r1_v3_slot_registry.json"),
            "slot_response_sha256":hashlib.sha256(canonical(decisions).encode("utf-8")).hexdigest()}}
    validate_kfdg(graph,decisions)
    return json.loads(canonical(graph))


def validate_kfdg(graph,decisions=None):
    schema = load(PROTOCOL/"r1_v3_kfdg.schema.json")
    Draft202012Validator(schema).validate(graph)
    reg=registry(); backbone=load(PROTOCOL/"r1_functional_backbone.json")
    parameter_registry=load(PROTOCOL/"r1_parameter_registry.json")
    if graph["functional_nodes"]!=backbone["functional_nodes"] or graph["metric_anchor"]!=backbone["metric_anchor"]:
        raise SlotError("FUNCTIONAL_AUTHORITY", "functional backbone changed")
    authority=graph["authority"]
    for key,path in (("functional_backbone_sha256","r1_functional_backbone.json"),
        ("parameter_registry_sha256","r1_parameter_registry.json"),("slot_registry_sha256","r1_v3_slot_registry.json")):
        if authority[key]!=sha(PROTOCOL/path): raise SlotError("AUTHORITY_HASH",key)
    provenance={x["slot_id"]:x for x in graph["slot_provenance"]}
    if len(provenance)!=3 or set(provenance)!={s["slot_id"] for s in reg["slots"]}:
        raise SlotError("SLOT_PROVENANCE",str(provenance))
    if decisions is not None:
        checked=validate_slots(decisions)
        if graph["slot_provenance"]!=[next(x for x in checked["slots"] if x["slot_id"]==s["slot_id"]) for s in reg["slots"]]:
            raise SlotError("SLOT_PROVENANCE_DRIFT","decisions changed")
        if authority["slot_response_sha256"]!=hashlib.sha256(canonical(checked).encode("utf-8")).hexdigest():
            raise SlotError("SLOT_RESPONSE_HASH","decisions changed")
    present={sid for sid,item in provenance.items() if item["status"]=="PRESENT"}
    expected_features={s["feature_id"]:s for s in reg["slots"] if s["slot_id"] in present}
    features={f["id"]:f for f in graph["geometric_features"]}
    if set(features)!=set(expected_features) or len(features)!=len(graph["geometric_features"]):
        raise SlotError("FEATURE_PRESENCE","ABSENT/UNCERTAIN instantiated or PRESENT omitted")
    for fid,f in features.items():
        slot=expected_features[fid]
        if f["parameter_refs"]!=slot["parameter_refs"] or f["source_slot_id"]!=slot["slot_id"] or f["type"]!=slot["engineering_feature_type"]:
            raise SlotError("PARAMETER_MAPPING",fid)
        if len(f["parameter_refs"])!=len(set(f["parameter_refs"])): raise SlotError("DUPLICATE_REF",fid)
    source_params={p["id"]:p for p in parameter_registry["parameters"]}
    params={p["id"]:p for p in graph["parameters"]}
    if set(params)!=set(source_params) or len(params)!=len(graph["parameters"]): raise SlotError("PARAMETER_IDENTITY",str(params))
    claimed={ref for f in features.values() for ref in f["parameter_refs"]}
    if not claimed<=set(params): raise SlotError("DANGLING_REF",str(claimed-set(params)))
    for pid,p in params.items():
        src=source_params[pid]
        owner_slot=next((s for s in reg["slots"] if pid in s["parameter_refs"]),None)
        expected_active=owner_slot is not None and owner_slot["slot_id"] in present and not src["allowed_orphan"]
        expected_owner=owner_slot["slot_id"] if owner_slot else "deferred_fillet"
        expected_feature=owner_slot["feature_id"] if owner_slot else "deferred_fillet"
        if (p["active"],p["optimizable"],p["allowed_orphan"],p["owner_slot_id"],p["owner_feature_id"]) != (expected_active,src["optimizable"] and expected_active,not expected_active,expected_owner,expected_feature):
            raise SlotError("PARAMETER_OWNERSHIP",pid)
        if (pid in claimed)!=expected_active: raise SlotError("PARAMETER_CLAIM",pid)
    expected_constraints=[{"source":r["source"],"target":r["target"],"type":r["type"]}
        for r in reg["deterministic_relation_rules"] if set(r["if_present"])<=present]
    if graph["constraints"]!=expected_constraints: raise SlotError("RELATION_MAPPING","constraints differ")
    node_ids=set(features)|{n["id"] for n in graph["functional_nodes"]}
    if len(node_ids)!=len(features)+len(graph["functional_nodes"]): raise SlotError("DUPLICATE_NODE_ID","feature/functional")
    for relation in graph["constraints"]:
        if relation["source"] not in node_ids or relation["target"] not in node_ids or relation["source"]==relation["target"]:
            raise SlotError("DANGLING_RELATION",str(relation))
    return True


if __name__=="__main__": print(freeze_kfdg_schema())
