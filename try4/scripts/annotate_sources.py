"""Offline curated semantic grouping; no CAD parameter extraction for planning."""
import csv
import hashlib
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from prepare_phase12 import ROOT,EXP,SOURCES,SELECTED,dump

# Explicit per-source annotation, not a generator or shape template. Labels are
# checked visually after isolated rendering; all source leaves must be assigned.
GROUPS={
'R01':[
 ('base_module','base mounting pedestal',[0],None,'waist','ground mounting face','waist rotating support'),
 ('joint_module','shoulder pivot housing',[1],'waist','shoulder','waist support','upper-arm pivot'),
 ('link_module','upper-arm carrier assembly',[6],'shoulder','elbow','shoulder pivot','elbow pivot'),
 ('link_module','forearm side frame',[2],'elbow','wrist_angle','elbow pivot','gripper pitch attachment'),
 ('end_interface','parallel gripper assembly',[3,4,5],'wrist_angle',None,'wrist pitch attachment','two opposed contact fingers')],
'R02':[
 ('base_module','base mounting pedestal',[0],None,'waist','ground mounting face','waist rotating support'),
 ('joint_module','dual shoulder support',[1],'waist','shoulder','waist support','upper-arm pivot'),
 ('link_module','upper-arm side frame',[2],'shoulder','elbow','shoulder pivot','elbow pivot'),
 ('joint_module','elbow and forearm-roll housing',[3],'elbow','forearm_roll','elbow pivot','roll interface'),
 ('link_module','lower forearm housing',[4],'forearm_roll','wrist_angle','roll interface','wrist pitch pivot'),
 ('wrist_module','wrist pitch and roll carrier',[5],'wrist_angle','wrist_rotate','pitch pivot','tool roll interface'),
 ('end_interface','dual-rail gripper assembly',list(range(6,24)),'wrist_rotate',None,'tool roll attachment','opposed sliding jaws')],
'R03':[
 ('base_module','base skirt and mounting assembly',[0,1],None,'waist','ground mounting face','waist support'),
 ('joint_module','shoulder support assembly',[2],'waist','shoulder','waist support','upper-arm pivot'),
 ('link_module','upper-arm side frame',[3],'shoulder','elbow','shoulder pivot','elbow pivot'),
 ('link_module','forearm side frame',[4],'elbow','wrist_angle','elbow pivot','wrist pitch pivot'),
 ('wrist_module','wrist pitch and roll carrier',[5],'wrist_angle','wrist_rotate','pitch pivot','tool roll attachment'),
 ('end_interface','parallel gripper assembly',[6,7,8],'wrist_rotate',None,'tool roll attachment','opposed contact fingers')]
}
PALETTE=[[230,57,70],[95,125,180],[69,123,157],[42,157,143],[233,196,106],
         [244,162,97],[131,56,236],[255,0,110],[58,134,255],[6,174,130],[205,159,52],[17,138,178],
         [84,145,155],[239,71,111],[78,160,107],[205,133,3],[33,158,188],[155,90,20]]
