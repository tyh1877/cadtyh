"""Engineering-scale occupancy/stability audit for all nine frozen witnesses."""

from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

import FreeCAD as App
import Part

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "experiments/try6/scripts"))
from volumetric_geometry_state import safe_diagnostic_cut
from witness_boolean import accounting_limit, build_clearance_witness, exact_union, optional_splitter_cleanup, volumetric_state
from w1_semantics import sensitivity_category, topology_class


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


def reopened_record(shape, source, keepout):
    state = volumetric_state(shape, derived=True)
    if state.state == "EFFECTIVELY_EMPTY":
        outside = residual = 0.0
    else:
        outside = float(shape.cut(source).Volume)
        residual = float(shape.common(keepout).Volume)
    return {"state": state.state, "solid_count": state.solid_count,
            "volume_mm3": state.volume_mm3, "bbox_mm": bbox(shape),
            "outside_source_mm3": outside, "keepout_residual_mm3": residual}


def stable_pair(a, b, volume_limit, bbox_limit):
    if a["state"] != b["state"] or a["solid_count"] != b["solid_count"]:
        return False
    if abs(a["volume_mm3"]-b["volume_mm3"]) > volume_limit:
        return False
    if abs(a["outside_source_mm3"]-b["outside_source_mm3"]) > volume_limit:
        return False
    if abs(a["keepout_residual_mm3"]-b["keepout_residual_mm3"]) > volume_limit:
        return False
    a_box, b_box = a["bbox_mm"], b["bbox_mm"]
    if (a_box is None) != (b_box is None):
        return False
    return a_box is None or max(abs(x-y) for x, y in zip(a_box, b_box)) <= bbox_limit


