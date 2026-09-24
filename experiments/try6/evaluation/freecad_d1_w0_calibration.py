"""Synthetic-only exact-BREP Boolean calibration; never opens frozen witnesses."""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import FreeCAD as App
import Part

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "experiments/try6/scripts"))
from witness_boolean import build_clearance_witness, optional_splitter_cleanup, volumetric_state


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def box(x, width, height=10.0, depth=10.0):
    return Part.makeBox(width, height, depth, App.Vector(x, 0, 0))


def shape_bbox(shape):
    if not shape.Solids:
        return None
    b = shape.BoundBox
    return [b.XMin, b.YMin, b.ZMin, b.XMax, b.YMax, b.ZMax]


def main(job):
    cfg = read(ROOT / job["protocol"])
    source = box(0, 10)
    middle = box(3, 4)
    cases = [
        ("DISJOINT", source, [box(20, 2)], 0.0),
        ("PARTIAL", source, [box(5, 10)], 500.0),
        ("FULL_REMOVAL", source, [box(0, 10)], 1000.0),
        ("TOUCHING", source, [box(10, 3)], 0.0),
        ("OVERLAPPING_UNION", source, [middle, box(5, 4)], 600.0),
        ("REPEATED_OVERLAP", source, [middle, middle.copy()], 400.0),
        ("THIN_POSITIVE", source, [box(0, 0.0001)], 0.01),
        ("DERIVED_EMPTY", Part.Shape(), [box(0, 10)], 0.0),
    ]
    scratch = ROOT / job["scratch"]
    scratch.mkdir(parents=True, exist_ok=True)
    rows = []
    for name, body, keepouts, expected in cases:
        for path in cfg["candidate_paths"]:
            for repeat in range(cfg["calibration_repetitions"]):
                witness, removed, union, metrics = build_clearance_witness(
                    body, keepouts, {"absolute_mm3": 0.0, "relative": 0.0}, path=path)
                filename = scratch / f"{name}_{path}_{repeat}.brep"
                witness.exportBrep(str(filename))
                reopened = Part.read(str(filename))
                before = volumetric_state(witness, derived=True)
                after = volumetric_state(reopened, derived=True)
                bbox_before, bbox_after = shape_bbox(witness), shape_bbox(reopened)
                bbox_delta = (max(abs(a-b) for a, b in zip(bbox_before, bbox_after))
                              if bbox_before is not None and bbox_after is not None else
                              0.0 if bbox_before == bbox_after else math.inf)
                errors = [metrics["outside_source_residual_mm3"],
                          metrics["residual_keepout_intersection_mm3"],
                          metrics["conservation_error_mm3"],
                          metrics["removed_consistency_error_mm3"],
                          abs(metrics["removed_unique_volume_mm3"]-expected),
                          abs(before.volume_mm3-after.volume_mm3)]
                rows.append({"case": name, "path": path, "repeat": repeat,
                    "source_volume_mm3": metrics["source_volume_mm3"],
                    "keepout_union_volume_mm3": metrics["keepout_union_volume_mm3"],
                    "expected_overlap_mm3": expected,
                    "witness_volume_mm3": metrics["witness_volume_mm3"],
                    "removed_unique_volume_mm3": metrics["removed_unique_volume_mm3"],
                    "residual_forbidden_mm3": metrics["residual_keepout_intersection_mm3"],
                    "outside_source_mm3": metrics["outside_source_residual_mm3"],
                    "conservation_error_mm3": metrics["conservation_error_mm3"],
                    "removed_consistency_error_mm3": metrics["removed_consistency_error_mm3"],
                    "expected_overlap_error_mm3": abs(metrics["removed_unique_volume_mm3"]-expected),
                    "reopen_volume_delta_mm3": after.volume_mm3-before.volume_mm3,
                    "state": before.state, "reopen_state": after.state,
                    "solid_count": before.solid_count, "reopen_solid_count": after.solid_count,
                    "bbox_delta_mm": bbox_delta,
                    "max_absolute_error_mm3": max(errors),
                    "max_relative_error": max(errors)/max(1.0, metrics["source_volume_mm3"]),
                    "raw_brep_path": str(filename.relative_to(ROOT)).replace("\\", "/")})
    try:
        optional_splitter_cleanup(source, operation=lambda: (_ for _ in ()).throw(Part.OCCError("synthetic failure")))
        cleanup_status = "FAILURE_CAUGHT"
    except Part.OCCError:
        cleanup_status = "FAILURE_ESCAPED"
    output = {"schema_version": "d1_w0_synthetic_raw_v1", "rows": rows,
        "case_count": len(cases), "row_count": len(rows), "cleanup_failure_test": cleanup_status,
        "freecad_version": App.Version(), "occ_version": getattr(Part, "OCC_VERSION", None)}
    out = ROOT / job["output"]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"cases": len(cases), "rows": len(rows),
          "max_error": max(x["max_absolute_error_mm3"] for x in rows),
          "cleanup": cleanup_status}))


if __name__ == "__main__":
    main(read(sys.argv[1]))
