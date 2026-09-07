"""Assemble independent links at canonical URDF transforms; no visual adjustment."""
import json,sys
from pathlib import Path
import FreeCAD as App,FreeCADGui as Gui,Import,Mesh,Part
Gui.showMainWindow();job=json.loads(Path(sys.argv[-1]).read_text());root=Path(job['root']);out=Path(job['output']);s=json.loads(Path(job['skeleton']).read_text());doc=App.newDocument('Try5A_A0_Assembly');objects=[]
try:
 for link in s['links']:
  lid=link['link_id'];before={o.Name for o in doc.Objects};Import.insert(str(root/f'experiments/try5A/A0/{lid}/model.step'),doc.Name);new=[o for o in doc.Objects if o.Name not in before and hasattr(o,'Shape') and not o.Shape.isNull()];shape=Part.makeCompound([o.Shape.copy() for o in new]);[setattr(o.ViewObject,'Visibility',False) for o in new];obj=doc.addObject('Part::Feature','Link_'+lid);obj.Label='Link_'+lid;obj.Shape=shape;m=App.Matrix();T=link['world_transform_canonical'];
  # FreeCAD matrix translation is millimetres.
  for r in range(3):
   for c in range(3):setattr(m,f'A{r+1}{c+1}',T[r][c])
  m.A14=T[0][3]*1000;m.A24=T[1][3]*1000;m.A34=T[2][3]*1000;obj.Placement=App.Placement(m);obj.addProperty('App::PropertyString','SourceLink').SourceLink=lid;objects.append(obj)
 doc.recompute();out.mkdir(parents=True,exist_ok=True);doc.saveAs(str(out/'assembled_robot.FCStd'));Import.export(objects,str(out/'assembled_robot.step'));Mesh.export(objects,str(out/'assembled_robot.stl'));Gui.activeDocument();view=Gui.activeDocument().activeView();view.setCameraType('Orthographic');(out/'renders').mkdir(exist_ok=True)
 for name,method in {'front':'viewFront','side':'viewRight','top':'viewTop','isometric':'viewAxonometric'}.items():getattr(view,method)();view.fitAll();Gui.updateGui();view.saveImage(str(out/'renders'/(name+'.png')),1200,1200,'White')
 result={'status':'SUCCESS','placement_authority':'sanitized URDF canonical transforms','visual_adjustments':0,'links':len(objects),'fcstd':True,'step':True,'stl':True,'object_names':[o.Name for o in objects]};(out/'assembly_result.json').write_text(json.dumps(result,indent=2)+'\n')
finally:App.closeDocument(doc.Name);Gui.getMainWindow().close()
