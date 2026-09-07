"""Freeze Phase-5 evaluator inputs before the first metric run."""
import hashlib,json
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];EXP=ROOT/'try4';files=['protocol/phase5_evaluator_v1.json','scripts/freecad_export_gt_parts.py','scripts/prepare_phase5_gt.py','scripts/evaluate_phase5.py']
out={'frozen_at':datetime.now(timezone.utc).isoformat(),'before_final_metric_table':True,'supersedes':'phase5_method_snapshot_attempt_04.json','change':'make silhouette raster honor frozen 256x256 protocol; thresholds and other algorithms unchanged','files':{p:hashlib.sha256((EXP/p).read_bytes()).hexdigest() for p in files}}
(EXP/'results/phase5_method_snapshot.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8');print(json.dumps(out,indent=2))
