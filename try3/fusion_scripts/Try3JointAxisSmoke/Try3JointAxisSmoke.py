"""Verify a non-cardinal URDF-style axis can be represented by an as-built Fusion joint."""
import adsk.core, adsk.fusion, json, os, traceback

ROOT = r"D:\CADtest\papertest"
OUT = os.path.join(ROOT, "try3", "axis_smoke_result.json")


def box(comp, x):
    sketch = comp.sketches.add(comp.xYConstructionPlane)
    sketch.sketchCurves.sketchLines.addTwoPointRectangle(
        adsk.core.Point3D.create(x - 1, -1, 0), adsk.core.Point3D.create(x + 1, 1, 0)
    )
    inp = comp.features.extrudeFeatures.createInput(
        sketch.profiles.item(0), adsk.fusion.FeatureOperations.NewBodyFeatureOperation
    )
    inp.setDistanceExtent(False, adsk.core.ValueInput.createByReal(2))
    return comp.features.extrudeFeatures.add(inp).bodies.item(0)


def run(context):
    result = {"status": "FAILURE", "custom_axis_requested": [0.0, 1.0, 0.0]}
    try:
        app = adsk.core.Application.get()
        doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        design = adsk.fusion.Design.cast(app.activeProduct)
        # A new Fusion document can default to Direct Design. Both parametric
        # construction points and AsBuiltJoint require Parametric Design.
        design.designType = adsk.fusion.DesignTypes.ParametricDesignType
        root = design.rootComponent
        parent_occ = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
        child_transform = adsk.core.Matrix3D.create(); child_transform.translation = adsk.core.Vector3D.create(0, 0, 3)
        child_occ = root.occurrences.addNewComponent(child_transform)
        parent_body, child_body = box(parent_occ.component, 0), box(child_occ.component, 0)
        # Parametric construction points make a custom joint axis legal in
        # parametric design, where AsBuiltJoint is supported.
        points = root.constructionPoints
        point_input = points.createInput()
        point_input.setByPoint(adsk.core.Point3D.create(0, 0, 3))
        axis_start = points.add(point_input)
        point_input = points.createInput()
        point_input.setByPoint(adsk.core.Point3D.create(0, 1, 3))
        axis_end = points.add(point_input)
        axes = root.constructionAxes
        axis_input = axes.createInput()
        axis_input.setByTwoPoints(axis_start, axis_end)
        custom_axis = axes.add(axis_input)
        geometry = adsk.fusion.JointGeometry.createByPoint(
            child_body.vertices.item(0).createForAssemblyContext(child_occ)
        )
        joint_input = root.asBuiltJoints.createInput(parent_occ, child_occ, geometry)
        joint_input.setAsRevoluteJointMotion(adsk.fusion.JointDirections.CustomJointDirection, custom_axis)
        joint = root.asBuiltJoints.add(joint_input)
        design.computeAll()
        result.update({
            "status": "SUCCESS",
            "joint_count": root.asBuiltJoints.count,
            "joint_motion_type": joint.jointMotion.objectType,
            "rebuild_success": True,
            "native_document_name": doc.name,
        })
    except:
        result["traceback"] = traceback.format_exc()
    with open(OUT, "w") as handle:
        json.dump(result, handle, indent=2)
    try:
        app.userInterface.messageBox("Try-3 axis smoke finished: " + result["status"])
    except:
        pass
