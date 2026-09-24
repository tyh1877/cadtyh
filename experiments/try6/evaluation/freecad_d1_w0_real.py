"""Nine-subset exact-BREP technical audit; no relief or alignment science."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import FreeCAD as App
import Part

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "experiments/try6/scripts"))
from volumetric_geometry_state import safe_diagnostic_cut
from witness_boolean import (accounting_limit, build_clearance_witness, exact_union,
    optional_splitter_cleanup, volumetric_state)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def bbox(shape):
    if not shape.Solids:
        return None
    b = shape.BoundBox
    return [b.XMin, b.YMin, b.ZMin, b.XMax, b.YMax, b.ZMax]


def parity(before, after, limit):
    b1, b2 = bbox(before), bbox(after)
    bd = max(abs(a-b) for a, b in zip(b1, b2)) if b1 is not None and b2 is not None else 0.0 if b1 == b2 else float("inf")
    s1, s2 = volumetric_state(before, derived=True), volumetric_state(after, derived=True)
    return {"state_before": s1.state, "state_after": s2.state,
        "solids_before": s1.solid_count, "solids_after": s2.solid_count,
        "volume_delta_mm3": s2.volume_mm3-s1.volume_mm3, "bbox_delta_mm": bd,
        "pass": s1.state == s2.state and s1.solid_count == s2.solid_count and
                abs(s2.volume_mm3-s1.volume_mm3) <= limit and bd <= 1e-7}


def main(job):
    cfg = read(ROOT / job["protocol"])
    d1 = read(ROOT / cfg["frozen_d1_protocol"])
    calibration = read(ROOT / job["calibration"])
    pre = read(ROOT / job["pre_real_manifest"])
    if calibration["status"] != "PASS" or sha(ROOT / job["calibration"]) != pre["calibration_sha256"]:
        raise RuntimeError("synthetic tolerance not frozen")
    policy = calibration["BOOLEAN_ACCOUNTING_TOLERANCE"]
    construction = read(ROOT / cfg["frozen_kfde_construction"])
    geometry = read(ROOT / cfg["frozen_geometry_set"])
    source_path = ROOT / geometry["geometries"][0]["source_path"]
    if sha(source_path) != pre["C1_source_sha256"]:
        raise RuntimeError("frozen C1 source drift")
    allowed_path = ROOT / construction["allowed_region"]["path"]
    if sha(allowed_path) != pre["allowed_region_sha256"]:
        raise RuntimeError("allowed BREP drift")
    components = []
    for item in construction["components"]:
        path = ROOT / item["brep_path"]
        if sha(path) != pre["component_sha256"][item["component_id"]]:
            raise RuntimeError("component BREP drift: " + item["component_id"])
        shape = Part.read(str(path))
        volumetric_state(shape)
        components.append((item, shape))
    doc = App.openDocument(str(source_path))
    source_obj = doc.getObject("FrozenMatingEnvelopeCut")
    if source_obj is None:
        raise RuntimeError("frozen C1 mutable source missing")
    source = source_obj.Shape.copy()
    frozen_names = ("FrozenScaffold", "FrozenProximalBoreTool", "FrozenMatingEnvelopeTool")
    frozen_shapes = {name: doc.getObject(name).Shape.copy() for name in frozen_names}
    App.closeDocument(doc.Name)
    artifact = ROOT / job["artifact_root"]
    artifact.mkdir(parents=True, exist_ok=True)
    # Exact source/allowed subtraction is the frozen D1 mutable definition.
    mutable, _ = safe_diagnostic_cut(source, Part.read(str(allowed_path)))
    mutable_state = volumetric_state(mutable, derived=True)
    frozen_signatures = {}
    for name, shape in frozen_shapes.items():
        path = artifact / "frozen_signatures" / (name + ".brep")
        path.parent.mkdir(parents=True, exist_ok=True)
        shape.exportBrep(str(path))
        frozen_signatures[name] = {"sha256": sha(path), "state": volumetric_state(shape).record()}
    union_rows, path_rows, summary = [], [], []
    status = "PASS"
    failure = None
    for subset in d1["witness_subsets"]:
        selected_links = {"L03", "L05", "L06", "L07"} if subset == "FULL" else set(subset.split("_"))
        selected = [(item, shape) for item, shape in components if item["link_id"] in selected_links]
        try:
            union, union_trace = exact_union([shape for _, shape in selected])
            union_state = volumetric_state(union)
            subset_dir = artifact / subset
            subset_dir.mkdir(parents=True, exist_ok=True)
            union_path = subset_dir / "keepout_union.brep"
            union.exportBrep(str(union_path))
            reopened_union = Part.read(str(union_path))
            union_check = parity(union, reopened_union, accounting_limit(policy, mutable_state.volume_mm3))
            union_row = {"subset": subset, "component_ids": [x["component_id"] for x, _ in selected],
                "component_hashes": [x["brep_sha256"] for x, _ in selected],
                "component_count": len(selected), "union_state": union_state.record(),
                "union_trace": union_trace, "union_brep_path": str(union_path.relative_to(ROOT)).replace("\\", "/"),
                "union_brep_sha256": sha(union_path), "serialization": union_check,
                "valid": union_state.is_valid and union_check["pass"]}
            union_rows.append(union_row)
            if not union_row["valid"]:
                raise RuntimeError("KEEPOUT_UNION_BLOCKED")
            repeated = {}
            for path_name in cfg["candidate_paths"]:
                current_rows = []
                for repeat in range(2):
                    witness, removed, _, metrics = build_clearance_witness(
                        mutable, [shape for _, shape in selected], policy, path=path_name)
                    witness_path = subset_dir / f"{path_name}_{repeat}.brep"
                    witness.exportBrep(str(witness_path))
                    reopened = Part.read(str(witness_path))
                    witness_parity = parity(witness, reopened, metrics["accounting_limit_mm3"])
                    # FCStd round-trip is an independent FreeCAD container path.
                    fcstd_path = subset_dir / f"{path_name}_{repeat}.FCStd"
                    temporary = App.newDocument("W0_" + subset + "_" + str(repeat))
                    obj = temporary.addObject("Part::Feature", "DiagnosticWitness")
                    obj.Shape = witness
                    temporary.saveAs(str(fcstd_path))
                    App.closeDocument(temporary.Name)
                    reopened_doc = App.openDocument(str(fcstd_path))
                    fcstd_shape = reopened_doc.getObject("DiagnosticWitness").Shape.copy()
                    App.closeDocument(reopened_doc.Name)
                    fcstd_parity = parity(witness, fcstd_shape, metrics["accounting_limit_mm3"])
                    refined, cleanup_status = optional_splitter_cleanup(witness) if witness.Solids else (None, "EMPTY_NOT_CLEANED")
                    cleanup_delta = (refined.Volume-witness.Volume if refined is not None else None)
                    row = {"subset": subset, "path": path_name, "repeat": repeat, "metrics": metrics,
                        "BREP_parity": witness_parity, "FCStd_parity": fcstd_parity,
                        "cleanup_status": cleanup_status, "cleanup_volume_delta_mm3": cleanup_delta,
                        "witness_brep_path": str(witness_path.relative_to(ROOT)).replace("\\", "/"),
                        "witness_brep_sha256": sha(witness_path),
                        "witness_FCStd_path": str(fcstd_path.relative_to(ROOT)).replace("\\", "/"),
                        "witness_FCStd_sha256": sha(fcstd_path),
                        "technical_pass": metrics["invariants_pass"] and witness_parity["pass"] and fcstd_parity["pass"]}
                    current_rows.append(row)
                    path_rows.append(row)
                repeated[path_name] = current_rows
            canonical = repeated["UNION_THEN_SINGLE_CUT"]
            alternative = repeated["ORDERED_SEQUENTIAL_CUT"]
            canonical_repeat = (canonical[0]["metrics"]["witness_state"]["state"] == canonical[1]["metrics"]["witness_state"]["state"] and
                canonical[0]["metrics"]["witness_state"]["solid_count"] == canonical[1]["metrics"]["witness_state"]["solid_count"] and
                abs(canonical[0]["metrics"]["witness_volume_mm3"]-canonical[1]["metrics"]["witness_volume_mm3"]) <= canonical[0]["metrics"]["accounting_limit_mm3"])
            path_parity = (canonical[0]["metrics"]["witness_state"]["state"] == alternative[0]["metrics"]["witness_state"]["state"] and
                abs(canonical[0]["metrics"]["witness_volume_mm3"]-alternative[0]["metrics"]["witness_volume_mm3"]) <= canonical[0]["metrics"]["accounting_limit_mm3"])
            technical_pass = all(x["technical_pass"] for x in canonical) and canonical_repeat and path_parity
            summary.append({"subset": subset, "build_success": True,
                "state": canonical[0]["metrics"]["witness_state"]["state"],
                "solid_count": canonical[0]["metrics"]["witness_state"]["solid_count"],
                "source_volume_mm3": canonical[0]["metrics"]["source_volume_mm3"],
                "witness_volume_mm3": canonical[0]["metrics"]["witness_volume_mm3"],
                "removed_unique_volume_mm3": canonical[0]["metrics"]["removed_unique_volume_mm3"],
                "residual_keepout_mm3": canonical[0]["metrics"]["residual_keepout_intersection_mm3"],
                "accounting_error_mm3": canonical[0]["metrics"]["removed_consistency_error_mm3"],
                "accounting_limit_mm3": canonical[0]["metrics"]["accounting_limit_mm3"],
                "repeatability_pass": canonical_repeat, "alternate_path_parity": path_parity,
                "reopen_parity": all(x["BREP_parity"]["pass"] and x["FCStd_parity"]["pass"] for x in canonical),
                "technical_pass": technical_pass})
            if not technical_pass:
                status, failure = "BOOLEAN_ACCOUNTING_BLOCKED", subset
                break
        except Exception as exc:
            status = "KEEPOUT_UNION_BLOCKED" if "KEEPOUT_UNION_BLOCKED" in str(exc) else "WITNESS_BREP_CONSTRUCTION_BLOCKED"
            failure = {"subset": subset, "type": type(exc).__name__, "error": str(exc)}
            break
    after_signatures = {}
    for name, shape in frozen_shapes.items():
        path = artifact / "frozen_signatures_after" / (name + ".brep")
        path.parent.mkdir(parents=True, exist_ok=True)
        shape.exportBrep(str(path))
        after_signatures[name] = sha(path)
    output = {"status": status, "failure": failure, "expected_subsets": d1["witness_subsets"],
        "union_rows": union_rows, "path_rows": path_rows, "technical_summary": summary,
        "source_state": mutable_state.record(), "C1_source_sha256_after": sha(source_path),
        "frozen_signatures_before": frozen_signatures,
        "frozen_signatures_after": after_signatures,
        "frozen_signatures_invariant": all(frozen_signatures[n]["sha256"] == after_signatures[n] for n in frozen_names),
        "freecad_version": App.Version(), "occ_version": getattr(Part, "OCC_VERSION", None),
        "GT_evaluations": 0, "VLM_calls": 0, "final_96_case_mechanics_evaluations": 0}
    save(ROOT / job["output"], output)
    print(json.dumps({"status": status, "completed_subsets": len(summary), "failure": failure}))


if __name__ == "__main__":
    main(read(sys.argv[1]))
