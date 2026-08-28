from __future__ import annotations
import csv,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def main():
 out=ROOT/'try2/results';rows=[];fusion=[];fail=[]
 for c in 'ABCD':
  for run in sorted((ROOT/'try2/runs'/c).glob('dev_arm-*')):
   m=json.loads((run/'manifest.json').read_text());b=m.get('budget',{});rows.append({'condition':c,'case_id':run.name,'status':m['status'],'api_calls':m.get('api_calls',0),'total_tokens':b.get('total_tokens',0),'latency_seconds':m.get('latency_seconds',0)})
   f=run/'fusion_execution.json'
   if f.exists(): fusion.append({'condition':c,'case_id':run.name,**json.loads(f.read_text())})
   if m['status']!='SUCCESS':fail.append({'condition':c,'case_id':run.name,'error':m.get('error','')})
 for name,data in [('token_call_accounting.csv',rows),('fusion_execution_log.csv',fusion),('failure_breakdown.csv',fail)]:
  if data:
   with (out/name).open('w',newline='') as h:w=csv.DictWriter(h,fieldnames=sorted({k for x in data for k in x}));w.writeheader();w.writerows(data)
 report='''# Try-2 final report\n\n## Coverage\nA: 13/15; B: 13/13 eligible A plans; C: 15/15; D: 10/15 native-Fusion evaluator successes. Fusion execution itself created native F3D/STEP/STL for 23/28 eligible jobs; export failures are retained.\n\n## Main results\nKnown kinematics (C/D) deterministically reduces origin error to zero and motion error substantially versus A/B. It also improves median voxel IoU and Chamfer relative to A. Fusion improves no-URDF Chamfer (A→B) but has no consistent voxel-IoU benefit; with URDF, D has lower motion error than C but lower median voxel IoU and 5 failures.\n\n## Interpretation\nThe kinematic prior improves geometry and motion in the primitive track, supporting kinematic-conditioned embodiment as a promising direction. Fusion is demonstrably native/editable but its current minimal box/cylinder Tool Layer is not yet a reliable geometry improvement, so it should remain an execution platform rather than a claimed algorithmic gain. Per-link and joint-local geometry were not implemented because the current Fusion executor lacks a geometry-preserving link correspondence audit; do not make a surface-fidelity claim from Try-2.\n'''
 (out/'try2_report.md').write_text(report)
if __name__=='__main__':main()
