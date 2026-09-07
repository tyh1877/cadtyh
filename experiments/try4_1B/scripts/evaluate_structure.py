"""Independent-topology and declared-substructure realization evaluator."""
import argparse,csv,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=ROOT/'experiments/try4_1B';A=ROOT/'experiments/try4_1A';ap=argparse.ArgumentParser();ap.add_argument('--conditions',nargs='+',required=True);args=ap.parse_args()
def f1(a,b):a,b=set(a),set(b);return 2*len(a&b)/(len(a)+len(b)) if a or b else 1.0
rows=[];subs=[]
for pid in ('R02_P04','R02_P06'):
 gt=json.loads((HERE/f'topology_gt/{pid}_topology_gt.json').read_text());gr={n['role'] for n in gt['nodes']};grels={tuple(x) for x in gt['relations']};gopen=set(gt['required_open_spaces']);gsym={tuple(x) for x in gt['required_symmetry']}
 for cond in args.conditions:
  if cond=='B0':
   graph=json.loads((A/f'topology_graphs/A1/{pid}.json').read_text());idrole={n['node_id']:n['role'] for n in graph['nodes']};roles=set(idrole.values());rels={(idrole[x['source']],x['relation'],idrole[x['target']]) for x in graph['relations']};opens={n['role'] for n in graph['nodes'] if n['node_type']=='open_space'};syms={x for x in rels if x[1]=='symmetric_with'};realized=1.0;family_rate=0.0;coverage=1.0
  else:
   p=HERE/f'shape_family_schemas/{cond}/{pid}.json'
   if not p.exists():continue
   inst=json.loads(p.read_text());roles={s['semantic_role'] for s in inst['substructures']};idrole={s['substructure_id']:s['semantic_role'] for s in inst['substructures']};rels=set();opens={s['semantic_role'] for s in inst['substructures'] if s['gap_relation']};syms=set()
   for s in inst['substructures']:
    for target in s['connection_relation']:
     if target in idrole:rels.add((s['semantic_role'],'connected_to',idrole[target]))
    if s['symmetry_relation'] in idrole:syms.add((s['semantic_role'],'symmetric_with',idrole[s['symmetry_relation']]));rels|=syms
    if s['gap_relation'] and s['gap_relation'] in idrole:rels.add((s['semantic_role'],'separated_by_gap',idrole[s['gap_relation']]));rels.add((idrole[s['gap_relation']],'separated_by_gap',s['semantic_role']))
   log=json.loads((HERE/f'{cond}/{pid}/round_0/execution_log.json').read_text());ok={x['input_parameters']['feature_ref'] for x in log if x['success'] and not x['fallback_used']};required={s['feature_ref'] for s in inst['substructures']};realized=len(required&ok)/len(required);coverage=realized;advanced={x['executed_native_operation'] for x in log if x['success']} - {'Part::Box','Part::Cylinder'};family_rate=1.0 if realized==1 and advanced else 0.0
   for s in inst['substructures']:subs.append({'part_id':pid,'condition':cond,'substructure_id':s['substructure_id'],'semantic_role':s['semantic_role'],'realized':s['feature_ref'] in ok,'cad_strategy':s['cad_strategy'],'protected':bool(s.get('protected',False))})
  rows.append({'part_id':pid,'condition':cond,'node_role_f1':f1(gr,roles),'topology_relation_f1':f1(grels,rels),'component_region_count_accuracy':max(0,1-abs(len(roles)-len(gr))/len(gr)),'branch_fork_accuracy':f1({x for x in grels if x[1]=='branches_into'},{x for x in rels if x[1]=='branches_into'}),'opening_gap_recall':len(gopen&opens)/len(gopen) if gopen else 1,'symmetry_relation_accuracy':f1(gsym,syms),'substructure_realization_recall':realized,'shape_family_realization_rate':family_rate,'required_feature_coverage':coverage})
def merge(path,new):
 old=[]
 if path.exists():
  with path.open(encoding='utf-8') as f:old=list(csv.DictReader(f))
 keys={(x['part_id'],x['condition']) for x in new};out=[x for x in old if (x['part_id'],x['condition']) not in keys]+new;out.sort(key=lambda x:(x['part_id'],x['condition']));f=path.open('w',newline='',encoding='utf-8');w=csv.DictWriter(f,fieldnames=list(out[0]));w.writeheader();w.writerows(out);f.close()
merge(HERE/'results/topology_metrics.csv',rows)
if subs:
 p=HERE/'results/substructure_metrics.csv';old=[]
 if p.exists():
  with p.open(encoding='utf-8') as f:old=list(csv.DictReader(f))
 keys={(x['part_id'],x['condition']) for x in subs};old=[x for x in old if (x['part_id'],x['condition']) not in keys];allr=old+subs;allr.sort(key=lambda x:(x['part_id'],x['condition'],x['substructure_id']));f=p.open('w',newline='',encoding='utf-8');w=csv.DictWriter(f,fieldnames=list(allr[0]));w.writeheader();w.writerows(allr);f.close()
print(json.dumps({'topology_rows':len(rows),'substructures':len(subs)}))
