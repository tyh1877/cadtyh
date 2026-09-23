"""Freeze the API schema projected from the sole canonical slot contract."""

from __future__ import annotations

import json
from pathlib import Path

from experiments.try6.scripts.r1_contract import ROOT, HERE, load, sha
from experiments.try6.scripts.r1_v2_projection import project

RESULT=HERE/"results/try6_0_r1_v3/schema"


def save(path,obj):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,indent=2,sort_keys=True,ensure_ascii=False)+"\n",encoding="utf-8")


def freeze():
    cfg=load(HERE/"protocol/r1_v3_protocol.json")
    canonical=load(ROOT/cfg["canonical_slot_schema"])
    rules=load(ROOT/cfg["projection_rules"])
    api,removed=project(canonical,rules)
    save(RESULT/"canonical_slot_schema.json",canonical)
    save(RESULT/"api_transport_schema.json",api)
    save(RESULT/"projection_rules.json",rules)
    report={"schema_version":"robotcad_try6_r1_v3_projection_report_v1",
        "canonical_source_path":cfg["canonical_slot_schema"],
        "canonical_source_sha256":sha(ROOT/cfg["canonical_slot_schema"]),
        "projection_rules_path":cfg["projection_rules"],
        "projection_rules_sha256":sha(ROOT/cfg["projection_rules"]),
        "api_schema_sha256":sha(RESULT/"api_transport_schema.json"),
        "removed":removed,"removed_count":len(removed),
        "local_contract_unchanged":True,"api_compatible_unverified_until_preflight":True}
    save(RESULT/"projection_report.json",report)
    return report


if __name__=="__main__":print(json.dumps(freeze(),ensure_ascii=False))
