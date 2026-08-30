"""Generic RobotCAD SkillCall -> Autodesk Fusion API adapter (v1)."""
import adsk.core, adsk.fusion, json, os, time, traceback

ROOT=r"D:\CADtest\papertest"

class FusionAPIBackend:
 def __init__(self,design,root,record):self.design,self.root,self.record=design,root,record
 def component(self,name):
  occ=self.root.occurrences.addNewComponent(adsk.core.Matrix3D.create());occ.component.name=name;return occ.component
 def log(self,call,feature):
  self.record['calls'].append({'call_id':call['call_id'],'skill':call['skill'],'target_component':call['target_component'],'feature_id':feature.entityToken if feature else None,'feature_type':feature.objectType if feature else None,'status':'SUCCESS'})
 def box(self,c,l,r):
  s=c.sketches.add(c.xYConstructionPlane);s.sketchCurves.sketchLines.addTwoPointRectangle(adsk.core.Point3D.create(-l/20,-r/10,0),adsk.core.Point3D.create(l/20,r/10,0));x=c.features.extrudeFeatures.createInput(s.profiles.item(0),adsk.fusion.FeatureOperations.NewBodyFeatureOperation);x.setDistanceExtent(False,adsk.core.ValueInput.createByReal(2*r/10));return c.features.extrudeFeatures.add(x)
 def cylinder(self,c,r,l):
  s=c.sketches.add(c.xYConstructionPlane);s.sketchCurves.sketchCircles.addByCenterRadius(adsk.core.Point3D.create(0,0,0),r/10);x=c.features.extrudeFeatures.createInput(s.profiles.item(0),adsk.fusion.FeatureOperations.NewBodyFeatureOperation);x.setDistanceExtent(False,adsk.core.ValueInput.createByReal(l/10));return c.features.extrudeFeatures.add(x)
 def rotary(self,c,p):
  r,l=p['radius_mm'],p['length_mm'];s=c.sketches.add(c.xZConstructionPlane);s.sketchCurves.sketchLines.addTwoPointRectangle(adsk.core.Point3D.create(r/20,0,0),adsk.core.Point3D.create(r/10,l/10,0));x=c.features.revolveFeatures.createInput(s.profiles.item(0),c.zConstructionAxis,adsk.fusion.FeatureOperations.NewBodyFeatureOperation);x.setAngleExtent(False,adsk.core.ValueInput.createByString('360 deg'));return c.features.revolveFeatures.add(x)
 def loft(self,c,p):
  r,l=p['radius_mm'],p['length_mm'];s1=c.sketches.add(c.xYConstructionPlane);s1.sketchCurves.sketchCircles.addByCenterRadius(adsk.core.Point3D.create(0,0,0),r/10);pi=c.constructionPlanes.createInput();pi.setByOffset(c.xYConstructionPlane,adsk.core.ValueInput.createByReal(l/10));plane=c.constructionPlanes.add(pi);s2=c.sketches.add(plane);s2.sketchCurves.sketchCircles.addByCenterRadius(adsk.core.Point3D.create(0,0,0),max(r*.65,1)/10);x=c.features.loftFeatures.createInput(adsk.fusion.FeatureOperations.NewBodyFeatureOperation);x.loftSections.add(s1.profiles.item(0));x.loftSections.add(s2.profiles.item(0));return c.features.loftFeatures.add(x)
 def fillet(self,c,feature,p):
  edges=adsk.core.ObjectCollection.create()
  for e in feature.bodies.item(0).edges:edges.add(e)
  x=c.features.filletFeatures.createInput();x.addConstantRadiusEdgeSet(edges,adsk.core.ValueInput.createByReal(p.get('fillet_radius_mm',1)/10),True);return c.features.filletFeatures.add(x)
 def shell(self,c,feature,p):
  faces=adsk.core.ObjectCollection.create();faces.add(feature.bodies.item(0).faces.item(0));x=c.features.shellFeatures.createInput(faces,False);x.insideThickness=adsk.core.ValueInput.createByReal(max(.1,p.get('shell_thickness_mm',1))/10);return c.features.shellFeatures.add(x)
 def execute(self,call,components):
  p=call['parameters'];name=call['target_component'];c=components.setdefault(name,self.component(name));skill=call['skill'];feature=None
  if skill=='CreateRotaryJointHousing':feature=self.rotary(c,p)
  elif skill=='CreateLoftedLinkHousing':feature=self.loft(c,p)
  elif skill=='CreateRoundedLinkHousing':feature=self.fillet(c,self.box(c,p['length_mm'],p['radius_mm']),p)
  elif skill=='CreateFlangeInterface':feature=self.cylinder(c,p['radius_mm'],max(2,p['length_mm']*.25))
  elif skill=='CreateShellHousing':feature=self.shell(c,self.box(c,p['length_mm'],p['radius_mm']),p)
  elif skill=='CreateJointTransition':feature=self.loft(c,p)
  elif skill=='ApplyFilletGroup':feature=self.fillet(c,self.box(c,p['length_mm'],p['radius_mm']),p)
  else: raise RuntimeError('unsupported in v1 backend: '+skill)
  self.log(call,feature)
 def export(self,path):
  self.design.computeAll();em=self.design.exportManager;em.execute(em.createFusionArchiveExportOptions(path+'.f3d',self.root));em.execute(em.createSTEPExportOptions(path+'.step',self.root));em.execute(em.createSTLExportOptions(self.root,path+'.stl'))

def make_design():
 app=adsk.core.Application.get();doc=app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType);design=adsk.fusion.Design.cast(app.activeProduct);design.designType=adsk.fusion.DesignTypes.ParametricDesignType;return app,design,design.rootComponent
