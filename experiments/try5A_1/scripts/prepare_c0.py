"""Freeze C0=A2 provenance without generating any CAD."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];SRC=ROOT/'experiments/try5A';HERE=ROOT/'experiments/try5A_1'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
files=[SRC/'inputs/sanitized_urdf/px100_sanitized.urdf',SRC/'blackboard/kinematic_skeleton.json',SRC/'blackboard/robot_assembly_plan.json',SRC/'blackboard/joint_interface_graph.json',*sorted((SRC/'interface_graph/contracts').glob('*.json')),*[(SRC/f'A2/L{i:02d}/cad_ir.json') for i in range(12)],*[(SRC/f'A2/L{i:02d}/InterfaceRefs.json') for i in range(12)]]
out={'condition':'C0','source_condition':'Try5A A2','cad_regenerated':False,'files':{str(p.relative_to(ROOT)):sha(p) for p in files},'forbidden_generator_inputs':['GT STEP','GT B-Rep','GT dimensions']};(HERE/'results').mkdir(exist_ok=True);(HERE/'results/c0_frozen_manifest.json').write_text(json.dumps(out,indent=2)+'\n');(HERE/'C0').mkdir(exist_ok=True);(HERE/'C0/reference.json').write_text(json.dumps({'source':'experiments/try5A/A2','frozen_manifest':'results/c0_frozen_manifest.json','links':12,'joints':11},indent=2)+'\n');print(json.dumps({'files':len(files)}))
