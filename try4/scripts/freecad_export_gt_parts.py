"""Export frozen GT STEP component groups as per-Macro-Part STL for evaluation."""
import json,sys
from pathlib import Path
import FreeCAD as App
import Import,Mesh

def main(job_path):
    job=json.loads(Path(job_path).read_text(encoding='utf-8'));out=Path(job['output']);out.mkdir(parents=True,exist_ok=True)
    doc=App.newDocument('Try4Phase5GT')
    try:
        Import.insert(job['step'],doc.Name);doc.recompute()
        leaves=[o for o in doc.Objects if o.TypeId=='Part::Feature' and not o.Shape.isNull() and o.Shape.Faces]
        by_id={f'C{i:02d}':o for i,o in enumerate(leaves)}
        records=[]
        for part in job['parts']:
            objs=[by_id[c] for c in part['source_components']];path=out/(part['part_id']+'.stl');Mesh.export(objs,str(path))
            records.append({'part_id':part['part_id'],'source_components':part['source_components'],'stl':str(path),'solids':sum(len(o.Shape.Solids) for o in objs),'faces':sum(len(o.Shape.Faces) for o in objs)})
        (out/'export_manifest.json').write_text(json.dumps({'status':'SUCCESS','parts':records,'freecad_version':App.Version()},indent=2)+'\n',encoding='utf-8')
    finally:App.closeDocument(doc.Name)
if __name__=='__main__':main(sys.argv[-1])
