"""Deterministic graph and realized-operation topology metrics."""
import csv,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=ROOT/'experiments/try4_1A';TRY4=ROOT/'try4';PIDS=['R02_P02','R02_P04','R02_P05','R02_P06']
def f1(a,b):
 a,b=set(a),set(b);tp=len(a&b);return 2*tp/(len(a)+len(b)) if a or b else 1.0
rows=[]
for pid in PIDS:
 target=json.loads((HERE/f'topology_graphs/TARGET/{pid}.json').read_text());tn={n['node_id']:n for n in target['nodes']};target_roles={n['role'] for n in target['nodes']};target_open={n['role'] for n in target['nodes'] if n['node_type']=='open_space'};tr={(tn[x['source']]['role'],x['relation'],tn[x['target']]['role']) for x in target['relations']};tb={x for x in tr if x[1]=='branches_into'}
 for cond in ('A0','A1','A2'):
  pred=json.loads((HERE/f'topology_graphs/{cond}/{pid}.json').read_text());pn={n['node_id']:n for n in pred['nodes']};pr={(pn[x['source']]['role'],x['relation'],pn[x['target']]['role']) for x in pred['relations']};pb={x for x in pr if x[1]=='branches_into'};proles={n['role'] for n in pred['nodes']};popen={n['role'] for n in pred['nodes'] if n['node_type']=='open_space'};base=TRY4/f'T1/{pid}/round_0' if cond=='A0' else HERE/f'{cond}/{pid}/round_0';log=json.loads((base/'execution_log.json').read_text());ok={x['input_parameters']['feature_ref'] for x in log if x['success'] and not x['fallback_used']};mapped=[n for n in pred['nodes'] if n['cad_feature_refs'] and set(n['cad_feature_refs'])<=ok]
  rows.append({'part_id':pid,'condition':cond,'target_node_count':len(tn),'predicted_node_count':len(pn),'component_region_count_accuracy':max(0,1-abs(len(pn)-len(tn))/len(tn)),'branch_fork_accuracy':f1(tb,pb),'opening_gap_recall':len(target_open&popen)/len(target_open) if target_open else 1,'topology_relation_f1':f1(tr,pr),'topology_node_role_f1':f1(target_roles,proles),'realized_node_fraction':len(mapped)/len(pn)})
with (HERE/'results/topology_metrics.csv').open('w',newline='',encoding='utf-8') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
print(json.dumps({'rows':len(rows)}))
