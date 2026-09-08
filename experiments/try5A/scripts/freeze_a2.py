"""Freeze shared-contract A2 plans before FreeCAD execution."""
import hashlib,json
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=ROOT/'experiments/try5A'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
files=[HERE/'blackboard/robot_assembly_plan.json',HERE/'blackboard/joint_interface_graph.json',HERE/'scripts/materialize_a2.py',ROOT/'try4/scripts/freecad_t1_executor.py',*[HERE/f'interface_graph/contracts/J{i:02d}.json' for i in range(11)],*[HERE/f'A2/L{i:02d}/cad_ir.json' for i in range(12)]];src=(HERE/'scripts/materialize_a2.py').read_text();out={'frozen_at':datetime.now(timezone.utc).isoformat(),'before_freecad':True,'files':{str(p.relative_to(ROOT)):sha(p) for p in files},'required_consumption_tokens':{'robot_assembly_plan':"robot_assembly_plan.json" in src,'joint_interface_graph':"joint_interface_graph.json" in src,'contract_hash':"contract_sha256" in src,'prismatic_limits':"j['limits']" in src}};(HERE/'results/a2_method_snapshot.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2));raise SystemExit(not all(out['required_consumption_tokens'].values()))
