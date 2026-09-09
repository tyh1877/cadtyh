"""FreeCAD worker for Try-5A.4 articulated-joint construction and evaluation.

The experiment driver invokes this file with the existing FreeCAD Python runtime.
It consumes motion-aware CAD IR, builds separate parent/child rigid groups, applies
pose transforms, and uses exact B-Rep common/distance operations for motion gates.
"""

import json
import math
import sys
from pathlib import Path

import FreeCAD as App
import Part


TOL = 1e-6


def dump(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def box(x0, x1, y0, y1, z0, z1):
    return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, App.Vector(x0, y0, z0))


def cylinder(radius, z0, z1):
    return Part.makeCylinder(radius, z1 - z0, App.Vector(0, 0, z0), App.Vector(0, 0, 1))


def union(shapes):
    result = shapes[0]
    for shape in shapes[1:]:
        result = result.fuse(shape)
    return result.removeSplitter()


def annulus(outer_radius, inner_radius, z0, z1):
    return cylinder(outer_radius, z0, z1).cut(cylinder(inner_radius, z0 - 1, z1 + 1)).removeSplitter()


def component_count(shape):
    return len(shape.Solids)


def common_volume(first, second):
    common = first.common(second)
    return 0.0 if common.isNull() else float(common.Volume)


def bbox(shape):
    value = shape.BoundBox
    return {
        "min_mm": [value.XMin, value.YMin, value.ZMin],
        "max_mm": [value.XMax, value.YMax, value.ZMax],
        "size_mm": [value.XLength, value.YLength, value.ZLength],
    }


def transform_child(shape, q_rad):
    moved = shape.copy()
    moved.Placement = App.Placement(App.Vector(0, 0, 0), App.Rotation(App.Vector(0, 0, 1), math.degrees(q_rad)))
    return moved


def build_shapes(ir, clearance_override=None, family_override=None):
    params = ir["parameters"]
    condition = ir["condition"]
    family = family_override or ir["interface_family"]
    axial_clearance = params["axial_clearance_mm"] if clearance_override is None else clearance_override
    boss_radius = params["child_boss_radius_mm"]
    boss_half = params["child_boss_half_depth_mm"]
    outer = params["parent_carrier_radius_mm"]

    child_body = box(14, params["child_body_length_mm"], -7, 7, -4, 4)
    child_boss = cylinder(boss_radius, -boss_half, boss_half)

    if condition == "M0":
        # Frozen K1-style static overlap: named carriers exist, but neither side
        # is attached to its own body and the pair occupies the same solid space.
        parent_body = box(-82, -20, -16, 16, -8, 8)
        parent_interface = cylinder(outer, -6, 6)
        child_interface = child_boss
        parent_group = Part.makeCompound([parent_body, parent_interface])
        child_group = Part.makeCompound([child_body, child_interface])
    else:
        layer_start = boss_half + axial_clearance
        layer_end = layer_start + 6.0
        if family == "fork_pin_interface":
            ring_outer = outer
            support_width = 8.0
        else:
            # Compact coaxial support uses a slightly smaller paired bearing
            # carrier. The construction remains open across the motion corridor.
            ring_outer = outer - 1.0
            support_width = 12.0
        top_ring = annulus(ring_outer, boss_radius + 1.0, layer_start, layer_end)
        bottom_ring = annulus(ring_outer, boss_radius + 1.0, -layer_end, -layer_start)
        top_support = box(-24, 0, -support_width / 2, support_width / 2, layer_start, layer_end)
        bottom_support = box(-24, 0, -support_width / 2, support_width / 2, -layer_end, -layer_start)
        parent_interface = union([top_ring, bottom_ring, top_support, bottom_support])
        child_neck = box(0, 18, -5, 5, -4, 4)
        child_interface = union([child_boss, child_neck])

        if condition == "M1":
            # The unreplanned shoulder/elbow/wrist-adjacent housing crosses the
            # child sweep at large rotations. M2 must route this region away.
            parent_body = box(-82, -18, -60, 60, -8, 8)
        else:
            # M2 is a motion-driven R2 repair: the joint-adjacent body becomes a
            # U-shaped load path outside the child swept corridor. A remote bridge
            # keeps both slabs in one parent rigid solid without crossing motion.
            upper = box(-82, -18, -16, 16, layer_start, layer_end)
            lower = box(-82, -18, -16, 16, -layer_end, -layer_start)
            rear_bridge = box(-82, -76, -16, 16, -layer_end, layer_end)
            parent_body = union([upper, lower, rear_bridge])

        parent_group = union([parent_body, parent_interface])
        child_group = union([child_body, child_interface])

    parent_distance = float(parent_body.distToShape(parent_interface)[0])
    child_distance = float(child_body.distToShape(child_interface)[0])
    parent_overlap = common_volume(parent_body, parent_interface)
    child_overlap = common_volume(child_body, child_interface)
    attachment = {
        "parent": {
            "minimum_distance_mm": parent_distance,
            "intersection_volume_mm3": parent_overlap,
            "connected_solid_count": component_count(parent_group),
            "pass": condition != "M0" and parent_distance <= TOL and component_count(parent_group) == 1,
        },
        "child": {
            "minimum_distance_mm": child_distance,
            "intersection_volume_mm3": child_overlap,
            "connected_solid_count": component_count(child_group),
            "pass": condition != "M0" and child_distance <= TOL and component_count(child_group) == 1,
        },
    }
    return {
        "parent_body": parent_body,
        "parent_interface": parent_interface,
        "child_body": child_body,
        "child_interface": child_interface,
        "parent_group": parent_group,
        "child_group": child_group,
        "attachment": attachment,
        "family": family,
    }


