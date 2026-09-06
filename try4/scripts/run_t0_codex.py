"""Run one independent, no-retry Codex CLI context per DEV_A Macro-Part."""
import csv,hashlib,json,subprocess,time
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];EXP=ROOT/'try4';OUT=EXP/'T0';RESULTS=EXP/'results'
PROMPT=EXP/'prompts/t0_direct.md';SCHEMA=EXP/'schemas/t0_direct_output.schema.json'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2)+'\n',encoding='utf-8')

def main():
    validation=json.loads((RESULTS/'phase12_validation.json').read_text())
    assert validation['status']=='PASS' and validation['reconstruction_runs']==0
    # Refuse if Phase 1+2 sources changed after user confirmation.
    for rel,value in validation['phase12_snapshot'].items():assert sha(EXP/rel)==value,(rel,'changed')
    split={r['robot_id']:r for r in csv.DictReader((EXP/'robots/try4_robot_split.csv').open())}
    assert split['R01']['role']=='DEV_A'
    packet_manifest={r['part_id']:r for r in json.loads((RESULTS/'packet_manifest.json').read_text())}
    parts=sorted(pid for pid in packet_manifest if pid.startswith('R01_'))
    assert parts==[f'R01_P{i:02d}' for i in range(5)]
    # Freeze the complete T0 method before the first model call.
    method_files=[PROMPT,SCHEMA,Path(__file__),EXP/'scripts/freecad_t0_executor.py',EXP/'scripts/run_t0_freecad.py',EXP/'scripts/validate_t0.py']
    method={'created_at':datetime.now(timezone.utc).isoformat(),'condition':'T0','policy':'single pass; independent ephemeral Codex CLI context; no retry/review/repair','files':{str(p.relative_to(EXP)):sha(p) for p in method_files},'cli_version':subprocess.check_output(['codex','--version'],text=True).strip()}
    dump(RESULTS/'t0_method_snapshot.json',method)
    rows=[]
    for pid in parts:
        packet=EXP/packet_manifest[pid]['packet_path']; assert sha(packet)==packet_manifest[pid]['sha256']
        work=EXP/'packets'/pid; out=OUT/pid/'round_0';out.mkdir(parents=True,exist_ok=True)
        target=work/'t0_agent_output.json'
        if target.exists() or (out/'agent_output.json').exists():raise RuntimeError(f'{pid}: formal output exists; refusing second call')
        images=[str((work/r['path']).resolve()) for r in json.loads(packet.read_text())['reference_images']]
        image_args=[value for image in images for value in ['-i',image]]
        # This installed exec subcommand advertises but rejects the approval flag;
        # read-only sandboxing is sufficient because the agent only returns JSON.
        cmd=['codex','exec','--ephemeral','--ignore-user-config','--skip-git-repo-check','-C',str(work),'-s','read-only',*image_args,'--output-schema',str(SCHEMA.resolve()),'--json','-o',str(target),'-']
        started=time.time();p=subprocess.run(cmd,input=PROMPT.read_text(encoding='utf-8'),capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=1200);elapsed=time.time()-started
        (out/'codex_events.jsonl').write_text(p.stdout,encoding='utf-8');(out/'codex_stderr.txt').write_text(p.stderr,encoding='utf-8')
        status='SUCCESS' if p.returncode==0 and target.is_file() else 'FAILURE'
        if target.is_file():
            target.replace(out/'agent_output.json')
        record={'part_id':pid,'status':status,'returncode':p.returncode,'elapsed_seconds':elapsed,'packet_sha256':sha(packet),'output_sha256':sha(out/'agent_output.json') if status=='SUCCESS' else '',
                'images_attached':10,'context_policy':'independent_ephemeral_packet_only','model_retry_count':0,'cli_invocation_attempt':5,'started_at':datetime.now(timezone.utc).isoformat(),'error':p.stderr[-1000:] if p.returncode else ''}
        dump(out/'agent_manifest.json',record);rows.append(record);print(pid,status,flush=True)
    with (RESULTS/'t0_codex_calls.csv').open('w',newline='',encoding='utf-8') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

if __name__=='__main__':main()
