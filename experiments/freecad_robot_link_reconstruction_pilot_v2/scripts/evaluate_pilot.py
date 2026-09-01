from __future__ import annotations

import json
import math
import csv
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import trimesh
from scipy.spatial import cKDTree

from pilot_common import EXP, RESULTS, RUNS, VERSIONS, FEATURE_FAMILY, dump_json, ensure_dirs, feature_rows_from_graph, frozen_rows, load_json, write_csv


CUTTER_FEATURES = {"recess", "cutout", "hollow_region", "slot", "gap", "lightening_cut"}


def executed_semantic_features(version: str, row: dict[str, str]) -> set[str]:
    path = RUNS / version / row["case_id"] / row["link_id"] / "freecad" / "execution_log.json"
    if not path.exists():
        return set()
    log = json.loads(path.read_text(encoding="utf-8"))
    features = set()
    for record in log:
        if not record.get("success"):
            continue
        params = record.get("input_parameters") or {}
        sem = params.get("semantic_feature_type")
        op_type = params.get("op_type")
        if sem:
            features.add(sem)
        elif version == "R0":
            # R0 has no explicit MFG. This weak mapping is used only to keep a
            # baseline denominator; it does not give R0 credit for specific
            # role semantics such as flange vs bearing boss.
            if op_type == "revolve":
                features.add("proximal_joint_housing")
            elif op_type == "loft":
                features.add("tapered_transition")
            elif op_type == "fillet":
                features.add("fillet_group")
            elif op_type == "chamfer":
                features.add("chamfer_group")
            elif op_type == "extrude":
                features.add("elongated_main_body" if row["role"] in {"upper_arm", "main_link", "forearm"} else "main_housing")
    return features


def expected_features(row: dict[str, str]) -> list[str]:
    return [x for x in row["expected_visible_features"].split(";") if x]


def feature_recall_rows() -> list[dict[str, Any]]:
    rows = []
    for version in VERSIONS:
        for row in frozen_rows():
            expected = expected_features(row)
            realized = executed_semantic_features(version, row)
            correct = [f for f in expected if f in realized]
            rows.append(
                {
                    "version": version,
                    "case_id": row["case_id"],
                    "link_id": row["link_id"],
                    "role": row["role"],
                    "expected_count": len(expected),
                    "correct_count": len(correct),
                    "mfr": len(correct) / len(expected) if expected else 0.0,
                    "expected_features": ";".join(expected),
                    "realized_features": ";".join(sorted(realized)),
                    "missing_features": ";".join(f for f in expected if f not in realized),
                }
            )
    return rows


def native_feature_usage_rows() -> list[dict[str, Any]]:
    rows = []
    native_keys = {
        "revolve_count": "Revolution",
        "loft_count": "Loft",
        "sweep_count": "Sweep",
        "shell_count": "Thickness",
        "fillet_count": "Fillet",
        "chamfer_count": "Chamfer",
        "boolean_count": "Fuse|Cut",
        "pattern_count": "Array",
    }
    for version in VERSIONS:
        for row in frozen_rows():
            path = RUNS / version / row["case_id"] / row["link_id"] / "freecad" / "execution_log.json"
            log = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
            types = [str(x.get("native_object_type") or x.get("executed_native_operation") or "") for x in log if x.get("success")]
            out = {"version": version, "case_id": row["case_id"], "link_id": row["link_id"], "role": row["role"], "operation_count": len(log)}
            for key, pattern in native_keys.items():
                parts = pattern.split("|")
                out[key] = sum(any(part in t for part in parts) for t in types)
            rows.append(out)
    return rows


def load_mesh_points(path: str, samples: int = 2500):
    mesh = trimesh.load(path, force="mesh")
    if mesh.is_empty:
        raise ValueError("empty mesh")
    if not mesh.is_watertight:
        mesh.remove_unreferenced_vertices()
    pts, _ = trimesh.sample.sample_surface(mesh, samples)
    center = pts.mean(axis=0)
    pts = pts - center
    scale = np.linalg.norm(pts.max(axis=0) - pts.min(axis=0))
    if scale <= 1e-9:
        scale = 1.0
    return pts / scale


def chamfer_hd95(a: np.ndarray, b: np.ndarray) -> tuple[float, float]:
    ta = cKDTree(a)
    tb = cKDTree(b)
    da, _ = tb.query(a)
    db, _ = ta.query(b)
    return float((da.mean() + db.mean()) / 2.0), float(np.percentile(np.concatenate([da, db]), 95))


