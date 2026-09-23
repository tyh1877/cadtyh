"""Independent fresh-slot gate before any formal C1-v2 solver candidate."""

from __future__ import annotations

import json

from jsonschema import Draft202012Validator

from experiments.try6.scripts.r1_contract import ROOT,HERE,load,sha
from experiments.try6.scripts.r1_v3_contract import assemble,validate_kfdg,validate_slots
from experiments.try6.scripts.run_r1_reliability import save

RESULT=HERE/"results/try6_0_c1_v2"


def validate():
    cfg=load(HERE/"protocol/try6_0_c1_v2.json")
    pre=load(RESULT/"pre_run_manifest.json")
    record=load(RESULT/"slot/validation.json")
    if pre["protocol_sha256"]!=sha(HERE/"protocol/try6_0_c1_v2.json") or record["status"]!="PASS":
        raise RuntimeError("protocol/fresh slot gate failed")
    if (RESULT/"solver").exists():raise RuntimeError("solver ran before independent slot validation")
    raw=(RESULT/"slot/raw_response.txt").read_text(encoding="utf-8")
    http=load(RESULT/"slot/http_response.json")
    sdk=load(RESULT/"slot/response.json")
    if raw!=http["choices"][0]["message"]["content"] or raw!=sdk["choices"][0]["message"]["content"]:
        raise RuntimeError("raw HTTP/SDK mismatch")
    req=load(RESULT/"slot/request.json")
    if sha(ROOT/req["exact_request_path"])!=req["exact_request_sha256"]:
        raise RuntimeError("exact request hash mismatch")
    parsed=json.loads(raw)
    Draft202012Validator(load(ROOT/cfg["slot_api_schema"])).validate(parsed)
    checked=validate_slots(parsed)
    graph=assemble(checked);validate_kfdg(graph,checked)
    if graph!=load(RESULT/"kfdg/canonical_kfdg.json"):
        raise RuntimeError("stored graph differs from deterministic assembly")
    if checked!=load(RESULT/"slot/validated_slots.json"):
        raise RuntimeError("slot response changed after raw validation")
    active=load(RESULT/"kfdg/active_parameters.json")
    slot_statuses={x["slot_id"]:x["status"] for x in checked["slots"]}
    if active["slot_statuses"]!=slot_statuses or len(active["active_ids"])<2:
        raise RuntimeError("active parameter derivation invalid")
    if slot_statuses["visible_pocket"]!="PRESENT" and any(pid.startswith("recess_") for pid in active["active_ids"]):
        raise RuntimeError("absent pocket optimized")
    lock=load(ROOT/"experiments/try5A/results/try5b1_a1_frozen_scaffold/formal_holdout_lock.json")
    if lock["accessed"] is not False or lock["evaluation_count"]!=0:raise RuntimeError("holdout lock violated")
    result={"status":"PASS","fresh_calls":1,"raw_transport_valid":True,"local_contract_valid":True,
        "canonical_kfdg_valid":True,"no_response_repair":True,"slot_statuses":slot_statuses,
        "active_parameters":active["active_ids"],"gt_evaluations":0,"formal_holdout_evaluations":0}
    save(RESULT/"slot/independent_validation.json",result)
    print(json.dumps(result))
    return result


if __name__=="__main__":validate()
