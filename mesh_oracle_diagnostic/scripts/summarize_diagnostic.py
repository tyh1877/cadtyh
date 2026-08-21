"""Summarize I/M/L evidence without treating oracle geometry as reconstruction quality."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from statistics import median

ROOT=Path(__file__).resolve().parents[2]
CONDITIONS=("I_image_baseline","M_monolithic_mesh","L_per_link_mesh_oracle")
METRICS=("assembly_assembly_graph_f1","kinematic_joint_type_accuracy","kinematic_axis_error_degrees_median","kinematic_joint_origin_error_normalized_median","motion_link_translation_error_normalized_median","motion_link_rotation_error_degrees_median")

def number(value): return float(value) if isinstance(value,(int,float)) else None

def main():
    parser=argparse.ArgumentParser();parser.add_argument("--manifest",type=Path,default=ROOT/"mesh_oracle_diagnostic/results/input_manifest.csv");parser.add_argument("--runs-root",type=Path,default=ROOT/"mesh_oracle_diagnostic/runs");parser.add_argument("--output-dir",type=Path,default=ROOT/"mesh_oracle_diagnostic/results");args=parser.parse_args();args.output_dir.mkdir(parents=True,exist_ok=True)
    cases=list(csv.DictReader(args.manifest.open(encoding="utf-8-sig")));rows=[]
    for condition in CONDITIONS:
        for item in cases:
            if condition=="I_image_baseline":
                source=ROOT/"go_nogo4/runs/multiview_static"/item["case_id"]; manifest=json.loads((source/"manifest.json").read_text(encoding="utf-8")); result=json.loads((source/"evaluation/results.json").read_text(encoding="utf-8"))
            else:
                source=args.runs_root/condition/item["case_id"]; manifest=json.loads((source/"manifest.json").read_text(encoding="utf-8")) if (source/"manifest.json").is_file() else {"status":"NOT_RUN","budget":{}}; result=json.loads((source/"evaluation/results.json").read_text(encoding="utf-8")) if (source/"evaluation/results.json").is_file() else {}
            row={"condition":condition,"case_id":item["case_id"],"status":manifest["status"],"total_tokens":manifest.get("budget",{}).get("total_tokens",0),"error":manifest.get("error")}
            for family in ("assembly","kinematic","motion","geometry"):
                for key,value in result.get(family,{}).items():
                    if not isinstance(value,(list,dict)):row[f"{family}_{key}"]=value
            # A root-only match cannot define an articulated trajectory; an
            # unmatched joint cannot define axis/origin accuracy.
            if int(row.get("motion_mapped_links") or 0) <= 1:
                row["motion_link_translation_error_normalized_median"] = None
                row["motion_link_rotation_error_degrees_median"] = None
            if int(row.get("kinematic_matched_joints") or 0) == 0:
                row["kinematic_axis_error_degrees_median"] = None
                row["kinematic_joint_origin_error_normalized_median"] = None
            row["failure_patterns"]=";".join(result.get("outcome",{}).get("failure_patterns",["invalid_cad"] if manifest["status"]=="FAILURE" else []));rows.append(row)
    with (args.output_dir/"case_results.csv").open("w",newline="",encoding="utf-8-sig") as f: writer=csv.DictWriter(f,fieldnames=sorted({k for r in rows for k in r}));writer.writeheader();writer.writerows(rows)
    aggregates=[]
    for c in CONDITIONS:
        track=[r for r in rows if r["condition"]==c];valid=[r for r in track if r["status"]=="SUCCESS"];out={"condition":c,"cases":len(track),"executed":len(valid),"failed":sum(r["status"]=="FAILURE" for r in track),"tokens_total":sum(int(r["total_tokens"]or 0) for r in track)}
        for metric in METRICS:
            x=[number(r.get(metric)) for r in valid];x=[v for v in x if v is not None];out[f"median_{metric}"]=median(x) if x else None
        aggregates.append(out)
    with (args.output_dir/"aggregate_results.csv").open("w",newline="",encoding="utf-8-sig") as f: writer=csv.DictWriter(f,fieldnames=list(aggregates[0]));writer.writeheader();writer.writerows(aggregates)
    by={r["condition"]:r for r in aggregates};i,m,l=(by[x] for x in CONDITIONS)
    # A positive result requires M to be available and L to retain a material residual kinematic gap.
    monolithic_available=m["executed"]>=5;per_link_residual=(number(l.get("median_motion_link_translation_error_normalized_median")) or 0)>0.05 or (number(l.get("median_kinematic_joint_origin_error_normalized_median")) or 0)>0.05
    decision="KINEMATIC_RESIDUAL_SUPPORTED" if monolithic_available and per_link_residual else "INCONCLUSIVE_OR_GEOMETRY_DOMINATED"
    lines=["# Mesh Oracle Diagnostic report","",f"## Diagnostic decision: {decision}","","This is a point-cloud mesh representation diagnostic, not a native STL-understanding or main benchmark result.","","| condition | executed | failed | Graph F1 | joint type | axis error | origin error | motion translation |","|---|---:|---:|---:|---:|---:|---:|---:|"]
    for r in aggregates:lines.append("| {condition} | {executed} | {failed} | {median_assembly_assembly_graph_f1} | {median_kinematic_joint_type_accuracy} | {median_kinematic_axis_error_degrees_median} | {median_kinematic_joint_origin_error_normalized_median} | {median_motion_link_translation_error_normalized_median} |".format(**r))
    lines += ["","I=image baseline; M=unlabeled merged surface points; L=anonymous per-link surface-point and mesh oracle. Geometry is not a reconstruction score for L. M motion metrics are omitted when only the root link matches.","",f"M available on at least five cases: {monolithic_available}; residual L kinematic gap: {per_link_residual}.","", "Interpretation: if L remains poor in graph/origin/motion, kinematic recovery remains difficult even after geometry and part decomposition are supplied. If L is nearly correct, the bottleneck is primarily perception/decomposition."]
    (args.output_dir/"mesh_oracle_report.md").write_text("\n".join(lines)+"\n",encoding="utf-8");print(json.dumps({"decision":decision,"monolithic_available":monolithic_available,"per_link_residual":per_link_residual},indent=2))

if __name__=="__main__":main()
