"""Fusion in-application smoke test for RobotCAD Try-2.

Run from Fusion: Utilities > Scripts and Add-Ins > Scripts > Try2FusionSmoke.
It creates native parametric components and attempts one as-built revolute joint,
then exports F3D/STEP/STL and writes an auditable JSON report.  It never imports
experiment geometry or accesses any GT data.
"""

import json
import os
import traceback

import adsk.core
import adsk.fusion


OUTPUT = r"D:\CADtest\papertest\try2\fusion_smoke"


def _component(root, name, x_offset_cm):
    transform = adsk.core.Matrix3D.create()
    transform.translation = adsk.core.Vector3D.create(x_offset_cm, 0, 0)
    occurrence = root.occurrences.addNewComponent(transform)
    component = occurrence.component
    component.name = name
    sketch = component.sketches.add(component.xYConstructionPlane)
    sketch.name = f"{name}_profile"
    sketch.sketchCurves.sketchCircles.addByCenterRadius(
        adsk.core.Point3D.create(0, 0, 0), 2.0
    )
    profile = sketch.profiles.item(0)
    extrude_input = component.features.extrudeFeatures.createInput(
        profile, adsk.fusion.FeatureOperations.NewBodyFeatureOperation
    )
    extrude_input.setDistanceExtent(False, adsk.core.ValueInput.createByReal(6.0))
    feature = component.features.extrudeFeatures.add(extrude_input)
    feature.name = f"{name}_extrude"
    return occurrence, component


def run(context):
    report = {"fusion_document_valid": False, "native_save_success": False,
              "step_export_success": False, "stl_export_success": False,
              "joint_create_success": False, "errors": []}
    try:
        os.makedirs(OUTPUT, exist_ok=True)
        app = adsk.core.Application.get()
        report["fusion_version"] = app.version
        document = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        design = adsk.fusion.Design.cast(app.activeProduct)
        root = design.rootComponent
        occ0, comp0 = _component(root, "L0", 0.0)
        occ1, comp1 = _component(root, "L1", 8.0)
        report["component_count"] = root.occurrences.count
        report["feature_count"] = (comp0.features.extrudeFeatures.count + comp1.features.extrudeFeatures.count)
        try:
            joint_input = root.asBuiltJoints.createInput(occ0, occ1, None)
            joint_input.setAsRevoluteJointMotion(
                adsk.fusion.JointDirections.ZAxisJointDirection
            )
            root.asBuiltJoints.add(joint_input)
            report["joint_create_success"] = True
        except Exception:
            report["errors"].append("joint: " + traceback.format_exc())
        report["joint_count"] = root.asBuiltJoints.count
        export_manager = design.exportManager
        f3d_path = os.path.join(OUTPUT, "try2_fusion_smoke.f3d")
        step_path = os.path.join(OUTPUT, "try2_fusion_smoke.step")
        stl_path = os.path.join(OUTPUT, "try2_fusion_smoke.stl")
        try:
            export_manager.execute(export_manager.createFusionArchiveExportOptions(f3d_path, root))
            report["native_save_success"] = os.path.isfile(f3d_path)
        except Exception:
            report["errors"].append("f3d: " + traceback.format_exc())
        try:
            export_manager.execute(export_manager.createSTEPExportOptions(step_path, root))
            report["step_export_success"] = os.path.isfile(step_path)
        except Exception:
            report["errors"].append("step: " + traceback.format_exc())
        try:
            export_manager.execute(export_manager.createSTLExportOptions(root, stl_path))
            report["stl_export_success"] = os.path.isfile(stl_path)
        except Exception:
            report["errors"].append("stl: " + traceback.format_exc())
        report["fusion_document_valid"] = bool(root and document and report["component_count"] == 2)
    except Exception:
        report["errors"].append("fatal: " + traceback.format_exc())
    with open(os.path.join(OUTPUT, "fusion_smoke_audit.json"), "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    adsk.core.Application.get().userInterface.messageBox(
        "Try-2 Fusion smoke test finished. Audit written to:\n" + OUTPUT
    )
