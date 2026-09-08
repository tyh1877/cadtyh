"""Create revised physical baseline: remove virtual-peer IF_J10 geometry from L08."""
import copy,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=ROOT/'experiments/try5A';T=HERE/'try5A_2';SRC=T/'D0_physicalized/links';OUT=T/'mechanism_validation/baseline';links=[f'L{i:02d}' for i in range(11)]
line={}
for lid in links:
 src=SRC/lid
 if lid!='L08':line[lid]={'model_dir':str(src.resolve()),'cad_ir':str((src/'cad_ir.json').resolve()),'origin':'D0_physicalized'};continue
 ir=json.loads((src/'cad_ir.json').read_text());remove={x['op_id'] for x in ir['operations'] if x['feature_ref']=='IF_J10'};ir['operations']=[x for x in ir['operations'] if x['op_id'] not in remove and not any(d in remove for d in x.get('dependencies',[]))];ir['final_objects']=[x for x in ir['final_objects'] if x not in remove];ir['virtual_peer_geometry_removed']=['IF_J10'];out=OUT/'L08';out.mkdir(parents=True,exist_ok=True);(out/'cad_ir.json').write_text(json.dumps(ir,indent=2)+'\n');(out/'agent_output.json').write_text(json.dumps({'part_id':'L08','link_id':'L08','condition':'co_repair_baseline','cad_ir':ir},indent=2)+'\n');(out/'InterfaceRefs.json').write_bytes((src/'InterfaceRefs.json').read_bytes());(out/'attachment_manifest.json').write_bytes((src/'attachment_manifest.json').read_bytes());line[lid]={'model_dir':str(out.resolve()),'cad_ir':str((out/'cad_ir.json').resolve()),'origin':'virtual_peer_filtered'}
(T/'mechanism_validation/baseline/lineage.json').write_text(json.dumps(line,indent=2)+'\n');print(json.dumps({'links':len(line),'rebuilt':['L08'],'removed':'IF_J10'}))
