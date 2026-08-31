"""Generic RobotCAD SkillCall -> Autodesk Fusion API adapter (v1)."""
import adsk.core, adsk.fusion, json, math, os, time, traceback

ROOT=r"D:\CADtest\papertest"

class FusionAPIBackend:
 def __init__(self,design,root,record):self.design,self.root,self.record,self.profiles=design,root,record,{}
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
 def edge_groups(self,c,max_edges=24):
  groups=[];all_edges=adsk.core.ObjectCollection.create()
  for body in c.bRepBodies:
   body_edges=[]
   for edge in body.edges:
    if len(body_edges)<max_edges:body_edges.append(edge);all_edges.add(edge)
   if body_edges:
    g=adsk.core.ObjectCollection.create()
    for edge in body_edges:g.add(edge)
    groups.append(g)
  if all_edges.count:groups.insert(0,all_edges)
  return groups
 def cut_feature(self,c,profile,distance_cm):
  if c.bRepBodies.count==0:raise RuntimeError('cut requested before target body exists')
  x=c.features.extrudeFeatures.createInput(profile,adsk.fusion.FeatureOperations.CutFeatureOperation);x.setDistanceExtent(False,adsk.core.ValueInput.createByReal(distance_cm));return c.features.extrudeFeatures.add(x)
 def profile_key(self,c,p):return (c.name,str(p.get('profile_id','default')))
 def create_profile(self,c,p):
  center=p.get('center',[0,0,0]);axis=p.get('axis',[0,0,1]);shape=p.get('shape','rectangle')
  offset=p.get('plane_offset_mm')
  if offset is None:offset=center[max(range(3),key=lambda i:abs(float(axis[i])))]
  plane=self.plane_axis(c,axis,float(offset)/10);u,v=self.plane_coords(center,axis)
  s=c.sketches.add(plane)
  if shape=='circle':
   s.sketchCurves.sketchCircles.addByCenterRadius(adsk.core.Point3D.create(u,v,0),max(.1,p.get('radius_mm',2)/10))
  else:
   size=p.get('size_mm',[10,10])
   s.sketchCurves.sketchLines.addTwoPointRectangle(adsk.core.Point3D.create(u-size[0]/20,v-size[1]/20,0),adsk.core.Point3D.create(u+size[0]/20,v+size[1]/20,0))
  self.profiles[self.profile_key(c,p)]=s.profiles.item(0)
  return s
 def op_extrude(self,c,p):
  profile=self.profiles.get(self.profile_key(c,p))
  if profile is None:
   self.create_profile(c,p);profile=self.profiles[self.profile_key(c,p)]
  op_name=p.get('operation','new_body')
  op=adsk.fusion.FeatureOperations.NewBodyFeatureOperation
  if op_name=='join':op=adsk.fusion.FeatureOperations.JoinFeatureOperation
  elif op_name=='cut':op=adsk.fusion.FeatureOperations.CutFeatureOperation
  x=c.features.extrudeFeatures.createInput(profile,op);x.setDistanceExtent(False,adsk.core.ValueInput.createByReal(float(p.get('distance_mm',10))/10));return c.features.extrudeFeatures.add(x)
 def op_loft(self,c,p):
  center=p.get('center',[0,0,0]);axis=p.get('axis',[0,0,1]);height=float(p.get('height_mm',p.get('height',10)))
  r0=float(p.get('bottom_radius_mm',p.get('bottom_radius',10)));r1=float(p.get('top_radius_mm',p.get('top_radius',1)))
  p0={'profile_id':str(p.get('profile_id','loft'))+'_0','shape':'circle','center':center,'axis':axis,'radius_mm':max(.1,r0),'plane_offset_mm':self.axis_offset(center,axis,-height/2)*10}
  p1={'profile_id':str(p.get('profile_id','loft'))+'_1','shape':'circle','center':center,'axis':axis,'radius_mm':max(.1,r1),'plane_offset_mm':self.axis_offset(center,axis,height/2)*10}
  s0=self.create_profile(c,p0);s1=self.create_profile(c,p1)
  op=adsk.fusion.FeatureOperations.NewBodyFeatureOperation if p.get('operation','new_body')!='join' else adsk.fusion.FeatureOperations.JoinFeatureOperation
  x=c.features.loftFeatures.createInput(op);x.loftSections.add(s0.profiles.item(0));x.loftSections.add(s1.profiles.item(0));return c.features.loftFeatures.add(x)
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
  radius=adsk.core.ValueInput.createByReal(max(.02,p.get('radius_mm',1)/10))
  last=None
  for edges in self.edge_groups(c):
   try:
    x=c.features.filletFeatures.createInput();x.addConstantRadiusEdgeSet(edges,radius,True);return c.features.filletFeatures.add(x)
   except Exception as exc:last=exc
  raise last or RuntimeError('no fillet edges')
 def op_chamfer(self,c,p):
  distance=adsk.core.ValueInput.createByReal(max(.02,p.get('distance_mm',1)/10))
  last=None
  for edges in self.edge_groups(c):
   try:
    x=c.features.chamferFeatures.createInput2();x.chamferEdgeSets.addEqualDistanceChamferEdgeSet(edges,distance,True);return c.features.chamferFeatures.add(x)
   except Exception as exc:last=exc
  raise last or RuntimeError('no chamfer edges')
 def op_hole(self,c,p):
  center=p.get('center',[0,0,0]);axis=p.get('axis',[0,0,1]);radius=p.get('radius_mm',2);depth=p.get('depth_mm',10)
  plane=self.plane_axis(c,axis,self.axis_offset(center,axis,-depth/2));u,v=self.plane_coords(center,axis)
  s=c.sketches.add(plane);s.sketchCurves.sketchCircles.addByCenterRadius(adsk.core.Point3D.create(u,v,0),radius/10)
  return self.cut_feature(c,s.profiles.item(0),depth/10)
 def op_boolean_cut(self,c,p):
  center=p.get('center',[0,0,0]);size=p.get('size_mm',[10,3,10]);axis=p.get('axis',[0,0,1])
  depth=max(1,float(p.get('depth_mm',size[2] if len(size)>2 else 10)))
  plane=self.plane_axis(c,axis,self.axis_offset(center,axis,-depth/2));u,v=self.plane_coords(center,axis)
  s=c.sketches.add(plane)
  if p.get('shape')=='circle':
   s.sketchCurves.sketchCircles.addByCenterRadius(adsk.core.Point3D.create(u,v,0),max(.1,p.get('radius_mm',2)/10))
  else:
   s.sketchCurves.sketchLines.addTwoPointRectangle(adsk.core.Point3D.create(u-size[0]/20,v-size[1]/20,0),adsk.core.Point3D.create(u+size[0]/20,v+size[1]/20,0))
  return self.cut_feature(c,s.profiles.item(0),depth/10)
 def op_circular_pattern(self,c,p):
  center=p.get('center',[0,0,0]);axis=p.get('axis',[0,0,1]);r=p.get('radius_mm',8);br=p.get('boss_radius_mm',1.5);h=p.get('boss_height_mm',2);count=int(p.get('count',4))
  count=max(2,min(count,12));seed=self.primitive_cylinder(c,{'center':[center[0]+r,center[1],center[2]],'axis':axis,'radius':br,'height':h})
  entities=adsk.core.ObjectCollection.create();entities.add(seed.bodies.item(0))
  x=c.features.circularPatternFeatures.createInput(entities,self.construction_axis(c,axis));x.quantity=adsk.core.ValueInput.createByReal(count);x.totalAngle=adsk.core.ValueInput.createByString('360 deg');return c.features.circularPatternFeatures.add(x)
 def execute(self,call,components):
  p=call['parameters'];name=call['target_component'];skill=str(call['skill']).strip()
  if skill=='PlaceComponentFromURDF':
   m=adsk.core.Matrix3D.create()
   for i,row in enumerate(p['transform_cm']):
    for j,value in enumerate(row):m.setCell(i,j,value)
   components[name]=self.component(name,m);self.log(call,None);return
  if skill=='CreateSharedJointReference':
   # The external URDF is authoritative for this reference. The backend records
   # the shared interface intent without inventing native joint semantics.
   self.log(call,None);return
  if name not in components:components[name]=self.component(name)
  entry=components[name];c=entry['component'];feature=None
  if skill=='CreateSketchProfile':feature=self.create_profile(c,p)
  elif skill=='Extrude':feature=self.op_extrude(c,p)
  elif skill=='Loft':feature=self.op_loft(c,p)
  elif skill=='CreateCompositeLinkGeometry':feature=self.composite(c,p)
  elif skill=='ApplyFillet':feature=self.op_fillet(c,p)
  elif skill=='ApplyChamfer':feature=self.op_chamfer(c,p)
  elif skill=='CreateHole':feature=self.op_hole(c,p)
  elif skill=='BooleanCut':feature=self.op_boolean_cut(c,p)
  elif skill=='CircularPattern':feature=self.op_circular_pattern(c,p)
  else: raise RuntimeError('unsupported in v1 backend: '+repr(skill))
  self.log(call,feature)
 def export(self,path,components=None):
  self.design.computeAll();em=self.design.exportManager;em.execute(em.createFusionArchiveExportOptions(path+'.f3d',self.root));em.execute(em.createSTEPExportOptions(path+'.step',self.root));em.execute(em.createSTLExportOptions(self.root,path+'.stl'))
  if components:
   mesh_dir=os.path.join(os.path.dirname(path),'meshes');os.makedirs(mesh_dir,exist_ok=True)
   for name,entry in components.items():em.execute(em.createSTLExportOptions(entry['occurrence'],os.path.join(mesh_dir,name+'.stl')))

def make_design():
 app=adsk.core.Application.get();doc=app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType);design=adsk.fusion.Design.cast(app.activeProduct);design.designType=adsk.fusion.DesignTypes.ParametricDesignType;return app,design,design.rootComponent
