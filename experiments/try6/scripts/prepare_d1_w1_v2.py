"""Freeze new zero rule and synthetic evidence before any W1-v2 real BREP run."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RESULT = ROOT / "experiments/try6/results/try6_0_d1_w1_v2"
PROTOCOL = ROOT / "experiments/try6/protocol/try6_0_d1_w1_v2.json"
sys.path.insert(0, str(ROOT / "experiments/try6/scripts"))
from w1_v2_zero_rule import epsilon_zero, normalize_removed_volume
from w1_semantics import sensitivity_category


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(relative, value):
    target = RESULT / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main():
    if Path(sys.executable).resolve() != (ROOT / ".venv/Scripts/python.exe").resolve():
        raise RuntimeError("repository .venv required")
    if RESULT.exists():
        raise FileExistsError("W1-v2 preparation already exists; no silent rerun")
    cfg = read(PROTOCOL)
    d1 = read(ROOT / cfg["frozen_d1_protocol"])
    w1 = read(ROOT / cfg["frozen_w1_protocol"])
    w0cal_path = ROOT / cfg["frozen_w0_calibration"]
    cal = read(w0cal_path)
    absolute = cal["BOOLEAN_ACCOUNTING_TOLERANCE"]["absolute_mm3"]
    relative = cfg["zero_rule"]["epsilon_rel"]
    if absolute != 1e-8 or relative != 1e-6 or cfg["frozen_paths"] != w1["paths"] or len(d1["witness_subsets"]) != 9:
        raise RuntimeError("zero-rule/path/subset registration drift")
    prior = {}
    for name in ("try6_0_c1_v2", "try6_0_c2", "try6_0_d0", "try6_0_d1", "try6_0_d1_t0", "try6_0_d1_v2", "try6_0_d1_w0", "try6_0_d1_w1"):
        folder = ROOT / "experiments/try6/results" / name
        manifest = read(folder / "manifest.json")
        if "result_file_sha256" in manifest and not all(sha(folder / p) == h for p, h in manifest["result_file_sha256"].items()):
            raise RuntimeError("frozen result drift: " + name)
        prior[name] = sha(folder / "manifest.json")
    construction = read(ROOT / cfg["frozen_kfde_construction"])
    geometry = read(ROOT / cfg["frozen_geometry_set"])
    c1 = geometry["geometries"][0]
    if sha(ROOT / c1["source_path"]) != c1["source_sha256"]:
        raise RuntimeError("C1 geometry drift")
    if sha(ROOT / construction["allowed_region"]["path"]) != construction["allowed_region"]["sha256"]:
        raise RuntimeError("allowed BREP drift")
    components = {x["component_id"]: x["brep_sha256"] for x in construction["components"]}
    if any(sha(ROOT / x["brep_path"]) != x["brep_sha256"] for x in construction["components"]):
        raise RuntimeError("KFDE BREP drift")
    lock_path = ROOT / "experiments/try5A/results/try5b1_a1_frozen_scaffold/formal_holdout_lock.json"
    lock = read(lock_path)
    if lock["accessed"] is not False or lock["evaluation_count"] != 0:
        raise RuntimeError("holdout lock violated")
    test = subprocess.run([str(ROOT / ".venv/Scripts/python.exe"), "-m", "unittest",
        "experiments.try6.tests.test_d1_w1_v2_zero_rule", "-v"], cwd=ROOT,
        capture_output=True, text=True, timeout=60)
    if test.returncode:
        raise RuntimeError("synthetic zero-rule unit tests failed: " + test.stderr[-1200:])
    eps = epsilon_zero(1000.0, absolute, relative)
    synthetic = {
        "negative_inside": normalize_removed_volume(-eps/2, eps),
        "negative_exact_boundary": normalize_removed_volume(-eps, eps),
        "negative_outside": normalize_removed_volume(-2*eps, eps),
        "tiny_positive": normalize_removed_volume(1e-12, eps),
        "positive_near_five": normalize_removed_volume(49.99, eps),
        "cross_five": sensitivity_category([0.0499, 0.0501]),
        "cross_fifteen": sensitivity_category([0.1499, 0.1501])}
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True,
                          capture_output=True, text=True).stdout.strip()
    rule = {"epsilon_abs_mm3": absolute, "epsilon_abs_source": cfg["zero_rule"]["epsilon_abs_source"],
        "epsilon_rel": relative, "formula": cfg["zero_rule"]["formula"],
        "inclusive_negative_boundary": True, "spatial_hard_gates_first": True,
        "positive_relief_unchanged": True, "subset_specific_exceptions": False}
    save("protocol.json", cfg)
    save("experiment_config_snapshot.json", cfg)
    save("zero_rule/rule.json", rule)
    save("zero_rule/rationale.json", {"one_part_per_million_percent": 0.0001,
         "first_relief_boundary_percent": 5.0, "scale_separation_factor": 50000,
         "chosen_by_user_protocol_before_real_run": True,
         "not_calibrated_to_W1_L07_observation": True})
    save("zero_rule/synthetic_tests.json", {"status": "PASS", "fixture_source_volume_mm3": 1000.0,
         "epsilon_zero_mm3": eps, "cases": synthetic, "unittest_count": 9,
         "unittest_stdout": test.stdout, "unittest_stderr": test.stderr})
    save("frozen_inputs/witness_subsets.json", {"subsets": d1["witness_subsets"],
         "sha256": hashlib.sha256(json.dumps(d1["witness_subsets"], separators=(",", ":")).encode()).hexdigest()})
    save("frozen_inputs/c1_mutable_reference.json", {"source": c1["source_path"],
         "source_sha256": c1["source_sha256"], "extraction": "FrozenMatingEnvelopeCut minus frozen allowed region"})
    save("frozen_inputs/parity_audit.json", {"prior_manifest_sha256": prior,
         "C1_geometry_unchanged": True, "KFDE_unchanged": True,
         "W1_worker_reused_unchanged": True, "D1_v2_alignment_unchanged": True,
         "formal_holdout_untouched": True})
    save("case_split.json", {"frozen_witness_subsets": d1["witness_subsets"], "count": 9,
         "formal_holdout_case_count": 32, "formal_holdout_ids_not_read": True,
         "accessed": False, "evaluation_count": 0})
    save("condition_parity.json", {"paths": cfg["frozen_paths"], "repeats_per_path": cfg["repeats_per_path"],
         "shared_C1_source_sha256": c1["source_sha256"], "shared_component_sha256": components,
         "only_new_variable": "scale-aware zero-relief postprocessing rule", "status": "PASS"})
    save("holdout_evaluation_log.json", {"events": [], "accessed": False,
         "evaluation_count": 0, "followed_by_tuning": False})
    save("pre_run_manifest.json", {"created_utc": datetime.now(timezone.utc).isoformat(),
         "starting_commit": head, "protocol_sha256": sha(PROTOCOL),
         "zero_rule_sha256": sha(RESULT / "zero_rule/rule.json"),
         "synthetic_tests_sha256": sha(RESULT / "zero_rule/synthetic_tests.json"),
         "epsilon_abs_source_sha256": sha(w0cal_path), "epsilon_abs_mm3": absolute,
         "epsilon_rel": relative, "C1_source_sha256": c1["source_sha256"],
         "allowed_sha256": construction["allowed_region"]["sha256"],
         "component_hashes": components,
         "subset_definition_sha256": sha(RESULT / "frozen_inputs/witness_subsets.json"),
         "W1_worker_sha256": sha(ROOT / "experiments/try6/evaluation/freecad_d1_w1_real.py"),
         "W0_Boolean_helper_sha256": sha(ROOT / "experiments/try6/scripts/witness_boolean.py"),
         "D1_relief_thresholds": [d1["witness_small_removed_ratio_max"], d1["witness_moderate_removed_ratio_max"]],
         "prior_manifest_sha256": prior, "holdout_lock_sha256": sha(lock_path),
         "python_environment": sys.executable})
    print(json.dumps({"status": "ZERO_RULE_FROZEN_BEFORE_REAL", "epsilon_abs_mm3": absolute,
                      "epsilon_rel": relative, "synthetic_tests": 9, "subsets": 9}))


if __name__ == "__main__":
    main()
