from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import jsonschema

from pilot_common import EXP, FRAME, RUNS, dump_json, ensure_dirs, feature_rows_from_graph, frozen_rows, load_json, write_csv


SCHEMA = load_json(EXP / "schemas" / "executable_cad_ir_v1_1.schema.json")


def profile_rect(center, size):
    return {"profile_type": "rectangle", "closed": True, "parameters": {"center": center, "size_mm": size}}


def profile_circle(center, radius):
    return {"profile_type": "circle", "closed": True, "parameters": {"center": center, "radius_mm": radius}}


def op(op_id, op_type, target, deps, feature, **kwargs):
    return {
        "op_id": op_id,
        "op_type": op_type,
        "target_body": target,
        "dependencies": deps,
        "reference_frame": FRAME,
        "feature_ref": feature.get("feature_id", ""),
        "semantic_feature_type": feature.get("feature_type", ""),
        **kwargs,
    }


def base_dims(role: str) -> tuple[float, float, float]:
    if role == "base_or_shoulder":
        return 120, 90, 30
    if role in {"upper_arm", "main_link", "forearm"}:
        return 160, 34, 24
    if role == "elbow_housing":
        return 80, 70, 42
    if role == "wrist_or_tool_side_link":
        return 90, 52, 18
    return 90, 40, 22


def feature_to_ops(feature: dict[str, Any], role: str, idx: int, existing: list[str], final_body: str | None) -> tuple[list[dict[str, Any]], str | None]:
    ftype = feature["feature_type"]
    fid = feature["feature_id"]
    length, width, thick = base_dims(role)
    ops: list[dict[str, Any]] = []
    oid = f"op_{idx:03d}"
    if ftype in {"main_link_body", "elongated_main_body", "main_housing", "support_frame", "palm_plate"}:
        if ftype == "elongated_main_body":
            ops.append(
                op(
                    oid,
                    "loft",
                    fid,
                    [],
                    feature,
                    profiles=[
                        profile_rect([-length / 2, 0, 0], [width * 1.2, thick]),
                        profile_rect([length / 2, 0, 0], [width * 0.75, thick * 0.85]),
                    ],
                    solid=True,
                    operation_mode="new_body",
                )
            )
        else:
            ops.append(op(oid, "extrude", fid, [], feature, profile=profile_rect([0, 0, 0], [length, width]), distance_mm=thick, operation_mode="new_body"))
        return ops, oid
    if ftype in {"proximal_joint_housing", "distal_joint_housing", "bearing_boss", "mounting_boss", "flange", "tool_flange", "connector_housing"}:
        x = -length / 2 if ftype.startswith("proximal") else length / 2
        if ftype in {"flange", "tool_flange"}:
            radius = max(width * 0.45, 18)
            # FreeCAD Part::Revolution is stable for a closed rectangular
            # cross-section offset from the axis. Revolving an annulus face
            # around an external axis creates invalid/self-intersecting native
            # shapes, so ring holes must be represented by separate cut features
            # rather than by an annulus-as-revolve source.
            prof = profile_rect([x + radius * 0.65, radius * 0.15, thick / 2], [radius * 0.35, radius * 0.35])
        else:
            radius = max(width * 0.35, 14)
            prof = profile_rect([x + radius, thick * 0.6, thick / 2], [radius * 0.45, thick * 1.2])
        ops.append(op(oid, "revolve", fid, [], feature, profile=prof, axis={"point": [x, 0, thick / 2], "direction": [0, 1, 0]}, angle_deg=360, operation_mode="new_body"))
        return ops, oid
    if ftype in {"tapered_transition", "lofted_transition", "blended_joint_transition", "rounded_section", "web", "rib", "cover_region", "strengthening_boss"}:
        x0 = -length * 0.25
        x1 = length * 0.25
        ops.append(
            op(
                oid,
                "loft",
                fid,
                [],
                feature,
                profiles=[profile_rect([x0, 0, thick * 0.6], [width, thick * 0.55]), profile_rect([x1, 0, thick * 0.7], [width * 0.62, thick * 0.35])],
                solid=True,
                operation_mode="new_body",
            )
        )
        return ops, oid
    if ftype in {"recess", "cutout", "hollow_region", "slot", "gap", "lightening_cut"}:
        cutter_id = oid
        cut_id = f"op_{idx:03d}_cut"
        cutter = op(cutter_id, "extrude", fid, [], feature, profile=profile_rect([0, 0, thick * 0.4], [length * 0.35, width * 0.45]), distance_mm=thick * 1.4, operation_mode="new_body")
        if final_body is None:
            return [cutter], cutter_id
        cut = op(cut_id, "boolean_cut", final_body, [final_body, cutter_id], feature, tool_bodies=[cutter_id])
        return [cutter, cut], cut_id
    if ftype == "fillet_group" and final_body:
        return [op(oid, "fillet", final_body, [final_body], feature, radius_mm=0.5, edge_selectors=[{"edge_index": 1}])], oid
    if ftype == "chamfer_group" and final_body:
        return [op(oid, "chamfer", final_body, [final_body], feature, distance_mm=0.5, edge_selectors=[{"edge_index": 1}])], oid
    return [], final_body


