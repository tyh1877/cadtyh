from __future__ import annotations

import json
from pathlib import Path


EXP = Path(__file__).resolve().parents[1]

REQUIRED = [
    "README.md",
    "TRY3_FREECAD_PROTOCOL.md",
    "REQUIREMENT_EVIDENCE_CHECKLIST.md",
    "tryset5_v1.csv",
    "tryset5_selection.md",
    "try3_freecad_config.json",
    "schemas/visual_evidence_packet_v1.schema.json",
    "schemas/mechanical_embodiment_plan_v1.schema.json",
    "schemas/interface_graph_v1.schema.json",
    "schemas/mechanical_feature_graph_v1.schema.json",
    "schemas/skill_call_v1.schema.json",
    "schemas/executable_cad_ir_v2.schema.json",
    "prompts/visual_evidence_agent.md",
    "prompts/mechanical_embodiment_architect.md",
    "prompts/interface_engineer.md",
    "prompts/part_cad_engineer.md",
    "prompts/assembly_integrator.md",
    "prompts/verification_agent.md",
    "scripts/audit_inputs.py",
    "scripts/run_visual_agent.py",
    "scripts/stale_artifact_guard.py",
    "scripts/run_stage.py",
]


def main() -> int:
    missing = [p for p in REQUIRED if not (EXP / p).exists()]
    schema_errors = []
    for path in (EXP / "schemas").glob("*.schema.json"):
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            schema_errors.append({"path": str(path), "error": str(exc)})
    result = {"missing": missing, "schema_errors": schema_errors}
    print(json.dumps(result, indent=2))
    return 1 if missing or schema_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
