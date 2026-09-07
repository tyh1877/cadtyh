"""Freeze Phase 6–8 formal method after pilot and before full T2 matrix."""
import hashlib,json
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];EXP=ROOT/'try4';files=['protocol/phase5_evaluator_v1.json','results/phase5_method_snapshot.json','protocol/phase78_repair_protocol_v1.json','schemas/repair_contract.schema.json','schemas/post_repair_review.schema.json','skills/structured_part_review/SKILL.md','skills/structured_part_repair/SKILL.md','scripts/materialize_t2_round.py','scripts/run_t2_round.py','scripts/update_t2_state.py','scripts/run_phase8_matrix.py','codex_authored/T2/round1_decisions.json','AMENDMENT_PHASE8_POST_REVIEW.md']
out={'frozen_at':datetime.now(timezone.utc).isoformat(),'after_numeric_pass_visual_audit':True,'before_phase8_continuation':True,'supersedes':'phase78_method_snapshot_attempt_01.json','files':{p:hashlib.sha256((EXP/p).read_bytes()).hexdigest() for p in files}};(EXP/'results/phase78_method_snapshot.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8');print(json.dumps(out,indent=2))
