"""Compile robot-specific morphology contracts from generic policy + frozen plans."""
import hashlib,json
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[3];HERE=ROOT/'experiments/try5A';POLICY=ROOT/'try5/knowledge/coarse_morphology/gate_policy.json';PLAN=HERE/'blackboard/robot_assembly_plan.json';R5=HERE/'blackboard/r5_subassembly_plan.json';SKEL=HERE/'blackboard/kinematic_skeleton.json';OUT=HERE/'blackboard/coarse_morphology_contracts.json'
policy=json.loads(POLICY.read_text());plan=json.loads(PLAN.read_text());r5=json.loads(R5.read_text()) if R5.exists() else {'link_overrides':{}};skel=json.loads(SKEL.read_text());plans={x['link_id']:{**x,**r5['link_overrides'].get(x['link_id'],{})} for x in plan['links']};joints=skel['joints'];contracts=[]
for lid,p in plans.items():
 contracts.append({'link_id':lid,'realization':'virtual_frame' if p['body_family']=='interface_marker' else 'physical_body','planned_envelope_mm':[1000*x for x in p['coarse_envelope_m']],'principal_direction_local':p['principal_direction'],'body_family':p['body_family'],'functional_role':p['role'],'required_interfaces':[j['joint_id'] for j in joints if lid in (j['parent'],j['child']) and plans[j['child']]['body_family']!='interface_marker'],'required_relations':['valid_geometry','commensurate_envelope','principal_direction_preserved']+([] if p['body_family']=='interface_marker' else ['connected_rigid_load_path'])})
groups=[]
for parent in plans:
 js=[j for j in joints if j['parent']==parent and j['joint_type']=='prismatic']
 if len(js)<2:continue
 for aidx,a in enumerate(js):
  for b in js[aidx+1:]:
   mimic=b.get('mimic') or a.get('mimic');opposed=bool(mimic and float(mimic.get('multiplier',1))<0)
   if not opposed:continue
   children=[a['child'],b['child']];axes=[np.array(a['axis'],float),np.array(b['axis'],float)];tool=np.mean([np.array(plans[x]['principal_direction'],float) for x in children],axis=0);tool=(tool/np.linalg.norm(tool)).tolist();groups.append({'subassembly_id':'opposed_prismatic_pair_'+parent,'derived_from':'shared parent + two prismatic children + negative mimic relation','carrier_link':parent,'functional_members':children,'joint_ids':[a['joint_id'],b['joint_id']],'motion_axes_local':[x.tolist() for x in axes],'tool_direction_local':tool,'required_relations':['members_are_distinct','members_lie_on_opposite_sides_of_carrier','members_extend_beyond_nonfunctional_carrier_along_tool_direction','motion_mimic_is_opposed','multi_view_functional_members_are_distinguishable'],'suggested_failure_scope':'R5_SUBASSEMBLY_REPLAN'})
out={'schema_version':'try5A_coarse_morphology_contract_v1','compiled_before_cad_evaluation':True,'sources':{'policy':str(POLICY.relative_to(ROOT)).replace('\\','/'),'policy_sha256':hashlib.sha256(POLICY.read_bytes()).hexdigest(),'plan_sha256':hashlib.sha256(PLAN.read_bytes()).hexdigest(),'r5_subassembly_plan_sha256':hashlib.sha256(R5.read_bytes()).hexdigest() if R5.exists() else None,'skeleton_sha256':hashlib.sha256(SKEL.read_bytes()).hexdigest()},'thresholds':policy['thresholds'],'links':contracts,'functional_subassemblies':groups,'visual_evidence_required':['front','side','top','isometric']};OUT.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'links':len(contracts),'subassemblies':len(groups),'r5_overrides':len(r5['link_overrides']),'output':str(OUT.relative_to(ROOT))},indent=2))
