"""Produce D0 physical-only assembly from frozen C1; virtual frames are omitted."""
import json,sys
from pathlib import Path
import FreeCAD as App,FreeCADGui as Gui,Import,Mesh,Part
job=json.loads(Path(sys.argv[-1]).read_text());root=Path(job['root']);here=root/'experiments/try5A';target=here/'try5A_2/D0/physical_assembly';source=root/'experiments/try5A_1/C1';types={x['link_id']:x for x in json.loads((here/'try5A_2/virtual_link_filter/link_realization_types.json').read_text())['links']};s=json.loads((here/'blackboard/kinematic_skeleton.json').read_text());Gui.showMainWindow();doc=App.newDocument('Try5A2_D0_Physical');objs=[]
try:
 for link in s['links']:
  lid=link['link_id']
  if not types[lid]['solid_generation_allowed']: continue
  d=App.openDocument(str(source/lid/'model.FCStd'));ir=json.loads((source/lid/'cad_ir.json').read_text());shape=Part.makeCompound([d.getObject(n).Shape.copy() for n in ir['final_objects']]);App.closeDocument(d.Name);o=doc.addObject('Part::Feature','Link_'+lid);o.Shape=shape;m=App.Matrix();T=link['world_transform_canonical']
  for r in range(3):
   for c in range(3):setattr(m,f'A{r+1}{c+1}',T[r][c])
  m.A14=T[0][3]*1000;m.A24=T[1][3]*1000;m.A34=T[2][3]*1000;m.A44=1;o.Placement=App.Placement(m);o.addProperty('App::PropertyString','SourceLink').SourceLink=lid;o.ViewObject.ShapeColor=(0.25,0.45,0.68);objs.append(o)
 doc.recompute();target.mkdir(parents=True,exist_ok=True);doc.saveAs(str(target/'assembled_robot.FCStd'));Import.export(objs,str(target/'assembled_robot.step'));Mesh.export(objs,str(target/'assembled_robot.stl'));v=Gui.activeDocument().activeView();v.setCameraType('Orthographic');(target/'renders').mkdir(exist_ok=True)
 for name,method in {'front':'viewFront','side':'viewRight','top':'viewTop','isometric':'viewAxonometric'}.items():getattr(v,method)();v.fitAll();Gui.updateGui();v.saveImage(str(target/'renders'/(name+'.png')),1200,1200,'White')
 (target/'assembly_result.json').write_text(json.dumps({'status':'SUCCESS','condition':'D0','physical_links':len(objs),'excluded_virtual_links':[x for x,t in types.items() if not t['solid_generation_allowed']],'source':'frozen Try5-A.1 C1'},indent=2)+'\n')
finally:App.closeDocument(doc.Name);Gui.getMainWindow().close()
