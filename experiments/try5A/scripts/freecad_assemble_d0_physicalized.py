"""Assemble physicalized D0 from 11 physical link models at frozen URDF transforms."""
import json,sys
from pathlib import Path
import FreeCAD as App,FreeCADGui as Gui,Import,Mesh,Part
job=json.loads(Path(sys.argv[-1]).read_text());root=Path(job['root']);here=root/'experiments/try5A';T=here/'try5A_2';out=T/'D0_physicalized/assembly';types={x['link_id']:x for x in json.loads((T/'virtual_link_filter/link_realization_types.json').read_text())['links']};s=json.loads((here/'blackboard/kinematic_skeleton.json').read_text());Gui.showMainWindow();doc=App.newDocument('D0Physicalized');objs=[]
try:
 for link in s['links']:
  lid=link['link_id']
  if not types[lid]['solid_generation_allowed']:continue
  p=T/'D0_physicalized/links'/lid;d=App.openDocument(str(p/'model.FCStd'));ir=json.loads((p/'cad_ir.json').read_text());shape=Part.makeCompound([d.getObject(n).Shape.copy() for n in ir['final_objects']]);App.closeDocument(d.Name);o=doc.addObject('Part::Feature','Link_'+lid);o.Shape=shape;m=App.Matrix();M=link['world_transform_canonical']
  for r in range(3):
   for c in range(3):setattr(m,f'A{r+1}{c+1}',M[r][c])
  m.A14=M[0][3]*1000;m.A24=M[1][3]*1000;m.A34=M[2][3]*1000;m.A44=1;o.Placement=App.Placement(m);o.addProperty('App::PropertyString','SourceLink').SourceLink=lid;o.ViewObject.ShapeColor=(.25,.45,.68);objs.append(o)
 doc.recompute();out.mkdir(parents=True,exist_ok=True);doc.saveAs(str(out/'assembled_robot.FCStd'));Import.export(objs,str(out/'assembled_robot.step'));Mesh.export(objs,str(out/'assembled_robot.stl'));v=Gui.activeDocument().activeView();v.setCameraType('Orthographic');(out/'renders').mkdir(exist_ok=True)
 for name,method in {'front':'viewFront','side':'viewRight','top':'viewTop','isometric':'viewAxonometric'}.items():getattr(v,method)();v.fitAll();Gui.updateGui();v.saveImage(str(out/'renders'/(name+'.png')),1200,1200,'White')
 (out/'assembly_result.json').write_text(json.dumps({'status':'SUCCESS','physical_links':len(objs),'virtual_links_excluded':['L11'],'placement_authority':'frozen sanitized URDF'},indent=2)+'\n')
finally:App.closeDocument(doc.Name);Gui.getMainWindow().close()