def voxel_iou(a: np.ndarray, b: np.ndarray, pitch: float = 0.05) -> float:
    va = {tuple(np.floor(p / pitch).astype(int)) for p in a}
    vb = {tuple(np.floor(p / pitch).astype(int)) for p in b}
    if not va and not vb:
        return 0.0
    return len(va & vb) / len(va | vb)


def geometry_rows() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows = []
    local_rows = []
    for version in VERSIONS:
        for row in frozen_rows():
            gt = row.get("gt_mesh_path") or ""
            pred = RUNS / version / row["case_id"] / row["link_id"] / "freecad" / "model.stl"
            base = {"version": version, "case_id": row["case_id"], "link_id": row["link_id"], "role": row["role"]}
            if not gt or not Path(gt).exists() or not pred.exists():
                rows.append({**base, "status": "GT_OR_PRED_MESH_MISSING", "voxel_iou": "", "chamfer": "", "hd95": ""})
                for side in ["proximal", "distal"]:
                    local_rows.append({**base, "joint_side": side, "status": "GT_OR_PRED_MESH_MISSING", "local_chamfer": "", "local_hd95": "", "local_iou": ""})
                continue
            try:
                a = load_mesh_points(str(pred))
                b = load_mesh_points(gt)
                chamfer, hd95 = chamfer_hd95(a, b)
                rows.append({**base, "status": "SUCCESS", "voxel_iou": voxel_iou(a, b), "chamfer": chamfer, "hd95": hd95})
                # Development diagnostic: local regions are approximated in
                # normalized link coordinates because no GT part segmentation is
                # allowed. This is comparable across R0/R1/R2 but not a final
                # benchmark metric.
                for side, xcenter in [("proximal", -0.25), ("distal", 0.25)]:
                    aa = a[np.linalg.norm(a - np.array([xcenter, 0, 0]), axis=1) < 0.35]
                    bb = b[np.linalg.norm(b - np.array([xcenter, 0, 0]), axis=1) < 0.35]
                    if len(aa) < 20 or len(bb) < 20:
                        local_rows.append({**base, "joint_side": side, "status": "INSUFFICIENT_LOCAL_POINTS", "local_chamfer": "", "local_hd95": "", "local_iou": ""})
                    else:
                        c, h = chamfer_hd95(aa, bb)
                        local_rows.append({**base, "joint_side": side, "status": "SUCCESS", "local_chamfer": c, "local_hd95": h, "local_iou": voxel_iou(aa, bb)})
            except Exception as exc:
                rows.append({**base, "status": "GEOMETRY_EVAL_FAILURE", "voxel_iou": "", "chamfer": "", "hd95": "", "failure_reason": f"{type(exc).__name__}: {exc}"})
    return rows, local_rows


def resource_rows() -> list[dict[str, Any]]:
    rows = []
    graph_gen = RESULTS / "feature_graph_generation.csv"
    gen_records = []
    if graph_gen.exists():
        with graph_gen.open(encoding="utf-8", newline="") as f:
            gen_records = list(csv.DictReader(f))
    exec_records = []
    with (RESULTS / "execution_metrics.csv").open(encoding="utf-8", newline="") as f:
        exec_records = list(csv.DictReader(f))
    for version in VERSIONS:
        for row in frozen_rows():
            gens = [r for r in gen_records if r.get("version") == version and r.get("case_id") == row["case_id"] and r.get("link_id") == row["link_id"]]
            ex = next((r for r in exec_records if r.get("version") == version and r.get("case_id") == row["case_id"] and r.get("link_id") == row["link_id"]), {})
            rows.append(
                {
                    "version": version,
                    "case_id": row["case_id"],
                    "link_id": row["link_id"],
                    "llm_calls": len(gens),
                    "total_tokens": sum(int(float(g.get("total_tokens") or 0)) for g in gens),
                    "planning_latency_seconds": sum(float(g.get("elapsed_seconds") or 0) for g in gens),
                    "freecad_execution_time_seconds": ex.get("execution_time_seconds", ""),
                    "cad_operation_count": ex.get("operation_count", ""),
                }
            )
    return rows


def make_render_contact_sheets() -> None:
    out = RESULTS / "contact_sheets"
    out.mkdir(parents=True, exist_ok=True)
    for row in frozen_rows():
        fig = plt.figure(figsize=(10, 3))
        for idx, version in enumerate(VERSIONS):
            ax = fig.add_subplot(1, 3, idx + 1, projection="3d")
            stl = RUNS / version / row["case_id"] / row["link_id"] / "freecad" / "model.stl"
            ax.set_title(version)
            if stl.exists():
                try:
                    pts = load_mesh_points(str(stl), 1000)
                    ax.scatter(pts[:, 0], pts[:, 1], pts[:, 2], s=1)
                except Exception:
                    pass
            ax.set_axis_off()
        fig.suptitle(f"{row['case_id']} {row['link_id']} {row['role']}")
        fig.tight_layout()
        fig.savefig(out / f"{row['case_id']}_{row['link_id']}_contact.png", dpi=150)
        plt.close(fig)


