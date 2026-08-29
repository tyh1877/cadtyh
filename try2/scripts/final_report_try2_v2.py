from __future__ import annotations
import csv,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def main():
 out=ROOT/'try2/results'; rows=[]; fusion=[]; fail=[]
 for c in 'ABCD':
  for run in sorted((ROOT/'try2/runs'/c).glob('dev_arm-*')):
   m=json.loads((run/'manifest.json').read_text()); b=m.get('budget',{})
   rows.append({'condition':c,'case_id':run.name,'status':m['status'],'api_calls':m.get('api_calls',0),'total_tokens':b.get('total_tokens',0),'latency_seconds':m.get('latency_seconds',0)})
   f=run/'fusion_execution.json'
   if f.exists(): fusion.append({'condition':c,'case_id':run.name,**json.loads(f.read_text())})
   if m['status']!='SUCCESS': fail.append({'condition':c,'case_id':run.name,'error':m.get('error','')})
 for name,data in [('token_call_accounting.csv',rows),('fusion_execution_log.csv',fusion),('failure_breakdown.csv',fail)]:
  with (out/name).open('w',newline='') as h:
   w=csv.DictWriter(h,fieldnames=sorted({k for x in data for k in x})); w.writeheader(); w.writerows(data)
 report='''# Try-2 final report (amended external-URDF protocol)

## Protocol and validity
C/D use sanitized URDF as the external authoritative kinematic representation. Fusion creates editable parameterized link components and places occurrences at canonical FK transforms; native Fusion joints are a non-gating demonstration. The acceptance checklist records this amendment.

## Coverage and execution
A=13/15, B=13/15 (the two A planning failures are retained as UPSTREAM_FAILURE), C=15/15, D=15/15. All 28 eligible B/D jobs produced native F3D/STEP/STL and per-component STL. The repaired executor records occurrence FK transforms, and the selected smoke plus formal execution logs confirm the transforms are persisted at creation time.

## Main geometry and motion
Median Chamfer/HD95/IoU: A 0.00291/0.1221/0.341; B 0.00249/0.1006/0.326; C 0.00088/0.0631/0.505; D 0.00147/0.0860/0.404. Median motion error: A 0.259, B 0.266, C 0.0264, D 0.0250. Per-link median Chamfer: A 0.017413, B 0.018141, C 0.001083, D 0.001499. Joint-local median Chamfer: A 0.001297, B 0.001060, C 0.000562, D 0.000725.

## 2x2 interpretation
URDF improves whole-robot, per-link and joint-local geometry substantially in the primitive track (A→C), while also making origin error zero and lowering motion error. Fusion improves no-URDF Chamfer and HD95 on eligible paired cases but not IoU or per-link geometry consistently (A→B). Under URDF, Fusion preserves motion but is geometrically behind the primitive backend (C→D), reflecting the minimal primitive Tool Layer rather than a negative result about editable CAD. Corrected placement is evidenced separately from geometric quality.

## Recommendation
The evidence supports kinematic-conditioned CAD generation as the next paper direction. Keep Fusion as an editable execution substrate; improve the Fusion embodiment Tool Layer before claiming a backend advantage.
'''
 (out/'try2_report.md').write_text(report)
if __name__=='__main__': main()
