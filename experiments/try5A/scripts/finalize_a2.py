"""Finalize A2 artifacts and Try-5A method snapshot."""
import csv,hashlib,json
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=ROOT/'experiments/try5A'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
manifest=[]
for p in list((HERE/'A2').rglob('*'))+list((HERE/'assemblies/A2').rglob('*')):
 if p.is_file():manifest.append({'path':str(p.relative_to(HERE)),'bytes':p.stat().st_size,'sha256':sha(p)})
with (HERE/'results/a2_artifact_manifest.csv').open('w',newline='',encoding='utf-8') as f:w=csv.DictWriter(f,fieldnames=list(manifest[0]));w.writeheader();w.writerows(manifest)
(HERE/'blackboard/final_state.json').write_text(json.dumps({'robot_id':'R01','L0':'KINEMATIC_CHECKED','L1':'ROBOT_PLANNED','L2':'INTERFACES_PLANNED','A0':'COMPLETE','A1':'COMPLETE','A2':'COMPLETE','assembly':'COMPLETE','evaluation':'COMPLETE','Try5B':'NOT_STARTED'},indent=2)+'\n')
files=[HERE/'results/a2_method_snapshot.json',HERE/'results/a2_evaluation_snapshot.json',HERE/'results/coarse_evaluation_snapshot.json',HERE/'scripts/freecad_assemble_a2.py',HERE/'scripts/run_a2_assembly.py',HERE/'scripts/evaluate_condition.py',HERE/'scripts/evaluate_coarse_geometry.py',HERE/'scripts/finalize_try5A.py',HERE/'blackboard/robot_assembly_plan.json',HERE/'blackboard/joint_interface_graph.json'];out={'created_at':datetime.now(timezone.utc).isoformat(),'experiment':'Try-5A complete','files':{str(p.relative_to(ROOT)):sha(p) for p in files}};(HERE/'results/try5A_final_method_snapshot.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'artifacts':len(manifest)}))
