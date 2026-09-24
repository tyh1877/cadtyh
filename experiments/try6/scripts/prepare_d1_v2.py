"""Fail-closed D1-v2 preregistration against frozen D1 science and T0 semantics."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RESULT = ROOT / "experiments/try6/results/try6_0_d1_v2"
V2 = ROOT / "experiments/try6/protocol/try6_0_d1_v2.json"


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(relative, data):
    target = RESULT / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main():
    if Path(sys.executable).resolve() != (ROOT / ".venv/Scripts/python.exe").resolve():
        raise RuntimeError("repository .venv required")
    if RESULT.exists():
        raise FileExistsError("D1-v2 already prepared; no silent rerun")
    v2 = read(V2)
    d1 = read(ROOT / v2["science_protocol"])
    t0 = read(ROOT / v2["technical_semantics"])
    if v2["scientific_amendments"] or d1["kfde_numerical_epsilon_mm3"] != t0["numerical_tolerance_mm3"]:
        raise RuntimeError("scientific protocol/tolerance drift")
    t0_result = read(ROOT / "experiments/try6/results/try6_0_d1_t0/audit/independent_validation.json")
    if t0_result["decision"] != "READY_FOR_D1_V2":
        raise RuntimeError("T0 technical readiness missing")
    prior = {}
    for name in ("try6_0_c1_v2", "try6_0_c2", "try6_0_d0", "try6_0_d1"):
        folder = ROOT / "experiments/try6/results" / name
        manifest = read(folder / "manifest.json")
        if not all(sha(folder / p) == digest for p, digest in manifest["result_file_sha256"].items()):
            raise RuntimeError("frozen prior changed: " + name)
        prior[name] = sha(folder / "manifest.json")
    prior["try6_0_d1_t0"] = sha(ROOT / "experiments/try6/results/try6_0_d1_t0/manifest.json")
    frozen = read(ROOT / "experiments/try6/results/try6_0_d1/frozen_inputs/geometry_set.json")
    construction = read(ROOT / d1["kfde_construction"])
    if len(frozen["geometries"]) != 5 or len(construction["components"]) != 13:
        raise RuntimeError("5x13 frozen case set drift")
    if any(sha(ROOT / x["source_path"]) != x["source_sha256"] or
           sha(ROOT / x["full_brep_path"]) != x["full_brep_sha256"] or
           sha(ROOT / x["mutable_brep_path"]) != x["mutable_brep_sha256"] for x in frozen["geometries"]):
        raise RuntimeError("frozen geometry BREP/source drift")
    if sha(ROOT / construction["allowed_region"]["path"]) != construction["allowed_region"]["sha256"]:
        raise RuntimeError("frozen allowed BREP drift")
    if sha(ROOT / construction["keepout"]["path"]) != construction["keepout"]["sha256"]:
        raise RuntimeError("frozen keepout BREP drift")
    if any(sha(ROOT / x["brep_path"]) != x["brep_sha256"] for x in construction["components"]):
        raise RuntimeError("frozen component BREP drift")
    lock_path = ROOT / "experiments/try5A/results/try5b1_a1_frozen_scaffold/formal_holdout_lock.json"
    lock = read(lock_path)
    if lock["accessed"] is not False or lock["evaluation_count"] != 0:
        raise RuntimeError("holdout lock violated")
    source_hashes = {x["geometry_id"]: x["source_sha256"] for x in frozen["geometries"]}
    component_hashes = {x["component_id"]: x["brep_sha256"] for x in construction["components"]}
    mapping = [{"component_id": x["component_id"], "link_id": x["link_id"],
                "joint_id": x["joint_id"], "q_rad": x["q_rad"],
                "relative_transform_L04": x["relative_transform_L04"]} for x in construction["components"]]
    mapping_hash = hashlib.sha256(json.dumps(mapping, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True,
                          text=True, check=True).stdout.strip()
    save("protocol.json", d1)
    save("experiment_config_snapshot.json", v2)
    save("case_split.json", {"development_geometry_ids": list(source_hashes),
         "KFDE_component_ids": list(component_hashes), "alignment_case_count": 65,
         "witness_subsets": d1["witness_subsets"], "formal_holdout_case_count": 32,
         "formal_holdout_ids_not_read": True, "accessed": False, "evaluation_count": 0})
    save("condition_parity.json", {"scientific_protocol_unchanged": True,
         "technical_difference_only": "T0 empty BREP classification/safe Boolean", "status": "PASS"})
    save("frozen_inputs/geometry_set.json", frozen)
    save("frozen_inputs/kfde_reference.json", {"construction_report_path": d1["kfde_construction"],
         "construction_report_sha256": sha(ROOT / d1["kfde_construction"]),
         "component_hashes": component_hashes,
         "allowed_contact_sha256": construction["allowed_region"]["sha256"],
         "keepout_sha256": construction["keepout"]["sha256"]})
    save("frozen_inputs/source_hashes.json", source_hashes)
    save("frozen_inputs/exact_mechanics_reference.json", {"source": d1["exact_mechanics_source"],
         "sha256": sha(ROOT / d1["exact_mechanics_source"]),
         "URDF_sha256": sha(ROOT / d1["sanitized_urdf"]),
         "interface_contract_sha256": sha(ROOT / d1["interface_contracts"])})
    save("frozen_inputs/pose_mapping.json", {"mapping": mapping, "canonical_sha256": mapping_hash})
    save("frozen_inputs/parity_audit.json", {"status": "PASS", "frozen_manifest_hashes": prior,
         "geometry_source_hashes": source_hashes, "component_hashes": component_hashes,
         "pose_mapping_sha256": mapping_hash, "same_frozen_D1_protocol": True,
         "only_T0_empty_handling_changed": True, "formal_holdout_accessed": False})
    save("holdout_evaluation_log.json", {"events": [], "accessed": False,
         "evaluation_count": 0, "followed_by_tuning": False})
    save("pre_run_manifest.json", {"created_utc": datetime.now(timezone.utc).isoformat(),
         "starting_commit": head, "v2_config_sha256": sha(V2),
         "frozen_D1_protocol_sha256": sha(ROOT / v2["science_protocol"]),
         "T0_protocol_sha256": sha(ROOT / v2["technical_semantics"]),
         "T0_classifier_sha256": sha(ROOT / "experiments/try6/scripts/volumetric_geometry_state.py"),
         "source_hashes": source_hashes, "component_hashes": component_hashes,
         "KFDE_sha256": sha(ROOT / d1["kfde_construction"]),
         "exact_mechanics_sha256": sha(ROOT / d1["exact_mechanics_source"]),
         "URDF_sha256": sha(ROOT / d1["sanitized_urdf"]),
         "pose_mapping_sha256": mapping_hash,
         "allowed_contact_sha256": construction["allowed_region"]["sha256"],
         "tolerance_policy_sha256": sha(ROOT / "experiments/try6/results/try6_0_c2/kfde/tolerance_policy.json"),
         "witness_configuration_sha256": sha(ROOT / v2["science_protocol"]),
         "formal_holdout_lock_sha256": sha(lock_path), "python_environment": sys.executable,
         "VLM_calls": 0, "GT_evaluations": 0, "final_96_case_mechanics_evaluations": 0})
    print(json.dumps({"status": "READY_FOR_65_ROW_RUN", "cases": 65,
                      "witness_subsets": len(d1["witness_subsets"])}))


if __name__ == "__main__":
    main()
