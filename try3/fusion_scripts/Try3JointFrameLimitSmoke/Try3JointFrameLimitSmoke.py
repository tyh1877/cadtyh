"""Hard gate for the Try-3 Fusion executor: origin, axis, and limits.

This creates two editable components, places their as-built revolute joint at a
known non-zero world position, selects a root construction axis explicitly,
and reads the persisted native joint state back to JSON.  It does not consume
any benchmark case or ground-truth geometry.
"""
import adsk.core, adsk.fusion, json, os, traceback

ROOT = r"D:\CADtest\papertest"
OUT = os.path.join(ROOT, "try3", "joint_frame_limit_smoke_result.json")
EXPECTED_ORIGIN_CM = [2.0, 3.0, 4.0]
EXPECTED_AXIS = [0.0, 1.0, 0.0]
EXPECTED_LIMITS = [-1.25, 1.5]


def primitive_body(component):
    sketch = component.sketches.add(component.xYConstructionPlane)
    sketch.sketchCurves.sketchLines.addTwoPointRectangle(
        adsk.core.Point3D.create(-1, -1, 0), adsk.core.Point3D.create(1, 1, 0)
    )
    inp = component.features.extrudeFeatures.createInput(
        sketch.profiles.item(0), adsk.fusion.FeatureOperations.NewBodyFeatureOperation
    )
    inp.setDistanceExtent(False, adsk.core.ValueInput.createByReal(2))
    return component.features.extrudeFeatures.add(inp).bodies.item(0)


def point_geometry(root, origin_cm):
    """Make a persistent assembly-context point at a specified world location."""
    plane_input = root.constructionPlanes.createInput()
    plane_input.setByOffset(root.xYConstructionPlane, adsk.core.ValueInput.createByReal(origin_cm[2]))
    plane = root.constructionPlanes.add(plane_input)
    sketch = root.sketches.add(plane)
    point = sketch.sketchPoints.add(adsk.core.Point3D.create(origin_cm[0], origin_cm[1], 0))
    return adsk.fusion.JointGeometry.createByPoint(point)


def vector(v):
    return [float(v.x), float(v.y), float(v.z)]


def close(a, b, tol=1e-6):
    return all(abs(float(x) - float(y)) <= tol for x, y in zip(a, b))


def run(context):
    result = {"status": "FAILURE", "expected": {"origin_cm": EXPECTED_ORIGIN_CM, "axis": EXPECTED_AXIS, "limits_rad": EXPECTED_LIMITS}}
    try:
        app = adsk.core.Application.get()
        doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        design = adsk.fusion.Design.cast(app.activeProduct)
        design.designType = adsk.fusion.DesignTypes.ParametricDesignType
        root = design.rootComponent

        parent = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
        child_transform = adsk.core.Matrix3D.create()
        # Start two centimetres away from the intended joint origin.  A 90-degree
        # drive will make a wrong Z-axis implementation visibly distinguishable
        # from the requested world-Y implementation.
        child_transform.translation = adsk.core.Vector3D.create(4, 3, 4)
        child = root.occurrences.addNewComponent(child_transform)
        primitive_body(parent.component)
        primitive_body(child.component)

        geometry = point_geometry(root, EXPECTED_ORIGIN_CM)
        joint_input = root.asBuiltJoints.createInput(parent, child, geometry)
        # The root Y construction axis is an explicit persisted custom entity,
        # not an inferred cardinal direction from a body vertex.
        joint_input.setAsRevoluteJointMotion(
            adsk.fusion.JointDirections.CustomJointDirection, root.yConstructionAxis
        )
        joint = root.asBuiltJoints.add(joint_input)
        design.computeAll()

        motion = adsk.fusion.RevoluteJointMotion.cast(joint.jointMotion)
        limits = motion.rotationLimits
        limits.isMinimumValueEnabled = True
        limits.minimumValue = EXPECTED_LIMITS[0]
        limits.isMaximumValueEnabled = True
        limits.maximumValue = EXPECTED_LIMITS[1]
        design.computeAll()

        origin, _, _, z_axis = joint.transform.getAsCoordinateSystem()
        native_origin = [float(origin.x), float(origin.y), float(origin.z)]
        # `rotationAxisVector` is expressed in Fusion's joint-local frame.  The
        # persisted CustomJointDirection entity is the authoritative world-axis
        # evidence, and a driven pose checks that Fusion uses it physically.
        custom_entity = motion.customRotationAxisEntity
        custom_axis = vector(custom_entity.geometry.direction) if custom_entity else None
        motion.rotationValue = 1.5707963267948966
        design.computeAll()
        driven = child.transform.translation
        driven_origin = [float(driven.x), float(driven.y), float(driven.z)]
        persisted = {
            "origin_cm": native_origin,
            "rotation_axis_local": vector(motion.rotationAxisVector),
            "rotation_axis_mode": int(motion.rotationAxis),
            "custom_axis_entity_direction": custom_axis,
            "driven_child_origin_cm": driven_origin,
            "limits_rad": [float(limits.minimumValue), float(limits.maximumValue)],
            "minimum_enabled": bool(limits.isMinimumValueEnabled),
            "maximum_enabled": bool(limits.isMaximumValueEnabled),
            "joint_frame_z_axis": vector(z_axis),
            "motion_type": joint.jointMotion.objectType,
            "joint_count": root.asBuiltJoints.count,
        }
        # Axis direction is equivalent up to a sign for a revolute DOF.  The
        # driven position must remain at Y=3 while leaving the X axis, which is
        # impossible for a world-Z rotation in this setup.
        custom_mode = motion.rotationAxis == adsk.fusion.JointDirections.CustomJointDirection
        axis_match = custom_mode and custom_axis is not None and (close(custom_axis, EXPECTED_AXIS) or close(custom_axis, [-x for x in EXPECTED_AXIS])) and abs(driven_origin[1] - 3.0) < 1e-6 and abs(driven_origin[0] - 2.0) < 1e-4 and abs(abs(driven_origin[2] - 4.0) - 2.0) < 1e-4
        origin_match = close(native_origin, EXPECTED_ORIGIN_CM)
        limit_match = close(persisted["limits_rad"], EXPECTED_LIMITS) and persisted["minimum_enabled"] and persisted["maximum_enabled"]
        result.update({"persisted": persisted, "checks": {"origin": origin_match, "axis": axis_match, "limits": limit_match}, "status": "SUCCESS" if origin_match and axis_match and limit_match else "FAILURE", "native_document_name": doc.name})
    except:
        result["traceback"] = traceback.format_exc()
    with open(OUT, "w") as handle:
        json.dump(result, handle, indent=2)
    try:
        app.userInterface.messageBox("Try-3 joint frame/limit smoke finished: " + result["status"])
    except:
        pass
