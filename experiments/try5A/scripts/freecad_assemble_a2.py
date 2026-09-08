"""Assemble A2 link STEP files at unchanged canonical URDF transforms."""
import json,sys
from pathlib import Path
import FreeCAD as App,FreeCADGui as Gui,Import,Mesh,Part
Gui.showMainWindow();job=json.loads(Path(sys.argv[-1]).read_text());root=Path(job['root']);out=Path(job['output']);s=json.loads(Path(job['skeleton']).read_text());doc=App.newDocument('Try5A_A2_Assembly');objects=[]
try:
 for link in s['links']:
  lid=link['link_id'];source_path=root/f'experiments/try5A/A2/{lid}';ir=json.loads((source_path/'cad_ir.json').read_text())
  if not ir['final_objects']: continue
  source=App.openDocument(str(source_path/'model.FCStd'));shape=Part.makeCompound([source.getObject(name).Shape.copy() for name in ir['final_objects']]);App.closeDocument(source.Name);obj=doc.addObject('Part::Feature','Link_'+lid);obj.Shape=shape;m=App.Matrix();T=link['world_transform_canonical']
  for r in range(3):
   for c in range(3):setattr(m,f'A{r+1}{c+1}',T[r][c])
  m.A24=T[0][3]*1000;m.A24=T[1][3]*1000;m.A34=T[2][3]*1000;m.A41=0;m.A42=0;m.A43=0;m.A44=1;obj.Placement=App.Placement(m);obj.addProperty('App::PropertyString','SourceLink').SourceLink=lid;obj.ViewObject.ShapeColor=(0.25+0.04*(int(lid[-2:])%4),0.45,0.68);objects.append(obj)
 doc.recompute();out.mkdir(parents=True,exist_ok=True);doc.saveAs(str(out/'assembled_robot.FCStd'));Import.export(objects,str(out/'assembled_robot.step'));Mesh.export(objects,str(out/'assembled_robot.stl'));Gui.activeDocument();view=Gui.activeDocument().activeView();view.setCameraType('Orthographic');(out/'renders').mkdir(exist_ok=True)
 for name,method in {'front':'viewFront','side':'viewRight','top':'viewTop','isometric':'viewAxonometric'}.items():getattr(view,method)();view.fitAll();Gui.updateGui();view.saveImage(str(out/'renders'/(name+'.png')),1200,1200,'White')
 (out/'assembly_result.json').write_text(json.dumps({'status':'SUCCESS','condition':'A2','placement_authority':'sanitized URDF canonical transforms','visual_adjustments':0,'links':len(objects)},indent=2)+'\n')
finally:App.closeDocument(doc.Name);Gui.getMainWindow().close()