def graph_to_ir(graph: dict[str, Any], role: str) -> dict[str, Any]:
    features = feature_rows_from_graph(graph)
    ops: list[dict[str, Any]] = []
    final_body: str | None = None
    additive_feature_types = {
        "main_link_body",
        "elongated_main_body",
        "main_housing",
        "support_frame",
        "palm_plate",
        "proximal_joint_housing",
        "distal_joint_housing",
        "bearing_boss",
        "mounting_boss",
        "flange",
        "tool_flange",
        "connector_housing",
        "tapered_transition",
        "lofted_transition",
        "blended_joint_transition",
        "rounded_section",
        "web",
        "rib",
        "cover_region",
        "strengthening_boss",
    }
    cutter_feature_types = {"recess", "cutout", "hollow_region", "slot", "gap", "lightening_cut"}
    modifier_feature_types = {"fillet_group", "chamfer_group"}

    additive_features = [f for f in features if f["feature_type"] in additive_feature_types]
    cutter_features = [f for f in features if f["feature_type"] in cutter_feature_types]
    modifier_features = [f for f in features if f["feature_type"] in modifier_feature_types]

    created_solids: list[str] = []
    idx = 1
    for feature in additive_features:
        new_ops, _ = feature_to_ops(feature, role, idx, created_solids, None)
        idx += 1
        if not new_ops:
            continue
        ops.extend(new_ops)
        if new_ops[-1]["op_type"] in {"extrude", "revolve", "loft", "sweep"}:
            created_solids.append(new_ops[-1]["op_id"])

    if len(created_solids) > 1:
        union_feature = {"feature_id": "AUTO_UNION", "feature_type": "assembly_union"}
        union_id = f"op_{idx:03d}"
        idx += 1
        ops.append(op(union_id, "boolean_union", created_solids[0], created_solids, union_feature, tool_bodies=created_solids[1:]))
        final_body = union_id
    elif len(created_solids) == 1:
        final_body = created_solids[0]

    for feature in cutter_features:
        if final_body is None:
            break
        new_ops, last = feature_to_ops(feature, role, idx, created_solids, final_body)
        idx += 1
        if not new_ops:
            continue
        ops.extend(new_ops)
        if last:
            final_body = last

    for feature in modifier_features:
        if final_body is None:
            break
        new_ops, last = feature_to_ops(feature, role, idx, created_solids, final_body)
        idx += 1
        if not new_ops:
            continue
        ops.extend(new_ops)
        if last:
            final_body = last
    if not ops:
        return {"ir_version": "executable_cad_ir_v1_1", "case_id": graph["case_id"], "link_id": graph["link_id"], "bodies": [], "operations": []}
    ir = {
        "ir_version": "executable_cad_ir_v1_1",
        "case_id": graph["case_id"],
        "link_id": graph["link_id"],
        "bodies": [{"body_id": "body", "role": role}],
        "operations": ops,
        "final_object": final_body or ops[-1]["op_id"],
    }
    jsonschema.validate(ir, SCHEMA)
    return ir


def copy_r0(row: dict[str, str]) -> None:
    src = Path("freecad_backend_pilot") / "runs" / row["case_id"] / row["link_id"] / "executable_cad_ir.json"
    dst = RUNS / "R0" / row["case_id"] / row["link_id"] / "executable_cad_ir.json"
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.exists():
        shutil.copyfile(src, dst)
        manifest = {"version": "R0", "case_id": row["case_id"], "link_id": row["link_id"], "status": "SUCCESS", "source": str(src)}
    else:
        manifest = {"version": "R0", "case_id": row["case_id"], "link_id": row["link_id"], "status": "IR_INCOMPLETE", "source": str(src), "errors": ["missing R0 baseline IR"]}
    dump_json(dst.parent / "manifest.json", manifest)


def main() -> None:
    ensure_dirs()
    rows = []
    for row in frozen_rows():
        copy_r0(row)
    for version in ["R1", "R2"]:
        for row in frozen_rows():
            graph_path = RUNS / version / row["case_id"] / row["link_id"] / "mechanical_feature_graph.json"
            out_dir = RUNS / version / row["case_id"] / row["link_id"]
            status = "SUCCESS"
            errors: list[str] = []
            op_count = 0
            if not graph_path.exists():
                status = "MFG_MISSING"
                errors = ["mechanical_feature_graph.json missing"]
            else:
                try:
                    ir = graph_to_ir(load_json(graph_path), row["role"])
                    op_count = len(ir["operations"])
                    dump_json(out_dir / "executable_cad_ir.json", ir)
                except Exception as exc:
                    status = "IR_INCOMPLETE"
                    errors = [f"{type(exc).__name__}: {exc}"]
            manifest = {"version": version, "case_id": row["case_id"], "link_id": row["link_id"], "status": status, "operation_count": op_count, "errors": errors}
            dump_json(out_dir / "ir_manifest.json", manifest)
            rows.append(manifest)
            print(version, row["case_id"], row["link_id"], status, op_count)
    write_csv(EXP / "results" / "ir_translation_results.csv", rows)


if __name__ == "__main__":
    main()
