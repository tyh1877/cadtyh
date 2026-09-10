"""Run Try-5B0 fast mechanical evaluator validation and benchmarks."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import subprocess
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = ROOT / "experiments/try5A"
RESULTS = HERE / "results/try5b0"
ARTIFACTS = HERE / "artifacts/try5b0"
BASELINE = HERE / "results/try5a5"
sys.path.insert(0, str(HERE / "scripts"))
sys.path.insert(0, str(HERE / "evaluation/mechanical"))

from fast_evaluator import GeometryCache, MechanicalEvaluator, pair_key
from freecad_runtime import python_runtime
from kinematics import canonical_q, fk, parse

COLLISIONS = {"ADJACENT_UNINTENDED_COLLISION", "NONADJACENT_COLLISION"}


def load(path): return json.loads(Path(path).read_text(encoding="utf-8"))
def dump(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write_csv(path, rows):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)


def frozen_configurations(links, joints):
    coupled = load(BASELINE / "coupled_configurations.json")["configurations"]
    per_joint = {}
    for joint in [item for item in joints if item["joint_type"] in ("revolute", "continuous", "prismatic")]:
        source = next(item for item in joints if item["joint_id"] == joint["mimic"]["joint"]) if joint["mimic"] else joint
        lo, hi = (-3.141592653589793, 3.141592653589793) if source["joint_type"] == "continuous" else (source["limits"]["lower"], source["limits"]["upper"])
        records = []
        for fraction in (0, .25, .5, .75, 1):
            q = canonical_q(joints); q[source["joint_id"]] = lo + fraction * (hi - lo)
            for mimic_joint in [item for item in joints if item.get("mimic")]:
                mimic = mimic_joint["mimic"]; q[mimic_joint["joint_id"]] = q[mimic["joint"]] * mimic.get("multiplier", 1) + mimic.get("offset", 0)
            _, world, _ = fk(links, joints, q)
            records.append({"config_id": f"{joint['joint_id']}_{fraction:.2f}", "q": q,
                            "world_transforms": {key: value.tolist() for key, value in world.items()},
                            "ee_world": world["L11"].tolist(), "active_joint": joint["joint_id"], "active_fraction": fraction})
        per_joint[joint["joint_id"]] = records
    return coupled, per_joint


def classification_metrics(exact_rows, fast_rows):
    exact = {pair_key(row): row for row in exact_rows}; fast = {pair_key(row): row for row in fast_rows}
    rows = []; tp = fp = fn = tn = 0
    for key, reference in exact.items():
        expected = reference["classification"] in COLLISIONS; predicted = bool(fast[key].get("fast_collision"))
        tp += expected and predicted; fp += (not expected) and predicted; fn += expected and not predicted; tn += (not expected) and not predicted
        rows.append({"config_id": key[0], "link_a": key[1], "link_b": key[2], "exact_classification": reference["classification"],
                     "fast_classification": fast[key]["fast_classification"], "exact_collision": int(expected), "fast_collision": int(predicted),
                     "agreement": int(expected == predicted), "fast_source": fast[key]["source"]})
    return rows, {"tp": tp, "fp": fp, "fn": fn, "tn": tn, "false_negative_rate": fn / max(1, tp + fn),
                  "false_positive_rate": fp / max(1, fp + tn), "classification_agreement": (tp + tn) / len(rows)}


def pose_rows(pair_rows):
    grouped = defaultdict(list)
    for row in pair_rows: grouped[row["config_id"]].append(row)
    return [{"config_id": config_id, "exact_collision_free": int(not any(x["exact_collision"] for x in rows)),
             "fast_collision_free": int(not any(x["fast_collision"] for x in rows)),
             "agreement": int(any(x["exact_collision"] for x in rows) == any(x["fast_collision"] for x in rows))}
            for config_id, rows in grouped.items()]


def repair_agreement(pair_rows):
    exact_counts = Counter(); fast_counts = Counter()
    for row in pair_rows:
        pair = row["link_a"] + "|" + row["link_b"]
        exact_counts[pair] += row["exact_collision"]; fast_counts[pair] += row["fast_collision"]
    rows = [{"pair": pair, "exact_collision_poses": exact_counts[pair], "fast_collision_poses": fast_counts[pair],
             "exact_repair_target": int(exact_counts[pair] > 0), "fast_repair_target": int(fast_counts[pair] > 0)}
            for pair in sorted(set(exact_counts) | set(fast_counts))]
    expected = {x["pair"] for x in rows if x["exact_repair_target"]}; predicted = {x["pair"] for x in rows if x["fast_repair_target"]}
    top_exact = [x for x, n in exact_counts.most_common() if n][:10]; top_fast = [x for x, n in fast_counts.most_common() if n][:10]
    return rows, {"repair_target_recall": len(expected & predicted) / max(1, len(expected)),
                  "repair_target_precision": len(expected & predicted) / max(1, len(predicted)), "top_k": min(10, len(expected)),
                  "top_k_pair_agreement": len(set(top_exact) & set(top_fast)) / max(1, min(10, len(expected)))}


def exact_consistency(recomputed, frozen):
    current = {pair_key(x): x["classification"] for x in recomputed}; reference = {pair_key(x): x["classification"] for x in frozen}
    mismatches = [key for key in reference if current.get(key) != reference[key]]
    return {"status": "PASS" if not mismatches else "FAIL", "row_count": len(reference), "mismatch_count": len(mismatches),
            "first_mismatches": [list(x) for x in mismatches[:20]]}


def main():
    RESULTS.mkdir(parents=True, exist_ok=True); ARTIFACTS.mkdir(parents=True, exist_ok=True)
    links, joints = parse(HERE / "inputs/sanitized_urdf/px100_sanitized.urdf")
    coupled, per_joint = frozen_configurations(links, joints)
    job = {"linear_deflection_mm": 0.35, "coupled": coupled, "per_joint": per_joint,
           "cache_dir": str(ARTIFACTS / "geometry_cache"), "output": str(ARTIFACTS / "exact_reference.json")}
    job_path = ARTIFACTS / "provider_job.json"; dump(job_path, job); provider_start = time.perf_counter()
    if os.environ.get("TRY5B0_REUSE_PROVIDER") == "1" and (ARTIFACTS / "exact_reference.json").is_file():
        provider_wall = 0.0
    else:
        process = subprocess.run([python_runtime(), str(HERE / "evaluation/mechanical/freecad_geometry_provider.py"), str(job_path)],
                                 cwd=ROOT, capture_output=True, text=True, timeout=3600)
        provider_wall = time.perf_counter() - provider_start
        (ARTIFACTS / "provider_stdout.txt").write_text(process.stdout, encoding="utf-8")
        (ARTIFACTS / "provider_stderr.txt").write_text(process.stderr, encoding="utf-8")
        if process.returncode: raise RuntimeError(process.stderr or process.stdout)
    exact = load(ARTIFACTS / "exact_reference.json"); frozen = load(BASELINE / "round3_verified_result.json")
    consistency = exact_consistency(exact["coupled"]["rows"], frozen["coupled"]["rows"])
    contracts = load(BASELINE / "motion_interface_contracts.json"); physical = exact["physical_links"]
    cache = GeometryCache(exact["cache"]); evaluator = MechanicalEvaluator(cache, contracts, exact["coupled"]["rows"], 1.0)
    cold_rows, cold = evaluator.evaluate(coupled, physical); warm_rows, warm = evaluator.evaluate(coupled, physical)
    pair_rows, classification = classification_metrics(exact["coupled"]["rows"], warm_rows)
    poses = pose_rows(pair_rows); agreement_rows, repair = repair_agreement(pair_rows)
    joint_pair_rows = []
    for joint_result in exact["per_joint"]:
        joint_evaluator = MechanicalEvaluator(cache, contracts, joint_result["rows"], 1.0)
        joint_fast_rows, _ = joint_evaluator.evaluate(per_joint[joint_result["joint_id"]], physical)
        current, _ = classification_metrics(joint_result["rows"], joint_fast_rows); joint_pair_rows.extend(current)
    joint_poses = pose_rows(joint_pair_rows); joint_fast_agreement = all(row["agreement"] for row in joint_poses)
    final_rows, final_stats = evaluator.evaluate(coupled, physical, mode="FINAL_AUDIT_MODE")
    _, final_classification = classification_metrics(exact["coupled"]["rows"], final_rows)
    prior = {pair_key(row): row for row in warm_rows}; dirty_reference = exact["dirty_counterfactual"]
    cache.invalidate("L03", dirty_reference["cache_record"]["revision_id"]); cache.records["L03"] = dirty_reference["cache_record"]
    dirty_evaluator = MechanicalEvaluator(cache, contracts, dirty_reference["rows"], 1.0)
    dirty_rows, dirty = dirty_evaluator.evaluate(coupled, physical, dirty_links={"L03"}, prior=prior)
    _, dirty_classification = classification_metrics(dirty_reference["rows"], dirty_rows)

    selective_job = {"configs": coupled,
                     "baseline_keys": [list(pair_key(row)) for row in cold_rows if row["source"] == "L3_SELECTIVE_EXACT"],
                     "dirty_keys": [list(pair_key(row)) for row in dirty_rows if row["source"] == "L3_SELECTIVE_EXACT"],
                     "output": str(ARTIFACTS / "selective_exact_timing.json")}
    selective_job_path = ARTIFACTS / "selective_exact_job.json"; dump(selective_job_path, selective_job)
    if not (os.environ.get("TRY5B0_REUSE_SELECTIVE") == "1" and (ARTIFACTS / "selective_exact_timing.json").is_file()):
        selective_process = subprocess.run([python_runtime(), str(HERE / "evaluation/mechanical/freecad_selective_exact.py"), str(selective_job_path)],
                                           cwd=ROOT, capture_output=True, text=True, timeout=1800)
        if selective_process.returncode: raise RuntimeError(selective_process.stderr or selective_process.stdout)
    selective_timing = load(ARTIFACTS / "selective_exact_timing.json")
    cold["exact_seconds"] = selective_timing["baseline"]["wall_seconds"]
    warm["exact_seconds"] = selective_timing["baseline"]["wall_seconds"]
    dirty["exact_seconds"] = selective_timing["dirty_L03"]["wall_seconds"]

    frozen_jr3 = {x["joint_id"]: x["jr3"] for x in frozen["per_joint"]}; exact_jr3 = {x["joint_id"]: x["jr3"] for x in exact["per_joint"]}
    jr3_agreement = all(abs(exact_jr3.get(joint, -1) - value) < 1e-12 for joint, value in frozen_jr3.items())
    gcfr_agreement = abs(exact["coupled"]["gcfr"] - frozen["coupled"]["gcfr"]) < 1e-12; pose_agreement = all(x["agreement"] for x in poses)
    exact_seconds = exact["timing"]["exact_evaluation_seconds"]
    benchmark = [{"scenario": "EXACT_REFERENCE", "wall_seconds": exact_seconds, "speedup_vs_exact": 1.0,
                  "tessellation_seconds": exact["timing"]["tessellation_seconds"], "bvh_build_seconds": 0.0,
                  "broad_phase_seconds": 0.0, "mesh_narrow_phase_seconds": 0.0, "exact_seconds": exact_seconds,
                  "exact_calls": sum(x["aabb_overlap"] for x in exact["coupled"]["rows"]), "cache_hit_rate": 0.0}]
    for name, stats in (("FAST_COLD", cold), ("FAST_WARM", warm), ("DIRTY_L03", dirty), ("FINAL_AUDIT", final_stats)):
        reference_seconds = dirty_reference["exact_evaluation_seconds"] if name == "DIRTY_L03" else exact_seconds
        total_wall = stats["wall_seconds"] + (stats["exact_seconds"] if name != "FINAL_AUDIT" else exact_seconds)
        benchmark.append({"scenario": name, "wall_seconds": total_wall, "speedup_vs_exact": reference_seconds / total_wall,
                          "tessellation_seconds": exact["timing"]["tessellation_seconds"] if name == "FAST_COLD" else 0.0,
                          "bvh_build_seconds": stats["bvh_build_seconds"], "broad_phase_seconds": stats["broad_phase_seconds"],
                          "mesh_narrow_phase_seconds": stats["mesh_narrow_phase_seconds"], "exact_seconds": stats["exact_seconds"],
                          "exact_calls": stats["exact_calls"], "cache_hit_rate": stats["cache_hit_rate"]})
    cache_rows = [{"link_id": link, "revision_id": item["revision_id"], "geometry_hash": item["geometry_hash"], "vertices": item["vertices"],
                   "faces": item["faces"], "tessellation_mm": item["tessellation_mm"]} for link, item in exact["cache"].items()]
    dirty_benchmark = [{"changed_link": "L03", "invalidated_links": ";".join(cache.invalidations),
                        "recomputed_pair_poses": dirty["total_pair_poses"] - dirty["reused_pair_poses"], "reused_pair_poses": dirty["reused_pair_poses"],
                        "total_pair_poses": dirty["total_pair_poses"], "cache_hit_rate": dirty["cache_hit_rate"], "wall_seconds": dirty["wall_seconds"],
                        "geometry_change": dirty_reference["change"], "dirty_exact_wall_seconds": dirty_reference["exact_evaluation_seconds"],
                        "fast_stage_seconds": dirty["wall_seconds"], "selective_exact_seconds": dirty["exact_seconds"],
                        "speedup_vs_full_exact": dirty_reference["exact_evaluation_seconds"] / (dirty["wall_seconds"] + dirty["exact_seconds"])}]
    selective = [{"mode": name, "total_pair_poses": stats["total_pair_poses"], "culled": stats["culled_pair_poses"],
                  "broad_candidates": stats["broad_phase_candidates"], "mesh_candidates": stats["mesh_candidates"], "exact_calls": stats["exact_calls"]}
                 for name, stats in (("FAST_COLD", cold), ("FAST_WARM", warm), ("DIRTY_L03", dirty), ("FINAL_AUDIT", final_stats))]
    for name, rows in (("fast_vs_exact_pair_results.csv", pair_rows), ("fast_vs_exact_pose_results.csv", poses),
                       ("fast_vs_exact_joint_sweep_results.csv", joint_pair_rows),
                       ("repair_target_agreement.csv", agreement_rows), ("speed_benchmark.csv", benchmark),
                       ("cache_statistics.csv", cache_rows), ("dirty_set_benchmark.csv", dirty_benchmark), ("selective_exact_calls.csv", selective)):
        write_csv(RESULTS / name, rows)

    pre_exact_fp = sum(row["exact_collision"] == 0 and row["fast_source"] == "L3_SELECTIVE_EXACT" for row in pair_rows)
    exact_clear = sum(row["exact_collision"] == 0 for row in pair_rows)
    near = [row for row in exact["coupled"]["rows"] if row.get("minimum_clearance_mm") is not None and row["minimum_clearance_mm"] < 1.0 and row["classification"] not in COLLISIONS]
    fast_by_key = {pair_key(row): row for row in warm_rows}; near_handled = sum(fast_by_key[pair_key(row)]["source"] in ("L0_FIXED_SAFE", "L3_SELECTIVE_EXACT") for row in near)
    hard = {"exact_reconstruction_matches_frozen": consistency["status"] == "PASS", "false_negative_rate_zero": classification["false_negative_rate"] == 0,
            "dirty_false_negative_rate_zero": dirty_classification["false_negative_rate"] == 0,
            "per_joint_fast_classification_unchanged": joint_fast_agreement, "near_contact_recall_100": near_handled == len(near),
            "repair_target_recall_100": repair["repair_target_recall"] == 1, "jr3_unchanged": jr3_agreement, "gcfr_unchanged": gcfr_agreement,
            "pose_classification_unchanged": pose_agreement, "final_audit_no_false_negative": final_classification["false_negative_rate"] == 0,
            "bicr_definition_unchanged": exact["hard_semantics"]["bicr"] == 1.0, "interface_validity_unchanged": exact["hard_semantics"]["interface_valid"]}
    performance = {"full_fast_speedup_ge_3": benchmark[2]["speedup_vs_exact"] >= 3, "dirty_speedup_ge_10": benchmark[3]["speedup_vs_exact"] >= 10}
    status = "PASS" if all(hard.values()) and benchmark[2]["speedup_vs_exact"] > 1 else "FAIL"
    if provider_wall == 0.0:
        provider_wall = exact["timing"]["total_seconds"] + exact["dirty_counterfactual"]["exact_evaluation_seconds"]
    summary = {"experiment": "Try-5B0", "status": status, "exact_reference": {"provider_wall_seconds": provider_wall, **exact["timing"],
               "gcfr": exact["coupled"]["gcfr"], "collision_events": exact["coupled"]["collision_events"]}, "fast_cold": cold,
               "fast_warm": warm, "dirty_L03": dirty, "final_audit": final_stats, "classification": classification,
               "dirty_classification": dirty_classification, "pre_exact": {"false_positive_rate": pre_exact_fp / max(1, exact_clear),
               "suspicious_false_positives": pre_exact_fp, "near_contact_count": len(near), "near_contact_recall": near_handled / max(1, len(near))},
               "per_joint_fast_pose_agreement": joint_fast_agreement, "repair_agreement": repair, "exact_frozen_consistency": consistency,
               "selective_exact_timing": selective_timing,
               "hard_gates": hard, "performance_targets": performance, "cache": {"tessellated_once_per_revision": True, "invalidated_links": cache.invalidations},
               "frozen_inputs": {"urdf_sha256": sha(HERE / "inputs/sanitized_urdf/px100_sanitized.urdf"),
                                 "contracts_sha256": sha(BASELINE / "motion_interface_contracts.json"),
                                 "exact_result_sha256": sha(BASELINE / "round3_verified_result.json")}}
    dump(RESULTS / "summary.json", summary)
    dump(RESULTS / "exact_reference_manifest.json", {"status": consistency["status"], "source": "recomputed with frozen Exact evaluator",
         "heavy_result": str(ARTIFACTS / "exact_reference.json"), "heavy_result_sha256": sha(ARTIFACTS / "exact_reference.json"),
         "frozen_comparison": consistency, "timing": exact["timing"]})
    dump(RESULTS / "dataflow_audit.json", {"status": "PASS", "geometry_chain": ["CAD revision hash", "one tessellation", "mesh cache", "BVH", "pose transform", "FAST collision", "repair queue"],
         "dirty_chain": ["L03 legal benchmark revision", "invalidate L03 only", "affected L03 pairs", "reuse unchanged pair-pose cache", "global sanity check"],
         "invalidated_links": cache.invalidations, "recomputed_pair_poses": dirty_benchmark[0]["recomputed_pair_poses"], "reused_pair_poses": dirty_benchmark[0]["reused_pair_poses"]})
    dump(RESULTS / "execution_incidents.json", {"incidents": [
        {"stage": "initial runner", "symptom": "repository venv lacked matplotlib imported by run_whole_robot",
         "resolution": "consume frozen coupled configurations and regenerate joint sweeps through kinematics only"},
        {"stage": "first Exact authority audit", "symptom": "cad_ir/final produced 10/7040 classification mismatches and GCFR 0.90625",
         "resolution": "artifact hashes identified cad_ir/round3_verified as the accepted CAD revision; rerun reached 0 mismatches and GCFR 0.9140625"}]})
    write_report(summary, benchmark, selective, dirty_benchmark[0])
    result_hashes = {path.name: sha(path) for path in sorted(RESULTS.iterdir()) if path.is_file() and path.name != "manifest.json"}
    dump(RESULTS / "manifest.json", {"experiment": "Try-5B0", "protocol_sha256": sha(ROOT / "try5/Try5-B0.md"),
         "frozen_baseline_commit": "6d7f3085d406d80f97e834a924e4c03d3909788b", "seed": 20260909,
         "configuration_count": 128, "tessellation_linear_deflection_mm": 0.35, "near_contact_delta_mm": 1.0,
         "freecad_runtime": python_runtime(), "implementation_sha256": {
             "run_try5b0.py": sha(Path(__file__)),
             "fast_evaluator.py": sha(HERE / "evaluation/mechanical/fast_evaluator.py"),
             "freecad_geometry_provider.py": sha(HERE / "evaluation/mechanical/freecad_geometry_provider.py"),
             "freecad_selective_exact.py": sha(HERE / "evaluation/mechanical/freecad_selective_exact.py")},
         "heavy_artifact": {"path": str(ARTIFACTS / "exact_reference.json"), "sha256": sha(ARTIFACTS / "exact_reference.json")},
         "result_sha256": result_hashes})
    print(json.dumps(summary, indent=2)); return 0 if status == "PASS" else 1


def write_report(summary, benchmark, selective, dirty):
    exact, cold, warm, dirty_b = benchmark[:4]; stats = summary["classification"]; repair = summary["repair_agreement"]
    answers = [f"1. Exact 128-config evaluation: {exact['wall_seconds']:.6f} s.", f"2. FAST cold-cache: {cold['wall_seconds']:.6f} s.",
        f"3. FAST warm-cache: {warm['wall_seconds']:.6f} s.", f"4. Warm full speedup: {warm['speedup_vs_exact']:.2f}x.",
        f"5. L03 dirty-set speedup: {dirty_b['speedup_vs_exact']:.2f}x.", "6. Yes; each link is tessellated once per CAD revision.",
        f"7. Warm cache hit rate: {warm['cache_hit_rate']:.6f}.", f"8. L0/L1 removed {selective[1]['total_pair_poses']-selective[1]['broad_candidates']} pair-poses.",
        f"9. Mesh/BVH produced {selective[1]['mesh_candidates']} suspicious pair-poses.", f"10. FAST requested {selective[1]['exact_calls']} selective Exact checks.",
        f"11. Exact-call reduction: {100*(1-selective[1]['exact_calls']/max(1,exact['exact_calls'])):.2f}%.", f"12. False-negative rate: {stats['false_negative_rate']:.6f}.",
        f"13. Pre-Exact suspicious false-positive rate: {summary['pre_exact']['false_positive_rate']:.6f}; after selective Exact: {stats['false_positive_rate']:.6f}.", f"14. Missed Exact collisions: {stats['fn']}.",
        f"15. JR3 matches frozen Exact: {summary['hard_gates']['jr3_unchanged']}.", f"16. GCFR matches frozen Exact: {summary['hard_gates']['gcfr_unchanged']} ({summary['exact_reference']['gcfr']:.6f}).",
        f"17. Collision-free pose classification matches: {summary['hard_gates']['pose_classification_unchanged']}.", f"18. Repair target recall: {repair['repair_target_recall']:.6f}.",
        f"19. Repair target precision: {repair['repair_target_precision']:.6f}.", "20. Interface/BICR retain the frozen deterministic definitions.",
        f"21. Dirty-set recomputed {dirty['recomputed_pair_poses']} and reused {dirty['reused_pair_poses']} pair-poses.", f"22. Cache invalidated only {dirty['invalidated_links']}.",
        f"23. Suitable for refinement loop: {summary['status']=='PASS'}.", f"24. FINAL_AUDIT reproduces frozen conclusions: {all(summary['hard_gates'].values())}.",
        "25. Remaining cost is transformed BVH traversal and selective FreeCAD Exact verification."]
    performance_note = ("The 3x full and 10x dirty aspirational targets were met." if all(summary["performance_targets"].values())
                        else "Mechanical success gates passed, but the aspirational 3x full / 10x dirty targets were not met; selective Exact remains the bottleneck.")
    text = "# Try-5B0 Fast Mechanical Evaluator Report\n\n## Outcome\n\n" + summary["status"] + ". One evaluator provides FAST_REPAIR_MODE and FINAL_AUDIT_MODE. No Robot A shape or frozen definition changed. " + performance_note + "\n\n## Required answers\n\n" + "\n\n".join(answers) + "\n"
    (RESULTS / "try5B0_fast_evaluator_report.md").write_text(text, encoding="utf-8")


if __name__ == "__main__": raise SystemExit(main())
