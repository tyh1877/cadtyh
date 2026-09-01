from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path

from PIL import Image

from pilot_common import EXP, INPUTS, ROOT, ROLE_EXPECTATIONS, ensure_dirs, normalize_case_for_render, urdf_link_joint_context, write_csv


SOURCE_MANIFEST = ROOT / "freecad_backend_pilot" / "input_manifest.csv"
RENDER_ROOT = ROOT / "go_nogo1" / "results" / "prototype_feasibility" / "renders"


def source_render_paths(case_id: str) -> list[Path]:
    arm_id = normalize_case_for_render(case_id)
    folder = RENDER_ROOT / arm_id
    if not folder.exists():
        return []
    return sorted(p for p in folder.iterdir() if p.suffix.lower() in {".png", ".jpg", ".jpeg"})


def make_crops(row: dict[str, str]) -> list[dict[str, object]]:
    images = source_render_paths(row["case_id"])
    out_dir = EXP / "runs" / "R2" / row["case_id"] / row["link_id"] / "local_evidence"
    out_dir.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, object]] = []
    if not images:
        return [
            {
                "case_id": row["case_id"],
                "link_id": row["link_id"],
                "crop_id": "LOCAL_EVIDENCE_UNAVAILABLE",
                "crop_path": "",
                "crop_source_view": "",
                "bbox_xyxy": "",
                "localization_method": "no_frozen_render_found",
                "related_link": row["link_id"],
                "related_joint": "",
                "gt_geometry_used": False,
            }
        ]
    chosen = [p for p in images if any(view in p.name for view in ["iso", "front", "top"])]
    if not chosen:
        chosen = images[:3]
    labels = ["link_level", "proximal_joint", "distal_joint"]
    for idx, label in enumerate(labels):
        src = chosen[idx % len(chosen)]
        image = Image.open(src)
        w, h = image.size
        # Deterministic, non-GT heuristic crop. It intentionally does not use
        # mesh masks or part segmentation.
        if label == "proximal_joint":
            box = (int(w * 0.05), int(h * 0.20), int(w * 0.55), int(h * 0.85))
        elif label == "distal_joint":
            box = (int(w * 0.45), int(h * 0.15), int(w * 0.95), int(h * 0.80))
        else:
            box = (int(w * 0.15), int(h * 0.10), int(w * 0.85), int(h * 0.90))
        crop_id = f"{label}_crop"
        dst = out_dir / f"{crop_id}.png"
        image.crop(box).save(dst)
        records.append(
            {
                "case_id": row["case_id"],
                "link_id": row["link_id"],
                "crop_id": crop_id,
                "crop_path": str(dst),
                "crop_source_view": str(src),
                "bbox_xyxy": json.dumps(box),
                "localization_method": "deterministic_non_gt_render_crop",
                "related_link": row["link_id"],
                "related_joint": "proximal" if label == "proximal_joint" else "distal" if label == "distal_joint" else "",
                "gt_geometry_used": False,
            }
        )
    return records


def main() -> None:
    ensure_dirs()
    rows = []
    with SOURCE_MANIFEST.open(encoding="utf-8", newline="") as handle:
        for item in csv.DictReader(handle):
            context = urdf_link_joint_context(item["case_id"], item["link_id"])
            expected = ROLE_EXPECTATIONS.get(item["role"], {"expected": [], "optional": []})
            gt_mesh = ROOT / "operation_plan_pilot" / "runs" / item["case_id"] / item["link_id"] / "meshes" / f"{item['case_id'].replace('-', '_')}_{item['link_id']}.stl"
            rows.append(
                {
                    **item,
                    "urdf_path": str(ROOT / "try2" / "inputs" / "sanitized_urdf" / f"{item['case_id']}.urdf"),
                    "proximal_joint": context.get("proximal_joint") or "",
                    "distal_joint": context.get("distal_joint") or "",
                    "expected_visible_features": ";".join(expected["expected"]),
                    "optional_visible_features": ";".join(expected["optional"]),
                    "gt_mesh_path": str(gt_mesh) if gt_mesh.exists() else "",
                }
            )
    write_csv(INPUTS / "frozen_links.csv", rows)
    lines = ["# Frozen link roles", ""]
    for row in rows:
        lines.append(f"- `{row['case_id']}/{row['link_id']}`: `{row['role']}`")
        lines.append(f"  - proximal_joint: `{row['proximal_joint'] or 'none'}`")
        lines.append(f"  - distal_joint: `{row['distal_joint'] or 'none'}`")
        lines.append(f"  - expected visible features: `{row['expected_visible_features']}`")
    (INPUTS / "frozen_link_roles.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    all_crops = []
    for row in rows:
        all_crops.extend(make_crops(row))
    write_csv(EXP / "results" / "local_evidence_audit.csv", all_crops)
    manifest = {"gt_geometry_used": False, "records": all_crops}
    (INPUTS / "local_evidence_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"links": len(rows), "local_evidence_records": len(all_crops), "gt_geometry_used": False}, indent=2))


if __name__ == "__main__":
    main()
