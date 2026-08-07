"""Extract STEP/B-Rep topology and compare it with the frozen mesh score."""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from OCP.BRepAdaptor import BRepAdaptor_Curve, BRepAdaptor_Surface
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps
from OCP.IFSelect import IFSelect_RetDone
from OCP.STEPControl import STEPControl_Reader
from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE, TopAbs_SOLID
from OCP.TopExp import TopExp_Explorer
from OCP.TopoDS import TopoDS
from OCP.StlAPI import StlAPI_Writer

sys.path.insert(0, str(Path(__file__).parent))
from remesh_robustness import load_mesh, measure  # noqa: E402


def enum_name(value):
    return str(value).split(".")[-1].replace("GeomAbs_", "")


def explore(shape, kind):
    explorer = TopExp_Explorer(shape, kind)
    while explorer.More():
        yield explorer.Current()
        explorer.Next()


def step_metrics(path: Path, tessellation_path: Path):
    reader = STEPControl_Reader()
    status = reader.ReadFile(str(path))
    if status != IFSelect_RetDone:
        raise ValueError(f"STEP reader status {status}")
    transferred = reader.TransferRoots()
    if transferred < 1:
        raise ValueError("no transferred roots")
    shape = reader.OneShape()
    surface_counts, surface_areas = Counter(), defaultdict(float)
    curve_counts = Counter()
    total_area = 0.0
    for item in explore(shape, TopAbs_FACE):
        face = TopoDS.Face_s(item)
        surface = enum_name(BRepAdaptor_Surface(face).GetType())
        props = GProp_GProps()
        BRepGProp.SurfaceProperties_s(face, props)
        area = max(0.0, float(props.Mass()))
        surface_counts[surface] += 1
        surface_areas[surface] += area
        total_area += area
    for item in explore(shape, TopAbs_EDGE):
        curve_counts[enum_name(BRepAdaptor_Curve(TopoDS.Edge_s(item)).GetType())] += 1
    n_faces, n_edges = sum(surface_counts.values()), sum(curve_counts.values())
    n_solids = sum(1 for _ in explore(shape, TopAbs_SOLID))
    planar_area = surface_areas.get("Plane", 0.0)
    freeform_area = surface_areas.get("BSplineSurface", 0.0) + surface_areas.get("BezierSurface", 0.0)
    tessellation_path.parent.mkdir(parents=True, exist_ok=True)
    triangulation = BRepMesh_IncrementalMesh(shape, 0.2, False, 0.3, True)
    triangulation.Perform()
    if not triangulation.IsDone() or not StlAPI_Writer().Write(shape, str(tessellation_path)):
        raise ValueError("STEP tessellation failed")
    mesh_values = measure(load_mesh(tessellation_path))
    return {
        "step_ok": True, "n_faces": n_faces, "n_edges": n_edges, "n_solids": n_solids,
        "total_surface_area": total_area,
        "nonplanar_area_fraction": 1 - planar_area / total_area if total_area else math.nan,
        "freeform_area_fraction": freeform_area / total_area if total_area else math.nan,
        "edge_face_ratio": n_edges / n_faces if n_faces else math.nan,
        "surface_type_counts": json.dumps(surface_counts, sort_keys=True),
        "surface_type_areas": json.dumps(surface_areas, sort_keys=True),
        "curve_type_counts": json.dumps(curve_counts, sort_keys=True),
        **{f"stepmesh_{key}": value for key, value in mesh_values.items()},
    }


def robust_z(values):
    values = pd.Series(values, dtype=float)
    median = values.median()
    mad = np.median(np.abs(values - median))
    scale = 1.4826 * mad if mad > 0 else values.std(ddof=0)
    return (values - median) / (scale if scale > 0 else 1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--entities", type=Path, required=True)
    parser.add_argument("--mesh-features", type=Path, required=True)
    parser.add_argument("--mesh-summary", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    sources = pd.read_csv(args.source_manifest)
    rows = []
    for _, source in sources.iterrows():
        step_path = Path(str(source.step_files).split(";")[0])
        try:
            metrics = step_metrics(step_path, args.output_dir / "step_tessellations" / f"{source.slug}.stl")
        except Exception as exc:
            metrics = {"step_ok": False, "error": f"{type(exc).__name__}: {exc}"}
        rows.append({"dataset_name": source.dataset_name, "manufacturer": source.manufacturer,
                     "step_path": str(step_path), **metrics})
        print(f"{source.dataset_name}: {metrics.get('step_ok')}", flush=True)
    brep = pd.DataFrame(rows)
    valid = brep.step_ok.fillna(False)
    components = pd.DataFrame({
        "log_faces": np.log1p(brep.loc[valid, "n_faces"]),
        "nonplanar_area_fraction": brep.loc[valid, "nonplanar_area_fraction"],
        "freeform_area_fraction": brep.loc[valid, "freeform_area_fraction"],
        "edge_face_ratio": brep.loc[valid, "edge_face_ratio"],
    })
    brep.loc[valid, "brep_complexity_score"] = pd.concat(
        [robust_z(components[c]) for c in components], axis=1
    ).clip(-3, 3).mean(axis=1)
    scaling = json.loads(args.mesh_summary.read_text(encoding="utf-8"))["score_scaling"]
    stepmesh_z = []
    for field, values in scaling.items():
        stepmesh_z.append(((brep[f"stepmesh_{field}"] - values["median"]) / values["robust_scale"]).clip(-3, 3))
    brep["same_geometry_mesh_score"] = pd.concat(stepmesh_z, axis=1).mean(axis=1)
    entities = pd.read_csv(args.entities)[["entity_id", "manufacturer", "name"]]
    mesh = pd.read_csv(args.mesh_features)
    mesh = mesh[(mesh.ratio == 1.0) & mesh.feature_ok][["entity_id", "complexity_score"]]
    paired = brep.merge(entities, left_on=["manufacturer", "dataset_name"],
                        right_on=["manufacturer", "name"], how="left").merge(mesh, on="entity_id", how="left")
    paired = paired.rename(columns={"complexity_score": "mesh_complexity_score"})
    complete = paired.dropna(subset=["brep_complexity_score", "mesh_complexity_score"])
    rho = spearmanr(complete.brep_complexity_score, complete.mesh_complexity_score).statistic
    same_geometry = brep.dropna(subset=["brep_complexity_score", "same_geometry_mesh_score"])
    same_geometry_rho = spearmanr(
        same_geometry.brep_complexity_score, same_geometry.same_geometry_mesh_score
    ).statistic
    summary = {
        "n_step_models": int(len(brep)), "n_step_parsed": int(valid.sum()),
        "n_mesh_brep_pairs": int(len(complete)), "manufacturers": int(complete.manufacturer.nunique()),
        "mesh_brep_spearman_rho": float(rho),
        "passes_threshold_0_50": bool(rho >= .50), "meets_target_0_60": bool(rho >= .60),
        "same_geometry_step_tessellation_n": int(len(same_geometry)),
        "same_geometry_mesh_brep_spearman_rho": float(same_geometry_rho),
        "same_geometry_passes_threshold_0_50": bool(same_geometry_rho >= .50),
        "scope_warning": "All current STEP pairs are from one manufacturer/product family; external validity is not established.",
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    paired.to_csv(args.output_dir / "mesh_brep_pairs.csv", index=False, encoding="utf-8-sig")
    (args.output_dir / "brep_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
