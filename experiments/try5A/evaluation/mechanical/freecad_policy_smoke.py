"""Small FreeCAD smoke test proving constrained/unconstrained policy dispatch."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SCRIPTS = ROOT / "experiments/try5A/scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import freecad_motion_realization as frozen  # noqa: E402
from freecad_link_refinement import refined_shape  # noqa: E402


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main():
    base = ROOT / "experiments/try5A/results/try5a5"
    contracts = load(base / "motion_interface_contracts.json")
    ir = load(base / "cad_ir/round3_verified/L03.json")
    scaffold = frozen.link_shape(ir["link_spec"], contracts, ir["body_scale"], ir.get("repair_state"))["group"]
    schema = {"span_mm": 100, "thickness_mm": 8, "proximal_height_mm": 34, "mid_height_mm": 28, "lateral_offset_mm": -18, "major_recess": True}
    constrained = refined_shape("L03", "central_web", schema, contracts, ir["link_spec"]["realization_type"], scaffold)
    unconstrained = refined_shape("L03", "central_web", schema, contracts, ir["link_spec"]["realization_type"], scaffold, {
        "protected_interface_cuts": False,
        "preserve_frozen_scaffold": False,
        "auto_attachment_closure": False,
        "mechanical_rejection": False,
        "rollback_on_failure": False,
    })
    payload = {
        "status": "PASS" if constrained["assembly_strategy"] == "FROZEN_SCAFFOLD" and unconstrained["assembly_strategy"] == "NATURAL_CONTACT_ONLY" and constrained["group"].hashCode() != unconstrained["group"].hashCode() else "FAIL",
        "constrained": {"assembly_strategy": constrained["assembly_strategy"], "solid_count": constrained["solid_count"], "attachment_valid": constrained["attachment_valid"], "shape_hash": constrained["group"].hashCode()},
        "unconstrained": {"assembly_strategy": unconstrained["assembly_strategy"], "solid_count": unconstrained["solid_count"], "attachment_valid": unconstrained["attachment_valid"], "shape_hash": unconstrained["group"].hashCode()},
    }
    print(json.dumps(payload, indent=2))
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
