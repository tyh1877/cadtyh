"""Finalize A1 manifests, state and method snapshot."""
import csv,hashlib,json
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=ROOT/'experiments/try5A'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
execution=list(csv.DictReader((HERE/'results/a1_link_execution.csv').open()));manifest=[]
for p in list((HERE/'A1').rglob('*'))+list((HERE/'assemblies/A1').rglob('*')):
 if p.is_file():manifest.append({'path':str(p.relative_to(HERE)),'bytes':p.stat().st_size,'sha256':sha(p)})
with (HERE/'results/a1_artifact_manifest.csv').open('w',newline='',encoding='utf-8') as f:w=csv.DictWriter(f,fieldnames=list(manifest[0]));w.writeheader();w.writerows(manifest)
(HERE/'blackboard/a1_state.json').write_text(json.dumps({'condition':'A1','robot_plan':'CONSUMED','shared_interface_contract':'NOT_CONSUMED','links':'12/12 BUILT','assembly':'ASSEMBLED','evaluation':'COMPLETE','repair_applied':False,'A2':'NOT_STARTED'},indent=2)+'\n')
files=[HERE/'results/a1_method_snapshot.json',HERE/'scripts/freecad_assemble_a0.py',HERE/'scripts/freecad_assemble_a1.py',HERE/'scripts/run_a1_assembly.py',HERE/'scripts/run_a0_evaluation.py',HERE/'scripts/run_a1_evaluation.py',HERE/'scripts/compare_a0_a1.py',HERE/'blackboard/robot_assembly_plan.json'];out={'created_at':datetime.now(timezone.utc).isoformat(),'condition':'A1','files':{str(p.relative_to(ROOT)):sha(p) for p in files},'a0_frozen_commit':'b90c1ea'};(HERE/'results/a1_final_method_snapshot.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'links':12,'operations':sum(int(x['operations']) for x in execution)}))
