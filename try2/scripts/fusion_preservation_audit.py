"""Audit currently evidenced Fusion preservation without inferring unrecorded facts."""
from __future__ import annotations
import csv,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def main():
 rows=[]
 for src,dst in (('A','B'),('C','D')):
  for run in sorted((ROOT/'try2/runs'/src).glob('dev_arm-*')):
   bp=run/'blueprint.json';fx=ROOT/'try2/runs'/dst/run.name/'fusion_execution.json'
   if not bp.exists() or not fx.exists():continue
   plan=json.loads(bp.read_text());result=json.loads(fx.read_text());base=result['status']=='SUCCESS'
   rows.append({'condition':dst,'case_id':run.name,'link_preserved':base and result.get('component_count')==len(plan['links']),'joint_count_preserved':base and result.get('joint_count')==len(plan['joints']),'axis_preserved':False,'origin_preserved':False,'limit_preserved':False,'reason':'CURRENT_TOOL_LAYER_CREATES_Z_AXIS_JOINTS_ONLY'})
 out=ROOT/'try2/results';out.mkdir(exist_ok=True)
 with (out/'kinematic_preservation.csv').open('w',newline='') as h:w=csv.DictWriter(h,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
if __name__=='__main__':main()
