"""Compile attachment contracts and CAD IR for D0_physicalized from frozen C1 only."""
import copy,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=ROOT/'experiments/try5A';T=HERE/'try5A_2';SRC=ROOT/'experiments/try5A_1/C1';rows=json.loads((T/'evaluator/raw/d0_attachment_rows.json').read_text());types={x['link_id']:x for x in json.loads((T/'virtual_link_filter/link_realization_types.json').read_text())['links']};FRAME={'origin':[0,0,0],'x_axis':[1,0,0],'y_axis':[0,1,0],'z_axis':[0,0,1]}
def dump(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
contracts=[]
for r in rows:
 if not r['included_in_bicr']:continue
 lid=r['link_id'];cid=r['carrier_id'];action='FUSE_OVERLAPPING_CARRIER' if r['classification']=='OVERLAPPING_SEPARATE_SOLID' else 'ADD_NECK_CONNECTOR'
 extent=0.0 if action=='FUSE_OVERLAPPING_CARRIER' else r['minimum_distance_mm']
 c={'repair_id':f'D0P_{lid}_{cid}','link_id':lid,'interface_id':cid,'source_body':r['body_target_object'],'target_carrier':r['carrier_object'],'attachment_classification':r['classification'],'repair_action':action,'attachment_subregion':{'carrier_bbox_source':'frozen D0 carrier B-Rep','body_nearest_region':r['body_target_object'],'allowed_connector_corridor_mm':[r.get('nearest_body_point_mm'),r.get('nearest_carrier_point_mm')],'protected_mating_side':'carrier cylindrical/annular mating envelope unchanged','maximum_connector_extent_mm':extent+0.05,'forbidden_external_direction':'outside nearest-point corridor'},'protected':['joint frame','port radius','port depth','target gap','mating geometry'],'cad_consumption':'pending'};contracts.append(c)
# Contracts are consumed deterministically into Boolean union / local connector operations.
for lid,t in types.items():
 if not t['solid_generation_allowed']:continue
 src=SRC/lid;out=T/'D0_physicalized/links'/lid;ir=json.loads((src/'cad_ir.json').read_text());ops=copy.deepcopy(ir['operations']);final=list(ir['final_objects']);local=[x for x in contracts if x['link_id']==lid];counter=max(int(x['op_id'].split('_')[-1]) for x in ops)+1;manifest=[]
 for c in local:
  base=c['source_body'];carrier=c['target_carrier'];connector=None
  if c['repair_action']=='ADD_NECK_CONNECTOR':
   a,b=c['attachment_subregion']['allowed_connector_corridor_mm'];dist=sum((a[k]-b[k])**2 for k in range(3))**.5
   if dist<=1e-6:raise RuntimeError(f'empty connector corridor {c["repair_id"]}')
   # Extend both ends by 0.5 mm so the connector has positive volumetric overlap with frozen solids.
   unit=[(b[k]-a[k])/dist for k in range(3)];a=[a[k]-0.5*unit[k] for k in range(3)];b=[b[k]+0.5*unit[k] for k in range(3)]
   connector=f'op_{counter:03d}';counter+=1;ops.append({'op_id':connector,'op_type':'oriented_box','target_body':connector,'dependencies':[],'feature_ref':'ATTACHMENT_CONNECTOR_'+c['interface_id'],'reference_frame':FRAME,'start':a,'end':b,'width_mm':8.0,'depth_mm':8.0,'operation_mode':'new_body'})
   fuse_conn=f'op_{counter:03d}';counter+=1;ops.append({'op_id':fuse_conn,'op_type':'boolean_union','target_body':base,'dependencies':[base,connector],'feature_ref':'ATTACHMENT_'+c['interface_id'],'reference_frame':FRAME,'tool_bodies':[connector]});base=fuse_conn
  fuse=f'op_{counter:03d}';counter+=1;ops.append({'op_id':fuse,'op_type':'boolean_union','target_body':base,'dependencies':[base,carrier],'feature_ref':'ATTACHMENT_'+c['interface_id'],'reference_frame':FRAME,'tool_bodies':[carrier]})
  final=[x for x in final if x not in {c['source_body'],carrier}];final.append(fuse);c['cad_consumption']={'connector_object':connector,'attachment_result_object':fuse,'source_body':c['source_body'],'target_carrier':carrier};manifest.append(c['cad_consumption']|{'interface_id':c['interface_id'],'repair_action':c['repair_action']})
 ir['ir_version']='try5A_2_d0_physicalized_attachment_v1';ir['operations']=ops;ir['final_objects']=final;ir['attachment_manifest']=manifest;ir['assumptions']=['frozen D0 interface operations and frames','only attachment subregions added','virtual links excluded'];ir['editable_parameter']=next(x for x in [ir['editable_parameter']] if x)
 out.mkdir(parents=True,exist_ok=True);dump(out/'cad_ir.json',ir);dump(out/'agent_output.json',{'part_id':lid,'link_id':lid,'condition':'D0_physicalized','cad_ir':ir});dump(out/'InterfaceRefs.json',json.loads((src/'InterfaceRefs.json').read_text()));dump(out/'attachment_manifest.json',manifest);dump(T/'D0_physicalized/attachment_subregions'/f'{lid}.json',[x['attachment_subregion']|{'interface_id':x['interface_id']} for x in local]);dump(T/'D0_physicalized/attachment_contracts'/f'{lid}.json',local)
dump(T/'D0_physicalized/attachment_contracts/all_contracts.json',contracts);print(json.dumps({'physical_links':sum(t['solid_generation_allowed'] for t in types.values()),'contracts':len(contracts),'fuses':sum(c['repair_action']=='FUSE_OVERLAPPING_CARRIER' for c in contracts),'connectors':sum(c['repair_action']=='ADD_NECK_CONNECTOR' for c in contracts)}))
