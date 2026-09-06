"""Build allowlisted generator packets and explicit, view-backed feature lists."""
import csv
import hashlib
import json
import math
import shutil
from prepare_phase12 import ROOT,EXP,SELECTED,dump

# Curated from all 18 four-view isolated sheets in this task, not inferred from
# exact CAD faces or dimensions. Per-part list entries: region, visible feature,
# critical, source views. Common critical interface expectations come separately
# from the explicitly supplied semantic/joint context.
FEATURES={
'R01_P00':[('body','scalloped tapered pedestal',False,['front','side','isometric']),('base','polygonal mounting plate and rear extension',True,['top','isometric']),('top','annular recessed seating region',True,['top','isometric'])],
'R01_P01':[('body','stepped box housing and projecting lower support',False,['front','side','isometric']),('side','circular pivot cover outline',True,['side','isometric']),('top','rectangular inset cover boundary',False,['top'])],
'R01_P02':[('body','two separated long side plates and cross carrier',True,['front','top','isometric']),('side_plates','paired rectangular slots',False,['side','isometric']),('distal','open rounded fork ends',True,['side','isometric']),('proximal','circular pivot interface',True,['side','isometric'])],
'R01_P03':[('body','open-sided forearm with wide proximal box',True,['top','isometric']),('distal','fork opening with round terminal notches',True,['side','isometric']),('side','rectangular side slot',False,['side','isometric']),('proximal','circular pivot boundary',True,['side'])],
'R01_P04':[('jaws','two opposed tapered fingers with an open gap',True,['top','isometric']),('carriage','crosswise sliding carriage blocks',True,['front','top','isometric']),('attachment','forked pitch bracket with side slot',True,['side','isometric'])],
'R02_P00':[('body','scalloped tapered pedestal',False,['front','side','isometric']),('base','polygonal mounting plate and rear extension',True,['top','isometric']),('top','circular seating boundary',True,['top','isometric'])],
'R02_P01':[('base','wide circular support disk',True,['top','isometric']),('body','upright narrow support block',True,['front','side']),('pivot','coaxial circular side interfaces',True,['side','isometric'])],
'R02_P02':[('body','long narrow web and widened end carriers',True,['front','side','isometric']),('distal','forked open end',True,['side','isometric']),('proximal','circular pivot with raised cover boundary',True,['side','top'])],
'R02_P03':[('body','long narrow beam between roll housing and fork',True,['top','isometric']),('fork','triangular lightening openings and web structure',False,['top','isometric']),('roll','circular end housing',True,['front','side','isometric'])],
'R02_P04':[('body','offset widened plate outline with narrowed transition',True,['top','isometric']),('side','open channel between side members',True,['side']),('plate','visible distributed small hole pattern',False,['top','isometric']),('joint','round side housing boundaries',True,['front','side'])],
'R02_P05':[('body','two curved bracket arms separated by open space',True,['top','isometric']),('fork','rounded terminal notches and rectangular slots',True,['side','isometric']),('roll','large circular roll flange',True,['front','isometric'])],
'R02_P06':[('jaws','two opposed plate fingers with open grip gap',True,['top','isometric']),('carriage','dual rail and sliding carriage assembly',True,['front','top','isometric']),('plates','triangular rib/web bracing',False,['side','isometric'])],
'R03_P00':[('body','scalloped skirt and round upper seating disk',False,['front','isometric']),('base','polygonal base and rectangular rear extension',True,['top','isometric'])],
'R03_P01':[('base','circular mounting disk',True,['top','isometric']),('body','two upright supports with a clear central gap',True,['front','top','isometric']),('pivot','opposed circular pivot faces',True,['side','isometric'])],
'R03_P02':[('body','slender beam joining wider unequal end carriers',True,['front','side','isometric']),('distal','round terminal through opening',True,['side','isometric']),('proximal','circular pivot boss and stepped cover edge',True,['side','isometric'])],
'R03_P03':[('body','tapered widened section and slender central beam',True,['side','isometric']),('distal','forked attachment with round open notch',True,['side','top']),('proximal','circular pivot boundary and cover perimeter',True,['side','isometric'])],
'R03_P04':[('body','two curved side plates and transverse carrier',True,['top','isometric']),('fork','open terminal notches and side slots',True,['side','isometric']),('roll','round end interface',True,['front','isometric'])],
'R03_P05':[('jaws','two opposed tapered fingers separated by open gap',True,['top','isometric']),('carriage','cross rail and sliding blocks',True,['front','top']),('attachment','rectangular wrist attachment housing',True,['side','isometric'])]
}

