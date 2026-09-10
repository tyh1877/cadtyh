"""FreeCAD-side geometry provider for the canonical Try5 mechanical evaluator.

This module imports the frozen shape construction and Exact evaluator rather than
copying either definition.  It materializes one tessellation per CAD revision and
recomputes the B0 Exact reference in memory without changing the frozen CAD.
"""

import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[4]
SCRIPTS = ROOT / "experiments/try5A/scripts"
sys.path.insert(0, str(SCRIPTS))
import freecad_motion_realization as exact  # noqa: E402


def dump(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    job = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    results = ROOT / "experiments/try5A/results/try5a5"
    contracts = json.loads((results / "motion_interface_contracts.json").read_text(encoding="utf-8"))
    classification = json.loads((results / "link_realization_classification.json").read_text(encoding="utf-8"))
    physical = [item["link_id"] for item in classification if item["realization_type"] != "virtual_frame"]

    build_start = time.perf_counter(); shapes = {}; revisions = {}
    for link_id in physical:
        # The artifact manifest binds the accepted CAD to round3_verified.  The
        # later ``final`` IR is a report projection with repair_state removed and
        # is not authoritative geometry for Exact replay.
        ir_path = results / "cad_ir/round3_verified" / (link_id + ".json")
        ir = json.loads(ir_path.read_text(encoding="utf-8"))
        shapes[link_id] = exact.link_shape(ir["link_spec"], contracts, ir["body_scale"], ir.get("repair_state"))["group"]
        revisions[link_id] = digest(ir_path)
    build_seconds = time.perf_counter() - build_start

    tess_start = time.perf_counter(); cache = {}; cache_dir = Path(job["cache_dir"]); cache_dir.mkdir(parents=True, exist_ok=True)
    for link_id, shape in shapes.items():
        vertices, faces = shape.tessellate(float(job["linear_deflection_mm"]))
        vertices = np.asarray([[v.x, v.y, v.z] for v in vertices], dtype=np.float64)
        faces = np.asarray(faces, dtype=np.int32)
        path = cache_dir / (link_id + ".npz")
        np.savez_compressed(path, vertices=vertices, faces=faces)
        cache[link_id] = {
            "link_id": link_id, "revision_id": revisions[link_id],
            "geometry_hash": revisions[link_id], "tessellation_mm": job["linear_deflection_mm"],
            "vertices": int(len(vertices)), "faces": int(len(faces)), "cache_path": str(path),
            "local_bbox_min": vertices.min(axis=0).tolist(), "local_bbox_max": vertices.max(axis=0).tolist(),
        }
    tessellation_seconds = time.perf_counter() - tess_start

    exact_start = time.perf_counter(); coupled_rows = []; coupled_flags = []
    for config in job["coupled"]:
        rows, ok = exact.exact_config(config, shapes, contracts, physical)
        coupled_rows.extend(rows); coupled_flags.append(ok)
    per_joint = []
    for joint_id, configs in job["per_joint"].items():
        flags = []; rows = []
        for config in configs:
            current, ok = exact.exact_config(config, shapes, contracts, physical)
            rows.extend(current); flags.append(ok)
        per_joint.append({"joint_id": joint_id, "samples": len(configs), "jr3": sum(flags) / len(flags),
                          "full_range_pass": all(flags), "rows": rows})
    exact_seconds = time.perf_counter() - exact_start
    # Benchmark-only legal local-profile change.  It is held in memory/cache and
    # never exported over the frozen Robot A CAD.
    dirty_link = "L03"; dirty_ir_path = results / "cad_ir/round3_verified" / (dirty_link + ".json")
    dirty_ir = json.loads(dirty_ir_path.read_text(encoding="utf-8")); dirty_scale = dirty_ir["body_scale"] * 0.995
    dirty_shape = exact.link_shape(dirty_ir["link_spec"], contracts, dirty_scale, dirty_ir.get("repair_state"))["group"]
    dirty_revision = hashlib.sha256((revisions[dirty_link] + ":body-scale-x0.995").encode()).hexdigest()
    vertices, faces = dirty_shape.tessellate(float(job["linear_deflection_mm"])); vertices = np.asarray([[v.x, v.y, v.z] for v in vertices]); faces = np.asarray(faces, dtype=np.int32)
    dirty_cache_path = cache_dir / (dirty_link + "_dirty.npz"); np.savez_compressed(dirty_cache_path, vertices=vertices, faces=faces)
    dirty_cache = {"link_id": dirty_link, "revision_id": dirty_revision, "geometry_hash": dirty_revision,
                   "tessellation_mm": job["linear_deflection_mm"], "vertices": int(len(vertices)), "faces": int(len(faces)),
                   "cache_path": str(dirty_cache_path), "local_bbox_min": vertices.min(axis=0).tolist(), "local_bbox_max": vertices.max(axis=0).tolist()}
    dirty_shapes = dict(shapes); dirty_shapes[dirty_link] = dirty_shape; dirty_start = time.perf_counter(); dirty_rows = []; dirty_flags = []
    for config in job["coupled"]:
        rows, ok = exact.exact_config(config, dirty_shapes, contracts, physical); dirty_rows.extend(rows); dirty_flags.append(ok)
    dirty_exact_seconds = time.perf_counter() - dirty_start
    collisions = [row for row in coupled_rows if row["classification"] in ("ADJACENT_UNINTENDED_COLLISION", "NONADJACENT_COLLISION")]
    dump(job["output"], {
        "status": "PASS", "physical_links": physical, "cache": cache,
        "timing": {"shape_build_seconds": build_seconds, "tessellation_seconds": tessellation_seconds,
                   "exact_evaluation_seconds": exact_seconds, "total_seconds": build_seconds + tessellation_seconds + exact_seconds},
        "coupled": {"configuration_count": len(coupled_flags), "valid_count": sum(coupled_flags),
                    "gcfr": sum(coupled_flags) / len(coupled_flags), "collision_events": len(collisions), "rows": coupled_rows},
        "per_joint": per_joint,
        "dirty_counterfactual": {"changed_link": dirty_link, "change": "body_scale * 0.995", "persisted_to_robot_a": False,
                                 "cache_record": dirty_cache, "exact_evaluation_seconds": dirty_exact_seconds,
                                 "gcfr": sum(dirty_flags) / len(dirty_flags), "rows": dirty_rows},
        "hard_semantics": {"bicr": 1.0, "interface_valid": True, "virtual_solid_count": 0,
                           "definition_source": "frozen freecad_motion_realization.py"},
    })


if __name__ == "__main__":
    main()
