"""Freeze C0 and evaluator inputs before collision analysis."""
import hashlib,json
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=ROOT/'experiments/try5A_1';SRC=ROOT/'experiments/try5A'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
files=[HERE/'results/c0_frozen_manifest.json',HERE/'collision_cache/collision_poses.json',HERE/'scripts/build_collision_poses.py',HERE/'scripts/freecad_exact_collision.py',SRC/'inputs/sanitized_urdf/px100_sanitized.urdf',*[(SRC/f'A2/L{i:02d}/cad_ir.json') for i in range(12)],*[(SRC/f'A2/L{i:02d}/model.FCStd') for i in range(12)]]
out={'frozen_at':datetime.now(timezone.utc).isoformat(),'before_collision_analysis':True,'files':{str(p.relative_to(ROOT)):sha(p) for p in files}};(HERE/'results/phase13_method_snapshot.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'files':len(files)}))