def main(job):
    cfg = read(ROOT / job["protocol"])
    d1 = read(ROOT / cfg["frozen_d1_protocol"])
    pre = read(ROOT / job["pre_run_manifest"])
    policy_doc = read(ROOT / cfg["frozen_w0_result"] / "calibration/tolerance_calibration.json")
    policy = policy_doc["BOOLEAN_ACCOUNTING_TOLERANCE"]
    construction = read(ROOT / cfg["frozen_kfde_construction"])
    geometry = read(ROOT / cfg["frozen_geometry_set"])
    source_path = ROOT / geometry["geometries"][0]["source_path"]
    if sha(source_path) != pre["C1_source_sha256"]:
        raise RuntimeError("frozen C1 source drift")
    allowed_path = ROOT / construction["allowed_region"]["path"]
    if sha(allowed_path) != pre["allowed_sha256"]:
        raise RuntimeError("frozen allowed region drift")
    component_shapes = []
    for item in construction["components"]:
        path = ROOT / item["brep_path"]
        if sha(path) != pre["component_hashes"][item["component_id"]]:
            raise RuntimeError("frozen component drift: " + item["component_id"])
        shape = Part.read(str(path))
        volumetric_state(shape)
        component_shapes.append((item, shape))
    doc = App.openDocument(str(source_path))
    source_obj = doc.getObject("FrozenMatingEnvelopeCut")
    if source_obj is None:
        raise RuntimeError("frozen C1 mutable source missing")
    source = source_obj.Shape.copy()
    frozen_names = ("FrozenScaffold", "FrozenProximalBoreTool", "FrozenMatingEnvelopeTool")
    frozen = {name: doc.getObject(name).Shape.copy() for name in frozen_names}
    App.closeDocument(doc.Name)
    mutable, _ = safe_diagnostic_cut(source, Part.read(str(allowed_path)))
    source_state = volumetric_state(mutable, derived=True)
    if source_state.state == "EFFECTIVELY_EMPTY":
        raise RuntimeError("C1 mutable unexpectedly empty")
    scratch = ROOT / job["artifact_root"]
    scratch.mkdir(parents=True, exist_ok=True)
    signatures_before = {}
    for name, shape in frozen.items():
        path = scratch / "signatures_before" / (name + ".brep")
        path.parent.mkdir(parents=True, exist_ok=True)
        shape.exportBrep(str(path))
        signatures_before[name] = sha(path)
    rows = []
    for subset in d1["witness_subsets"]:
        links = {"L03", "L05", "L06", "L07"} if subset == "FULL" else set(subset.split("_"))
        selected = [(item, shape) for item, shape in component_shapes if item["link_id"] in links]
        row = {"subset": subset, "selected_component_ids": [x["component_id"] for x, _ in selected],
               "source_volume_mm3": source_state.volume_mm3, "paths": [], "status": None,
               "failure": None}
        try:
            keepout, _ = exact_union([shape for _, shape in selected])
            union_state = volumetric_state(keepout)
            folder = scratch / subset
            folder.mkdir(parents=True, exist_ok=True)
            keepout_path = folder / "keepout_union.brep"
            keepout.exportBrep(str(keepout_path))
            reopened_union = Part.read(str(keepout_path))
            if not stable_pair(reopened_record(keepout, mutable, keepout),
                               reopened_record(reopened_union, mutable, keepout),
                               accounting_limit(policy, source_state.volume_mm3),
                               cfg["stability_policy"]["bbox_limit_mm"]):
                raise RuntimeError("union serialization parity failed")
            row["union"] = {"state": union_state.record(), "brep_sha256": sha(keepout_path),
                            "component_count": len(selected),
                            "brep_path": str(keepout_path.relative_to(ROOT)).replace("\\", "/")}
            samples = []
            for path_name in cfg["paths"]:
                for repeat in range(cfg["repeats_per_path"]):
                    witness, _, _, metrics = build_clearance_witness(
                        mutable, [shape for _, shape in selected], policy, path=path_name)
                    raw_record = reopened_record(witness, mutable, keepout)
                    brep = folder / f"{path_name}_{repeat}.brep"
                    witness.exportBrep(str(brep))
                    reopened_brep = Part.read(str(brep))
                    brep_record = reopened_record(reopened_brep, mutable, keepout)
                    fcstd = folder / f"{path_name}_{repeat}.FCStd"
                    temp = App.newDocument("W1_" + subset + "_" + path_name + "_" + str(repeat))
                    obj = temp.addObject("Part::Feature", "DiagnosticWitness")
                    obj.Shape = witness
                    temp.saveAs(str(fcstd))
                    App.closeDocument(temp.Name)
                    reopened_doc = App.openDocument(str(fcstd))
                    fcstd_shape = reopened_doc.getObject("DiagnosticWitness").Shape.copy()
                    App.closeDocument(reopened_doc.Name)
                    fcstd_record = reopened_record(fcstd_shape, mutable, keepout)
                    _, cleanup_status = optional_splitter_cleanup(witness) if witness.Solids else (None, "EMPTY_NOT_CLEANED")
                    limit = accounting_limit(policy, source_state.volume_mm3)
                    sample = {"path": path_name, "repeat": repeat, "memory": raw_record,
                        "BREP_reopen": brep_record, "FCStd_reopen": fcstd_record,
                        "BREP_parity": stable_pair(raw_record, brep_record, limit, cfg["stability_policy"]["bbox_limit_mm"]),
                        "FCStd_parity": stable_pair(raw_record, fcstd_record, limit, cfg["stability_policy"]["bbox_limit_mm"]),
                        "cleanup_status": cleanup_status,
                        "accounting_delta_mm3": metrics["removed_consistency_error_mm3"],
                        "accounting_source_fraction": metrics["removed_consistency_error_mm3"]/source_state.volume_mm3,
                        "accounting_relief_fraction": metrics["removed_consistency_error_mm3"]/
                            max(abs(metrics["volume_difference_mm3"]), policy["absolute_mm3"]),
                        "unique_removed_volume_mm3": metrics["removed_unique_volume_mm3"],
                        "witness_brep_path": str(brep.relative_to(ROOT)).replace("\\", "/"),
                        "witness_brep_sha256": sha(brep),
                        "witness_FCStd_path": str(fcstd.relative_to(ROOT)).replace("\\", "/"),
                        "witness_FCStd_sha256": sha(fcstd)}
                    samples.append(sample)
                    row["paths"].append(sample)
            records = [s[key] for s in samples for key in ("memory", "BREP_reopen", "FCStd_reopen")]
            source_limit = accounting_limit(policy, source_state.volume_mm3)
            raw_ratios = [(source_state.volume_mm3-r["volume_mm3"])/source_state.volume_mm3 for r in records]
            if any(x < -source_limit/source_state.volume_mm3 for x in raw_ratios):
                raise ArithmeticError("witness volume exceeds source beyond frozen stability limit")
            ratios = [max(0.0, x) for x in raw_ratios]
            category = sensitivity_category(ratios)
            topologies = [topology_class(r["state"], r["solid_count"]) for r in records]
            keepout_limit = cfg["occupancy_policy"]["keepout_intersection_limit_mm3"]
            occupancy_pass = all(r["outside_source_mm3"] <= source_limit and
                                 r["keepout_residual_mm3"] <= keepout_limit for r in records)
            reopen_pass = all(s["BREP_parity"] and s["FCStd_parity"] for s in samples)
            repeat_pass = all(stable_pair(
                next(s["memory"] for s in samples if s["path"] == path and s["repeat"] == 0),
                next(s["memory"] for s in samples if s["path"] == path and s["repeat"] == 1),
                source_limit, cfg["stability_policy"]["bbox_limit_mm"])
                for path in cfg["paths"])
            topology_pass = len(set(topologies)) == 1
            interval_width = category["interval"][1]-category["interval"][0]
            numeric_pass = interval_width <= cfg["stability_policy"]["maximum_relief_interval_width_ratio"]
            row.update({"relief_sensitivity": category, "raw_relief_ratios": raw_ratios,
                "interval_width_ratio": interval_width,
                "topology_classes": sorted(set(topologies)), "topology_stable": topology_pass,
                "occupancy_pass": occupancy_pass, "repeatability_pass": repeat_pass,
                "reopen_parity_pass": reopen_pass, "path_relief_stability_pass": numeric_pass,
                "source_exterior_limit_mm3": source_limit,
                "keepout_residual_limit_mm3": keepout_limit,
                "interface_invariant": True})
            if not occupancy_pass:
                row["status"] = "WITNESS_OCCUPANCY_INVALID"
            elif not topology_pass:
                row["status"] = "WITNESS_TOPOLOGY_UNSTABLE"
            elif not (repeat_pass and reopen_pass and numeric_pass):
                row["status"] = "WITNESS_NUMERICALLY_UNSTABLE"
            else:
                row["status"] = "PASS"
        except Exception as exc:
            row["status"] = "WITNESS_CONSTRUCTION_BLOCKED"
            row["failure"] = {"type": type(exc).__name__, "detail": str(exc)}
        rows.append(row)
    signatures_after = {}
    for name, shape in frozen.items():
        path = scratch / "signatures_after" / (name + ".brep")
        path.parent.mkdir(parents=True, exist_ok=True)
        shape.exportBrep(str(path))
        signatures_after[name] = sha(path)
    interface_invariant = signatures_before == signatures_after and sha(source_path) == pre["C1_source_sha256"]
    for row in rows:
        row["interface_invariant"] = interface_invariant
        if not interface_invariant:
            row["status"] = "WITNESS_OCCUPANCY_INVALID"
    result = {"rows": rows, "expected_subsets": d1["witness_subsets"],
        "frozen_signatures_before": signatures_before, "frozen_signatures_after": signatures_after,
        "interface_invariant": interface_invariant,
        "source_state": source_state.record(), "FreeCAD_version": App.Version(),
        "OCC_version": getattr(Part, "OCC_VERSION", None),
        "GT_evaluations": 0, "VLM_calls": 0, "final_96_case_mechanics_evaluations": 0}
    save(ROOT / job["output"], result)
    print(json.dumps({"subsets": len(rows), "statuses": {x["subset"]: x["status"] for x in rows}}))


if __name__ == "__main__":
    main(read(sys.argv[1]))
