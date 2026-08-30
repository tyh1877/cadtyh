"""Generic RobotCAD SkillCall -> Autodesk Fusion API adapter (v1)."""
import adsk.core, adsk.fusion, json, os, time, traceback

ROOT=r"D:\CADtest\papertest"

class FusionAPIBackend:
 def __init__(self,design,root,record):self.design,self.root,self.record=design,root,record
 def component(self,name,matrix=None):
  occ=self.root.occurrences.addNewComponent(matrix or adsk.core.Matrix3D.create());occ.component.name=name;return {'component':occ.component,'occurrence':occ}
 def log(self,call,feature):
  self.record['calls'].append({'call_id':call['call_id'],'skill':call['skill'],'target_component':call['target_component'],'feature_id':feature.entityToken if feature else None,'feature_type':feature.objectType if feature else None,'status':'SUCCESS'})
 def plane_axis(self,c,axis,offset_cm):
  axis=[round(float(x),6) for x in axis]
  if abs(axis[0])>=abs(axis[1]) and abs(axis[0])>=abs(axis[2]):base=c.yZConstructionPlane
  elif abs(axis[1])>=abs(axis[2]):base=c.xZConstructionPlane
  else:base=c.xYConstructionPlane
  pi=c.constructionPlanes.createInput();pi.setByOffset(base,adsk.core.ValueInput.createByReal(offset_cm));return c.constructionPlanes.add(pi)
 def plane_coords(self,center,axis):
  axis=[abs(float(x)) for x in axis]
  if axis[0]>=axis[1] and axis[0]>=axis[2]:return center[1]/10,center[2]/10
  if axis[1]>=axis[2]:return center[0]/10,center[2]/10
  return center[0]/10,center[1]/10
 def axis_offset(self,center,axis,delta_mm=0):
  axis=[float(x) for x in axis]
  idx=max(range(3),key=lambda i:abs(axis[i]))
  sign=1 if axis[idx]>=0 else -1
  return (center[idx]+sign*delta_mm)/10
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
 def primitive_box(self,c,p):
  center=p.get('center',[0,0,0]);size=p.get('size',[10,10,10])
  plane=self.plane_axis(c,[0,0,1],(center[2]-size[2]/2)/10)
  s=c.sketches.add(plane);x0=(center[0]-size[0]/2)/10;y0=(center[1]-size[1]/2)/10;x1=(center[0]+size[0]/2)/10;y1=(center[1]+size[1]/2)/10
  s.sketchCurves.sketchLines.addTwoPointRectangle(adsk.core.Point3D.create(x0,y0,0),adsk.core.Point3D.create(x1,y1,0))
  x=c.features.extrudeFeatures.createInput(s.profiles.item(0),adsk.fusion.FeatureOperations.NewBodyFeatureOperation);x.setDistanceExtent(False,adsk.core.ValueInput.createByReal(size[2]/10));return c.features.extrudeFeatures.add(x)
 def primitive_cylinder(self,c,p):
  center=p.get('center',[0,0,0]);axis=p.get('axis',[0,0,1]);height=p.get('height',10);radius=p.get('radius',10)
  plane=self.plane_axis(c,axis,self.axis_offset(center,axis,-height/2));u,v=self.plane_coords(center,axis)
  s=c.sketches.add(plane);s.sketchCurves.sketchCircles.addByCenterRadius(adsk.core.Point3D.create(u,v,0),radius/10)
  x=c.features.extrudeFeatures.createInput(s.profiles.item(0),adsk.fusion.FeatureOperations.NewBodyFeatureOperation);x.setDistanceExtent(False,adsk.core.ValueInput.createByReal(height/10));return c.features.extrudeFeatures.add(x)
 def primitive_cone(self,c,p):
  center=p.get('center',[0,0,0]);axis=p.get('axis',[0,0,1]);height=p.get('height',10);r0=p.get('bottom_radius',p.get('radius_bottom',10));r1=p.get('top_radius',p.get('radius_top',0))
  plane0=self.plane_axis(c,axis,self.axis_offset(center,axis,-height/2));plane1=self.plane_axis(c,axis,self.axis_offset(center,axis,height/2));u,v=self.plane_coords(center,axis)
  s0=c.sketches.add(plane0);s0.sketchCurves.sketchCircles.addByCenterRadius(adsk.core.Point3D.create(u,v,0),max(r0,.1)/10)
  s1=c.sketches.add(plane1);s1.sketchCurves.sketchCircles.addByCenterRadius(adsk.core.Point3D.create(u,v,0),max(r1,.1)/10)
  x=c.features.loftFeatures.createInput(adsk.fusion.FeatureOperations.NewBodyFeatureOperation);x.loftSections.add(s0.profiles.item(0));x.loftSections.add(s1.profiles.item(0));return c.features.loftFeatures.add(x)
 def primitive_sphere(self,c,p):
  center=p.get('center',[0,0,0]);r=p.get('radius',10)
  return self.primitive_cylinder(c,{'center':center,'axis':[0,0,1],'radius':r,'height':2*r})
 def composite(self,c,p):
  features=[]
  for prim in p.get('primitives',[]):
   kind=prim.get('type')
   if kind=='box':features.append(self.primitive_box(c,prim))
   elif kind=='cylinder':features.append(self.primitive_cylinder(c,prim))
   elif kind=='cone':features.append(self.primitive_cone(c,prim))
   elif kind=='sphere':features.append(self.primitive_sphere(c,prim))
   else:raise RuntimeError('unsupported primitive in composite: '+str(kind))
  if not features:raise RuntimeError('composite has no primitives')
  return features[-1]
 def execute(self,call,components):
  p=call['parameters'];name=call['target_component'];skill=call['skill']
  if skill=='PlaceComponentFromURDF':
   m=adsk.core.Matrix3D.create()
   for i,row in enumerate(p['transform_cm']):
    for j,value in enumerate(row):m.setCell(i,j,value)
   components[name]=self.component(name,m);self.log(call,None);return
  if skill=='CreateSharedJointReference':
   # The external URDF is authoritative for this reference. The backend records
   # the shared interface intent without inventing native joint semantics.
   self.log(call,None);return
  entry=components.setdefault(name,self.component(name));c=entry['component'];feature=None
  if skill=='CreateCompositeLinkGeometry':feature=self.composite(c,p)
  elif skill=='CreateRotaryJointHousing':feature=self.rotary(c,p)
  elif skill=='CreateLoftedLinkHousing':feature=self.loft(c,p)
  elif skill=='CreateRoundedLinkHousing':feature=self.fillet(c,self.box(c,p['length_mm'],p['radius_mm']),p)
  elif skill=='CreateFlangeInterface':feature=self.cylinder(c,p['radius_mm'],max(2,p['length_mm']*.25))
  elif skill=='CreateShellHousing':feature=self.shell(c,self.box(c,p['length_mm'],p['radius_mm']),p)
  elif skill=='CreateJointTransition':feature=self.loft(c,p)
  elif skill=='ApplyFilletGroup':feature=self.fillet(c,self.box(c,p['length_mm'],p['radius_mm']),p)
  else: raise RuntimeError('unsupported in v1 backend: '+skill)
  self.log(call,feature)
 def export(self,path,components=None):
  self.design.computeAll();em=self.design.exportManager;em.execute(em.createFusionArchiveExportOptions(path+'.f3d',self.root));em.execute(em.createSTEPExportOptions(path+'.step',self.root));em.execute(em.createSTLExportOptions(self.root,path+'.stl'))
  if components:
   mesh_dir=os.path.join(os.path.dirname(path),'meshes');os.makedirs(mesh_dir,exist_ok=True)
   for name,entry in components.items():em.execute(em.createSTLExportOptions(entry['occurrence'],os.path.join(mesh_dir,name+'.stl')))

def make_design():
 app=adsk.core.Application.get();doc=app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType);design=adsk.fusion.Design.cast(app.activeProduct);design.designType=adsk.fusion.DesignTypes.ParametricDesignType;return app,design,design.rootComponent
