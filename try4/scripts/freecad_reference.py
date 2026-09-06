"""Offline native STEP inventory/reference renderer. No reconstruction logic."""
import hashlib
import json
import sys
from pathlib import Path
import FreeCAD as App
import FreeCADGui as Gui
Gui.showMainWindow()
import ImportGui

METHODS = {'front':'viewFront','rear':'viewRear','left':'viewLeft','right':'viewRight','side':'viewRight','top':'viewTop','isometric':'viewAxonometric'}

def dump(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2)+'\n', encoding='utf-8')

def color(obj, rgb):
    c=tuple(x/255 for x in rgb)
    m=App.Material(); m.DiffuseColor=(*c,1.0); m.AmbientColor=(*tuple(x*.3 for x in c),1.0)
    obj.ViewObject.ShapeColor=c
    obj.ViewObject.ShapeAppearance=(m,)*max(1,len(obj.Shape.Faces))
    obj.ViewObject.setElementColors({'Face':(*c,1.0)})

def main(job):
    output=Path(job['output']); output.mkdir(parents=True,exist_ok=True)
    doc=App.newDocument('Reference')
    try:
        ImportGui.insert(job['step'],doc.Name); doc.recompute()
        leaves=[o for o in doc.Objects if o.TypeId=='Part::Feature' and not o.Shape.isNull() and o.Shape.Faces]
        inventory=[{'component_id':f'C{i:02d}','object_name':o.Name,'source_label':o.Label,'solids':len(o.Shape.Solids),'faces':len(o.Shape.Faces)} for i,o in enumerate(leaves)]
        dump(output/'inventory.json',{'step_sha256':hashlib.sha256(Path(job['step']).read_bytes()).hexdigest(),'components':inventory,'freecad_version':App.Version()})
        if job.get('inventory_only'):return
        parts=job['parts']; assignments=[c for p in parts for c in p['source_components']]
        assert sorted(assignments)==sorted(r['component_id'] for r in inventory) and len(set(assignments))==len(assignments)
        byid={r['component_id']:o for r,o in zip(inventory,leaves)}
        for p in parts:
            for c in p['source_components']:color(byid[c],p['color_rgb'])
        Gui.activeDocument(); Gui.updateGui()
        view=Gui.activeDocument().activeView(); view.setAnimationEnabled(False); view.setCameraType('Orthographic')
        metadata=[]
        def render(folder,names):
            for name in names:
                getattr(view,METHODS[name])(); view.fitAll(); Gui.updateGui()
                # Small framing margin; stored camera is authoritative for QA/reuse.
                folder.mkdir(parents=True,exist_ok=True)
                view.saveImage(str(folder/(name+'.png')),1400,1400,'White')
                metadata.append({'image':str((folder/(name+'.png')).relative_to(output)),'view':name,'camera':view.getCamera(),'resolution':[1400,1400],'projection':'orthographic'})
        for o in leaves:o.ViewObject.Visibility=True
        render(output/'global',['front','rear','left','right','top','isometric'])
        for p in parts:
            selected=set(p['source_components'])
            for c,o in byid.items():o.ViewObject.Visibility=c in selected
            render(output/'isolated'/p['part_id'],['front','side','top','isometric'])
        dump(output/'camera_manifest.json',metadata)
        dump(output/'render_result.json',{'status':'SUCCESS','parts':len(parts),'images':len(metadata),'coverage_components':len(assignments)})
    finally:
        App.closeDocument(doc.Name); Gui.getMainWindow().close()

if __name__=='__main__':
    main(json.loads(Path(sys.argv[-1]).read_text(encoding='utf-8')))
