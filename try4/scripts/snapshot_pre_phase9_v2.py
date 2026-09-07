"""Record the final development-pilot method and artifact hashes."""
import hashlib,json
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];EXP=ROOT/'try4';files=['protocol/pre_phase9_v2_protocol.json','codex_authored/PRE_PHASE9_V2/pilot_blueprints.json','skills/cad_operation_vocabulary_v2/SKILL.md','scripts/compile_pre_phase9_v2.py','scripts/run_pre_phase9_v2_pilot.py','scripts/evaluate_pre_phase9_v2.py','protocol/phase5_evaluator_v1.json']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
out={'created_at':datetime.now(timezone.utc).isoformat(),'snapshot_type':'development pilot final method; no formal freeze','base_commit':'86cab8d','files':{p:sha(EXP/p) for p in files}};(EXP/'results/pre_phase9_v2_method_snapshot.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
