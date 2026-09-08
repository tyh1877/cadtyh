"""Assemble generated condition links in frozen canonical URDF frames."""
import json,sys
from pathlib import Path
import FreeCAD as App,FreeCADGui as Gui,Import,Mesh,Part
job=json.loads(Path(sys.argv[-1]).read_text());root=Path(job['root']);cond=job['condition'];here=root/'experiments/try5A_1';out=here/'assemblies'/cond;s=json.loads((root/'experiments/try5A/blackboard/kinematic_skeleton.json').read_text());Gui.showMainWindow();doc=App.newDocument('Try5A1_'+cond);objs=[]
try:
 for link in s['links']:
  lid=link['link_id'];p=here/cond/lid;source=App.openDocument(str(p/'model.FCStd'));ir=json.loads((p/'cad_ir.json').read_text());shape=Part.makeCompound([source.getObject(x).Shape.copy() for x in ir['final_objects']]);App.closeDocument(source.Name);o=doc.addObject('Part::Feature','Link_'+lid);o.Shape=shape;m=App.Matrix();T=link['world_transform_canonical']
  for r in range(3):
   for c in range(3):setattr(m,f'A{r+1}{c+1}',T[r][c])
  m.A14=T[0][3]*1000;m.A24=T[1][3]*1000;m.A34=T[2][3]*1000;m.A44=1;o.Placement=App.Placement(m);o.addProperty('App::PropertyString','SourceLink').SourceLink=lid;o.ViewObject.ShapeColor=(0.22+0.04*(int(lid[-2:])%4),0.45,0.70);objs.append(o)
 doc.recompute();out.mkdir(parents=True,exist_ok=True);doc.saveAs(str(out/'assembled_robot.FCStd'));Import.export(objs,str(out/'assembled_robot.step'));Mesh.export(objs,str(out/'assembled_robot.stl'));v=Gui.activeDocument().activeView();v.setCameraType('Orthographic');(out/'renders').mkdir(exist_ok=True)
 for name,method in {'front':'viewFront','side':'viewRight','top':'viewTop','isometric':'viewAxonometric'}.items():getattr(v,method)();v.fitAll();Gui.updateGui();v.saveImage(str(out/'renders'/(name+'.png')),1200,1200,'White')
 (out/'assembly_result.json').write_text(json.dumps({'status':'SUCCESS','condition':cond,'links':len(objs),'placement_authority':'frozen sanitized URDF canonical transforms','visual_adjustments':0},indent=2)+'\n')
finally: App.closeDocument(doc.Name);Gui.getMainWindow().close()