URDF_ROOT=ROOT/'go_nogo1/sources/urdf_files_dataset/urdf_files/robotics-toolbox/xacro_generated/interbotix_descriptions/urdf'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    sources={r['slug']:r for r in csv.DictReader((SOURCES/'source_manifest.csv').open(encoding='utf-8-sig'))}
    provenance=[]; splits=[]
    for rid,slug,role in SELECTED:
        inv=json.loads((EXP/'artifacts'/rid/'inventory.json').read_text())
        components=inv['components']; byid={c['component_id']:c for c in components}
        u=URDF_ROOT/(slug+'.urdf'); tree=ET.parse(u).getroot()
        names=[n.get('name') for n in tree.findall('link')]; lmap={n:f'L{i:02d}' for i,n in enumerate(names)}
        joints=[]; jmap={}
        for i,node in enumerate(tree.findall('joint')):
            jid=f'J{i:02d}';jmap[node.get('name')]=jid
            origin=node.find('origin');axis=node.find('axis');limit=node.find('limit')
            joints.append({'joint_id':jid,'joint_type':node.get('type'),'parent':lmap[node.find('parent').get('link')],'child':lmap[node.find('child').get('link')],
                           'origin_xyz_m':[float(x) for x in (origin.get('xyz','0 0 0') if origin is not None else '0 0 0').split()],
                           'origin_rpy_rad':[float(x) for x in (origin.get('rpy','0 0 0') if origin is not None else '0 0 0').split()],
                           'axis':[float(x) for x in (axis.get('xyz','0 0 1') if axis is not None else '0 0 1').split()],
                           'limits':{k:float(limit.get(k)) for k in ['lower','upper'] if limit is not None and limit.get(k) is not None}})
        dump(EXP/'robots/sanitized_kinematics'/f'{rid}.json',{'robot_id':rid,'links':list(lmap.values()),'joints':joints,'authority':'sanitized_urdf','units':{'translation':'m','rotation':'rad'}})
        parts=[]
        for i,(kind,label,cids,prox,dist,pdesc,ddesc) in enumerate(GROUPS[rid]):
            pid=f'{rid}_P{i:02d}'; related=[jmap[n] for n in [prox,dist] if n]
            finger_ids=[jmap[n] for n in ['left_finger','right_finger'] if n in jmap] if kind=='end_interface' else []
            parts.append({'part_id':pid,'role_class':kind,'semantic_label':label,'color_rgb':PALETTE[i+{'R01':0,'R02':5,'R03':12}[rid]],
                          'description':f'Exterior mechanical region comprising the {label}; retain its visible silhouette and both boundary interface regions.',
                          'proximal_joint':jmap.get(prox),'distal_joint':jmap.get(dist),'related_joints':related+finger_ids,
                          'source_components':[f'C{n:02d}' for n in cids],
                          'source_mapping':[byid[f'C{n:02d}'] for n in cids],
                          'interfaces':[{'side':'proximal','joint_id':jmap.get(prox),'semantic_type':pdesc,'region':'proximal attachment boundary'}, {'side':'distal','joint_id':jmap.get(dist),'semantic_type':ddesc,'region':'distal attachment/contact boundary'}],
                          'critical_regions':['primary exterior envelope',pdesc,ddesc],
                          'mapping_status':'semantic association from source labels and supplied URDF; STEP-to-URDF rigid registration not established',
                          'multi_body_policy':'retain constituent bodies and visible separations; do not fuse moving jaws' if kind=='end_interface' else 'retain visible exterior and source constituent membership; not asserted to be a manufacturing part'})
        assert sorted(c for p in parts for c in p['source_components'])==sorted(byid)
        dump(EXP/'robots/semantic_parts'/f'{rid}.json',{'schema_version':'try4_semantic_parts_v1','robot_id':rid,'offline_annotation_only':True,'source_step_sha256':inv['step_sha256'],'parts':parts})
        dof={'px100':4,'vx300s':6,'rx200':5}[slug]
        splits.append({'robot_id':rid,'source_robot':sources[slug]['dataset_name'],'role':role,'arm_dof':dof,'number_of_macro_parts':len(parts),'leaf_components':len(components),'source_solids':sum(c['solids'] for c in components),
                       'geometry_difficulty':'easy_medium' if role=='DEV_A' else 'relative_hard' if role=='DEV_B' else 'medium_transfer',
                       'surface_complexity':'plates_round_bosses_openings' if role!='DEV_B' else 'split_forearm_wrist_curved_contours_dense_gripper',
                       'why_selected':'available native STEP and local URDF; '+('compact pilot' if role=='DEV_A' else '24 leaves, 6 arm axes, complex wrist and multi-body gripper' if role=='DEV_B' else 'unused in prior colored-step five-case cohort; same-family transfer only')})
        provenance.append({'robot_id':rid,**sources[slug],'step_path':str(Path(sources[slug]['step_files']).relative_to(ROOT)),'step_sha256':inv['step_sha256'],'urdf_path':str(u.relative_to(ROOT)),'urdf_sha256':sha(u),'joint_name_mapping_offline':jmap,'freecad_version':inv['freecad_version'],'version_policy':'source ZIP/STEP hashes are authoritative; source has no pinned release tag','regeneration_script':'go_nogo1/scripts/download_trossen_step.py'})
    for record in provenance:
        record['urdf_dataset_url']='https://github.com/utecrobotics/urdf_files_dataset'
        record['urdf_dataset_commit']='81f4cdac42c3a51ba88833180db5bf3697988c87'
    out=EXP/'robots/try4_robot_split.csv';out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(splits[0]));w.writeheader();w.writerows(splits)
    dump(EXP/'robots/source_provenance.json',provenance)
    print(json.dumps({'robots':len(splits),'parts':sum(r['number_of_macro_parts'] for r in splits),'split_frozen_before_try4_generations':True}))

if __name__=='__main__':main()
