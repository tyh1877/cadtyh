"""Deterministic canonical-VFP to API-schema projection (only uniqueItems)."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

from jsonschema import Draft202012Validator

from experiments.try6.scripts.r1_contract import ROOT, HERE, load, sha


def pointer(parts):
    return "/" + "/".join(str(part).replace("~","~0").replace("/","~1") for part in parts)


def project(canonical, rules):
    Draft202012Validator.check_schema(canonical)
    if rules["allowed_removed_keywords"] != ["uniqueItems"] or not rules["no_other_keyword_removal"]:
        raise ValueError("projection rule expansion is not authorized")
    output = copy.deepcopy(canonical)
    removed = []
    def visit(obj, parts):
        if isinstance(obj, dict):
            if "uniqueItems" in obj:
                if obj.get("type") != "array" or obj["uniqueItems"] is not True:
                    raise ValueError("unsupported uniqueItems shape")
                removed.append({"keyword":"uniqueItems","path":pointer(parts+["uniqueItems"]),"value":obj.pop("uniqueItems"),
                    "reason":rules["reason"],"api_evidence":rules["api_evidence"],
                    "local_validator_replacement":rules["local_validator_replacement"]})
            for key,value in obj.items(): visit(value, parts+[key])
        elif isinstance(obj,list):
            for index,value in enumerate(obj): visit(value, parts+[index])
    visit(output,[])
    if len(removed) != rules["expected_removed_count"]:
        raise ValueError(f"expected {rules['expected_removed_count']} removals, got {len(removed)}")
    Draft202012Validator.check_schema(output)
    return output, removed


def freeze_projection(result_root=None):
    cfg = load(HERE / "protocol/r1_v2_protocol.json")
    canonical_path = ROOT / cfg["canonical_schema"]
    rules_path = ROOT / cfg["projection_rules"]
    canonical, rules = load(canonical_path), load(rules_path)
    api, removed = project(canonical,rules)
    result = Path(result_root or HERE / "results/try6_0_r1_v2") / "schema_projection"
    result.mkdir(parents=True,exist_ok=True)
    def save(name,value):
        (result/name).write_text(json.dumps(value,indent=2,sort_keys=True,ensure_ascii=False)+"\n",encoding="utf-8")
    save("canonical_vfp_schema.json",canonical)
    save("api_transport_schema.json",api)
    save("projection_rules.json",rules)
    report = {"schema_version":"robotcad_try6_r1_v2_projection_report_v1",
        "canonical_source_path":cfg["canonical_schema"],"canonical_source_sha256":sha(canonical_path),
        "projection_rules_path":cfg["projection_rules"],"projection_rules_sha256":sha(rules_path),
        "removed":removed,"removed_count":len(removed),"api_schema_sha256":sha(result/"api_transport_schema.json"),
        "local_contract_unchanged":True,"api_compatible_unverified_until_preflight":True}
    save("projection_report.json",report)
    return report


if __name__ == "__main__": print(json.dumps(freeze_projection(),ensure_ascii=False))
