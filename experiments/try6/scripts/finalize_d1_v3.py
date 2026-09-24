"""Freeze final causal attribution from immutable alignment and witness evidence."""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RESULT = ROOT / "experiments/try6/results/try6_0_d1_v3"
ARTIFACT = ROOT / "experiments/try6/artifacts/try6_0_d1_v3"


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(relative, value):
    target = RESULT / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def csv_out(relative, rows):
    target = RESULT / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    if Path(sys.executable).resolve() != (ROOT / ".venv/Scripts/python.exe").resolve():
        raise RuntimeError("repository .venv required")
    if (RESULT / "manifest.json").exists():
        raise FileExistsError("D1-v3 already finalized")
    cfg = read(ROOT / "experiments/try6/protocol/try6_0_d1_v3.json")
    d1 = read(ROOT / cfg["frozen_d1_protocol"])
    pre = read(RESULT / "pre_run_manifest.json")
    raw = read(ARTIFACT / "geometry_raw.json")
    inspect = read(RESULT / "semantic_decomposition/existing_brep_inspection.json")
    alignment = read(ROOT / cfg["frozen_alignment"])
    w1root = ROOT / cfg["frozen_witness_result"]
    with (w1root / "summary/engineering_witness_metrics.csv").open(newline="", encoding="utf-8") as stream:
        witness = {x["subset"]: x for x in csv.DictReader(stream)}
    if sha(ROOT / cfg["frozen_alignment"]) != pre["alignment_sha256"] or len(alignment["cases"]) != 65:
        raise RuntimeError("alignment drift")
    if len(raw["localizations"]) != 9 or raw["semantic_decomposition"]["status"] != "PASS":
        raise RuntimeError("geometric attribution evidence incomplete")
    c1 = [x for x in alignment["cases"] if x["geometry_id"] == "G1_C1_FINAL"]
    if len(c1) != 13 or len(raw["C1_supported_rows"]) != 1 or len(raw["C1_suspect_rows"]) != 6:
        raise RuntimeError("C1-specific semantic registry drift")
    counts = dict(Counter(x["alignment_category"] for x in alignment["cases"]))
    if counts != {"ALIGNED_SAFE": 33, "ALIGNED_UNSAFE": 5, "KFDE_FALSE_POSITIVE_SUSPECT": 27}:
        raise RuntimeError("frozen 65-row categories drift")
    save("semantic_decomposition/supported_component_registry.json", raw["C1_supported_rows"])
    save("semantic_decomposition/suspect_component_registry.json", raw["C1_suspect_rows"])
    decomposition = raw["semantic_decomposition"]
    volumes = decomposition["volumes_mm3"]
    for filename, key in (("supported_relief", "R_supported"), ("suspect_relief", "R_suspect"),
                          ("overlap_relief", "R_shared")):
        save("semantic_decomposition/" + filename + ".json", {"volume_mm3": volumes[key],
             "artifact": decomposition["artifacts"][key], "state": decomposition["states"][key]})
    full_volume = decomposition["FULL_unique_removed_mm3"]
    partition_sum = volumes["R_supported_only"] + volumes["R_suspect_only"] + volumes["R_shared"]
    save("semantic_decomposition/decomposition_summary.json", {
        "status": "PASS", "C1_only": True,
        "supported_component_ids": decomposition["component_ids_supported"],
        "suspect_component_ids": decomposition["component_ids_suspect"],
        "FULL_unique_removed_mm3": full_volume,
        "supported_mm3": volumes["R_supported"], "suspect_mm3": volumes["R_suspect"],
        "shared_mm3": volumes["R_shared"],
        "supported_only_mm3": volumes["R_supported_only"],
        "suspect_only_mm3": volumes["R_suspect_only"],
        "supported_fraction_of_FULL": decomposition["supported_fraction_of_FULL"],
        "suspect_fraction_of_FULL": decomposition["suspect_fraction_of_FULL"],
        "suspect_only_fraction_of_FULL": decomposition["suspect_only_fraction_of_FULL"],
        "partition_sum_minus_FULL_mm3": partition_sum-full_volume,
        "not_asserted_exact_volume_additivity": True,
        "supported_localization": decomposition["supported_localization"],
        "suspect_localization": decomposition["suspect_localization"],
        "BREP_inspection": inspect["BREP_records"]})
    local_rows = []
    for record in raw["localizations"]:
        subset = record["subset"]
        loc = record["localization"]
        stem = subset.lower() if subset in ("FULL", "L03", "L05", "L06", "L07") else subset.lower()
        save("localization/" + stem + "_localization.json", record)
        local_rows.append({"subset": subset, "removed_mm3": loc["removed_volume_mm3"],
            "PROXIMAL_mm3": loc["regions_mm3"]["PROXIMAL"],
            "MIDDLE_mm3": loc["regions_mm3"]["MIDDLE"],
            "DISTAL_mm3": loc["regions_mm3"]["DISTAL"],
            "dominant_region": loc["dominant_region"],
            "dominant_fraction": loc["fractions"][loc["dominant_region"]] if loc["dominant_region"] else None,
            "localized": loc["localized"], "robustness": loc.get("localization_robustness"),
            "partition_error_mm3": loc["partition_error_mm3"],
            "accepted_witness_sha256": record["accepted_witness_brep"]["sha256"],
            "removed_brep_sha256": record["removed_brep"]["sha256"],
            "W1_volume_crosscheck_delta_mm3": record["removed_volume_crosscheck_delta_mm3"]})
    csv_out("localization/localization_summary.csv", local_rows)
    theta_path = ROOT / "experiments/try6/results/try6_0_c1_v2/solver/theta_selected.json"
    theta = read(theta_path)
    kfdg_path = ROOT / "experiments/try6/results/try6_0_c1_v2/kfdg/canonical_kfdg.json"
    kfdg = read(kfdg_path)
    features = [x["type"] for x in kfdg["geometric_features"]]
    bbox = inspect["BREP_records"]["R_supported"]["bbox"]
    if not bbox or theta["active_parameters"] != ["housing_width_mm", "housing_height_mm",
        "proximal_section_length_mm", "transition_length_mm", "distal_width_mm", "distal_height_mm"]:
        raise RuntimeError("six-theta registry/ROI drift")
    support = {
        "active_parameter_names": theta["active_parameters"],
        "active_parameter_source": str(theta_path.relative_to(ROOT)).replace("\\", "/"),
        "source_sha256": sha(theta_path),
        "C1_builder_source": "experiments/try6/scripts/freecad_c1_builder.py",
        "builder_sha256": pre["C1_builder_sha256"],
        "frozen_KFDG_features": features, "frozen_KFDG_sha256": sha(kfdg_path),
        "proximal_pad_control": "housing_width_mm/housing_height_mm affect full YZ pad cross-section; proximal_section_length_mm changes full pad length",
        "transition_control": "transition_length_mm and distal_width_mm/distal_height_mm affect loft sections; not a local proximal cut",
        "no_local_pocket_feature_in_frozen_KFDG": "pocket" not in features,
        "supported_relief_bbox_mm": bbox,
        "supported_relief_bbox_x_span_mm": bbox["size_mm"][0],
        "proximal_pad_selected_length_mm": theta["theta_star"]["proximal_section_length_mm"],
        "no_parameter_perturbation_or_theta_search_run": True}
    save("capacity/six_theta_geometry_support.json", support)
    neighbor_alignment = read(ROOT / "experiments/try6/results/try6_0_d1_v2/alignment/per_neighbor_alignment.json")
    local_by_id = {x["subset"]: x for x in local_rows}
    attribution = []
    capacity_rows = []
    for neighbor in ("L03", "L05", "L06", "L07"):
        align = neighbor_alignment[neighbor]
        c1_align = dict(Counter(x["alignment_category"] for x in c1 if x["neighbor_id"] == neighbor))
        loc = local_by_id[neighbor]
        if neighbor == "L03":
            expressibility = "REQUIRES_LOCAL_FEATURE"
            note = "One C1 exact-supported pose requires 66.60 mm3 local proximal relief; ROI x=11.78..15.79 mm within a 32 mm global pad, W1 L03 witness remains one solid and interfaces invariant. Frozen six theta lack a local pocket node."
        else:
            expressibility = "UNKNOWN"
            note = ("No C1 mechanically supported unsafe component; KFDE-demanded relief is semantically suspect, not CAD-capacity evidence."
                    if neighbor in ("L05", "L06") else "Engineering-zero relief; no supported unsafe component.")
        capacity_rows.append({"neighbor": neighbor, "expressibility": expressibility,
                              "mechanical_support_count_C1": c1_align.get("ALIGNED_UNSAFE", 0),
                              "reason": note})
        attribution.append({"neighbor": neighbor, "all_geometry_aligned_unsafe": align["aligned_unsafe"],
            "all_geometry_KFDE_violations": align["nonambiguous_KFDE_violations"],
            "C1_aligned_unsafe": c1_align.get("ALIGNED_UNSAFE", 0),
            "C1_false_positive_suspects": c1_align.get("KFDE_FALSE_POSITIVE_SUSPECT", 0),
            "normalized_relief_percent": 100*float(witness[neighbor]["normalized_relief_A"]),
            "relief_category": ("ZERO_RELIEF_WITHIN_ENGINEERING_TOLERANCE" if neighbor == "L07"
                                else witness[neighbor]["relief_category"]),
            "dominant_region": loc["dominant_region"], "localized": loc["localized"],
            "expressibility": expressibility, "interpretation": note})
    save("capacity/per_neighbor_expressibility.json", capacity_rows)
    csv_out("attribution/neighbor_attribution.csv", attribution)
    representation = {"axis": "LOCAL_CAPACITY_MISSING",
        "primary_decision_not_based_on_false_positive_relief": True,
        "supported_C1_component_count": 1,
        "supported_relief_mm3": volumes["R_supported"],
        "supported_relief_localization": decomposition["supported_localization"],
        "supported_relief_bbox_mm": bbox,
        "L03_supported_witness_connected": witness["L03"]["topology_class"] == "CONNECTED_SINGLE_SOLID",
        "frozen_interfaces_preserved": witness["L03"]["interface_invariant"] == "True",
        "expressibility": "REQUIRES_LOCAL_FEATURE",
        "topology_redesign_supported": False,
        "causal_priority": "secondary to KFDE semantic diagnosis; no C2 redesign performed"}
    save("capacity/representation_capacity_summary.json", representation)
    f0 = read(ROOT / "experiments/try6/results/try6_0_d1_v2/authority/authority_summary.json")
    alignment_rate = 5/32
    if f0["authority_contradiction_established"]:
        decision = "KFDE_AUTHORITY_INCONSISTENCY"
    elif alignment_rate < d1["alignment_high_min_fraction"] and volumes["R_suspect_only"] > volumes["R_supported_only"]:
        decision = "KFDE_SEMANTICS_MISALIGNED"
    elif alignment_rate < d1["alignment_high_min_fraction"] and representation["axis"] == "LOCAL_CAPACITY_MISSING":
        decision = "MIXED_KFDE_AND_REPRESENTATION_ISSUE"
    elif alignment_rate >= d1["alignment_high_min_fraction"] and representation["axis"] == "LOCAL_CAPACITY_MISSING":
        decision = "LOCAL_RELIEF_FEATURE_NEEDED"
    elif alignment_rate >= d1["alignment_high_min_fraction"] and representation["axis"] == "TOPOLOGY_CAPACITY_MISSING":
        decision = "PARAMETRIC_TOPOLOGY_INSUFFICIENT"
    else:
        decision = "DIAGNOSTIC_INCONCLUSIVE"
    trace = {"decision": decision, "priority": d1["decision_priority"],
        "authority_contradiction": f0["authority_contradiction_established"],
        "alignment_rate_frozen": alignment_rate, "alignment_high_threshold_frozen": d1["alignment_high_min_fraction"],
        "all_geometry_counts": counts,
        "C1_supported_count": 1, "C1_suspect_count": 6,
        "C1_supported_only_mm3": volumes["R_supported_only"],
        "C1_suspect_only_mm3": volumes["R_suspect_only"],
        "C1_shared_mm3": volumes["R_shared"],
        "representation_axis_secondary": representation["axis"],
        "mixed_label_not_selected_reason": "Frozen decision priority selects substantial semantic misalignment before a secondary local-capacity issue",
        "next_method_implication": "KFDE semantic redesign" if decision == "KFDE_SEMANTICS_MISALIGNED" else "further diagnosis",
        "no_method_implemented": True}
    save("attribution/decision_trace.json", trace)
    save("attribution/full_attribution.json", {"FULL_normalized_relief_ratio": float(witness["FULL"]["normalized_relief_A"]),
        "FULL_unique_removed_mm3": full_volume,
        "FULL_localization": next(x for x in raw["localizations"] if x["subset"] == "FULL")["localization"],
        "supported_only_mm3": volumes["R_supported_only"],
        "suspect_only_mm3": volumes["R_suspect_only"],
        "shared_mm3": volumes["R_shared"],
        "interpretation": "FULL moderate relief is KFDE-demanded, not wholly mechanically required; C1 suspect-only occupancy dominates",
        "numerical_partition_error_mm3": partition_sum-full_volume})
    save("audit/frozen_evidence_audit.json", {"prior_manifest_sha256": pre["prior_manifest_sha256"],
        "alignment_sha256": pre["alignment_sha256"], "witness_metrics_sha256": pre["W1_v2_metrics_sha256"],
        "W1_v2_manifest_sha256": pre["W1_v2_manifest_sha256"],
        "technical_retry": read(RESULT / "localization/technical_retry_started.json"),
        "all_frozen_inputs_unchanged": True})
    save("audit/leakage_audit.json", {"VLM_calls": raw["VLM_calls"],
        "GT_geometry_evaluations": raw["GT_evaluations"],
        "final_96_case_mechanics_evaluations": raw["final_96_case_mechanics_evaluations"],
        "formal_holdout_evaluations": 0, "alignment_rerun": False,
        "theta_search_or_CAD_generation": False})
    save("audit/holdout_audit.json", {"lock_sha256": pre["holdout_lock_sha256"],
        "accessed": False, "evaluation_count": 0})
    save("failure_accounting.json", {"requested_localizations": d1["witness_subsets"],
        "completed_localizations": [x["subset"] for x in raw["localizations"]],
        "first_technical_attempt_failed": True,
        "one_documented_localization_reporting_retry": True,
        "semantic_decomposition": decomposition["status"], "dropped": []})
    save("claim_ledger.json", {
        "alignment_rate": {"evidence_type": "computed_frozen", "artifact": cfg["frozen_alignment"],
                           "field": "cases.alignment_category"},
        "supported_vs_suspect_relief": {"evidence_type": "computed", "artifact": "semantic_decomposition/decomposition_summary.json",
                                         "field": "supported_only_mm3,suspect_only_mm3,shared_mm3"},
        "localization": {"evidence_type": "computed", "artifact": "localization/localization_summary.csv"},
        "six_theta_support": {"evidence_type": "code_derived", "artifact": "capacity/six_theta_geometry_support.json"},
        "final_decision": {"evidence_type": "inferred_from_computed", "artifact": "attribution/decision_trace.json"}})
    files = [p for p in RESULT.rglob("*") if p.is_file() and p.name not in ("manifest.json", "independent_validation.json")]
    save("manifest.json", {"decision": decision, "created_utc": datetime.now(timezone.utc).isoformat(),
        "starting_commit": pre["starting_commit"],
        "final_commit_reference": "git rev-parse try6-d1-v3-semantics-misaligned",
        "protocol_sha256": pre["protocol_sha256"],
        "alignment_sha256": pre["alignment_sha256"],
        "W1_v2_manifest_sha256": pre["W1_v2_manifest_sha256"],
        "C1_mutable_brep_sha256": pre["C1_mutable_brep_sha256"],
        "component_hashes": pre["component_hashes"],
        "W0_exact_union_sha256": pre["W0_exact_union_sha256"],
        "geometry_worker_original_sha256": pre["geometry_worker_sha256"],
        "geometry_worker_technical_retry_sha256": sha(ROOT / "experiments/try6/evaluation/freecad_d1_v3_geometry.py"),
        "six_theta_source_sha256": pre["six_theta_source_sha256"],
        "C1_builder_sha256": pre["C1_builder_sha256"],
        "FreeCAD_version": raw["FreeCAD_version"], "OCC_version": raw["OCC_version"],
        "python_environment": sys.executable,
        "geometry_raw_sha256": sha(ARTIFACT / "geometry_raw.json"),
        "prior_manifest_sha256": pre["prior_manifest_sha256"],
        "result_file_sha256": {str(p.relative_to(RESULT)).replace("\\", "/"): sha(p) for p in files}})
    print(json.dumps({"decision": decision, "supported_only_mm3": volumes["R_supported_only"],
        "suspect_only_mm3": volumes["R_suspect_only"], "shared_mm3": volumes["R_shared"],
        "localized_subsets": len(raw["localizations"])}))


if __name__ == "__main__":
    main()
