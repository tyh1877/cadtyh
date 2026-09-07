"""Freeze evaluator-only topology GT separately from B1 generator inputs."""
import hashlib,json
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=ROOT/'experiments/try4_1B'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
gt=list(sorted((HERE/'topology_gt').glob('*.json')));gen=[HERE/'protocol.json',HERE/'schemas/executable_shape_family_v1.schema.json',HERE/'docs/executable_shape_family_v1.md',HERE/'scripts/materialize_condition.py',HERE/'scripts/shape_family_gate.py',HERE/'scripts/run_condition.py',*sorted((HERE/'shape_family_schemas/B1').glob('*.json')),ROOT/'try4/scripts/freecad_t1_executor.py',ROOT/'try4/protocol/phase5_evaluator_v1.json'];out={'frozen_at':datetime.now(timezone.utc).isoformat(),'before_b1_execution':True,'evaluator_only_topology_gt':{str(p.relative_to(HERE)):sha(p) for p in gt},'generator_method_files':{str(p.relative_to(HERE)) if HERE in p.parents else str(p.relative_to(ROOT)):sha(p) for p in gen},'generator_forbidden_path_scan':'materialize_condition.py contains no topology_gt token'};(HERE/'results').mkdir(exist_ok=True);(HERE/'results/b1_method_snapshot.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
