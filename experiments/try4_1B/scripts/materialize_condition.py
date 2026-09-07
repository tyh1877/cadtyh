"""Compile schema-valid family instances into MFG and CAD IR; never reads topology_gt."""
import argparse,json
from pathlib import Path
import jsonschema
ROOT=Path(__file__).resolve().parents[3];HERE=ROOT/'experiments/try4_1B';TRY4=ROOT/'try4'
def dump(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2)+'\n',encoding='utf-8')
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--condition',choices=['B1','B2'],required=True);a=ap.parse_args();schema=json.loads((HERE/'schemas/executable_shape_family_v1.schema.json').read_text());rows=[]
 for path in sorted((HERE/f'shape_family_schemas/{a.condition}').glob('*.json')):
  inst=json.loads(path.read_text());jsonschema.validate(inst,schema);pid=inst['part_id'];prior=json.loads((ROOT/f'experiments/try4_1A/A1/{pid}/round_0/agent_output.json').read_text());features=[]
  for s in inst['substructures']:features.append({'feature_id':s['feature_ref'],'requirement_refs':[],'feature_type':s['semantic_role'],'role':'substructure','evidence':['isolated_front','isolated_side','isolated_top','isolated_isometric'],'reference_region':s['semantic_role'],'estimated_dimensions_mm':{'bbox':s['approximate_bbox']},'shape_family':s['shape_family'],'intended_cad_strategy':s['cad_strategy'],'dependencies':s['connection_relation'],'critical':s['substructure_id'] in inst['required_substructures'],'confidence':0.75,'status':'PLANNED'})
  graph={'features':features};ops=inst['construction_sequence'];used={o['feature_ref'] for o in ops};required={s['feature_ref'] for s in inst['substructures']};assert required<=used
  ir={**prior['cad_ir'],'bodies':[{'body_id':f'B{i:02d}','role':a.condition+' final object','feature_ids':sorted(required),'final_object':x} for i,x in enumerate(inst['final_objects'])],'operations':ops,'final_objects':inst['final_objects'],'editable_parameter':inst['editable_parameter'],'assumptions':[a.condition+' executable family instance; no GT geometry or topology-GT consumed']};agent={**prior,'condition':a.condition,'executable_shape_family':inst,'feature_graph':graph,'cad_ir':ir};out=HERE/a.condition/pid/'round_0';dump(out/'agent_output.json',agent);dump(out/'feature_graph.json',graph);dump(out/'cad_ir.json',ir);dump(HERE/f'feature_graphs/{a.condition}/{pid}.json',graph);dump(HERE/f'cad_ir/{a.condition}/{pid}.json',ir);rows.append(pid)
 print(json.dumps({'condition':a.condition,'parts':rows}))
if __name__=='__main__':main()
