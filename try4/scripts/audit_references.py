"""Deterministic reference-image QA and contact sheets, not feature evaluation."""
import json
import hashlib
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
from prepare_phase12 import EXP,SELECTED,dump

def main():
    rows=[]
    for rid,slug,role in SELECTED:
        root=EXP/'artifacts'/rid
        ann=json.loads((EXP/'robots/semantic_parts'/f'{rid}.json').read_text())
        inv=json.loads((root/'inventory.json').read_text())
        members=[x for p in ann['parts'] for x in p['source_components']]
        assert sorted(members)==sorted(c['component_id'] for c in inv['components'])
        cameras=json.loads((root/'camera_manifest.json').read_text())
        assert len(cameras)==6+4*len(ann['parts'])
        for meta in cameras:
            path=root/meta['image']
            with Image.open(path) as im:
                arr=np.asarray(im.convert('RGB'));mask=np.any(arr<245,axis=2)
                ys,xs=np.where(mask)
                border=bool(mask[:3,:].any() or mask[-3:,:].any() or mask[:,:3].any() or mask[:,-3:].any())
                occupancy=float(mask.mean())
                # Broad automatic gate: inspection determines semantic usefulness.
                ok=bool(len(xs) and occupancy>.005 and not border and im.size==(1400,1400))
                rows.append({'robot_id':rid,'image':meta['image'],'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'occupancy':occupancy,'touches_border':border,'bbox_px':[int(xs.min()),int(ys.min()),int(xs.max()),int(ys.max())] if len(xs) else None,'status':'PASS' if ok else 'FAIL'})
        sheet=Image.new('RGB',(1120,300*len(ann['parts'])),'white');draw=ImageDraw.Draw(sheet)
        for i,p in enumerate(ann['parts']):
            for j,view in enumerate(['front','side','top','isometric']):
                im=Image.open(root/'isolated'/p['part_id']/(view+'.png')).convert('RGB');im.thumbnail((270,260))
                sheet.paste(im,(j*280,i*300));draw.text((j*280+5,i*300+263),p['part_id']+' '+view,fill='black')
            draw.text((5,i*300+282),p['semantic_label'],fill='black')
        folder=EXP/'results/contact_sheets';folder.mkdir(parents=True,exist_ok=True);sheet.save(folder/f'{rid}_isolated.png')
        global_sheet=Image.new('RGB',(840,590),'white');draw=ImageDraw.Draw(global_sheet)
        for i,v in enumerate(['front','rear','left','right','top','isometric']):
            im=Image.open(root/'global'/(v+'.png')).convert('RGB');im.thumbnail((270,270));global_sheet.paste(im,((i%3)*280,(i//3)*295));draw.text(((i%3)*280+5,(i//3)*295+270),rid+' '+v,fill='black')
        global_sheet.save(folder/f'{rid}_global.png')
    result={'status':'PASS' if all(r['status']=='PASS' for r in rows) else 'FAIL','robots':3,'parts':18,'images':len(rows),'failures':[r for r in rows if r['status']=='FAIL'],'checks':rows}
    dump(EXP/'results/reference_audit.json',result)
    print(json.dumps({k:v for k,v in result.items() if k!='checks'},indent=2))
    if result['status']!='PASS':raise SystemExit(1)

if __name__=='__main__':main()
