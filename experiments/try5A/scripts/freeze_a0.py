"""Freeze A0 independent decisions and materialized plans before FreeCAD."""
import hashlib,json
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=ROOT/'experiments/try5A'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
files=[HERE/'codex_authored/A0/independent_link_decisions.json',HERE/'scripts/materialize_a0.py',ROOT/'try4/scripts/freecad_t1_executor.py',HERE/'inputs/sanitized_urdf/px100_sanitized.urdf',HERE/'inputs/input_manifest.json',*[HERE/f'A0/L{i:02d}/cad_ir.json' for i in range(12)]];src=(HERE/'scripts/materialize_a0.py').read_text();forbidden=['robot_assembly_plan','joint_interface_graph','shared_port','shared_interface_envelope'];out={'frozen_at':datetime.now(timezone.utc).isoformat(),'before_freecad':True,'files':{str(p.relative_to(ROOT)):sha(p) for p in files},'forbidden_tokens':{x:(x in src) for x in forbidden}};(HERE/'results/a0_method_snapshot.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2));raise SystemExit(any(out['forbidden_tokens'].values()))
