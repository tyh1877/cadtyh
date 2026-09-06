"""Validate saved Phase 1+2 evidence; never invokes reconstruction or transfer."""
import csv
import hashlib
import json
from pathlib import Path
from prepare_phase12 import ROOT,EXP,dump

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    audit=json.loads((EXP/'results/reference_audit.json').read_text());assert audit['status']=='PASS' and audit['images']==90
    leakage=json.loads((EXP/'results/leakage_audit.json').read_text());assert leakage['status']=='PASS' and len(leakage['packets'])==18
    splits=list(csv.DictReader((EXP/'robots/try4_robot_split.csv').open()))
    assert len(splits)==3 and {r['role'] for r in splits}=={'DEV_A','DEV_B','TRANSFER'}
    provenance=json.loads((EXP/'robots/source_provenance.json').read_text());colors=[];parts=[]
    for r in provenance:
        assert sha(ROOT/r['step_path'])==r['step_sha256']
        assert sha(ROOT/r['urdf_path'])==r['urdf_sha256']
    for r in splits:
        rid=r['robot_id'];ann=json.loads((EXP/'robots/semantic_parts'/f'{rid}.json').read_text())
        inv=json.loads((EXP/'artifacts'/rid/'inventory.json').read_text())
        members=[c for p in ann['parts'] for c in p['source_components']]
        assert sorted(members)==sorted(c['component_id'] for c in inv['components']) and len(set(members))==len(members)
        assert len(ann['parts'])==int(r['number_of_macro_parts'])
        for p in ann['parts']:
            pid=p['part_id'];colors.append(tuple(p['color_rgb']));parts.append(pid)
            root=EXP/'packets'/pid;packet=json.loads((root/'part_input.json').read_text())
            assert packet['part_id']==pid and packet['color_rgb']==p['color_rgb']
            assert len(packet['reference_images'])==10
            for ref in packet['reference_images']:
                image=(root/ref['path']).resolve();assert image.is_relative_to(root.resolve()) and sha(image)==ref['sha256']
            assert sha(root/packet['lod']['path'])==packet['lod']['sha256']
            for feature in packet['expected_features']:
                assert feature['evidence_views'] and all((root/v).is_file() for v in feature['evidence_views'])
            assert len(packet['interfaces'])==2
    assert len(parts)==len(set(parts))==len(set(colors))==18
    for rec in audit['checks']:assert sha(EXP/'artifacts'/rec['robot_id']/rec['image'])==rec['sha256']
    assert not any((EXP/name).exists() for name in ['T0','T1','T2','runs'])
    for f in EXP.rglob('*'):
        if f.is_file() and 'artifacts' not in f.relative_to(EXP).parts:
            assert f.suffix.lower() not in ['.fcstd','.step','.stp','.stl','.brep'],str(f)
    freeze_files=[EXP/'try4.md',EXP/'robots/try4_robot_split.csv',EXP/'robots/source_provenance.json',EXP/'skills/robot_part_modeling_standard/SKILL.md']
    freeze_files+=list((EXP/'robots/semantic_parts').glob('*.json'))+list((EXP/'robots/feature_checklists').glob('*.json'))
    freeze_files+=list((EXP/'scripts').glob('*.py'))
    result={'status':'PASS','completed_phases':[1,2],'next_state':'AWAIT_USER_CONFIRMATION_PHASE_3','reconstruction_runs':0,
            'robots':3,'macro_parts':18,'global_views':18,'isolated_views':72,'unique_colors':18,
            'source_leaves':sum(int(r['leaf_components']) for r in splits),'source_solids':sum(int(r['source_solids']) for r in splits),
            'features':sum(len(json.loads(p.read_text())) for p in (EXP/'robots/feature_checklists').glob('*.json')),
            'geometry_or_quality_thresholds_frozen':False,'lod_relative_scale_ratio':{'value':.02,'status':'PROVISIONAL_DEV_ONLY'},
            'scope':'Reference/annotation/LOD preparation only. Semantic expert validation and numerical STEP-URDF registration not asserted.',
            'phase12_snapshot':{str(p.relative_to(EXP)):sha(p) for p in freeze_files}}
    dump(EXP/'results/phase12_validation.json',result)
    legend=[]
    for p in sorted((EXP/'robots/semantic_parts').glob('*.json')):
        for part in json.loads(p.read_text())['parts']:
            legend.append({'part_id':part['part_id'],'semantic_label':part['semantic_label'],'role_class':part['role_class'],'color_hex':'#'+''.join(f'{c:02X}' for c in part['color_rgb']),'source_components':';'.join(part['source_components'])})
    with (EXP/'results/semantic_part_index.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(legend[0]));w.writeheader();w.writerows(legend)
    print(json.dumps({k:v for k,v in result.items() if k!='phase12_snapshot'},indent=2))

if __name__=='__main__':main()
