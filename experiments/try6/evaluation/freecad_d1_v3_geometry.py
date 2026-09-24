"""Frozen-evidence L04 relief localization and C1 semantic overlap audit."""

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
from witness_boolean import exact_union, volumetric_state


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def export(shape, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    shape.exportBrep(str(path))
    return {"path": str(path.relative_to(ROOT)).replace("\\", "/"), "sha256": sha(path)}


def region_volumes(shape, source, stations):
    if not shape.Solids:
        return {"PROXIMAL": 0.0, "MIDDLE": 0.0, "DISTAL": 0.0}
    b = source.BoundBox
    x0, x1, x2, x3 = b.XMin-1.0, stations[0], stations[1], b.XMax+1.0
    y0, z0 = b.YMin-1.0, b.ZMin-1.0
    dy, dz = b.YLength+2.0, b.ZLength+2.0
    values = {}
    for name, lo, hi in (("PROXIMAL", x0, x1), ("MIDDLE", x1, x2), ("DISTAL", x2, x3)):
        box = Part.makeBox(hi-lo, dy, dz, App.Vector(lo, y0, z0))
        values[name] = float(shape.common(box).Volume)
    return values


def localize(shape, source, stations, threshold):
    volume = float(shape.Volume) if shape.Solids else 0.0
    regions = region_volumes(shape, source, stations)
    discrepancy = sum(regions.values())-volume
    if volume <= 0:
        return {"removed_volume_mm3": volume, "regions_mm3": regions,
                "fractions": {k: None for k in regions}, "dominant_region": None,
                "localized": None, "partition_error_mm3": discrepancy,
                "status": "NO_MEASURABLE_RELIEF"}
    fractions = {k: v/volume for k, v in regions.items()}
    dominant = max(fractions, key=fractions.get)
    uncertainty = abs(discrepancy)
    conservative_min = max(0.0, regions[dominant]-uncertainty)/(volume+uncertainty)
    conservative_max = ((regions[dominant]+uncertainty)/(volume-uncertainty)
                        if volume > uncertainty else None)
    robust = ("LOCALIZED_ROBUST" if conservative_min >= threshold else
              "NOT_LOCALIZED_ROBUST" if conservative_max is not None and conservative_max < threshold else
              "LOCALIZATION_NUMERICALLY_AMBIGUOUS")
    return {"removed_volume_mm3": volume, "regions_mm3": regions,
            "fractions": fractions, "dominant_region": dominant,
            "localized": fractions[dominant] >= threshold,
            "conservative_dominant_fraction_min": conservative_min,
            "conservative_dominant_fraction_max": conservative_max,
            "localization_robustness": robust,
            "partition_error_mm3": discrepancy,
            "partition_consistent_with_original_D1_1e-3_mm3": abs(discrepancy) <= 1e-3,
            "status": "MEASURED"}


def main(job):
    cfg = read(ROOT / job["protocol"])
    d1 = read(ROOT / cfg["frozen_d1_protocol"])
    construction = read(ROOT / cfg["frozen_kfde_construction"])
    frozen = read(ROOT / cfg["frozen_geometry_set"])
    alignment = read(ROOT / cfg["frozen_alignment"])
    pre = read(ROOT / job["pre_run_manifest"])
    w1root = ROOT / cfg["frozen_witness_result"]
    if sha(ROOT / cfg["frozen_alignment"]) != pre["alignment_sha256"] or len(alignment["cases"]) != 65:
        raise RuntimeError("frozen alignment drift")
    if d1["witness_longitudinal_cut_stations_mm"] != [21.0, 42.0]:
        raise RuntimeError("frozen longitudinal stations drift")
    source_item = frozen["geometries"][0]
    if sha(ROOT / source_item["mutable_brep_path"]) != source_item["mutable_brep_sha256"]:
        raise RuntimeError("C1 mutable BREP drift")
    allowed_path = ROOT / construction["allowed_region"]["path"]
    if sha(allowed_path) != construction["allowed_region"]["sha256"]:
        raise RuntimeError("frozen allowed region drift")
    mutable_source = Part.read(str(ROOT / source_item["mutable_brep_path"]))
    mutable, _ = safe_diagnostic_cut(mutable_source, Part.read(str(allowed_path)))
    mutable_state = volumetric_state(mutable, derived=True)
    if not mutable_state.can_boolean_cut:
        raise RuntimeError("C1 mutable unexpectedly nonvolumetric")
    component_shapes = []
    for item in construction["components"]:
        path = ROOT / item["brep_path"]
        if sha(path) != item["brep_sha256"]:
            raise RuntimeError("frozen component BREP drift")
        component_shapes.append((item, Part.read(str(path))))
    artifact = ROOT / job["artifact_root"]
    artifact.mkdir(parents=True, exist_ok=True)
    locations = []
    for subset in d1["witness_subsets"]:
        links = {"L03", "L05", "L06", "L07"} if subset == "FULL" else set(subset.split("_"))
        selected = [(item, shape) for item, shape in component_shapes if item["link_id"] in links]
        keepout, _ = exact_union([shape for _, shape in selected])
        removed = mutable.common(keepout)
        removed_state = volumetric_state(removed, derived=True)
        saved = export(removed, artifact / "removed" / subset / "unique_removed.brep")
        path_records = read(w1root / "witnesses" / subset / "path_records.json")
        accepted = next(x for x in path_records if x["path"] == cfg["frozen_witness_path"] and x["repeat"] == 0)
        witness_path = ROOT / accepted["witness_brep_path"]
        if sha(witness_path) != accepted["witness_brep_sha256"]:
            raise RuntimeError("accepted witness BREP drift: " + subset)
        witness = Part.read(str(witness_path))
        witness_state = volumetric_state(witness, derived=True)
        local = localize(removed, mutable, d1["witness_longitudinal_cut_stations_mm"],
                         d1["witness_localized_one_longitudinal_third_min_fraction"])
        locations.append({"subset": subset, "component_ids": [x["component_id"] for x, _ in selected],
            "accepted_witness_brep": {"path": accepted["witness_brep_path"],
                                      "sha256": accepted["witness_brep_sha256"]},
            "accepted_witness_state": witness_state.record(),
            "removed_brep": saved, "removed_state": removed_state.record(),
            "W1_recorded_unique_removed_mm3": accepted["unique_removed_volume_mm3"],
            "removed_volume_crosscheck_delta_mm3": local["removed_volume_mm3"]-accepted["unique_removed_volume_mm3"],
            "localization": local})
    c1_rows = [x for x in alignment["cases"] if x["geometry_id"] == "G1_C1_FINAL"]
    supported = [x for x in c1_rows if x["alignment_category"] == "ALIGNED_UNSAFE"]
    suspect = [x for x in c1_rows if x["alignment_category"] == "KFDE_FALSE_POSITIVE_SUSPECT"]
    ids_supported = {x["component_id"] for x in supported}
    ids_suspect = {x["component_id"] for x in suspect}
    decomposition = {"status": "SUPPORTED_RELIEF_DECOMPOSITION_UNAVAILABLE", "reason": None}
    try:
        k_supported, _ = exact_union([shape for item, shape in component_shapes if item["component_id"] in ids_supported])
        k_suspect, _ = exact_union([shape for item, shape in component_shapes if item["component_id"] in ids_suspect])
        r_supported = mutable.common(k_supported)
        r_suspect = mutable.common(k_suspect)
        shared = r_supported.common(r_suspect)
        supported_only = r_supported.cut(r_suspect)
        suspect_only = r_suspect.cut(r_supported)
        shapes = {"K_supported": k_supported, "K_suspect": k_suspect,
                  "R_supported": r_supported, "R_suspect": r_suspect,
                  "R_shared": shared, "R_supported_only": supported_only,
                  "R_suspect_only": suspect_only}
        states = {name: volumetric_state(shape, derived=True).record() for name, shape in shapes.items()}
        artifacts = {name: export(shape, artifact / "decomposition" / (name + ".brep"))
                     for name, shape in shapes.items()}
        full = next(x for x in locations if x["subset"] == "FULL")["localization"]["removed_volume_mm3"]
        decomposition = {"status": "PASS", "component_ids_supported": sorted(ids_supported),
            "component_ids_suspect": sorted(ids_suspect), "states": states, "artifacts": artifacts,
            "volumes_mm3": {name: state["volume_mm3"] for name, state in states.items()},
            "FULL_unique_removed_mm3": full,
            "supported_fraction_of_FULL": states["R_supported"]["volume_mm3"]/full if full else None,
            "suspect_fraction_of_FULL": states["R_suspect"]["volume_mm3"]/full if full else None,
            "suspect_only_fraction_of_FULL": states["R_suspect_only"]["volume_mm3"]/full if full else None,
            "supported_localization": localize(r_supported, mutable,
                d1["witness_longitudinal_cut_stations_mm"],
                d1["witness_localized_one_longitudinal_third_min_fraction"]),
            "suspect_localization": localize(r_suspect, mutable,
                d1["witness_longitudinal_cut_stations_mm"],
                d1["witness_localized_one_longitudinal_third_min_fraction"])}
    except Exception as exc:
        decomposition["reason"] = {"type": type(exc).__name__, "detail": str(exc)}
    output = {"status": "PASS", "FreeCAD_version": App.Version(),
        "OCC_version": getattr(Part, "OCC_VERSION", None),
        "C1_mutable_state": mutable_state.record(), "localizations": locations,
        "C1_supported_rows": supported, "C1_suspect_rows": suspect,
        "semantic_decomposition": decomposition,
        "VLM_calls": 0, "GT_evaluations": 0, "final_96_case_mechanics_evaluations": 0}
    target = ROOT / job["output"]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"localizations": len(locations), "supported": len(supported),
        "suspect": len(suspect), "decomposition": decomposition["status"]}))


if __name__ == "__main__":
    main(read(sys.argv[1]))