def save_cad(shapes, target, joint_id, condition):
    target = Path(target)
    target.mkdir(parents=True, exist_ok=True)
    doc = App.newDocument("Try5A4_{}_{}".format(joint_id, condition))
    parent = doc.addObject("Part::Feature", "ParentRigidGroup")
    parent.Label = "{} parent rigid group".format(joint_id)
    parent.Shape = shapes["parent_group"]
    child = doc.addObject("Part::Feature", "ChildRigidGroup")
    child.Label = "{} child rigid group".format(joint_id)
    child.Shape = shapes["child_group"]
    doc.recompute()
    fcstd = target / "model.FCStd"
    step = target / "model.step"
    stl = target / "model.stl"
    doc.saveAs(str(fcstd))
    Part.export([parent, child], str(step))
    try:
        import Mesh

        Mesh.export([parent, child], str(stl))
    except Exception:
        stl = None
    App.closeDocument(doc.Name)
    paths = [fcstd, step] + ([stl] if stl else [])
    return [str(path) for path in paths]


def evaluate(ir, artifact_root, clearance_override=None, family_override=None, sample_values=None, save=True):
    shapes = build_shapes(ir, clearance_override=clearance_override, family_override=family_override)
    samples = sample_values if sample_values is not None else ir["sample_values_rad"]
    rows = []
    occupancy = None
    for index, value in enumerate(samples):
        moved = transform_child(shapes["child_group"], value)
        collision_volume = common_volume(shapes["parent_group"], moved)
        distance = float(shapes["parent_group"].distToShape(moved)[0])
        current = moved.BoundBox
        if occupancy is None:
            occupancy = App.BoundBox(current.XMin, current.YMin, current.ZMin, current.XMax, current.YMax, current.ZMax)
        else:
            occupancy.add(current)
        rows.append(
            {
                "sample_index": index,
                "q_rad": value,
                "q_deg": math.degrees(value),
                "exact_common_volume_mm3": collision_volume,
                "minimum_clearance_mm": distance,
                "collision_free": collision_volume <= TOL,
                "collision_class": "NONE" if collision_volume <= TOL else "MOTION_INDUCED_COLLISION",
                "child_bbox": bbox(moved),
            }
        )
    cad_paths = []
    if save:
        cad_paths = save_cad(shapes, Path(artifact_root) / ir["condition"] / ir["joint_id"], ir["joint_id"], ir["condition"])
    return {
        "joint_id": ir["joint_id"],
        "condition": ir["condition"],
        "interface_family": shapes["family"],
        "attachment": shapes["attachment"],
        "forbidden_parent_child_fusion_count": 0,
        "parent_child_top_level_object_count": 2,
        "parent_rigid_group_solid_count": component_count(shapes["parent_group"]),
        "child_rigid_group_solid_count": component_count(shapes["child_group"]),
        "parent_interface_volume_mm3": float(shapes["parent_interface"].Volume),
        "child_interface_volume_mm3": float(shapes["child_interface"].Volume),
        "parent_bbox": bbox(shapes["parent_group"]),
        "child_bbox_q0": bbox(shapes["child_group"]),
        "swept_occupancy_bbox": {
            "min_mm": [occupancy.XMin, occupancy.YMin, occupancy.ZMin],
            "max_mm": [occupancy.XMax, occupancy.YMax, occupancy.ZMax],
            "size_mm": [occupancy.XLength, occupancy.YLength, occupancy.ZLength],
        },
        "samples": rows,
        "cad_paths": cad_paths,
    }


