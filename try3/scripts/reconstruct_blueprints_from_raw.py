"""Recover valid blueprints from preserved Try-3 final planner responses."""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'try3/scripts'))
from generate_try3_plans import enforce,skeleton
def main():
 p=argparse.ArgumentParser();p.add_argument('--version',choices=('V1','V2'),required=True);p.add_argument('--case',required=True);a=p.parse_args();run=ROOT/'try3/runs'/a.version/a.case;history=json.loads((run/'raw_history.json').read_text());raw=history[-1]['response'];links,joints=skeleton(ROOT/'try2/inputs/sanitized_urdf'/(a.case+'.urdf'));bp=enforce(raw,links,joints);(run/'blueprint.json').write_text(json.dumps(bp,indent=2));print(json.dumps({'case_id':a.case,'version':a.version,'links':len(bp['links']),'primitive_count':sum(len(x['primitives']) for x in bp['links'])}))
if __name__=='__main__':main()
