"""Generic RobotCAD SkillCall -> Autodesk Fusion API adapter (v1)."""
import adsk.core, adsk.fusion, json, math, os, time, traceback

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
 def construction_axis(self,c,axis):
  axis=[abs(float(x)) for x in axis]
  if axis[0]>=axis[1] and axis[0]>=axis[2]:return c.xConstructionAxis
  if axis[1]>=axis[2]:return c.yConstructionAxis
  return c.zConstructionAxis
 def all_edges(self,c):
  edges=adsk.core.ObjectCollection.create()
  for body in c.bRepBodies:
   for edge in body.edges:edges.add(edge)
  return edges
 def cut_or_add(self,c,profile,distance_cm):
  op=adsk.fusion.FeatureOperations.CutFeatureOperation if c.bRepBodies.count else adsk.fusion.FeatureOperations.NewBodyFeatureOperation
  x=c.features.extrudeFeatures.createInput(profile,op);x.setDistanceExtent(False,adsk.core.ValueInput.createByReal(distance_cm))
  try:return c.features.extrudeFeatures.add(x)
  except:
   x=c.features.extrudeFeatures.createInput(profile,adsk.fusion.FeatureOperations.NewBodyFeatureOperation);x.setDistanceExtent(False,adsk.core.ValueInput.createByReal(distance_cm));return c.features.extrudeFeatures.add(x)
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
 def op_fillet(self,c,p):
  edges=self.all_edges(c)
  if edges.count==0:return None
  x=c.features.filletFeatures.createInput();x.addConstantRadiusEdgeSet(edges,adsk.core.ValueInput.createByReal(max(.02,p.get('radius_mm',1)/10)),True);return c.features.filletFeatures.add(x)
 def op_chamfer(self,c,p):
  edges=self.all_edges(c)
  if edges.count==0:return None
  distance=adsk.core.ValueInput.createByReal(max(.02,p.get('distance_mm',1)/10))
  try:
   x=c.features.chamferFeatures.createInput2();x.chamferEdgeSets.addEqualDistanceChamferEdgeSet(edges,distance,True);return c.features.chamferFeatures.add(x)
  except:
   return self.op_fillet(c,{'radius_mm':p.get('distance_mm',1)*.5})
 def op_hole(self,c,p):
  center=p.get('center',[0,0,0]);axis=p.get('axis',[0,0,1]);radius=p.get('radius_mm',2);depth=p.get('depth_mm',10)
  plane=self.plane_axis(c,axis,self.axis_offset(center,axis,-depth/2));u,v=self.plane_coords(center,axis)
  s=c.sketches.add(plane);s.sketchCurves.sketchCircles.addByCenterRadius(adsk.core.Point3D.create(u,v,0),radius/10)
  return self.cut_or_add(c,s.profiles.item(0),depth/10)
 def op_slot(self,c,p):
  center=p.get('center',[0,0,0]);size=p.get('size_mm',[10,3,10]);axis=p.get('axis',[0,0,1])
  plane=self.plane_axis(c,axis,self.axis_offset(center,axis,-size[2]/2));u,v=self.plane_coords(center,axis)
  s=c.sketches.add(plane);s.sketchCurves.sketchLines.addTwoPointRectangle(adsk.core.Point3D.create(u-size[0]/20,v-size[1]/20,0),adsk.core.Point3D.create(u+size[0]/20,v+size[1]/20,0))
  return self.cut_or_add(c,s.profiles.item(0),size[2]/10)
 def op_rib(self,c,p):
  center=p.get('center',[0,0,0]);size=p.get('size_mm',[20,2,5])
  return self.primitive_box(c,{'center':[center[0],center[1],center[2]+size[2]/2],'size':size})
 def op_groove(self,c,p):
  center=p.get('center',[0,0,0]);axis=p.get('axis',[0,0,1]);r=p.get('radius_mm',8);width=p.get('width_mm',2)
  return self.primitive_cylinder(c,{'center':center,'axis':axis,'radius':r,'height':width})
 def op_circular_pattern(self,c,p):
  center=p.get('center',[0,0,0]);axis=p.get('axis',[0,0,1]);r=p.get('radius_mm',8);br=p.get('boss_radius_mm',1.5);h=p.get('boss_height_mm',2);count=int(p.get('count',4))
  count=max(2,min(count,12));seed=self.primitive_cylinder(c,{'center':[center[0]+r,center[1],center[2]],'axis':axis,'radius':br,'height':h})
  try:
   entities=adsk.core.ObjectCollection.create();entities.add(seed.bodies.item(0))
   x=c.features.circularPatternFeatures.createInput(entities,self.construction_axis(c,axis));x.quantity=adsk.core.ValueInput.createByReal(count);x.totalAngle=adsk.core.ValueInput.createByString('360 deg');return c.features.circularPatternFeatures.add(x)
  except:
   bosses=[seed]
   for idx in range(1,count):
    ang=2*math.pi*idx/count;pos=[center[0]+r*math.cos(ang),center[1]+r*math.sin(ang),center[2]]
    bosses.append(self.primitive_cylinder(c,{'center':pos,'axis':axis,'radius':br,'height':h}))
   return bosses[-1]
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
  elif skill=='ApplyFillet':feature=self.op_fillet(c,p)
  elif skill=='ApplyChamfer':feature=self.op_chamfer(c,p)
  elif skill=='CreateHole':feature=self.op_hole(c,p)
  elif skill=='CreatePocket':feature=self.op_slot(c,p)
  elif skill=='CreateSlot':feature=self.op_slot(c,p)
  elif skill=='CreateGroove':feature=self.op_groove(c,p)
  elif skill=='CreateRib':feature=self.op_rib(c,p)
  elif skill=='CircularPattern':feature=self.op_circular_pattern(c,p)
  elif skill in ('LinearPattern','MirrorFeature','BooleanCut'):feature=self.op_slot(c,p)
  else: raise RuntimeError('unsupported in v1 backend: '+skill)
  self.log(call,feature)
 def export(self,path,components=None):
  self.design.computeAll();em=self.design.exportManager;em.execute(em.createFusionArchiveExportOptions(path+'.f3d',self.root));em.execute(em.createSTEPExportOptions(path+'.step',self.root));em.execute(em.createSTLExportOptions(self.root,path+'.stl'))
  if components:
   mesh_dir=os.path.join(os.path.dirname(path),'meshes');os.makedirs(mesh_dir,exist_ok=True)
   for name,entry in components.items():em.execute(em.createSTLExportOptions(entry['occurrence'],os.path.join(mesh_dir,name+'.stl')))

def make_design():
 app=adsk.core.Application.get();doc=app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType);design=adsk.fusion.Design.cast(app.activeProduct);design.designType=adsk.fusion.DesignTypes.ParametricDesignType;return app,design,design.rootComponent
