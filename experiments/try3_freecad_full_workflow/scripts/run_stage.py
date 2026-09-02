from __future__ import annotations

import argparse
import json
from pathlib import Path


EXP = Path(__file__).resolve().parents[1]
RESULTS = EXP / "results"

STAGE_DEPENDENCIES = {
    "audit_inputs": [],
    "visual_agent": ["audit_inputs"],
    "mep": ["visual_agent"],
    "interface_graph": ["mep"],
    "v0_baseline": ["audit_inputs"],
    "v1_per_link": ["visual_agent"],
    "v2_full": ["visual_agent", "mep", "interface_graph"],
    "freecad_backend": ["v0_baseline|v1_per_link|v2_full"],
    "assembly_integration": ["freecad_backend", "interface_graph"],
    "evaluation": ["assembly_integration"],
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Try-3 FreeCAD full workflow stage runner skeleton.")
    parser.add_argument("stage", choices=sorted(STAGE_DEPENDENCIES))
    parser.add_argument("--dry-run", action="store_true", help="Print stage contract without executing.")
    args = parser.parse_args()

    RESULTS.mkdir(parents=True, exist_ok=True)
    contract = {
        "experiment": "try3_freecad_full_workflow",
        "stage": args.stage,
        "dependencies": STAGE_DEPENDENCIES[args.stage],
        "status": "SKELETON_ONLY",
        "note": "This runner encodes workflow order. Implement stage-specific execution before formal runs.",
    }
    print(json.dumps(contract, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

