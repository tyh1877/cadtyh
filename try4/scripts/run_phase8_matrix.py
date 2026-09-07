"""Run one formal T2 round only for supplied actionable contracts."""
import argparse,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];EXP=ROOT/'try4'
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--round',type=int,required=True);ap.add_argument('--parts',nargs='*');args=ap.parse_args();folder=EXP/f'codex_authored/T2/round_{args.round}';contracts=sorted(folder.glob('R*.json'));contracts=[c for c in contracts if not args.parts or c.stem in args.parts];results=[]
 for c in contracts:
  data=json.loads(c.read_text());pid=data['part_id']
  if args.round>1:
   prev=json.loads((EXP/'T2'/pid/f'round_{args.round-1}/part_state.json').read_text());
   if prev['state'] not in ('LOCAL_REPAIR','REPLAN'):results.append({'part_id':pid,'status':'SKIPPED','reason':prev['state']});continue
  p=subprocess.run([sys.executable,'-X','utf8',str(EXP/'scripts/run_t2_round.py'),'--contract',str(c)],cwd=ROOT)
  if p.returncode:results.append({'part_id':pid,'status':'EXECUTION_FAILURE','returncode':p.returncode});continue
  q=subprocess.run([sys.executable,'-X','utf8',str(EXP/'scripts/update_t2_state.py'),'--part',pid,'--round',str(args.round)],cwd=ROOT);results.append({'part_id':pid,'status':'STATE_UPDATED' if q.returncode==0 else 'STATE_FAILURE','returncode':q.returncode})
 suffix='' if not args.parts else '_continuation';(EXP/f'results/phase8_round{args.round}_execution{suffix}.json').write_text(json.dumps(results,indent=2)+'\n',encoding='utf-8');print(json.dumps(results));return 0 if all(x['status'] in ('STATE_UPDATED','SKIPPED') for x in results) else 1
if __name__=='__main__':raise SystemExit(main())
