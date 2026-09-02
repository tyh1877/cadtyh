from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
EXP = Path(__file__).resolve().parents[1]
TRYSET = EXP / "tryset5_v1.csv"
RESULTS = EXP / "results"


def rel_exists(path_text: str) -> bool:
    return (ROOT / path_text).exists()


def audit_case(row: dict[str, str]) -> dict[str, str]:
    image_json_path = ROOT / row["image_text_json"]
    urdf_path = ROOT / row["sanitized_urdf"]
    out = {
        "case_id": row["case_id"],
        "image_text_json_exists": str(image_json_path.exists()),
        "sanitized_urdf_exists": str(urdf_path.exists()),
        "all_required_views_exist": "False",
        "engineering_text_exists": "False",
        "leakage_flags": "",
    }
    leakage_flags: list[str] = []
    if image_json_path.exists():
        data = json.loads(image_json_path.read_text(encoding="utf-8"))
        images = data.get("images", {})
        required = ["front", "rear", "left", "right", "top", "isometric"]
        out["all_required_views_exist"] = str(all(view in images and rel_exists(images[view]) for view in required))
        text_fields = data.get("text_fields", {})
        rendered_prompt = str(data.get("rendered_prompt", ""))
        out["engineering_text_exists"] = str(bool(text_fields) and bool(rendered_prompt))
        forbidden_terms = ["mesh", "cad", "product identity", "hidden part labels"]
        # The rendered instruction may mention forbidden sources only as
        # prohibitions. This audit records suspicious positive leakage terms.
        for term in forbidden_terms:
            if term in rendered_prompt.lower() and "do not assume access" not in rendered_prompt.lower():
                leakage_flags.append(term)
    out["leakage_flags"] = ";".join(leakage_flags)
    return out


def main() -> int:
    RESULTS.mkdir(parents=True, exist_ok=True)
    rows = list(csv.DictReader(TRYSET.open("r", encoding="utf-8")))
    audit_rows = [audit_case(row) for row in rows]
    out_path = RESULTS / "input_audit.csv"
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(audit_rows[0].keys()))
        writer.writeheader()
        writer.writerows(audit_rows)
    failures = [
        row for row in audit_rows
        if row["image_text_json_exists"] != "True"
        or row["sanitized_urdf_exists"] != "True"
        or row["all_required_views_exist"] != "True"
        or row["engineering_text_exists"] != "True"
        or row["leakage_flags"]
    ]
    print(json.dumps({"cases": len(audit_rows), "failures": failures, "output": str(out_path)}, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

