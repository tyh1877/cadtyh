"""Independent D1-T0 readiness validator; run after the FreeCAD worker exits."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RESULT = ROOT / "experiments/try6/results/try6_0_d1_t0"


def read(relative):
    return json.loads((RESULT / relative).read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(relative, value):
    path = RESULT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main():
    manifest = read("manifest.json")
    config = read("protocol.json")
    states = read("geometry_state/g1_g5_states.json")
    tests = read("tests/test_report.json")
    booleans = read("boolean_safety/operation_results.json")
    parity = read("roundtrip/parity_report.json")
    frozen = read("audit/frozen_state_audit.json")
    leakage = read("audit/leakage_audit.json")
    holdout = read("audit/holdout_audit.json")
    dummy = read("audit/no_dummy_geometry_audit.json")
    checks = {}
    checks["protocol_hash"] = sha(ROOT / "experiments/try6/protocol/try6_0_d1_t0.json") == manifest["protocol_sha256"]
    checks["classifier_hash"] = sha(ROOT / "experiments/try6/scripts/volumetric_geometry_state.py") == manifest["classifier_implementation_sha256"]
    checks["worker_hash"] = sha(ROOT / "experiments/try6/evaluation/freecad_d1_t0_audit.py") == manifest["worker_sha256"]
    checks["frozen_manifests"] = frozen["unchanged"] and all(
        sha(ROOT / path / "manifest.json") == digest for path, digest in frozen["before"].items())
    checks["five_source_hashes"] = len(states) == 5 and all(
        sha(ROOT / row["source_path"]) == row["source_sha256"] for row in states)
    checks["frozen_tolerance"] = config["numerical_tolerance_mm3"] == 1e-6
    checks["synthetic_tests"] = tests["count"] >= 16 and tests["all_pass"] and tests["passed"] == tests["count"]
    checks["five_classified"] = len(states) == 5 and all(
        row["full"]["can_boolean_cut"] and row["mutable"]["state"] != "INVALID_BREP" for row in states)
    g5 = states[4]
    checks["g5_legitimate_empty"] = (g5["mutable"]["state"] == "EFFECTIVELY_EMPTY" and
        g5["verified_empty_provenance"] and g5["full"]["can_boolean_cut"] and
        g5["full_minus_allowed_volume_mm3"] == 0 and g5["mutable"]["solid_count"] == 0)
    checks["boolean_safety"] = (booleans["g5"]["branch"] == "EMPTY_A_NO_OCC_CUT" and
        booleans["synthetic"]["empty_A"] == "EMPTY_A_NO_OCC_CUT" and
        booleans["synthetic"]["empty_B"] == "EMPTY_B_NO_OCC_CUT" and
        booleans["synthetic"]["nonvolumetric_refused"] and booleans["synthetic"]["invalid_refused"])
    checks["row_retention"] = len(booleans["component_rows"]) == 13 and all(
        x["status"] == "EMPTY_MUTABLE_GEOMETRY" and x["intersection_volume_mm3"] == 0 and
        x["violation"] is False for x in booleans["component_rows"])
    checks["empty_witness_semantics"] = (booleans["empty_witness_semantics"]["removed_ratio"] ==
        "NOT_APPLICABLE_EMPTY_MUTABLE")
    checks["roundtrip"] = len(parity["roundtrips"]) == 5 and all(
        x["state_parity"] and x["solid_count_parity"] and x["repeated_deterministic"] and
        x["volume_parity_within_frozen_tolerance"] for x in parity["roundtrips"])
    checks["cross_path"] = len(parity["cross_paths"]) == 5 and all(x["state_parity"] for x in parity["cross_paths"])
    checks["no_dummy"] = not dummy["dummy_geometry_created"] and dummy["empty_solid_count"] == 0
    checks["no_scientific_evaluation"] = all(value == 0 for key, value in leakage.items() if key != "D1_v2_alignment_rows") and leakage["D1_v2_alignment_rows"] == 0
    lock_path = ROOT / holdout["lock_path"]
    live_lock = json.loads(lock_path.read_text(encoding="utf-8"))
    checks["holdout_guard"] = (sha(lock_path) == holdout["lock_sha256"] and
        live_lock["accessed"] is False and live_lock["evaluation_count"] == 0)
    if not checks["g5_legitimate_empty"]:
        decision = "GEOMETRY_PROVENANCE_AMBIGUOUS"
    elif not checks["roundtrip"] or not checks["cross_path"]:
        decision = "BREP_SERIALIZATION_INCONSISTENT"
    elif not checks["boolean_safety"] or not checks["row_retention"]:
        decision = "BOOLEAN_PATH_UNSAFE"
    elif not all(checks.values()):
        decision = "EMPTY_GEOMETRY_SEMANTICS_BLOCKED"
    else:
        decision = "READY_FOR_D1_V2"
    validation = {"validated_utc": datetime.now(timezone.utc).isoformat(),
                  "decision": decision, "checks": checks, "passed": sum(checks.values()),
                  "total": len(checks), "independent_of_runner": True,
                  "scientific_alignment_conclusion": None}
    save("audit/independent_validation.json", validation)
    print(json.dumps({"decision": decision, "passed": validation["passed"], "total": validation["total"]}))
    if decision != "READY_FOR_D1_V2":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
