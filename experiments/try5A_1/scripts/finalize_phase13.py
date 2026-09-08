"""Record raw collision provenance and evaluator resource use."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=ROOT/'experiments/try5A_1'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
raw=HERE/'collision_cache/c0_raw_pairs.json';poses=HERE/'collision_cache/collision_poses.json';out={'raw_pairs_sha256':sha(raw),'poses_sha256':sha(poses),'raw_pairs_bytes':raw.stat().st_size,'exact_evaluator':'FreeCAD B-Rep common volume'};(HERE/'results/c0_collision_manifest.json').write_text(json.dumps(out,indent=2)+'\n');(HERE/'results/resource_metrics.csv').write_text('condition,links,poses,pair_evaluations,broad_candidates,exact_boolean_candidates,narrow_errors,agent_calls,tokens\nC0,12,13,858,292,292,0,0,UNAVAILABLE\n');print(json.dumps(out))
