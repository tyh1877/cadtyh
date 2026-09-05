"""Execute one frozen Codex-agent Try-3 case inside FreeCAD's Python runtime."""
from __future__ import annotations

import json
import sys
import time
import traceback
from pathlib import Path

import FreeCAD  # type: ignore
import Import  # type: ignore
import Mesh  # type: ignore
import Part  # type: ignore


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def placement(matrix_values):
    matrix = FreeCAD.Matrix()
    for row in range(4):
        for col in range(4):
            setattr(matrix, f"A{row + 1}{col + 1}", float(matrix_values[row][col]))
    return FreeCAD.Placement(matrix)


def main(job_path: Path) -> int:
    job = json.loads(job_path.read_text(encoding="utf-8"))
    root = Path(job["repo_root"])
    sys.path.insert(0, str(root))
    from robotcad.backends.freecad_api.FreeCADBackend import execute_ir  # noqa: E402

    output = Path(job["output_dir"])
    result_path = Path(job["result_path"])
    started = time.time()
    result = {
        "case_id": job["case_id"], "version": job["version"], "status": "FAILURE",
        "link_results": [], "assembly": {}, "error_type": "", "error": "",
        "traceback": "", "elapsed_seconds": 0.0,
    }
    assembly_doc = None
    try:
        for link in job["links"]:
            link_id = link["link_id"]
            link_output = output / "links" / link_id / "freecad"
            ir = json.loads(Path(link["ir_path"]).read_text(encoding="utf-8"))
            link_result = execute_ir(ir, link_output)
            write_json(link_output / "execution_log.json", link_result["execution_log"])
            write_json(link_output / "feature_manifest.json", link_result["feature_manifest"])
            write_json(link_output / "object_tree.json", link_result["object_tree"])
            write_json(link_output / "execution_result.json", {key: value for key, value in link_result.items() if key not in {"execution_log", "feature_manifest", "object_tree"}})
            result["link_results"].append({
                "link_id": link_id, "status": link_result["status"], "error": link_result.get("error") or "",
                "operation_count": len(ir["operations"]),
                "native_success_count": sum(bool(item.get("success")) for item in link_result["execution_log"]),
                "fallback_count": sum(bool(item.get("fallback_used")) for item in link_result["execution_log"]),
                "exports": link_result.get("exports") or {},
            })
        failures = [item for item in result["link_results"] if item["status"] != "SUCCESS"]
        if failures:
            raise RuntimeError(f"LINK_EXECUTION_FAILURES:{[(x['link_id'], x['error']) for x in failures]}")

        assembly_doc = FreeCAD.newDocument(f"{job['case_id']}_{job['version']}_assembly")
        components = []
        component_dir = output / "assembly" / "components"
        component_dir.mkdir(parents=True, exist_ok=True)
        for link in job["links"]:
            link_id = link["link_id"]
            step_path = output / "links" / link_id / "freecad" / "model.step"
            shape = Part.read(str(step_path))
            if shape.isNull() or not shape.isValid():
                raise RuntimeError(f"INVALID_LINK_STEP:{link_id}")
            obj = assembly_doc.addObject("Part::Feature", f"Component_{link_id}")
            obj.Label = link_id
            obj.addProperty("App::PropertyString", "RobotCADLinkId", "RobotCAD")
            obj.RobotCADLinkId = link_id
            obj.addProperty("App::PropertyString", "PlacementAuthority", "RobotCAD")
            obj.PlacementAuthority = "sanitized_urdf"
            obj.Shape = shape
            obj.Placement = placement(link["world_transform_mm"])
            components.append(obj)
            Mesh.export([obj], str(component_dir / f"{link_id}.stl"))
        for joint in job["joints"]:
            ref = assembly_doc.addObject("App::FeaturePython", f"JointRef_{joint['joint_id']}")
            ref.Label = joint["joint_id"]
            ref.addProperty("App::PropertyString", "ParentLink", "RobotCAD")
            ref.addProperty("App::PropertyString", "ChildLink", "RobotCAD")
            ref.addProperty("App::PropertyString", "JointType", "RobotCAD")
            ref.addProperty("App::PropertyVector", "LocalOriginMm", "RobotCAD")
            ref.addProperty("App::PropertyVector", "LocalAxis", "RobotCAD")
            ref.ParentLink, ref.ChildLink, ref.JointType = joint["parent"], joint["child"], joint["joint_type"]
            ref.LocalOriginMm = FreeCAD.Vector(*joint["origin_xyz_mm"])
            ref.LocalAxis = FreeCAD.Vector(*joint["axis"])
        assembly_doc.recompute()
        assembly_dir = output / "assembly"
        assembly_dir.mkdir(parents=True, exist_ok=True)
        fcstd = assembly_dir / "assembly.FCStd"
        step = assembly_dir / "assembly.step"
        stl = assembly_dir / "assembly.stl"
        assembly_doc.saveAs(str(fcstd))
        Import.export(components, str(step))
        Mesh.export(components, str(stl))
        valid_components = sum(not obj.Shape.isNull() and obj.Shape.isValid() for obj in components)
        result["assembly"] = {
            "component_count": len(components), "valid_component_count": valid_components,
            "joint_reference_count": len(job["joints"]),
            "fcstd": str(fcstd), "step": str(step), "stl": str(stl),
            "fcstd_exists": fcstd.is_file(), "step_exists": step.is_file(), "stl_exists": stl.is_file(),
            "component_mesh_dir": str(component_dir), "placement_source": "sanitized_urdf",
        }
        if valid_components != len(job["links"]) or not all(result["assembly"][key] for key in ["fcstd_exists", "step_exists", "stl_exists"]):
            raise RuntimeError("ASSEMBLY_VALIDATION_FAILURE")
        result["status"] = "SUCCESS"
    except Exception as exc:
        result["error_type"] = type(exc).__name__
        result["error"] = str(exc)
        result["traceback"] = traceback.format_exc()
    finally:
        result["elapsed_seconds"] = time.time() - started
        write_json(result_path, result)
        if assembly_doc is not None:
            FreeCAD.closeDocument(assembly_doc.Name)
    return 0 if result["status"] == "SUCCESS" else 1


if __name__ == "__main__":
    raise SystemExit(main(Path(sys.argv[-1]).resolve()))

