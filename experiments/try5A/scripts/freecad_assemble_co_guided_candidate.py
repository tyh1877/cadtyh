import json,sys
from pathlib import Path
import FreeCAD as App,FreeCADGui as Gui,Import,Mesh,Part
job=json.loads(Path(sys.argv[-1]).read_text());root=Path(job['root']);T=root/'experiments/try5A/try5A_2';line=json.loads((T/'mechanism_validation/candidate/lineage.json').read_text());s=json.loads((root/'experiments/try5A/blackboard/kinematic_skeleton.json').read_text());out=T/'mechanism_validation/candidate/assembly';Gui.showMainWindow();doc=App.newDocument('CoGuidedCandidate');objs=[]
try:
 for link in s['links']:
  lid=link['link_id']
  if lid not in line:continue
  p=Path(line[lid]['model_dir']);d=App.openDocument(str(p/'model.FCStd'));ir=json.loads((p/'cad_ir.json').read_text());shape=Part.makeCompound([d.getObject(n).Shape.copy() for n in ir['final_objects']]);App.closeDocument(d.Name);o=doc.addObject('Part::Feature','Link_'+lid);o.Shape=shape;m=App.Matrix();M=link['world_transform_canonical']
  for r in range(3):
   for c in range(3):setattr(m,f'A{r+1}{c+1}',M[r][c])
  m.A14=M[0][3]*1000;m.A24=M[1][3]*1000;m.A34=M[2][3]*1000;m.A44=1;o.Placement=App.Placement(m);o.ViewObject.ShapeColor=(.25,.45,.68);objs.append(o)
 doc.recompute();out.mkdir(parents=True,exist_ok=True);doc.saveAs(str(out/'assembled_robot.FCStd'));Import.export(objs,str(out/'assembled_robot.step'));Mesh.export(objs,str(out/'assembled_robot.stl'));v=Gui.activeDocument().activeView();v.setCameraType('Orthographic');(out/'renders').mkdir(exist_ok=True)
 for n,fn in {'front':'viewFront','side':'viewRight','top':'viewTop','isometric':'viewAxonometric'}.items():getattr(v,fn)();v.fitAll();Gui.updateGui();v.saveImage(str(out/'renders'/(n+'.png')),1200,1200,'White')
 (out/'assembly_result.json').write_text(json.dumps({'status':'SUCCESS','physical_links':len(objs),'excluded_virtual_links':['L11'],'condition':'co_guided_candidate'},indent=2)+'\n')
finally:App.closeDocument(doc.Name);Gui.getMainWindow().close()
