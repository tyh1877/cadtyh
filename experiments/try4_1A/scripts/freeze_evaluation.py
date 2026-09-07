"""Freeze Try-4.1A evaluators before reading A1/A2 metric results."""
import hashlib,json
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=ROOT/'experiments/try4_1A';files=['scripts/evaluate.py','scripts/evaluate_topology.py','scripts/make_contact_sheets.py','../../try4/scripts/evaluate_phase5.py','../../try4/protocol/phase5_evaluator_v1.json','planning_inputs.json']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
out={'frozen_at':datetime.now(timezone.utc).isoformat(),'before_metric_run':True,'files':{p:sha((HERE/p).resolve()) for p in files}};(HERE/'results/evaluation_snapshot.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
