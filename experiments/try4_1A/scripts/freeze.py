"""Freeze Try-4.1A inputs/plans/method before the first new FreeCAD execution."""
import hashlib,json
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=ROOT/'experiments/try4_1A';files=['protocol.json','shape_family_vocabulary.json','planning_inputs.json','input_manifest.json','schemas/mechanical_topology_graph.schema.json','scripts/materialize.py','scripts/run_freecad.py','../../try4/protocol/phase5_evaluator_v1.json','../../try4/scripts/freecad_t1_executor.py']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
out={'frozen_at':datetime.now(timezone.utc).isoformat(),'before_new_execution':True,'files':{p:sha((HERE/p).resolve()) for p in files}};(HERE/'results/method_snapshot.json').parent.mkdir(parents=True,exist_ok=True);(HERE/'results/method_snapshot.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