def aggregate_report(mfr_rows: list[dict[str, Any]], geom_rows: list[dict[str, Any]]) -> None:
    agg = []
    for version in VERSIONS:
        m = [r for r in mfr_rows if r["version"] == version]
        g = [r for r in geom_rows if r["version"] == version and r["status"] == "SUCCESS"]
        agg.append(
            {
                "version": version,
                "link_count": len(m),
                "mean_mfr": sum(float(r["mfr"]) for r in m) / len(m),
                "mean_voxel_iou": sum(float(r["voxel_iou"]) for r in g) / len(g) if g else "",
                "mean_chamfer": sum(float(r["chamfer"]) for r in g) / len(g) if g else "",
                "mean_hd95": sum(float(r["hd95"]) for r in g) / len(g) if g else "",
            }
        )
    write_csv(RESULTS / "aggregate_results.csv", agg)
    dump_json(RESULTS / "aggregate_results.json", agg)


def traceability_rows() -> list[dict[str, Any]]:
    rows = []
    for row in frozen_rows():
        out = RUNS / "R2" / row["case_id"] / row["link_id"]
        obs_path = out / "local_visual_observations.json"
        graph_path = out / "mechanical_feature_graph_v2.json"
        ir_path = out / "executable_cad_ir_v1_2.json"
        observations = load_json(obs_path).get("observations", []) if obs_path.exists() else []
        graph = load_json(graph_path) if graph_path.exists() else {}
        features = feature_rows_from_graph(graph) if graph else []
        ir = load_json(ir_path) if ir_path.exists() else {}
        obs_refs = {str(item.get("observation_id")) for item in observations if isinstance(item, dict) and item.get("observation_id")}
        obs_refs |= {str(item.get("evidence_ref")) for item in observations if isinstance(item, dict) and item.get("evidence_ref")}
        cited_features = []
        for feature in features:
            refs = {str(x) for x in feature.get("visible_evidence_refs", [])}
            if refs & obs_refs or any(ref.startswith("crop:") for ref in refs):
                cited_features.append(str(feature.get("feature_id")))
        ir_feature_refs = {str(op.get("feature_ref")) for op in ir.get("operations", []) if op.get("feature_ref")}
        rows.append(
            {
                "version": "R2",
                "case_id": row["case_id"],
                "link_id": row["link_id"],
                "local_observation_count": len(observations),
                "feature_count": len(features),
                "features_with_local_evidence": len(cited_features),
                "ir_operation_count": len(ir.get("operations", [])),
                "ir_ops_trace_to_local_evidence": sum(1 for ref in ir_feature_refs if ref in set(cited_features)),
                "traceability_status": "SUCCESS" if observations and cited_features and ir_feature_refs else "MISSING",
            }
        )
    return rows


def failed_operation_rows() -> list[dict[str, Any]]:
    rows = []
    for version in VERSIONS:
        for row in frozen_rows():
            path = RUNS / version / row["case_id"] / row["link_id"] / "freecad" / "execution_log.json"
            if not path.exists():
                continue
            for record in json.loads(path.read_text(encoding="utf-8")):
                if record.get("success"):
                    continue
                params = record.get("input_parameters") or {}
                rows.append(
                    {
                        "version": version,
                        "case_id": row["case_id"],
                        "link_id": row["link_id"],
                        "op_id": record.get("op_id"),
                        "op_type": params.get("op_type") or record.get("requested_operation"),
                        "semantic_feature_type": params.get("semantic_feature_type", ""),
                        "failure_reason": str(record.get("failure_reason", ""))[:500],
                    }
                )
    return rows


