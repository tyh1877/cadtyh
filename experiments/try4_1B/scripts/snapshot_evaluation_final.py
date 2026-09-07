"""Record the row-order-only evaluator amendment after final audit."""
import hashlib,json
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=ROOT/'experiments/try4_1B';files=['scripts/evaluate_conditions.py','scripts/evaluate_structure.py','scripts/structure_gate.py','protocol.json','topology_gt/R02_P04_topology_gt.json','topology_gt/R02_P06_topology_gt.json','../../try4/scripts/evaluate_phase5.py']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
out={'created_at':datetime.now(timezone.utc).isoformat(),'supersedes':'evaluation_snapshot_attempt_01.json','change':'deterministic substructure row ordering only; metric values and gates unchanged','files':{p:sha((HERE/p).resolve()) for p in files}};(HERE/'results/evaluation_snapshot.json').write_text(json.dumps(out,indent=2)+'\n')
