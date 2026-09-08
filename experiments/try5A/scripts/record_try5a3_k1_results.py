"""Snapshot current K1 evaluator outputs before restoring frozen historical reports."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3];HERE=ROOT/'experiments/try5A';OUT=HERE/'results/try5a3_full';OUT.mkdir(parents=True,exist_ok=True)
interface=json.loads((HERE/'results/a2_common_interface_metrics.json').read_text())
sweep=json.loads((HERE/'results/a2_common_joint_sweep.json').read_text())
exact=json.loads((OUT/'k1_exact_collision/summary.json').read_text())
meaning=json.loads((OUT/'k1_mechanical_meaningfulness.json').read_text())
out={'condition':'K1_knowledge_guided','interface_summary':interface['summary'],'sweep_free_pose_rate':sweep['collision_free_sample_rate'],'exact_collision':exact,'mechanical_meaningfulness':{'rate':meaning['meaningful_geometry_rate'],'patches':meaning['meaningless_patch_count']},'status':'PASS'}
(OUT/'k1_evaluation.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