def write_markdown_report(aggregate: list[dict[str, Any]], mfr_rows: list[dict[str, Any]]) -> None:
    exec_rows = list(csv.DictReader((RESULTS / "execution_metrics.csv").open(encoding="utf-8", newline="")))
    gen_rows = list(csv.DictReader((RESULTS / "feature_graph_generation.csv").open(encoding="utf-8", newline="")))
    ir_rows = list(csv.DictReader((RESULTS / "ir_translation.csv").open(encoding="utf-8", newline="")))
    fallback_total = sum(int(float(r.get("fallback_count") or 0)) for r in exec_rows)
    def count(rows: list[dict[str, str]], version: str, status: str) -> int:
        return sum(r.get("version") == version and r.get("status") == status for r in rows)
    lines = [
        "# FreeCAD Robot Link Reconstruction Pilot v2 Report",
        "",
        "## Protocol",
        "",
        "- Dataset: same six frozen links from v1; no new links were added or removed.",
        "- R0: deterministic FreeCAD baseline.",
        "- R1-v2: Mechanical Feature Graph v2 with explicit anchors and dimensions.",
        "- R2-v2: GLM `glm-5.3-flash` with real multimodal `image_url` inputs for global views and local crops, then MFG v2.",
        "- Formal backend: FreeCADCmd + FreeCAD Python API. MCP is not part of acceptance.",
        "- Failure policy: missing geometry fields are `IR_INCOMPLETE`; silent fallback is forbidden.",
        "",
        "## Aggregate metrics",
        "",
        "| version | links | mean MFR | mean voxel IoU | mean Chamfer | mean HD95 | success links |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for item in aggregate:
        version = item["version"]
        subset = [r for r in exec_rows if r["version"] == version]
        success = sum(r["status"] == "SUCCESS" for r in subset)
        lines.append(
            f"| {version} | {item['link_count']} | {item['mean_mfr']} | {item['mean_voxel_iou']} | {item['mean_chamfer']} | {item['mean_hd95']} | {success}/6 |"
        )
    lines.extend(
        [
            "",
            "## Pipeline success by stage",
            "",
            "| version | MFG schema success | IR complete | FreeCAD batch success |",
            "|---|---:|---:|---:|",
            f"| R1-v2 | {count(gen_rows, 'R1', 'SUCCESS')}/6 | {count(ir_rows, 'R1', 'SUCCESS')}/6 | {count(exec_rows, 'R1', 'SUCCESS')}/6 |",
            f"| R2-v2 | {count(gen_rows, 'R2', 'SUCCESS')}/6 | {count(ir_rows, 'R2', 'SUCCESS')}/6 | {count(exec_rows, 'R2', 'SUCCESS')}/6 |",
            "",
            "## Acceptance check",
            "",
            f"- Silent fallback total: `{fallback_total}`.",
            "- Acceptance result: `NO-GO` for entering the full Try-3 FreeCAD multi-agent workflow.",
            "- Main failed criteria: batch success is below 5/6; R2-v2 improves MFR but succeeds on only 1/6 links; fillet/chamfer execution failures remain visible in `failed_operations.csv`.",
            "- Primary bottleneck: VLM/MFG schema compliance and MFG-to-IR parameter completeness. Secondary bottleneck: fillet/chamfer selector/backend robustness on complex fused bodies.",
            "- Detailed per-link metrics are in `mechanical_feature_recall.csv`, `execution_metrics.csv`, `per_link_geometry.csv`, and `joint_local_geometry.csv`.",
            "- R2 visual traceability is in `r2_traceability.csv`.",
            "- Contact sheets are in `results/contact_sheets/`.",
            "",
            "## Known interpretation limits",
            "",
            "- This is link-level reconstruction, not full robot assembly.",
            "- Chamfer/HD95/IoU compare normalized meshes without GT segmentation; local joint metrics are diagnostic, not final benchmark claims.",
            "- If a generated link does not look like a robot link, inspect `local_visual_observations.json`, `mechanical_feature_graph_v2.json`, `executable_cad_ir_v1_2.json`, and `execution_log.json` to assign the bottleneck.",
        ]
    )
    (RESULTS / "freecad_robot_link_reconstruction_pilot_v2_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    ensure_dirs()
    mfr = feature_recall_rows()
    write_csv(RESULTS / "mechanical_feature_recall.csv", mfr)
    usage = native_feature_usage_rows()
    write_csv(RESULTS / "native_feature_usage.csv", usage)
    geom, joint = geometry_rows()
    write_csv(RESULTS / "per_link_geometry.csv", geom)
    write_csv(RESULTS / "joint_local_geometry.csv", joint)
    write_csv(RESULTS / "resource_accounting.csv", resource_rows())
    write_csv(RESULTS / "r2_traceability.csv", traceability_rows())
    write_csv(RESULTS / "failed_operations.csv", failed_operation_rows())
    make_render_contact_sheets()
    aggregate_report(mfr, geom)
    aggregate = load_json(RESULTS / "aggregate_results.json")
    write_markdown_report(aggregate, mfr)
    print(json.dumps(aggregate, indent=2))


if __name__ == "__main__":
    main()
