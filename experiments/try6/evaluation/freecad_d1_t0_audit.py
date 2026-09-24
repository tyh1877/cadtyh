"""FreeCAD-only, read-only D1-T0 geometry audit; no scientific evaluator calls."""

from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

import FreeCAD as App
import Part

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "experiments/try6/scripts"))
from volumetric_geometry_state import (EPSILON_MM3, classify_volumetric_shape,
    empty_intersection_record, empty_witness_record, safe_diagnostic_cut)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check(name, condition, detail=None):
    tests.append({"test": name, "pass": bool(condition), "detail": detail})


def state(shape, derived=False):
    return classify_volumetric_shape(shape, verified_derived_empty=derived)


def roundtrip(name, shape, derived, scratch):
    before = [state(shape, derived).record() for _ in range(3)]
    path = scratch / (name + ".brep")
    shape.exportBrep(str(path))
    reopened = Part.read(str(path))
    after = [state(reopened, derived).record() for _ in range(3)]
    within_path_stable = (len({json.dumps(x, sort_keys=True) for x in before}) == 1 and
                          len({json.dumps(x, sort_keys=True) for x in after}) == 1)
    record = {"name": name, "brep_sha256": sha(path), "before": before[0],
              "after": after[0], "repeated_deterministic": within_path_stable,
              "state_parity": before[0]["state"] == after[0]["state"],
              "solid_count_parity": before[0]["solid_count"] == after[0]["solid_count"],
              "serialization_volume_delta_mm3": after[0]["volume_mm3"] - before[0]["volume_mm3"],
              "volume_parity_within_frozen_tolerance": abs(after[0]["volume_mm3"] - before[0]["volume_mm3"]) <= EPSILON_MM3}
    roundtrips.append(record)
    return record


