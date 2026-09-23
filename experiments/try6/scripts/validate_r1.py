"""Independent post-run R1 representation validator; never reads GT/holdout cases."""

from __future__ import annotations

import hashlib
import json
import statistics
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path

from jsonschema import Draft202012Validator

from experiments.try6.scripts.r1_contract import ROOT, HERE, FORBIDDEN_VISUAL_TERMS, assemble, canonical, load, sha, validate_kfdg, validate_vfp

RESULT = HERE / "results/try6_0_r1"


def save(path, obj):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def pair_agreement(items, transform):
    pairs = list(combinations(range(len(items)),2))
    if not pairs: return None
    return sum(items[a] is not None and items[b] is not None and transform(items[a]) == transform(items[b]) for a,b in pairs) / len(pairs)


def representation():
    cfg = load(HERE / "protocol/r1_protocol.json")
    pre = load(RESULT / "preflight.json")
    if pre["protocol_sha256"] != sha(HERE / "protocol/r1_protocol.json"):
        raise RuntimeError("frozen protocol drift")
    for key,expected in pre["frozen_hashes"].items():
        if sha(ROOT / cfg[key]) != expected: raise RuntimeError(f"frozen {key} drift")
    schema = load(ROOT / cfg["vfp_schema"])
    calls = []
    proposals = []
    request_hashes = []
    all_evidence_hashes = {i["view"]:i["sha256"] for i in pre["images"]}
    for number in range(1,cfg["independent_calls"]+1):
        name = f"call_{number:02d}"
        folder = RESULT / "reliability" / name
        recorded = load(folder / "call_result.json")
        request_metadata = load(folder / "request_metadata.json") if (folder / "request_metadata.json").exists() else None
        check = {"call_number":number,"attempt_exists":(folder / "attempt_started.json").exists(),
                 "raw_schema_valid":False,"semantic_valid":False,"assembly_success":False,"canonical_kfdg_valid":False,
                 "response_repair_count":0,"duplicate_reference_count":0,"dangling_reference_count":0,
                 "unsupported_feature_count":0,"recorded_status":recorded["status"],"error":None}
        proposal = None
        if request_metadata:
            exact = ROOT / recorded["exact_http_request_path"]
            if sha(exact) != request_metadata["exact_request_sha256"]:
                raise RuntimeError(f"exact request hash mismatch {name}")
            sent = load(exact)
            if sent["response_format"]["json_schema"]["schema"] != schema or sent["response_format"]["json_schema"]["strict"] is not True:
                raise RuntimeError(f"schema not actually sent {name}")
            if request_metadata["image_hashes"] != all_evidence_hashes:
                raise RuntimeError(f"image evidence parity mismatch {name}")
            request_hashes.append(request_metadata["exact_request_sha256"])
        if (folder / "raw_response.txt").is_file():
            raw = (folder / "raw_response.txt").read_text(encoding="utf-8")
            http = load(folder / "http_response.json")
            sdk = load(folder / "sdk_response.json")
            if raw != http["choices"][0]["message"]["content"] or raw != sdk["choices"][0]["message"]["content"]:
                raise RuntimeError(f"HTTP/SDK raw mismatch {name}")
            try:
                parsed = json.loads(raw)
                if isinstance(parsed,dict) and isinstance(parsed.get("visual_features"),list):
                    for feature in parsed["visual_features"]:
                        if isinstance(feature,dict) and (feature.get("feature_type") not in {"main_housing","pocket","profile_transition"} or any(term in str(feature.get("local_name","")) for term in FORBIDDEN_VISUAL_TERMS)):
                            check["unsupported_feature_count"] += 1
                Draft202012Validator(schema).validate(parsed)
                check["raw_schema_valid"] = True
                proposal = parsed
                checked = validate_vfp(parsed)
                check["semantic_valid"] = True
                if (folder / "validated_vfp.json").is_file() and load(folder / "validated_vfp.json") != parsed:
                    check["response_repair_count"] += 1
                assembled = assemble(checked)
                check["assembly_success"] = True
                existing = RESULT / "canonical_kfdg" / f"{name}_kfdg.json"
                if not existing.is_file() or load(existing) != assembled:
                    raise RuntimeError("stored graph differs from independent deterministic assembly")
                validate_kfdg(assembled,checked)
                check["canonical_kfdg_valid"] = True
                for feature in assembled["geometric_features"]:
                    check["duplicate_reference_count"] += len(feature["parameter_refs"])-len(set(feature["parameter_refs"]))
                    ids = {p["id"] for p in assembled["parameters"]}
                    check["dangling_reference_count"] += sum(ref not in ids for ref in feature["parameter_refs"])
            except Exception as error:
                check["error"] = f"{type(error).__name__}: {error}"
        else:
            check["error"] = recorded.get("error","raw response missing")
        calls.append(check)
        proposals.append(proposal)
    request_parity = len(request_hashes) == cfg["independent_calls"] and len(set(request_hashes)) == 1
    consistency = {"denominator_calls":cfg["independent_calls"],"pair_count":cfg["independent_calls"]*(cfg["independent_calls"]-1)//2,
        "feature_type_agreement":pair_agreement(proposals,lambda x:sorted(f["feature_type"] for f in x["visual_features"])),
        "feature_count_agreement":pair_agreement(proposals,lambda x:len(x["visual_features"])),
        "role_agreement":pair_agreement(proposals,lambda x:sorted((f["feature_type"],tuple(sorted(f["parameter_roles"]))) for f in x["visual_features"])),
        "relation_agreement":pair_agreement(proposals,lambda x:sorted((f["feature_type"],canonical(f["relations"])) for f in x["visual_features"])),
        "missing_or_unparseable_proposals":sum(p is None for p in proposals)}
    save(RESULT / "reliability/proposal_consistency.json",consistency)
    denom = cfg["independent_calls"]
    counts = {key:sum(bool(c[key]) for c in calls) for key in ("raw_schema_valid","semantic_valid","assembly_success","canonical_kfdg_valid")}
    totals = {key:sum(c[key] for c in calls) for key in ("response_repair_count","duplicate_reference_count","dangling_reference_count","unsupported_feature_count")}
    gate = (len(calls)==denom and request_parity and all(value==denom for value in counts.values()) and
            all(value==0 for value in totals.values()) and all(c["attempt_exists"] for c in calls))
    summary = {"schema_version":"robotcad_try6_r1_reliability_summary_v1","timestamp_utc":datetime.now(timezone.utc).isoformat(),
        "requested_calls":denom,"attempts_retained":sum(c["attempt_exists"] for c in calls),"exact_request_body_parity":request_parity,
        "request_sha256":request_hashes[0] if request_parity else None,
        "raw_schema_validity_rate":counts["raw_schema_valid"]/denom,"vfp_semantic_validity_rate":counts["semantic_valid"]/denom,
        "graph_assembly_success_rate":counts["assembly_success"]/denom,"canonical_kfdg_validity_rate":counts["canonical_kfdg_valid"]/denom,
        "no_repair_rate":1-totals["response_repair_count"]/denom,
        "counts":counts,"totals":totals,"calls":calls,"representation_gate_pass":gate,
        "gt_evaluations":0,"formal_holdout_evaluations":0}
    save(RESULT / "reliability/reliability_summary.json",summary)
    save(RESULT / "canonical_kfdg/validator_report.json",{"representation_gate_pass":gate,
        "canonical_valid_count":counts["canonical_kfdg_valid"],"duplicate_refs":totals["duplicate_reference_count"],
        "dangling_refs":totals["dangling_reference_count"],"per_call":[{"call_number":c["call_number"],"valid":c["canonical_kfdg_valid"],"error":c["error"]} for c in calls]})
    print(json.dumps({"representation_gate_pass":gate,"counts":counts,"request_parity":request_parity,"totals":totals}))
    return summary


if __name__ == "__main__": representation()
