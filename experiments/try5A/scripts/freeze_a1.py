"""Freeze plan-consumed A1 IR before execution and audit forbidden L2 access."""
import hashlib,json
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=ROOT/'experiments/try5A'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
files=[HERE/'blackboard/robot_assembly_plan.json',HERE/'scripts/materialize_a1.py',ROOT/'try4/scripts/freecad_t1_executor.py',*[HERE/f'A1/L{i:02d}/cad_ir.json' for i in range(12)]];src=(HERE/'scripts/materialize_a1.py').read_text();forbidden=['joint_interface_graph','shared_port','shared_interface_envelope'];out={'frozen_at':datetime.now(timezone.utc).isoformat(),'before_freecad':True,'files':{str(p.relative_to(ROOT)):sha(p) for p in files},'forbidden_tokens':{x:x in src for x in forbidden}};(HERE/'results/a1_method_snapshot.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2));raise SystemExit(any(out['forbidden_tokens'].values()))
