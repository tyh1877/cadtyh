"""Freeze common A0/A1/A2 evaluator before unified comparison."""
import hashlib,json
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=ROOT/'experiments/try5A';files=[HERE/'scripts/evaluate_condition.py',HERE/'scripts/kinematics.py',HERE/'blackboard/kinematic_skeleton.json',*[HERE/f'{c}/L{i:02d}/InterfaceRefs.json' for c in ['A0','A1','A2'] for i in range(12)]]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
out={'frozen_at':datetime.now(timezone.utc).isoformat(),'before_unified_metrics':True,'files':{str(p.relative_to(ROOT)):sha(p) for p in files},'conditions':['A0','A1','A2']};(HERE/'results/a2_evaluation_snapshot.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'files':len(files),'conditions':out['conditions']}))
