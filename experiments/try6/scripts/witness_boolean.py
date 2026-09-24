"""Exact-BREP clearance witness primitives for W0; no scientific thresholds."""

from __future__ import annotations

import math

import Part

from volumetric_geometry_state import classify_volumetric_shape, safe_diagnostic_cut


def volumetric_state(shape, *, derived=False):
    result = classify_volumetric_shape(shape, verified_derived_empty=derived)
    if result.state in ("INVALID_BREP", "NONVOLUMETRIC_ONLY"):
        raise ValueError("unsupported Boolean geometry state: " + result.state)
    if not math.isfinite(result.volume_mm3):
        raise ValueError("non-finite BREP volume")
    return result


def exact_union(components):
    """Stable ordered OCC fuse; no arithmetic sum and no splitter cleanup."""
    if not components:
        return Part.Shape(), {"component_count": 0, "steps": []}
    current = components[0].copy()
    volumetric_state(current)
    steps = []
    for index, shape in enumerate(components[1:], 1):
        volumetric_state(shape)
        current = current.fuse(shape)
        current_state = volumetric_state(current)
        steps.append({"index": index, "volume_mm3": current_state.volume_mm3,
                      "solid_count": current_state.solid_count, "valid": current_state.is_valid})
    return current, {"component_count": len(components), "steps": steps}


def accounting_limit(policy, source_volume):
    return policy["absolute_mm3"] + policy["relative"] * max(1.0, source_volume)


def optional_splitter_cleanup(shape, operation=None):
    """Return diagnostic refined copy or a failure status; never replace raw."""
    operation = operation or shape.removeSplitter
    try:
        refined = operation()
    except Part.OCCError as exc:
        return None, "OPTIONAL_CLEANUP_FAILED: " + str(exc)
    if not volumetric_state(refined).can_boolean_cut:
        return None, "OPTIONAL_CLEANUP_INVALID_RESULT"
    return refined, "OPTIONAL_CLEANUP_SUCCEEDED"


def build_clearance_witness(mutable_body, keepout_components, tolerance_policy, *, path):
    """Return raw exact witness/unique removed BREP and independent invariants."""
    if path not in ("UNION_THEN_SINGLE_CUT", "ORDERED_SEQUENTIAL_CUT"):
        raise ValueError("undeclared construction path")
    source_state = volumetric_state(mutable_body, derived=True)
    union, union_trace = exact_union(keepout_components)
    union_state = volumetric_state(union, derived=not keepout_components)
    if path == "UNION_THEN_SINGLE_CUT":
        witness, cut_branch = safe_diagnostic_cut(mutable_body, union,
            a_derived_empty=source_state.state == "EFFECTIVELY_EMPTY",
            b_derived_empty=union_state.state == "EFFECTIVELY_EMPTY")
    else:
        witness = mutable_body.copy()
        branches = []
        for component in keepout_components:
            current = volumetric_state(witness, derived=True)
            witness, branch = safe_diagnostic_cut(witness, component,
                a_derived_empty=current.state == "EFFECTIVELY_EMPTY")
            branches.append(branch)
        cut_branch = branches
    witness_state = volumetric_state(witness, derived=True)
    if source_state.state == "EFFECTIVELY_EMPTY":
        removed = Part.Shape()
        outside_source = 0.0
        residual_keepout = 0.0
    else:
        removed = mutable_body.common(union)
        if witness_state.state == "EFFECTIVELY_EMPTY":
            outside_source = 0.0
            residual_keepout = 0.0
        else:
            outside_source = float(witness.cut(mutable_body).Volume)
            residual_keepout = float(witness.common(union).Volume)
    removed_state = volumetric_state(removed, derived=True)
    source_volume = source_state.volume_mm3
    witness_volume = witness_state.volume_mm3
    removed_volume = removed_state.volume_mm3
    subtraction_difference = source_volume - witness_volume
    conservation_error = abs(source_volume - witness_volume - removed_volume)
    removed_consistency_error = abs(subtraction_difference - removed_volume)
    limit = accounting_limit(tolerance_policy, source_volume)
    metrics = {"path": path, "source_state": source_state.record(),
        "keepout_union_state": union_state.record(), "witness_state": witness_state.record(),
        "removed_state": removed_state.record(), "union_trace": union_trace,
        "cut_branch": cut_branch, "source_volume_mm3": source_volume,
        "keepout_union_volume_mm3": union_state.volume_mm3,
        "witness_volume_mm3": witness_volume, "removed_unique_volume_mm3": removed_volume,
        "volume_difference_mm3": subtraction_difference,
        "outside_source_residual_mm3": outside_source,
        "residual_keepout_intersection_mm3": residual_keepout,
        "conservation_error_mm3": conservation_error,
        "removed_consistency_error_mm3": removed_consistency_error,
        "accounting_limit_mm3": limit,
        "invariants_pass": all(v <= limit for v in (outside_source, residual_keepout,
                                                        conservation_error, removed_consistency_error))}
    return witness, removed, union, metrics