def main():
    rows=[]; checklist=[]; manifests=[]
    lod=EXP/'skills/robot_part_modeling_standard/SKILL.md'
    for rid,slug,role in SELECTED:
        annotation=json.loads((EXP/'robots/semantic_parts'/f'{rid}.json').read_text())
        kin=json.loads((EXP/'robots/sanitized_kinematics'/f'{rid}.json').read_text())
        byjoint={j['joint_id']:j for j in kin['joints']}
        for p in annotation['parts']:
            pid=p['part_id']; root=EXP/'packets'/pid
            root.mkdir(parents=True,exist_ok=True)
            image_refs=[]
            for folder,views in [('global',['front','rear','left','right','top','isometric']),('isolated',['front','side','top','isometric'])]:
                for view in views:
                    source=EXP/'artifacts'/rid/folder
                    if folder=='isolated':source=source/pid
                    source=source/(view+'.png');relative=f'images/{folder}_{view}.png';dest=root/relative
                    dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,dest)
                    image_refs.append({'kind':folder,'view':view,'path':relative,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest()})
            features=[]
            for i,(region,description,critical,views) in enumerate(FEATURES[pid]):
                f={'feature_id':f'{pid}_E{i:02d}','region':region,'requirement':description,'critical':critical,
                   'evidence_views':[f'images/isolated_{v}.png' for v in views],
                   'annotation_source':'Codex offline visual inspection; not independent expert scoring',
                   'inclusion':'required_functional' if critical else 'visible_candidate_apply_dev_calibrated_relative_scale_rule',
                   'geometry_parameters':'must be estimated from images; no GT dimensions supplied'}
                features.append(f)
                checklist.append({'part_id':pid,'region':region,'feature':description,'critical':critical,'views':';'.join(views)})
            packet={'schema_version':'try4_part_input_v1','part_id':pid,'robot_id':rid,'role_class':p['role_class'],'semantic_label':p['semantic_label'],'color_rgb':p['color_rgb'],'description':p['description'],
                    'reference_images':image_refs,'global_color_legend':[{'part_id':q['part_id'],'color_rgb':q['color_rgb'],'semantic_label':q['semantic_label']} for q in annotation['parts']],
                    'related_joints':[byjoint[j] for j in p['related_joints']],
                    'proximal_joint':p['proximal_joint'],'distal_joint':p['distal_joint'],'interfaces':p['interfaces'],
                    'frame_warning':'URDF coordinates in local parent/joint frames; STEP render frame registration unverified. Do not project joint axes onto these images without a verified transform.',
                    'scale_context':{'units':'m','anchor_type':'sum_of_arm_joint_translation_lengths_from_sanitized_urdf','value':sum(math.sqrt(sum(v*v for v in j['origin_xyz_m'])) for j in kin['joints'] if j['joint_type']=='revolute'),'interpretation':'kinematic global scale bound; not measured part dimensions or exact max reach'},
                    'expected_features':features,'lod':{'path':'RobotPart-LOD.md','sha256':hashlib.sha256(lod.read_bytes()).hexdigest(),'phase':'v1 exterior standard; numeric thresholds provisional_DEV_only'},
                    'allowed_modeling_skills':{'target_native_operations':['Extrude','Pocket','Revolve','Loft','Sweep','Shell','BooleanFuse','BooleanCut','Fillet','Chamfer','Pattern','Mirror'],'availability':'operation contract scope only; shared modeling skills and parameter validation implemented in Phase 4, not certified here'},
                    'scope':'reference-only Phase 1+2; no generation until user confirms Phase 3','multi_body_policy':p['multi_body_policy']}
            shutil.copyfile(lod,root/'RobotPart-LOD.md');dump(root/'part_input.json',packet)
            dump(EXP/'robots/feature_checklists'/f'{pid}.json',features)
            manifests.append({'part_id':pid,'packet_path':str((root/'part_input.json').relative_to(EXP)),'sha256':hashlib.sha256((root/'part_input.json').read_bytes()).hexdigest(),'file_count':12})
            # Fixed allowlist means no offline source_mapping reaches planner.
            assert not any(k in packet for k in ['source_mapping','source_components','bbox_mm','faces','solids','source_label','source_step'])
            for ref in image_refs:assert (root/ref['path']).suffix=='.png'
            files=list(root.rglob('*'));extensions={x.suffix for x in files if x.is_file()}
            assert extensions<={'.json','.png','.md'}
            text=json.dumps(packet).lower()
            forbidden=['source_mapping','bbox_mm','brep','step_files','source_label','feature_tree','go_nogo1/','artifacts/']
            hits=[s for s in forbidden if s in text]
            rows.append({'part_id':pid,'status':'PASS' if not hits else 'FAIL','forbidden_hits':hits,'image_hashes_verified':all(hashlib.sha256((root/r['path']).read_bytes()).hexdigest()==r['sha256'] for r in image_refs),'dependency_files':len([x for x in files if x.is_file()])})
    dump(EXP/'results/packet_manifest.json',manifests)
    dump(EXP/'results/leakage_audit.json',{'status':'PASS' if all(r['status']=='PASS' and r['image_hashes_verified'] and r['dependency_files']==12 for r in rows) else 'FAIL','scope':'allowlisted packet dependency closure; not a filesystem sandbox or proof of context isolation','future_context_rule':'Stage a packet-only workspace for each Codex CLI part. Do not start from this offline annotation conversation or give generator repository-wide GT access.','reviewer_rule':'Grounded reviewer may access GT; generator repair receives contracts/images only, never source profiles or exact CAD extraction.','packets':rows})
    with (EXP/'results/expected_features.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(checklist[0]));w.writeheader();w.writerows(checklist)
    print(json.dumps({'packets':len(rows),'expected_features':len(checklist),'critical_features':sum(r['critical'] for r in checklist)}))

if __name__=='__main__':main()