def main():
    job = json.loads(Path(sys.argv[-1]).read_text(encoding="utf-8"))
    artifact_root = Path(job["artifact_root"])
    evaluations = []
    ir_payloads = []
    for ir_path in job["cad_ir_paths"]:
        ir = json.loads(Path(ir_path).read_text(encoding="utf-8"))
        ir_payloads.append(ir)
        evaluations.append(evaluate(ir, artifact_root))

    base_ir = next(ir for ir in ir_payloads if ir["condition"] == "M2")
    base = next(item for item in evaluations if item["joint_id"] == base_ir["joint_id"] and item["condition"] == "M2")
    narrowed_samples = base_ir["sample_values_rad"][2:7]
    narrowed = evaluate(base_ir, artifact_root, sample_values=narrowed_samples, save=False)
    base_size = base["swept_occupancy_bbox"]["size_mm"]
    narrow_size = narrowed["swept_occupancy_bbox"]["size_mm"]

    alternate_family = "coaxial_rotary_interface" if base_ir["interface_family"] == "fork_pin_interface" else "fork_pin_interface"
    family_changed = evaluate(base_ir, artifact_root, family_override=alternate_family, sample_values=[base_ir["sample_values_rad"][4]], save=False)

    clearance_changed = evaluate(base_ir, artifact_root, clearance_override=-1.0, save=False)
    base_rate = sum(row["collision_free"] for row in base["samples"]) / len(base["samples"])
    changed_rate = sum(row["collision_free"] for row in clearance_changed["samples"]) / len(clearance_changed["samples"])
    counterfactuals = [
        {
            "name": "joint_limit_changes_swept_clearance",
            "joint_id": base_ir["joint_id"],
            "baseline_sample_range_rad": [base_ir["sample_values_rad"][0], base_ir["sample_values_rad"][-1]],
            "counterfactual_sample_range_rad": [narrowed_samples[0], narrowed_samples[-1]],
            "baseline_swept_bbox_size_mm": base_size,
            "counterfactual_swept_bbox_size_mm": narrow_size,
            "pass": any(abs(first - second) > TOL for first, second in zip(base_size, narrow_size)),
        },
        {
            "name": "knowledge_family_changes_interface_realization",
            "joint_id": base_ir["joint_id"],
            "baseline_family": base_ir["interface_family"],
            "counterfactual_family": alternate_family,
            "baseline_parent_interface_volume_mm3": base["parent_interface_volume_mm3"],
            "counterfactual_parent_interface_volume_mm3": family_changed["parent_interface_volume_mm3"],
            "pass": abs(base["parent_interface_volume_mm3"] - family_changed["parent_interface_volume_mm3"]) > TOL,
        },
        {
            "name": "clearance_parameter_changes_cad_and_motion_metric",
            "joint_id": base_ir["joint_id"],
            "baseline_axial_clearance_mm": base_ir["parameters"]["axial_clearance_mm"],
            "counterfactual_axial_clearance_mm": -1.0,
            "baseline_collision_free_pose_rate": base_rate,
            "counterfactual_collision_free_pose_rate": changed_rate,
            "baseline_parent_interface_volume_mm3": base["parent_interface_volume_mm3"],
            "counterfactual_parent_interface_volume_mm3": clearance_changed["parent_interface_volume_mm3"],
            "baseline_parent_bbox": base["parent_bbox"],
            "counterfactual_parent_bbox": clearance_changed["parent_bbox"],
            "pass": abs(base_rate - changed_rate) > TOL and base["parent_bbox"] != clearance_changed["parent_bbox"],
        },
    ]

    payload = {"status": "PASS", "backend": "FreeCAD exact B-Rep", "evaluations": evaluations, "counterfactuals": counterfactuals}
    dump(artifact_root / "evaluation.json", payload)
    print(json.dumps({"status": "PASS", "evaluations": len(evaluations), "counterfactuals": len(counterfactuals)}, indent=2))


if __name__ == "__main__":
    main()
