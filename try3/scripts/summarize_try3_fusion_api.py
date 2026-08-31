"""Summarize Try-3 Fusion API execution and deterministic diagnostics."""
from __future__ import annotations

import csv
import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "try3" / "results"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def number(value: object) -> float | None:
    if value in (None, "", "nan"):
        return None
    try:
        x = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return x if x == x else None


def median(values: list[float | None]) -> float | None:
    clean = [x for x in values if x is not None]
    return statistics.median(clean) if clean else None


def fmt(value: float | None) -> str:
    return "" if value is None else f"{value:.6f}"


def main() -> None:
    batch = json.loads((ROOT / "try3" / "fusion_api_batch_results.json").read_text())
    case_rows = read_csv(RESULTS / "fusion_api_case_geometry.csv")
    iface_rows = read_csv(RESULTS / "fusion_api_interface_consistency.csv")
    tryset = read_csv(ROOT / "try3" / "tryset5_v1.csv")

    aggregate: list[dict[str, object]] = []
    for version in ("V1", "V2"):
        cases = [r for r in case_rows if r["version"] == version]
        iface = [r for r in iface_rows if r["version"] == version]
        success = [r for r in cases if r["execution_status"] == "SUCCESS"]
        iface_success = [r for r in iface if r["execution_status"] == "SUCCESS"]
        aggregate.append(
            {
                "version": version,
                "jobs": len(cases),
                "fusion_success": len(success),
                "fusion_failed": len(cases) - len(success),
                "median_chamfer": median([number(r.get("chamfer")) for r in success]),
                "median_hd95": median([number(r.get("hd95")) for r in success]),
                "median_voxel_iou": median([number(r.get("voxel_iou")) for r in success]),
                "component_correspondence_rate": sum(str(r.get("canonical_component_correspondence")) == "True" for r in success) / len(success) if success else None,
                "median_interface_gap": median([number(r.get("joint_center_surface_gap_normalized_median")) for r in iface_success]),
                "median_interface_gap_p95": median([number(r.get("joint_center_surface_gap_normalized_p95")) for r in iface_success]),
                "median_bbox_overlap_pairs": median([number(r.get("bbox_overlap_pairs")) for r in iface_success]),
            }
        )

    paired_cases = sorted(
        {r["case_id"] for r in case_rows if r["version"] == "V1" and r["execution_status"] == "SUCCESS"}
        & {r["case_id"] for r in case_rows if r["version"] == "V2" and r["execution_status"] == "SUCCESS"}
    )
    paired_lines = []
    for case in paired_cases:
        v1 = next(r for r in case_rows if r["version"] == "V1" and r["case_id"] == case)
        v2 = next(r for r in case_rows if r["version"] == "V2" and r["case_id"] == case)
        i1 = next(r for r in iface_rows if r["version"] == "V1" and r["case_id"] == case)
        i2 = next(r for r in iface_rows if r["version"] == "V2" and r["case_id"] == case)
        paired_lines.append(
            {
                "case_id": case,
                "chamfer_v1": number(v1.get("chamfer")),
                "chamfer_v2": number(v2.get("chamfer")),
                "gap_v1": number(i1.get("joint_center_surface_gap_normalized_median")),
                "gap_v2": number(i2.get("joint_center_surface_gap_normalized_median")),
                "bbox_overlap_v1": number(i1.get("bbox_overlap_pairs")),
                "bbox_overlap_v2": number(i2.get("bbox_overlap_pairs")),
            }
        )

    with (RESULTS / "fusion_api_aggregate_results.csv").open("w", newline="", encoding="utf-8") as f:
        fields = list(aggregate[0])
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(aggregate)

    success_by_version = {x["version"]: x for x in aggregate}
    failures = [(r["version"], r["case_id"], r["errors"][0] if r.get("errors") else "") for r in batch if r["status"] != "SUCCESS"]
    feature_counts = {}
    for r in batch:
        for c in r.get("calls", []):
            if c["skill"] == "CreateCompositeLinkGeometry":
                feature_counts[c["feature_type"]] = feature_counts.get(c["feature_type"], 0) + 1
            elif c["feature_type"]:
                feature_counts[c["feature_type"]] = feature_counts.get(c["feature_type"], 0) + 1

    report = [
        "# Try-3 Fusion API Report",
        "",
        "## Executive conclusion",
        "",
        "Try-3 is not a hard Go/No-Go. The repaired Fusion API path is executable and editable, but the current V2 method is not yet strong enough to claim a stable method improvement over V1.",
        "",
        "The strongest positive result is engineering feasibility: 8/10 formal V1/V2 jobs rebuilt in Fusion and exported F3D, STEP, assembled STL, and per-link STL. All successful jobs preserved canonical component correspondence.",
        "",
        "The main negative result is method effect: on the three paired V1/V2 successes, V2 improves joint-neighborhood gap in 2/3 cases but worsens Chamfer in 2/3 cases, and the bounding-box overlap proxy does not improve. This supports Try-3.x refinement, not expansion or a paper-level method claim yet.",
        "",
        "## TrySet-5",
        "",
        "| case | tier | role |",
        "|---|---|---|",
    ]
    for row in tryset:
        report.append(f"| `{row['case_id']}` | {row['tier']} | {row['role']} |")

    report += [
        "",
        "## Fusion API execution",
        "",
        "| version | jobs | success | failed | median Chamfer | median HD95 | median IoU | median interface gap | median bbox overlaps |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in aggregate:
        report.append(
            "| {version} | {jobs} | {fusion_success} | {fusion_failed} | {chamfer} | {hd95} | {iou} | {gap} | {bbox} |".format(
                version=row["version"],
                jobs=row["jobs"],
                fusion_success=row["fusion_success"],
                fusion_failed=row["fusion_failed"],
                chamfer=fmt(row["median_chamfer"]),
                hd95=fmt(row["median_hd95"]),
                iou=fmt(row["median_voxel_iou"]),
                gap=fmt(row["median_interface_gap"]),
                bbox=fmt(row["median_bbox_overlap_pairs"]),
            )
        )

    report += [
        "",
        "## Paired V1 vs V2 cases",
        "",
        "| case | Chamfer V1 | Chamfer V2 | interface gap V1 | interface gap V2 | bbox overlaps V1 | bbox overlaps V2 |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in paired_lines:
        report.append(
            f"| `{row['case_id']}` | {fmt(row['chamfer_v1'])} | {fmt(row['chamfer_v2'])} | {fmt(row['gap_v1'])} | {fmt(row['gap_v2'])} | {fmt(row['bbox_overlap_v1'])} | {fmt(row['bbox_overlap_v2'])} |"
        )

    report += [
        "",
        "## Recorded failures",
        "",
    ]
    for version, case, error in failures:
        report.append(f"- {version} `{case}`: {error}")

    report += [
        "",
        "## Skill execution evidence",
        "",
        "`CreateCompositeLinkGeometry` is now the primary geometry SkillCall. Fusion feature types recorded in the successful batch:",
        "",
    ]
    for name, count in sorted(feature_counts.items()):
        report.append(f"- `{name}`: {count}")

    report += [
        "",
        "## Required protocol answers",
        "",
        "V0 reproduction is provenance-only in this repaired Fusion API report: the five Try-2 D outputs are recorded in `v0_provenance.csv`, but they were not rerun through the new Fusion API skill backend.",
        "",
        "No GT geometry was sent to the model. GT meshes and original URDF geometry are loaded only after generation by deterministic evaluators.",
        "",
        "The Mechanical Embodiment Plan, Interface Graph, and Feature Graph schemas are frozen under `try3/schemas/`. V2 uses them before blueprint projection; V1 does not use the explicit MEP/interface/feature planning stage.",
        "",
        "Implemented RobotCAD Skills include `CreateCompositeLinkGeometry`, `ApplyFillet`, `ApplyChamfer`, `CreateHole`, `CreatePocket`, `CreateSlot`, `CreateGroove`, `CreateRib`, `CircularPattern`, placement, and shared joint references. Legacy robot-template names are projection aliases only, not formal execution skills.",
        "",
        "Visible feature recall is not yet computed by an objective detector, so it is not claimed. The screenshot and Fusion outputs show the prior cube collapse is fixed, but that is qualitative evidence only.",
        "",
        "Primary bottleneck: operation planning and Fusion Skill capability. Visual grounding supplies varied primitives, and external URDF preserves topology, but the current operation library still lacks robust interface-aware booleaning, collision control, and high-fidelity surface detail.",
        "",
        "Recommended next step: Try-3.x refinement focused on interface-aware composite skills and collision/overlap control, then rerun the same TrySet-5. Do not expand the benchmark yet.",
    ]

    (ROOT / "try3" / "try3_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(json.dumps({"aggregate_rows": len(aggregate), "paired_cases": len(paired_lines), "failures": len(failures)}, indent=2))


if __name__ == "__main__":
    main()
