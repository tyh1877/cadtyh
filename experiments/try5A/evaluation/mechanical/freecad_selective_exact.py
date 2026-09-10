"""Measure real pair-level FreeCAD Exact calls selected by the FAST stages."""

import hashlib
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]; SCRIPTS = ROOT / "experiments/try5A/scripts"; sys.path.insert(0, str(SCRIPTS))
import freecad_motion_realization as exact  # noqa: E402


def build(results, contracts, dirty=False):
    shapes = {}
    for path in sorted((results / "cad_ir/round3_verified").glob("L*.json")):
        ir = json.loads(path.read_text(encoding="utf-8")); link = ir["link_spec"]["link_id"]
        if ir["link_spec"]["realization_type"] == "virtual_frame": continue
        scale = ir["body_scale"] * (0.995 if dirty and link == "L03" else 1.0)
        shapes[link] = exact.link_shape(ir["link_spec"], contracts, scale, ir.get("repair_state"))["group"]
    return shapes


def evaluate(keys, configs, shapes):
    config_map = {item["config_id"]: item for item in configs}; digest = hashlib.sha256(); started = time.perf_counter(); calls = 0; distance_calls = 0
    for config_id, a, b in keys:
        config = config_map[config_id]; sa = exact.world_shape(shapes[a], config["world_transforms"][a]); sb = exact.world_shape(shapes[b], config["world_transforms"][b])
        volume = exact.common_volume(sa, sb); clearance = 0.0
        if volume <= exact.TOL: clearance = float(sa.distToShape(sb)[0]); distance_calls += 1
        digest.update(f"{config_id}|{a}|{b}|{volume:.12g}|{clearance:.12g}".encode()); calls += 1
    return {"wall_seconds": time.perf_counter() - started, "exact_calls": calls, "distance_calls": distance_calls, "result_digest": digest.hexdigest()}


def main():
    job = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")); results = ROOT / "experiments/try5A/results/try5a5"
    contracts = json.loads((results / "motion_interface_contracts.json").read_text(encoding="utf-8")); build_start = time.perf_counter()
    baseline = build(results, contracts); dirty = build(results, contracts, dirty=True); build_seconds = time.perf_counter() - build_start
    payload = {"shape_build_seconds": build_seconds,
               "baseline": evaluate(job["baseline_keys"], job["configs"], baseline),
               "dirty_L03": evaluate(job["dirty_keys"], job["configs"], dirty)}
    Path(job["output"]).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__": main()
