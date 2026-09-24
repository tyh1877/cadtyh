"""D1-T0 diagnostic volumetric semantics. No CAD or KFDE policy changes."""

from __future__ import annotations

from dataclasses import asdict, dataclass

EPSILON_MM3 = 1e-6  # Frozen C2/D1 numerical tolerance.


@dataclass(frozen=True)
class ShapeState:
    state: str
    volume_mm3: float
    solid_count: int
    shell_count: int
    face_count: int
    is_null: bool
    is_valid: bool
    can_boolean_cut: bool
    empty_reason: str | None = None
    below_tolerance_volumetric: bool = False

    def record(self):
        return asdict(self)


def classify_volumetric_shape(shape, *, verified_derived_empty=False, tolerance_mm3=EPSILON_MM3):
    """Fail closed unless empty provenance has been verified by the caller.

    A real solid remains volumetric even when its volume is below epsilon.
    Boundary-only residues may be empty only after verified subtraction.
    """
    if tolerance_mm3 != EPSILON_MM3:
        raise ValueError("D1/C2 frozen tolerance drift")
    if shape is None:
        return ShapeState("INVALID_BREP", 0.0, 0, 0, 0, True, False, False)
    try:
        null = bool(shape.isNull())
        if null:
            state = "EFFECTIVELY_EMPTY" if verified_derived_empty else "INVALID_BREP"
            reason = "TRUE_NULL_RESULT" if verified_derived_empty else None
            return ShapeState(state, 0.0, 0, 0, 0, True, verified_derived_empty, False, reason)
        valid = bool(shape.isValid())
        solids = list(shape.Solids)
        shells = len(shape.Shells)
        faces = len(shape.Faces)
        volume = float(shape.Volume)
        if not valid or volume < 0 or any(not s.isValid() for s in solids):
            return ShapeState("INVALID_BREP", volume, len(solids), shells, faces, False, False, False)
        volumetric = [s for s in solids if float(s.Volume) > 0]
        if len(volumetric) != len(solids):
            return ShapeState("INVALID_BREP", volume, len(solids), shells, faces, False, True, False)
        if solids:
            state = "VALID_SINGLE_SOLID" if len(solids) == 1 else "VALID_MULTI_SOLID"
            return ShapeState(state, volume, len(solids), shells, faces, False, True, True,
                              below_tolerance_volumetric=volume <= tolerance_mm3)
        if volume <= tolerance_mm3 and verified_derived_empty:
            return ShapeState("EFFECTIVELY_EMPTY", 0.0, 0, shells, faces, False, True, False,
                              "NO_VOLUMETRIC_SOLID_AFTER_ALLOWED_REGION_REMOVAL")
        if shells or faces:
            return ShapeState("NONVOLUMETRIC_ONLY", volume, 0, shells, faces, False, True, False)
        return ShapeState("INVALID_BREP", volume, 0, 0, 0, False, True, False)
    except (AttributeError, RuntimeError, ValueError, TypeError):
        return ShapeState("INVALID_BREP", 0.0, 0, 0, 0, False, False, False)


def safe_diagnostic_cut(a, b, *, a_derived_empty=False, b_derived_empty=False):
    """Return shape and explicit branch; only solid/solid reaches OCC.cut."""
    a_state = classify_volumetric_shape(a, verified_derived_empty=a_derived_empty)
    b_state = classify_volumetric_shape(b, verified_derived_empty=b_derived_empty)
    if "INVALID_BREP" in (a_state.state, b_state.state):
        raise ValueError("INVALID_BREP: diagnostic cut refused")
    if "NONVOLUMETRIC_ONLY" in (a_state.state, b_state.state):
        raise ValueError("NONVOLUMETRIC_ONLY: no volumetric cut")
    if a_state.state == "EFFECTIVELY_EMPTY":
        return a, "EMPTY_A_NO_OCC_CUT"
    if b_state.state == "EFFECTIVELY_EMPTY":
        return a, "EMPTY_B_NO_OCC_CUT"
    return a.cut(b), "OCC_CUT_EXECUTED"


def empty_intersection_record(component_id, mutable_state):
    if mutable_state.state != "EFFECTIVELY_EMPTY":
        raise ValueError("not an empty mutable geometry")
    return {"component_id": component_id, "intersection_volume_mm3": 0.0,
            "violation": False, "status": "EMPTY_MUTABLE_GEOMETRY"}


def empty_witness_record(mutable_state):
    if mutable_state.state != "EFFECTIVELY_EMPTY":
        raise ValueError("not an empty mutable geometry")
    return {"mutable_volume_mm3": 0.0, "removed_mutable_volume_mm3": 0.0,
            "removed_ratio": "NOT_APPLICABLE_EMPTY_MUTABLE",
            "mutable_carrier_connectivity": "NOT_APPLICABLE_EMPTY_MUTABLE"}
