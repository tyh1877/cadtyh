"""Aggregate completed Try-1 runs; failures remain in the fixed denominator."""
from __future__ import annotations
import csv,json,statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; conditions=("D1","D2","G1","O_GT")
def get(d,*keys):
 for k in keys:
  if not isinstance(d,dict):return None
  d=d.get(k)
 return d
def main():
 rows=[]
 for c in conditions:
  for run in sorted((ROOT/"try1/runs"/c).glob("dev_arm-*")):
   m=json.loads((run/"manifest.json").read_text()); e=json.loads((run/"evaluation.json").read_text()) if (run/"evaluation.json").exists() else {}
   rows.append({"condition":c,"case_id":m["case_id"],"status":m["status"],"api_calls":m["api_calls"],"tokens":m["budget"]["total_tokens"],"latency_seconds":m["latency_seconds"],"graph_f1":get(e,"assembly","assembly_graph_f1"),"joint_type_accuracy":get(e,"kinematic","joint_type_accuracy"),"axis_error":get(e,"kinematic","axis_error_degrees_median"),"origin_error":get(e,"kinematic","joint_origin_error_normalized_median"),"motion_translation":get(e,"motion","link_translation_error_normalized_median"),"chamfer":get(e,"geometry","chamfer"),"voxel_iou":get(e,"geometry","voxel_iou")})
 out=ROOT/"try1/results";out.mkdir(exist_ok=True)
 with (out/"case_results.csv").open("w",newline="") as f:w=csv.DictWriter(f,fieldnames=list(rows[0]) if rows else ["condition"]);w.writeheader();w.writerows(rows)
 metrics=("api_calls","tokens","latency_seconds","graph_f1","joint_type_accuracy","axis_error","origin_error","motion_translation","chamfer","voxel_iou"); aggregate=[]
 for c in conditions:
  subset=[r for r in rows if r["condition"]==c]; x={"condition":c,"denominator":len(subset),"success":sum(r["status"]=="SUCCESS" for r in subset)}
  for k in metrics:
   vals=[r[k] for r in subset if isinstance(r[k],(int,float))];x[f"median_{k}"]=statistics.median(vals) if vals else None;x[f"mean_{k}"]=statistics.mean(vals) if vals else None
  aggregate.append(x)
 with (out/"aggregate_results.csv").open("w",newline="") as f:w=csv.DictWriter(f,fieldnames=list(aggregate[0]) if aggregate else ["condition"]);w.writeheader();w.writerows(aggregate)
 pairs=[]
 by={(r["condition"],r["case_id"]):r for r in rows}
 for cid in sorted({r["case_id"] for r in rows}):
  d,g=by.get(("D2",cid)),by.get(("G1",cid));
  if d and g:
   for k in ("graph_f1","joint_type_accuracy","axis_error","origin_error","motion_translation","chamfer","voxel_iou"):
    if isinstance(d[k],(int,float)) and isinstance(g[k],(int,float)):pairs.append({"case_id":cid,"metric":k,"g1_minus_d2":g[k]-d[k]})
 with (out/"paired_deltas.csv").open("w",newline="") as f:w=csv.DictWriter(f,fieldnames=["case_id","metric","g1_minus_d2"]);w.writeheader();w.writerows(pairs)
 (out/"try1_report.md").write_text("# Try-1 report\n\nResults are development-only. G1 vs D2 is the primary comparison; O-GT is a hidden diagnostic upper bound. Run aggregation after all fixed cases complete.\n\n```json\n"+json.dumps(aggregate,indent=2)+"\n```\n")
if __name__=="__main__":main()
