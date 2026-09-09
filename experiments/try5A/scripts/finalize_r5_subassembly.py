"""Verify R5 independently from unresolved whole-robot morphology failures."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = ROOT / "experiments/try5A"
gate = json.loads((HERE / "results/a3_integrated_coarse_morphology_gate.json").read_text())
assembly = json.loads((HERE / "assemblies/A3_integrated/assembly_result.json").read_text())
r5_links = {"L06", "L07", "L08", "L09", "L10"}
link_rows = [row for row in gate["links"] if row["link_id"] in r5_links]
group = gate["functional_subassemblies"][0]
checks = {
    "all_r5_links_pass_hard_gates": all(row["hard_status"] == "PASS" for row in link_rows),
    "opposed_pair_deterministic_pass": group["deterministic_status"] == "PASS",
    "opposed_pair_visual_pass": group["visual_status"] == "PASS",
    "fresh_visual_review_consumed": gate["visual_review_packet"]["status"] == "REVIEW_CONSUMED",
    "canonical_xyz_placement_verified": assembly.get("translation_matrix_a14_a24_a34_verified") is True,
}
result = {
    "status": "PASS" if all(checks.values()) else "FAIL",
    "repair_scope": "R5_SUBASSEMBLY_REPLAN",
    "target": group["subassembly_id"],
    "members": sorted(r5_links),
    "checks": checks,
    "member_separation_mm": group["member_separation_mm"],
    "terminal_extension_mm": group["terminal_extension_mm"],
    "whole_robot_gate_status": gate["status"],
    "remaining_whole_robot_failures": gate["failure_targets"],
    "artifacts": {
        "fcstd": "experiments/try5A/assemblies/A3_integrated/assembled_robot.FCStd",
        "isometric": "experiments/try5A/assemblies/A3_integrated/renders/isometric.png",
        "front": "experiments/try5A/assemblies/A3_integrated/renders/front.png",
        "top": "experiments/try5A/assemblies/A3_integrated/renders/top.png"
    },
}
out = HERE / "results/try5a3_r5_subassembly_report.json"
out.write_text(json.dumps(result, indent=2) + "\n")
summary_path = HERE / "results/try5a3_integrated_summary.json"
summary = json.loads(summary_path.read_text())
summary["assembly"] = assembly
summary["r5_subassembly"] = {
    "status": result["status"],
    "target": result["target"],
    "member_separation_mm": result["member_separation_mm"],
    "terminal_extension_mm": result["terminal_extension_mm"],
}
summary_path.write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps(result, indent=2))
raise SystemExit(result["status"] != "PASS")