def main(job):
    global tests, roundtrips
    tests, roundtrips = [], []
    cfg = read(ROOT / job["d1_protocol"])
    construction = read(ROOT / cfg["kfde_construction"])
    scratch = ROOT / job["scratch"]
    scratch.mkdir(parents=True, exist_ok=True)
    allowed_path = ROOT / construction["allowed_region"]["path"]
    if sha(allowed_path) != construction["allowed_region"]["sha256"]:
        raise RuntimeError("frozen allowed BREP hash drift")
    allowed = Part.read(str(allowed_path))
    allowed_state = state(allowed)
    check("frozen_tolerance", cfg["kfde_numerical_epsilon_mm3"] == EPSILON_MM3)
    check("allowed_region_volumetric", allowed_state.can_boolean_cut)

    rows = []
    retained_shapes = {}
    for item in cfg["geometry_set"]:
        path = ROOT / item["path"]
        doc = App.openDocument(str(path))
        full_obj = doc.getObject("RigidGroup")
        if full_obj is None:
            raise RuntimeError("missing full RigidGroup: " + item["geometry_id"])
        full = full_obj.Shape.copy()
        mutable_obj = doc.getObject(item["mutable_object"])
        if item["mutable_object"] == "RigidGroup_minus_frozen_allowed_region":
            mutable, branch = safe_diagnostic_cut(full, allowed)
            derivation = "full_link_minus_frozen_allowed_region"
        else:
            if mutable_obj is None:
                raise RuntimeError("missing frozen mutable object: " + item["geometry_id"])
            mutable = mutable_obj.Shape.copy()
            branch = "EXACT_FROZEN_OBJECT"
            derivation = "exact_FrozenMatingEnvelopeCut_object"
        scaffold_obj = doc.getObject("FrozenScaffold")
        scaffold = scaffold_obj.Shape.copy() if scaffold_obj else None
        App.closeDocument(doc.Name)
        full_state = state(full)
        # Provenance verification occurs from the source extraction and the
        # independent coverage computation, not from geometry ID.
        uncovered, _ = safe_diagnostic_cut(full, allowed)
        coverage = float(full.common(allowed).Volume)
        complete_coverage = (len(uncovered.Solids) == 0
                             and float(uncovered.Volume) <= EPSILON_MM3)
        verified_empty = (derivation == "full_link_minus_frozen_allowed_region"
                          and full_state.can_boolean_cut and allowed_state.can_boolean_cut
                          and complete_coverage)
        mutable_state = state(mutable, verified_empty)
        row = {"geometry_id": item["geometry_id"], "source_path": item["path"],
               "source_sha256": sha(path), "extraction": derivation,
               "extraction_branch": branch, "full": full_state.record(),
               "mutable": mutable_state.record(), "allowed": allowed_state.record(),
               "scaffold": state(scaffold).record() if scaffold is not None else None,
               "coverage_volume_mm3": coverage, "full_minus_allowed_volume_mm3": float(uncovered.Volume),
               "common_minus_full_volume_mm3": coverage - full_state.volume_mm3,
               "common_volume_numerical_warning": abs(coverage - full_state.volume_mm3) > EPSILON_MM3,
               "complete_allowed_coverage": complete_coverage,
               "verified_empty_provenance": verified_empty}
        rows.append(row)
        retained_shapes[item["geometry_id"]] = (full, mutable, verified_empty)
    check("five_sources_open_and_classify", len(rows) == 5 and all(r["full"]["can_boolean_cut"] for r in rows))
    check("G1_G4_volumetric", rows[0]["mutable"]["can_boolean_cut"] and rows[3]["mutable"]["can_boolean_cut"])
    g5 = rows[4]
    check("G5_full_vs_mutable", g5["full"]["can_boolean_cut"] and g5["mutable"]["state"] == "EFFECTIVELY_EMPTY")
    check("G5_provenance_coverage", g5["verified_empty_provenance"] and g5["complete_allowed_coverage"])

    null = Part.Shape()
    single = Part.makeBox(1, 1, 1)
    multi = Part.makeCompound([Part.makeBox(1, 1, 1), Part.makeBox(1, 1, 1, App.Vector(3, 0, 0))])
    derived, _ = safe_diagnostic_cut(single, single)
    face = Part.makePlane(1, 1)
    fixtures = {"S0_NULL": (null, True, "EFFECTIVELY_EMPTY"),
                "S1_SINGLE": (single, False, "VALID_SINGLE_SOLID"),
                "S2_MULTI": (multi, False, "VALID_MULTI_SOLID"),
                "S3_DERIVED_EMPTY": (derived, True, "EFFECTIVELY_EMPTY"),
                "S4_FACE": (face, False, "NONVOLUMETRIC_ONLY")}
    for factor, label in ((0.5, "S5_HALF_EPS"), (1.0, "S5_EXACT_EPS"), (2.0, "S6_DOUBLE_EPS")):
        side = (factor * EPSILON_MM3) ** (1.0 / 3.0)
        fixtures[label] = (Part.makeBox(side, side, side), False, "VALID_SINGLE_SOLID")
    fixture_rows = []
    for name, (shape, derived_context, expected) in fixtures.items():
        actual = state(shape, derived_context)
        fixture_rows.append({"fixture": name, "expected": expected, "observed": actual.record()})
        check("fixture_" + name, actual.state == expected, actual.record())
    check("null_without_provenance_fail_closed", state(null).state == "INVALID_BREP")
    check("missing_shape_invalid", state(None).state == "INVALID_BREP")
    # A corrupt serialized BREP must fail on read, rather than being promoted
    # to legitimate empty. This does not forge an invalid OCC object.
    corrupt = scratch / "S7_corrupt.brep"
    corrupt.write_bytes(b"not a BREP\n")
    try:
        corrupt_rejected = state(Part.read(str(corrupt))).state == "INVALID_BREP"
    except Exception:
        corrupt_rejected = True
    check("corrupt_brep_rejected", corrupt_rejected)
    check("tiny_real_solids_not_empty", all(state(fixtures[k][0]).state == "VALID_SINGLE_SOLID"
                                         for k in ("S5_HALF_EPS", "S5_EXACT_EPS", "S6_DOUBLE_EPS")))
    empty_a, branch_a = safe_diagnostic_cut(derived, single, a_derived_empty=True)
    unchanged_b, branch_b = safe_diagnostic_cut(single, derived, b_derived_empty=True)
    check("empty_A_no_OCC", branch_a == "EMPTY_A_NO_OCC_CUT" and state(empty_a, True).state == "EFFECTIVELY_EMPTY")
    check("empty_B_unchanged", branch_b == "EMPTY_B_NO_OCC_CUT" and abs(unchanged_b.Volume - single.Volume) < 1e-12)
    try:
        safe_diagnostic_cut(face, single)
        face_refused = False
    except ValueError:
        face_refused = True
    check("nonvolumetric_cut_fail_closed", face_refused)
    try:
        safe_diagnostic_cut(None, single)
        invalid_refused = False
    except ValueError:
        invalid_refused = True
    check("invalid_cut_fail_closed", invalid_refused)

    for gid in ("G1_C1_FINAL", "G4_C0_DIRECT", "G5_F0_COARSE"):
        full, mutable, verified = retained_shapes[gid]
        roundtrip(gid + "_mutable", mutable, verified, scratch)
    roundtrip("S3_DERIVED_EMPTY", derived, True, scratch)
    roundtrip("S1_SINGLE", single, False, scratch)
    check("all_roundtrips_state_and_repeat", all(r["state_parity"] and r["solid_count_parity"] and
          r["volume_parity_within_frozen_tolerance"] and r["repeated_deterministic"] for r in roundtrips))
    # Reopen the previously frozen D1 BREP independently of the current export.
    prior = read(ROOT / job["frozen_geometry_set"])
    cross_paths = []
    for frozen in prior["geometries"]:
        gid = frozen["geometry_id"]
        current = next(r for r in rows if r["geometry_id"] == gid)
        saved_path = ROOT / frozen["mutable_brep_path"]
        if sha(saved_path) != frozen["mutable_brep_sha256"]:
            raise RuntimeError("D1 frozen BREP drift: " + gid)
        reopened = Part.read(str(saved_path))
        observed = state(reopened, current["verified_empty_provenance"])
        cross_paths.append({"geometry_id": gid, "prior_brep_sha256": sha(saved_path),
                            "fcstd_state": current["mutable"]["state"], "prior_brep_state": observed.state,
                            "state_parity": current["mutable"]["state"] == observed.state})
    check("G5_frozen_brep_cross_path", cross_paths[4]["state_parity"])
    check("all_five_cross_path", all(x["state_parity"] for x in cross_paths))
    _, g5_mutable, verified = retained_shapes["G5_F0_COARSE"]
    g5_reopened = Part.read(str(ROOT / prior["geometries"][4]["mutable_brep_path"]))
    _, g5_cut_branch = safe_diagnostic_cut(g5_reopened, allowed, a_derived_empty=verified)
    check("G5_deserialized_no_illegal_cut", g5_cut_branch == "EMPTY_A_NO_OCC_CUT")
    intersection_rows = [empty_intersection_record(c["component_id"], state(g5_reopened, verified))
                         for c in construction["components"]]
    check("empty_intersection_denominator_retained", len(intersection_rows) == 13 and
          all(r["status"] == "EMPTY_MUTABLE_GEOMETRY" for r in intersection_rows))
    witness = empty_witness_record(state(g5_reopened, verified))
    check("empty_witness_ratio_NA", witness["removed_ratio"] == "NOT_APPLICABLE_EMPTY_MUTABLE")
    check("no_dummy_geometry", state(g5_reopened, verified).solid_count == 0 and
          state(derived, True).solid_count == 0)
    result = {"freecad_version": App.Version(), "occ_version": getattr(Part, "OCC_VERSION", None),
              "geometry_states": rows, "synthetic_fixtures": fixture_rows,
              "roundtrips": roundtrips, "cross_paths": cross_paths,
              "g5_boolean_trace": {"branch": g5_cut_branch, "state": state(g5_reopened, verified).record()},
              "synthetic_boolean": {"empty_A": branch_a, "empty_B": branch_b,
                                    "nonvolumetric_refused": face_refused, "invalid_refused": invalid_refused},
              "empty_intersection_rows": intersection_rows, "empty_witness_semantics": witness,
              "tests": tests, "all_tests_pass": all(t["pass"] for t in tests),
              "VLM_calls": 0, "GT_evaluations": 0, "final_96_case_mechanics_evaluations": 0}
    out = ROOT / job["output"]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"tests": len(tests), "passed": sum(t["pass"] for t in tests),
                      "G5_state": g5["mutable"]["state"]}))


if __name__ == "__main__":
    main(read(sys.argv[1]))
