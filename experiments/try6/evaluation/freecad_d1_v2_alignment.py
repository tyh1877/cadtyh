"""Frozen D1 5x13 science with T0 empty-BREP handling; no GT or final96."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import FreeCAD as App
import Part
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "experiments/try5A/scripts"))
sys.path.insert(0, str(ROOT / "experiments/try6/scripts"))
import freecad_motion_realization as exact
import kinematics
from volumetric_geometry_state import (EPSILON_MM3, classify_volumetric_shape,
    empty_intersection_record, safe_diagnostic_cut)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_group(path):
    doc = App.openDocument(str(path))
    obj = doc.getObject("RigidGroup")
    if obj is None or obj.Shape.isNull():
        raise RuntimeError("missing full RigidGroup: " + str(path))
    shape = obj.Shape.copy()
    App.closeDocument(doc.Name)
    return shape


def main(job):
    cfg = read(ROOT / job["science_protocol"])
    geometry = read(ROOT / job["geometry_set"])
    construction = read(ROOT / cfg["kfde_construction"])
    if len(geometry["geometries"]) != 5 or len(construction["components"]) != 13:
        raise RuntimeError("frozen 5x13 set drift")
    if cfg["kfde_numerical_epsilon_mm3"] != EPSILON_MM3:
        raise RuntimeError("frozen epsilon drift")
    allowed = Part.read(str(ROOT / construction["allowed_region"]["path"]))
    if classify_volumetric_shape(allowed).can_boolean_cut is not True:
        raise RuntimeError("allowed region invalid")
    components = {x["component_id"]: Part.read(str(ROOT / x["brep_path"])) for x in construction["components"]}
    for component in construction["components"]:
        if classify_volumetric_shape(components[component["component_id"]]).can_boolean_cut is not True:
            raise RuntimeError("KFDE component invalid: " + component["component_id"])
    contracts = read(ROOT / cfg["interface_contracts"])
    classification = read(ROOT / cfg["physical_link_classification"])
    physical = [x["link_id"] for x in classification if x["realization_type"] != "virtual_frame"]
    shapes = {link: load_group(ROOT / cfg["frozen_nonpilot_root"] / link / "model.FCStd")
              for link in physical if link != "L04"}
    links, joints = kinematics.parse(ROOT / cfg["sanitized_urdf"])
    q0 = kinematics.canonical_q(joints)
    rows = []
    geometry_states = []
    for item in geometry["geometries"]:
        if sha(ROOT / item["source_path"]) != item["source_sha256"]:
            raise RuntimeError("frozen source drift: " + item["geometry_id"])
        full = Part.read(str(ROOT / item["full_brep_path"]))
        mutable = Part.read(str(ROOT / item["mutable_brep_path"]))
        full_state = classify_volumetric_shape(full)
        if not full_state.can_boolean_cut:
            raise RuntimeError("invalid full link: " + item["geometry_id"])
        # Provenance comes from the frozen extraction definition and direct
        # recomputation, never from the G5 name or expected result.
        derived_scope = item["extraction"] == "full_link_minus_frozen_allowed_region"
        verified_empty = False
        if derived_scope:
            recomputed, _ = safe_diagnostic_cut(full, allowed)
            recomputed_state = classify_volumetric_shape(recomputed, verified_derived_empty=True)
            verified_empty = recomputed_state.state == "EFFECTIVELY_EMPTY"
        mutable_state = classify_volumetric_shape(mutable, verified_derived_empty=verified_empty)
        if mutable_state.state in ("INVALID_BREP", "NONVOLUMETRIC_ONLY"):
            raise RuntimeError("unsupported mutable state: " + item["geometry_id"])
        addition, cut_branch = safe_diagnostic_cut(mutable, allowed, a_derived_empty=verified_empty)
        addition_state = classify_volumetric_shape(addition,
            verified_derived_empty=(mutable_state.state == "EFFECTIVELY_EMPTY"))
        if addition_state.state in ("INVALID_BREP", "NONVOLUMETRIC_ONLY"):
            # A valid solid can become empty after this second subtraction.
            if not addition.isNull() and len(addition.Solids) == 0 and addition.Volume <= EPSILON_MM3:
                addition_state = classify_volumetric_shape(addition, verified_derived_empty=True)
            else:
                raise RuntimeError("invalid post-allowed mutable addition: " + item["geometry_id"])
        geometry_states.append({"geometry_id": item["geometry_id"], "full": full_state.record(),
            "mutable": mutable_state.record(), "addition": addition_state.record(),
            "verified_empty_provenance": verified_empty, "cut_branch": cut_branch})
        shapes["L04"] = full
        for component in construction["components"]:
            joint = component["joint_id"]
            q = dict(q0)
            if joint in ("J03", "J05"):
                q[joint] = component["q_rad"]
            _, world, _ = kinematics.fk(links, joints, q)
            relative = np.linalg.inv(world["L04"]) @ world[component["link_id"]]
            if not np.allclose(relative, component["relative_transform_L04"], atol=1e-12):
                raise RuntimeError("KFDE/exact pose mapping drift: " + component["component_id"])
            config = {"config_id": item["geometry_id"] + "_" + component["component_id"],
                "world_transforms": {link: world[link].tolist() for link in physical}}
            exact_rows, _ = exact.exact_config(config, shapes, contracts, physical)
            pair = next(x for x in exact_rows if {x["link_a"], x["link_b"]} ==
                        {"L04", component["link_id"]})
            neighbor = components[component["component_id"]]
            if addition_state.state == "EFFECTIVELY_EMPTY":
                empty = empty_intersection_record(component["component_id"], addition_state)
                kfde_volume, violation, kfde_status = (empty["intersection_volume_mm3"],
                                                       empty["violation"], empty["status"])
                mutable_world_volume = 0.0
            else:
                kfde_volume = (0.0 if not exact.aabb_overlap(addition, neighbor)
                               else exact.common_volume(addition, neighbor))
                violation = kfde_volume > EPSILON_MM3
                kfde_status = "VOLUMETRIC_MUTABLE_GEOMETRY"
                addition_world = exact.moved(addition, world["L04"])
                neighbor_world = exact.moved(shapes[component["link_id"]], world[component["link_id"]])
                mutable_world_volume = (0.0 if not exact.aabb_overlap(addition_world, neighbor_world)
                                        else exact.common_volume(addition_world, neighbor_world))
            coordinate_delta = abs(kfde_volume - mutable_world_volume)
            if coordinate_delta > 1e-4:
                raise RuntimeError("same-pose mutable volume parity failed: " + config["config_id"])
            # Keep the original D1 taxonomy, scope-ambiguity, material and
            # decision thresholds unchanged.
            neighbor_world = exact.moved(shapes[component["link_id"]], world[component["link_id"]])
            allowed_world = exact.moved(allowed, world["L04"])
            allowed_common = (0.0 if not exact.aabb_overlap(allowed_world, neighbor_world)
                              else exact.common_volume(allowed_world, neighbor_world))
            unsafe = pair["classification"] in ("ADJACENT_UNINTENDED_COLLISION", "NONADJACENT_COLLISION")
            ambiguous_scope = item["baseline_exemption_scope_ambiguous"]
            if coordinate_delta > EPSILON_MM3:
                category = "AMBIGUOUS_NUMERICAL"
                ambiguity = "L04-frame/world-frame mutable overlap differs beyond frozen epsilon"
            elif violation and unsafe:
                category, ambiguity = "ALIGNED_UNSAFE", None
            elif violation and not unsafe:
                category = ("KFDE_FALSE_POSITIVE_SUSPECT" if kfde_volume >= cfg["material_exact_overlap_mm3"]
                            else "AMBIGUOUS_NUMERICAL")
                ambiguity = None if category == "KFDE_FALSE_POSITIVE_SUSPECT" else "below frozen material threshold"
            elif not violation and unsafe:
                category = ("AMBIGUOUS_NUMERICAL" if ambiguous_scope or allowed_common > EPSILON_MM3
                            else "KFDE_FALSE_NEGATIVE_SUSPECT")
                ambiguity = ("frozen baseline/full-link occupancy outside mutable KFDE scope"
                             if category == "AMBIGUOUS_NUMERICAL" else None)
            else:
                category, ambiguity = "ALIGNED_SAFE", None
            rows.append({"geometry_id": item["geometry_id"], "component_id": component["component_id"],
                "neighbor_id": component["link_id"], "joint_id": joint, "pose_q_rad": component["q_rad"],
                "geometry_fcstd_sha256": item["source_sha256"],
                "KFDE_component_brep_sha256": component["brep_sha256"],
                "mutable_geometry_state": mutable_state.state, "addition_geometry_state": addition_state.state,
                "kfde_status": kfde_status, "kfde_mutable_added_intersection_mm3": kfde_volume,
                "kfde_violation": violation, "exact_full_pair_common_mm3": pair["exact_common_mm3"],
                "exact_mutable_pair_common_mm3": mutable_world_volume,
                "allowed_region_pair_common_mm3": allowed_common,
                "coordinate_volume_delta_mm3": coordinate_delta,
                "exact_taxonomy": pair["classification"], "exact_adjacent": pair["adjacent"],
                "exact_unintended_collision": unsafe,
                "exact_allowed_contact_or_cluster_exception": pair["classification"] == "EXPECTED_INTERFACE_CONTACT" and pair["exact_common_mm3"] > EPSILON_MM3,
                "scope_ambiguity": ambiguous_scope, "alignment_category": category,
                "ambiguity_reason": ambiguity, "GT_accessed": False})
    if len(rows) != 65 or len({(x["geometry_id"], x["component_id"]) for x in rows}) != 65:
        raise RuntimeError("65-row denominator incomplete")
    save(ROOT / job["output"], {"schema_version": "try6_d1_v2_alignment_raw_v1", "status": "PASS",
        "geometry_count": 5, "component_count": 13, "case_count": 65,
        "geometry_states": geometry_states, "cases": rows,
        "exact_mechanics_source_sha256": sha(ROOT / cfg["exact_mechanics_source"]),
        "GT_accessed": False, "final_96_case_mechanics_run": False,
        "formal_holdout_accessed": False})
    print(json.dumps({"status": "PASS", "cases": 65,
        "categories": {c: sum(x["alignment_category"] == c for x in rows)
                       for c in sorted({x["alignment_category"] for x in rows})}}))


if __name__ == "__main__":
    main(read(sys.argv[1]))
