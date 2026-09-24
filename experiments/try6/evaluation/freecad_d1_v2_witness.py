"""Frozen D1 diagnostic witnesses using T0 safe cuts on mutable geometry."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import FreeCAD as App
import Mesh
import Part

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "experiments/try6/scripts"))
from volumetric_geometry_state import (EPSILON_MM3, classify_volumetric_shape,
    safe_diagnostic_cut, empty_witness_record)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def bbox(shape):
    if classify_volumetric_shape(shape, verified_derived_empty=True).state == "EFFECTIVELY_EMPTY":
        return None
    b = shape.BoundBox
    return [b.XMin, b.YMin, b.ZMin, b.XMax, b.YMax, b.ZMax]


def slab_volume(shape, x0, x1, y0, y1, z0, z1):
    if x1 <= x0 or not shape.Solids:
        return 0.0
    box = Part.makeBox(x1-x0, y1-y0, z1-z0, App.Vector(x0, y0, z0))
    return float(shape.common(box).Volume)


def fuse_without_changing_occupancy(a, b):
    """Use a valid raw fuse if OCC's optional splitter cleanup fails."""
    combined = a.fuse(b)
    if not classify_volumetric_shape(combined).can_boolean_cut:
        raise RuntimeError("fused BREP invalid")
    try:
        cleaned = combined.removeSplitter()
    except Part.OCCError as exc:
        return combined, "VALID_RAW_FUSE_SPLITTER_CLEANUP_FAILED: " + str(exc)
    if not classify_volumetric_shape(cleaned).can_boolean_cut:
        raise RuntimeError("splitter-cleaned BREP invalid")
    return cleaned, "SPLITTER_CLEANUP_EXECUTED"


