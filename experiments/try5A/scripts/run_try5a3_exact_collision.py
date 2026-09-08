"""Run the shared exact evaluator for the current A.3 physical A2 condition."""
import json, subprocess
from pathlib import Path
from freecad_runtime import python_runtime

ROOT=Path(__file__).resolve().parents[3];HERE=ROOT/'experiments/try5A';OUT=HERE/'results/try5a3_full/k1_exact_collision';poses=ROOT/'experiments/try5A_1/collision_cache/collision_poses.json'
types=json.loads((HERE/'try5A_2/virtual_link_filter/link_realization_types.json').read_text())['links'];physical=[x['link_id'] for x in types if x['collision_allowed']]
OUT.mkdir(parents=True,exist_ok=True);job=OUT/'job.json';job.write_text(json.dumps({'root':str(ROOT),'source_dir':'experiments/try5A','output_dir':str(OUT.relative_to(ROOT)),'poses_path':str(poses),'physical_links':physical},indent=2)+'\n')
r=subprocess.run([python_runtime(),str(ROOT/'experiments/try5A_1/scripts/freecad_exact_collision.py'),str(job)],cwd=ROOT,capture_output=True,text=True,timeout=1200);(OUT/'stdout.txt').write_text(r.stdout);(OUT/'stderr.txt').write_text(r.stderr);print(r.stdout or r.stderr);raise SystemExit(r.returncode)
