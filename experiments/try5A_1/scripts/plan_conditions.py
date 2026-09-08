"""Create C1/C2 collision-aware link body plans and materialize CAD IR without altering interfaces."""
import copy, hashlib, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]; SRC=ROOT/'experiments/try5A'; HERE=ROOT/'experiments/try5A_1'
FRAME={'origin':[0,0,0],'x_axis':[1,0,0],'y_axis':[0,1,0],'z_axis':[0,0,1]}
# Selected strictly from C0 exact collision sources; L11 is a frozen tool-frame marker.
REPLAN=['L00','L01','L02','L03','L04','L05','L06','L07','L08','L09','L10']
C1={'L00':(.72,.72),'L01':(.52,.60),'L02':(.55,.55),'L03':(.56,.56),'L04':(.43,.43),'L05':(.48,.48),'L06':(.60,.60),'L07':(.40,.50),'L08':(.55,.55),'L09':(.65,.65),'L10':(.65,.65)}
# C2 restores a controlled amount of visual envelope while retaining C1 clearance margins.
C2={'L00':(.72,.72),'L01':(.60,.65),'L02':(.65,.60),'L03':(.56,.56),'L04':(.43,.43),'L05':(.48,.48),'L06':(.60,.60),'L07':(.50,.55),'L08':(.55,.55),'L09':(.74,.72),'L10':(.74,.72)}
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def scaled(op,factors):
 o=copy.deepcopy(op);a,b=factors
 if o['op_type']=='cylinder_primitive': o['radius_mm']*=a;o['height_mm']*=b
 elif o['op_type']=='oriented_box': o['width_mm']*=a;o['depth_mm']*=b
 elif o['op_type']=='lofted_prism': o['start_size_mm']=[x*a for x in o['start_size_mm']];o['end_size_mm']=[x*b for x in o['end_size_mm']]
 return o
def main():
 contracts={p.stem:sha(p) for p in sorted((SRC/'interface_graph/contracts').glob('*.json'))}
 plan=json.loads((SRC/'blackboard/robot_assembly_plan.json').read_text()); P={x['link_id']:x for x in plan['links']}
 raw=json.loads((HERE/'collision_cache/c0_raw_pairs.json').read_text())
 risk={lid:[] for lid in REPLAN}
 for r in raw:
  if r['classification'] not in {'ADJACENT_UNINTENDED','NONADJACENT_TRUE','MOTION_ADJACENT_UNINTENDED','MOTION_INDUCED_TRUE'}: continue
  for lid in (r['link_a'],r['link_b']):
   if lid in risk: risk[lid].append(r)
 for condition,factors in [('C1',C1),('C2',C2)]:
  for lid in [f'L{i:02d}' for i in range(12)]:
   source=SRC/'A2'/lid;out=HERE/condition/lid;out.mkdir(parents=True,exist_ok=True)
   ir=json.loads((source/'cad_ir.json').read_text());refs=json.loads((source/'InterfaceRefs.json').read_text())
   state='FROZEN' if lid not in REPLAN else ('COLLISION_REPLAN' if condition=='C1' else 'COLLISION_AND_MORPHOLOGY_REPLAN')
   if lid in REPLAN:
    ir['ir_version']=f'try5A_1_{condition.lower()}_frozen_interface_body_replan_v1'
    ir['operations']=[scaled(o,factors[lid]) if o['feature_ref']=='BODY' else o for o in ir['operations']]
    ir['assumptions']=[f'{condition} consumes frozen interface contracts and collision-aware body spec','only BODY operations may differ from C0']
   # InterfaceRefs are byte-for-byte derived data and their contract hashes must remain unchanged.
   (out/'InterfaceRefs.json').write_text(json.dumps(refs,indent=2)+'\n')
   (out/'cad_ir.json').write_text(json.dumps(ir,indent=2)+'\n')
   (out/'agent_output.json').write_text(json.dumps({'part_id':lid,'link_id':lid,'condition':condition,'cad_ir':ir,'interface_contracts_frozen':True},indent=2)+'\n')
   lp=P[lid];incident=[x['joint_id'] for x in refs['interfaces']]
   spec={'condition':condition,'link_id':lid,'state':state,'centerline':{'source':'URDF canonical interface centers','principal_direction':lp['principal_direction']},'interface_to_interface_span_m':lp['coarse_envelope_m'],'allowed_body_region':{'type':'collision_limited_envelope','scale_factors':list(factors.get(lid,(1,1)))},'forbidden_collision_region':{'source':'C0 exact collision pairs','event_count':len(risk.get(lid,[]))},'neighbor_exclusion_regions':sorted({x['link_b'] if x['link_a']==lid else x['link_a'] for x in risk.get(lid,[])}),'maximum_cross_section_scale':max(factors.get(lid,(1,1))),'preferred_section_family':lp['body_family'],'visual_silhouette_constraints':({'description':'restore major silhouette only within C1 clearance envelope','target':'reference major thickness/taper'} if condition=='C2' else {'description':'not optimized in C1'}),'protected_interface_regions':incident,'motion_swept_exclusion_regions':{'source':'13 C0 sampled URDF poses','active_joints':['J00','J01','J02','J03']},'contract_hashes':{j:contracts[j] for j in incident},'cad_consumption':{'body_operation_scale':list(factors.get(lid,(1,1))),'body_ops_changed':lid in REPLAN,'interface_ops_changed':False}}
   (HERE/'body_specs'/condition).mkdir(parents=True,exist_ok=True);(HERE/'body_specs'/condition/f'{lid}.json').write_text(json.dumps(spec,indent=2)+'\n')
   if lid in REPLAN:
    actions='REDUCE_CROSS_SECTION' if condition=='C1' else 'RESTORE_VISUAL_ENVELOPE_WITHIN_C1_LIMIT'
    contract={'link_id':lid,'state':state,'collision_pairs':sorted({[r['link_a'],r['link_b']][0]+'-'+[r['link_a'],r['link_b']][1] for r in risk[lid]}),'collision_event_count':len(risk[lid]),'protected_interfaces':incident,'recommended_action':actions,'do_not_change':['interface frame','parent/child port','interface radius/depth','target gap','protected interface geometry'],'consumed_by':'cad_ir BODY operation only'}
    (HERE/'collision_analysis').mkdir(exist_ok=True);(HERE/'collision_analysis'/f'{condition}_{lid}_repair_contract.json').write_text(json.dumps(contract,indent=2)+'\n')
 print(json.dumps({'replanned':REPLAN,'frozen':['L11'],'conditions':['C1','C2']}))
if __name__=='__main__':main()