def main(job):
    cfg = read(ROOT / job["science_protocol"])
    construction = read(ROOT / cfg["kfde_construction"])
    if len(construction["components"]) != 13 or cfg["kfde_numerical_epsilon_mm3"] != EPSILON_MM3:
        raise RuntimeError("frozen witness input drift")
    allowed = Part.read(str(ROOT / construction["allowed_region"]["path"]))
    keepout = Part.read(str(ROOT / construction["keepout"]["path"]))
    source_path = ROOT / cfg["geometry_set"][0]["path"]
    source_hash = sha(source_path)
    doc = App.openDocument(str(source_path))
    source = doc.getObject("FrozenMatingEnvelopeCut").Shape.copy()
    scaffold = doc.getObject("FrozenScaffold").Shape.copy()
    frozen_names = ("FrozenScaffold", "FrozenProximalBoreTool", "FrozenMatingEnvelopeTool")
    frozen = {name: doc.getObject(name).Shape.copy() for name in frozen_names}
    App.closeDocument(doc.Name)
    if not classify_volumetric_shape(source).can_boolean_cut or not classify_volumetric_shape(keepout).can_boolean_cut:
        raise RuntimeError("source or keepout invalid")
    mutable, _ = safe_diagnostic_cut(source, allowed)
    mutable_state = classify_volumetric_shape(mutable, verified_derived_empty=True)
    preserved = source.common(allowed)
    components = {x["component_id"]: Part.read(str(ROOT / x["brep_path"])) for x in construction["components"]}
    result_root = ROOT / job["result_root"]
    artifact_root = ROOT / job["artifact_root"]
    all_rows = []
    for subset in cfg["witness_subsets"]:
        links = {"L03", "L05", "L06", "L07"} if subset == "FULL" else set(subset.split("_"))
        selected = [x for x in construction["components"] if x["link_id"] in links]
        relieved = mutable.copy()
        for component in selected:
            current_state = classify_volumetric_shape(relieved, verified_derived_empty=True)
            relieved, _ = safe_diagnostic_cut(relieved, components[component["component_id"]],
                                              a_derived_empty=current_state.state == "EFFECTIVELY_EMPTY")
        relieved_state = classify_volumetric_shape(relieved, verified_derived_empty=True)
        if relieved_state.state == "EFFECTIVELY_EMPTY":
            witness = preserved.copy()
            fusion_status = "NO_MUTABLE_SOLID_TO_FUSE"
        elif not preserved.Solids:
            witness = relieved.copy()
            fusion_status = "NO_PRESERVED_SOLID_TO_FUSE"
        else:
            witness, fusion_status = fuse_without_changing_occupancy(preserved, relieved)
        witness_state = classify_volumetric_shape(witness)
        if not witness_state.can_boolean_cut:
            raise RuntimeError("witness invalid: " + subset)
        removed, _ = safe_diagnostic_cut(source, witness)
        v_original = float(source.Volume)
        v_witness = float(witness.Volume)
        v_removed = max(0.0, v_original-v_witness)
        if mutable_state.state == "EFFECTIVELY_EMPTY":
            empty = empty_witness_record(mutable_state)
            ratio = empty["removed_ratio"]
        else:
            ratio = v_removed/v_original if v_original > 0 else "NOT_APPLICABLE_EMPTY_MUTABLE"
        if abs(float(removed.Volume)-v_removed) > 1e-3:
            raise RuntimeError("removed-volume Boolean mismatch: " + subset)
        group, group_fusion_status = fuse_without_changing_occupancy(scaffold, witness)
        b = source.BoundBox
        y0, y1, z0, z1 = b.YMin-1, b.YMax+1, b.ZMin-1, b.ZMax+1
        c1, c2 = cfg["witness_longitudinal_cut_stations_mm"]
        regions = {"proximal": slab_volume(removed, b.XMin-1, c1, y0, y1, z0, z1),
                   "middle": slab_volume(removed, c1, c2, y0, y1, z0, z1),
                   "distal": slab_volume(removed, c2, b.XMax+1, y0, y1, z0, z1)}
        if v_removed > EPSILON_MM3 and abs(sum(regions.values())-v_removed) > 1e-3:
            raise RuntimeError("regional removed-volume mismatch: " + subset)
        fractions = {name: volume/v_removed if v_removed > EPSILON_MM3 else 0.0
                     for name, volume in regions.items()}
        dominant = max(fractions, key=fractions.get) if v_removed > EPSILON_MM3 else "NONE"
        p0, p1 = cfg["proximal_carrier_audit_x_mm"]
        d0, d1 = cfg["distal_carrier_audit_x_mm"]
        proximal = slab_volume(witness, p0, p1, y0, y1, z0, z1) > EPSILON_MM3
        distal = slab_volume(witness, d0, d1, y0, y1, z0, z1) > EPSILON_MM3
        # The preserved source/allowed portion must remain inside the witness.
        missing_preserved, _ = safe_diagnostic_cut(preserved, witness)
        preserved_invariant = float(missing_preserved.Volume) <= EPSILON_MM3
        interface_safe = (preserved_invariant and sha(source_path) == source_hash and
                          all(not x.isNull() and x.isValid() for x in frozen.values()))
        connected = (len(witness.Solids) == 1 and len(group.Solids) == 1 and proximal and distal)
        localized = (max(fractions.values()) >= cfg["witness_localized_one_longitudinal_third_min_fraction"]
                     if v_removed > EPSILON_MM3 else True)
        if not interface_safe:
            category = "INTERFACE_DESTRUCTIVE"
        elif not connected:
            category = "TOPOLOGY_BREAKING_RELIEF"
        elif isinstance(ratio, float) and ratio <= cfg["witness_moderate_removed_ratio_max"] and localized:
            category = "LOCAL_CONNECTED_RELIEF"
        else:
            category = "GLOBAL_CONNECTED_SHRINKAGE"
        folder = artifact_root / subset
        folder.mkdir(parents=True, exist_ok=True)
        brep = folder / "witness.brep"
        removed_brep = folder / "removed_material.brep"
        witness.exportBrep(str(brep))
        removed.exportBrep(str(removed_brep))
        temp = App.newDocument("D1V2_Witness_" + subset)
        obj = temp.addObject("Part::Feature", "DiagnosticWitness")
        obj.Shape = witness
        step, stl = folder / "witness.step", folder / "witness.stl"
        Part.export([obj], str(step))
        Mesh.export([obj], str(stl))
        App.closeDocument(temp.Name)
        row = {"subset": subset, "selected_neighbors": sorted(links), "component_count": len(selected),
               "original_body_volume_mm3": v_original, "original_mutable_volume_mm3": float(mutable.Volume),
               "mutable_state": mutable_state.state, "witness_body_volume_mm3": v_witness,
               "removed_volume_mm3": v_removed, "removed_ratio": ratio,
               "witness_body_valid": witness.isValid(), "witness_body_solid_count": len(witness.Solids),
               "witness_fusion_status": fusion_status, "group_fusion_status": group_fusion_status,
               "fragment_count": max(0, len(witness.Solids)-1),
               "scaffold_fused_group_valid": group.isValid(),
               "scaffold_fused_group_solid_count": len(group.Solids),
               "proximal_carrier_present": proximal, "distal_carrier_present": distal,
               "mutable_carrier_connected": connected,
               "frozen_interface_signature_invariant": preserved_invariant,
               "functional_interface_safe": interface_safe,
               "bbox_before_mm": bbox(source), "bbox_after_mm": bbox(witness),
               "centroid_shift_mm": float(source.CenterOfMass.distanceToPoint(witness.CenterOfMass)),
               "removed_volume_by_longitudinal_region_mm3": regions,
               "removed_fraction_by_longitudinal_region": fractions,
               "dominant_removed_region": dominant, "localized_one_third": localized,
               "witness_category": category,
               "witness_brep_path": str(brep.relative_to(ROOT)).replace("\\", "/"),
               "witness_brep_sha256": sha(brep),
               "removed_brep_path": str(removed_brep.relative_to(ROOT)).replace("\\", "/"),
               "removed_brep_sha256": sha(removed_brep),
               "step_path": str(step.relative_to(ROOT)).replace("\\", "/"), "step_sha256": sha(step),
               "stl_path": str(stl.relative_to(ROOT)).replace("\\", "/"), "stl_sha256": sha(stl),
               "diagnostic_only_not_C2_candidate": True, "GT_accessed": False}
        save(result_root / subset / "witness_metrics.json", row)
        save(result_root / subset / "localization.json", {"regions_mm3": regions,
             "fractions": fractions, "dominant_region": dominant, "localized": localized})
        all_rows.append(row)
    save(result_root / "witness_summary.json", {"status": "PASS", "subsets": all_rows,
         "GT_accessed": False, "final_mechanics_evaluations": 0,
         "not_a_generated_design": True, "frozen_C1_fcstd_unchanged": sha(source_path) == source_hash})
    print(json.dumps({"status": "PASS", "subsets": len(all_rows),
          "full_removed_ratio": next(x["removed_ratio"] for x in all_rows if x["subset"] == "FULL")}))


if __name__ == "__main__":
    main(read(sys.argv[1]))
