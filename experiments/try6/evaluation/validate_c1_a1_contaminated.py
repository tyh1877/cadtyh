"""Independent fail-closed audit of the C1-A1 Phase-0 contamination result."""

from __future__ import annotations

import hashlib
import json
import math
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RESULT = ROOT / "experiments/try6/results/try6_0_c1_a1"


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    cfg = read(ROOT / "experiments/try6/protocol/try6_0_c1_a1.json")
    manifest = read(RESULT / "manifest.json")
    pre = read(RESULT / "pre_run_manifest.json")
    provenance = read(RESULT / "provenance/scale_provenance_audit.json")
    f0 = read(RESULT / "provenance/f0_scale_audit.json")
    registration = read(RESULT / "provenance/registration_dependency_audit.json")
    forbidden = read(RESULT / "provenance/forbidden_metric_paths.json")
    failure = read(RESULT / "failure_accounting.json")
    checks = {}
    checks["tracked_result_hashes"] = all(sha(RESULT / p) == digest for p, digest in manifest["result_file_sha256"].items())
    checks["prior_frozen_manifests"] = all(sha(ROOT / "experiments/try6/results" / ("try6_0_c1_v2" if k == "C1_v2" else "try6_0_d1_v3") / "manifest.json") == v
        for k, v in manifest["prior_manifest_sha256"].items())
    checks["protocol_hash"] = sha(ROOT / "experiments/try6/protocol/try6_0_c1_a1.json") == manifest["protocol_sha256"]
    urdf = ROOT / cfg["frozen_urdf"]
    j04 = next(j for j in ET.parse(urdf).getroot().findall("joint") if j.get("name") == "J04")
    actual_anchor = math.sqrt(sum(float(x)**2 for x in j04.find("origin").get("xyz").split()))*1000
    checks["exact_URDF_anchor"] = actual_anchor == f0["exact_J03_J04_anchor_mm"] == 63.0 and sha(urdf) == pre["URDF_sha256"]
    spec = next(x for x in read(ROOT / cfg["frozen_f0_spec"]) if x["link_id"] == "L04")
    ir = read(ROOT / cfg["frozen_f0_ir"])
    checks["F0_scale_lineage"] = spec["interface_span_mm"] == spec["major_length_mm"] == ir["link_spec"]["major_length_mm"] == 63.0 and f0["F0_round3_body_scale"] == ir["body_scale"]
    shape = read(RESULT / "provenance/f0_geometry_state.json")
    checks["F0_BREP_observed"] = shape["BREP_valid"] and shape["solid_count"] == 1 and shape["volume_mm3"] > 0 and sha(ROOT / cfg["frozen_f0_fcstd"]) == pre["F0_FCStd_sha256"]
    backbone = read(ROOT / "experiments/try6/protocol/r1_functional_backbone.json")
    kfdg = read(ROOT / cfg["frozen_c1_v2_result"] / "kfdg/canonical_kfdg.json")
    checks["functional_distal_anchor"] = backbone["metric_anchor"]["distance_mm"] == 63.0 and backbone["functional_nodes"][1]["frame_xyz_mm"] == [63.0, 0.0, 0.0] and kfdg["metric_anchor"]["distance_mm"] == 63.0
    builder = (ROOT / "experiments/try6/scripts/freecad_c1_builder.py").read_text(encoding="utf-8")
    solver = (ROOT / "experiments/try6/scripts/c1_v2_metric_solver.py").read_text(encoding="utf-8")
    checks["compiler_and_scaffold_leak"] = "abs(anchor-63.0)>1e-9" in builder and '"f0_fcstd"' in builder and '"f0_fcstd"' in solver and '"anchor_distance_mm":anchor' in solver
    evidence = read(ROOT / cfg["frozen_c1_v2_result"] / "visual_metric_evidence/visual_metric_evidence.json")
    reg = read(ROOT / cfg["frozen_c1_v2_result"] / "visual_metric_evidence/view_registration_report.json")
    checks["camera_scale_derived_from_anchor"] = all(abs(x["computed_px_per_mm"]-
        ((evidence["views"][x["view"]]["visible_color_bbox_px"][2]-evidence["views"][x["view"]]["visible_color_bbox_px"][0]) if x["view"] == "right" else
         (evidence["views"][x["view"]]["visible_color_bbox_px"][3]-evidence["views"][x["view"]]["visible_color_bbox_px"][1]))/63.0) < 1e-12
        for x in registration["views"]) and reg["anchor_distance_mm"] == 63.0
    c1cfg = read(ROOT / cfg["frozen_c1_v2_protocol"])
    checks["ROI_and_stations_anchor_derived"] = c1cfg["visual_evidence"]["roi_axis_mm"] == [12.0, 52.0] and c1cfg["visual_evidence"]["profile_stations_mm"] == [15.0, 30.0, 45.0] and registration["historical_ROI_profile_independent_of_anchor"] is False
    objective = (ROOT / "experiments/try6/scripts/c1_v2_visual_objective.py").read_text(encoding="utf-8")
    checks["objective_anchor_normalizer"] = "error=abs(predicted_width_mm-observed_width_mm)/self.anchor" in objective
    checks["provenance_rows_covered"] = provenance["row_count"] >= 17 and provenance["exact_metric_paths"] >= 10 and len(forbidden["exact_metric_paths"]) == provenance["exact_metric_paths"]
    checks["no_clean_F0_gauge"] = f0["pre_anchor_nonkinematic_gauge"]["usable_as_existing_clean_complete_F0_or_longitudinal_gauge"] is False and forbidden["latent_scale_option"]["status"] == "NOT_IMPLEMENTED"
    checks["conditional_protocol_stopped"] = failure["A1_N_proposed_candidates"] == failure["A1_F_proposed_candidates"] == failure["candidate_locks"] == failure["GT_evaluations"] == 0
    checks["no_GT_before_both_locks"] = read(RESULT / "audit/pre_gt_lock.json")["GT_access_permitted"] is False
    checks["no_forbidden_execution"] = all(value == 0 for value in read(RESULT / "audit/leakage_audit.json").values())
    checks["twenty_named_tests_honest"] = read(RESULT / "tests/test_report.json")["count"] >= 20 and read(RESULT / "tests/test_report.json")["paired_experiment_tests_not_run"] > 0
    lock_path = ROOT / "experiments/try5A/results/try5b1_a1_frozen_scaffold/formal_holdout_lock.json"
    lock = read(lock_path)
    checks["holdout_untouched"] = sha(lock_path) == pre["holdout_lock_sha256"] and lock["accessed"] is False and lock["evaluation_count"] == 0
    checks["decision_follows_gate"] = manifest["decision"] == "NOANCHOR_BASELINE_CONTAMINATED" and read(RESULT / "condition_parity.json")["status"] == "BLOCKED_BEFORE_PAIRED_RUN"
    if not all(checks.values()):
        raise RuntimeError("C1-A1 provenance validation failed: " + json.dumps(checks))
    output = {"decision": "NOANCHOR_BASELINE_CONTAMINATED",
        "checks": checks, "passed": len(checks), "total": len(checks),
        "independent_of_runner": True, "paired_candidates_run": 0,
        "GT_evaluations": 0, "scientific_anchor_effect_estimated": False}
    target = RESULT / "audit/independent_validation.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"decision": output["decision"], "passed": output["passed"], "total": output["total"]}))


if __name__ == "__main__":
    main()
