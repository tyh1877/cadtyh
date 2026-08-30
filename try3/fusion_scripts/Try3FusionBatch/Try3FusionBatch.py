"""Execute frozen Try-3 jobs as editable Fusion assemblies with native joint frames."""
import adsk.core, adsk.fusion, json, os, traceback, time, math
ROOT=r"D:\CADtest\papertest"; JOBS=os.path.join(ROOT,'try3','fusion_jobs.json'); RUNS=os.path.join(ROOT,'try3','runs'); RESULTS=os.path.join(ROOT,'try3','fusion_batch_results.json')
def mat(rpy,xyz):
 r,p,y=rpy;cr,sr=math.cos(r),math.sin(r);cp,sp=math.cos(p),math.sin(p);cy,sy=math.cos(y),math.sin(y)
 return [[cy*cp,cy*sp*sr-sy*cr,cy*sp*cr+sy*sr,xyz[0]/10],[sy*cp,sy*sp*sr+cy*cr,sy*sp*cr-cy*sr,xyz[1]/10],[-sp,cp*sr,cp*cr,xyz[2]/10],[0,0,0,1]]
def mul(a,b):return [[sum(a[i][k]*b[k][j] for k in range(4)) for j in range(4)] for i in range(4)]
def fm(a):
 m=adsk.core.Matrix3D.create()
 for i in range(4):
  for j in range(4):m.setCell(i,j,a[i][j])
 return m
def add_box(comp,p):
 sk=comp.sketches.add(comp.xYConstructionPlane);c=p['center'];s=p['size'];sk.sketchCurves.sketchLines.addTwoPointRectangle(adsk.core.Point3D.create((c[0]-s[0]/2)/10,(c[1]-s[1]/2)/10,0),adsk.core.Point3D.create((c[0]+s[0]/2)/10,(c[1]+s[1]/2)/10,0));i=comp.features.extrudeFeatures.createInput(sk.profiles.item(0),adsk.fusion.FeatureOperations.NewBodyFeatureOperation);i.setDistanceExtent(False,adsk.core.ValueInput.createByReal(s[2]/10));return comp.features.extrudeFeatures.add(i).bodies.item(0)
def add_cylinder(comp,p):
 sk=comp.sketches.add(comp.xYConstructionPlane);c=p['center'];sk.sketchCurves.sketchCircles.addByCenterRadius(adsk.core.Point3D.create(c[0]/10,c[1]/10,0),p['radius']/10);i=comp.features.extrudeFeatures.createInput(sk.profiles.item(0),adsk.fusion.FeatureOperations.NewBodyFeatureOperation);i.setDistanceExtent(False,adsk.core.ValueInput.createByReal(p['height']/10));return comp.features.extrudeFeatures.add(i).bodies.item(0)
def add_primitive(comp,p):
 if p['type']=='box':return add_box(comp,p)
 if p['type']=='cylinder':return add_cylinder(comp,p)
 if p['type']=='sphere':return add_cylinder(comp,{'center':p['center'],'radius':p['radius'],'height':2*p['radius']})
 return add_cylinder(comp,{'center':p['center'],'radius':max(p['bottom_radius'],p['top_radius']),'height':p['height']})
def add_fillet(comp,record):
 try:
  body=comp.bRepBodies.item(0);edges=adsk.core.ObjectCollection.create()
  for e in body.edges:edges.add(e)
  if edges.count:
   inp=comp.features.filletFeatures.createInput();inp.addConstantRadiusEdgeSet(edges,adsk.core.ValueInput.createByReal(.15),True);comp.features.filletFeatures.add(inp);record['skills'].append('ApplyFilletGroup')
 except:record['skill_failures'].append('ApplyFilletGroup')
def world_frames(job):
 links=job['blueprint']['links'];world={links[0]['name']:[[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]]};pending=list(job['blueprint']['joints'])
 while pending:
  rest=[]
  for j in pending:
   if j['parent'] in world:world[j['child']]=mul(world[j['parent']],mat(j['origin_rpy'],j['origin_xyz']))
   else:rest.append(j)
  if len(rest)==len(pending):raise RuntimeError('disconnected skeleton')
  pending=rest
 return world
def cardinal_axis(root,axis):
 i=max(range(3),key=lambda k:abs(axis[k]));return (root.xConstructionAxis,root.yConstructionAxis,root.zConstructionAxis)[i],axis[i]<0
def root_joint_point(root,xyz):
 # Parametric offset plane and sketch point establish the recorded joint origin.
 pi=root.constructionPlanes.createInput();pi.setByOffset(root.xYConstructionPlane,adsk.core.ValueInput.createByReal(xyz[2]/10));plane=root.constructionPlanes.add(pi);sk=root.sketches.add(plane);return sk.sketchPoints.add(adsk.core.Point3D.create(xyz[0]/10,xyz[1]/10,0))
def add_joint(root,occs,j,world,record):
 if j['type']=='fixed':return
 origin=mul(world[j['parent']],mat(j['origin_rpy'],j['origin_xyz']));axis=[sum(origin[i][k]*j['axis'][k] for k in range(3)) for i in range(3)];point=root_joint_point(root,[origin[0][3]*10,origin[1][3]*10,origin[2][3]*10]);geo=adsk.fusion.JointGeometry.createByPoint(point);inp=root.asBuiltJoints.createInput(occs[j['parent']],occs[j['child']],geo);entity,flip=cardinal_axis(root,axis)
 if j['type']=='prismatic':inp.setAsSliderJointMotion(adsk.fusion.JointDirections.CustomJointDirection,entity)
 else:inp.setAsRevoluteJointMotion(adsk.fusion.JointDirections.CustomJointDirection,entity)
 inp.isFlipped=flip;joint=root.asBuiltJoints.add(inp);joint.name=j['name'];motion=joint.jointMotion
 try:
  limits=motion.slideLimits if j['type']=='prismatic' else motion.rotationLimits;limits.isMinimumValueEnabled=True;limits.isMaximumValueEnabled=True;limits.minimumValue=j['lower']/10 if j['type']=='prismatic' else j['lower'];limits.maximumValue=j['upper']/10 if j['type']=='prismatic' else j['upper']
 except:record['skill_failures'].append('SetJointLimits:'+j['name'])
 t=joint.transform
 try:
  entity=motion.customSlideDirectionEntity if j['type']=='prismatic' else motion.customRotationAxisEntity
  native_axis=[entity.geometry.direction.x,entity.geometry.direction.y,entity.geometry.direction.z] if entity else None
  mode=int(motion.slideDirection if j['type']=='prismatic' else motion.rotationAxis)
 except:native_axis=None;mode=None
 record['joint_frames'][j['name']]={'origin_cm':[t.getCell(0,3),t.getCell(1,3),t.getCell(2,3)],'axis_world_requested':axis,'axis_flip_requested':flip,'native_custom_axis_entity_direction':native_axis,'native_axis_mode':mode,'joint_type':j['type'],'limits':[j['lower'],j['upper']]}
def run(context):
 app=adsk.core.Application.get();results=[]
 for job in json.load(open(JOBS))['jobs']:
  record={'case_id':job['case_id'],'version':job['version'],'status':'FAILURE','skills':[],'skill_failures':[],'joint_frames':{},'errors':[]};started=time.perf_counter()
  if job['status']!='READY':record['errors'].append(job.get('error','UPSTREAM_FAILURE'));results.append(record);continue
  try:
   doc=app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType);design=adsk.fusion.Design.cast(app.activeProduct);design.designType=adsk.fusion.DesignTypes.ParametricDesignType;root=design.rootComponent;world=world_frames(job);occs={}
   v2skills={x['link_id'] for x in job.get('features',{}).get('features',[]) if x.get('skill') in ('CreateRoundedLinkHousing','ApplyFilletGroup','CreateLoftedLinkHousing')}
   for link in job['blueprint']['links']:
    occ=root.occurrences.addNewComponent(fm(world[link['name']]));comp=occ.component;comp.name=link['name'];occs[link['name']]=occ
    for primitive in link['primitives']:add_primitive(comp,primitive)
    if job['version']=='V2' and link['name'] in v2skills:add_fillet(comp,record)
   for j in job['blueprint']['joints']:add_joint(root,occs,j,world,record)
   design.computeAll();out=os.path.join(RUNS,job['version'],job['case_id']);os.makedirs(os.path.join(out,'meshes'),exist_ok=True);em=design.exportManager;em.execute(em.createFusionArchiveExportOptions(os.path.join(out,'model.f3d'),root));em.execute(em.createSTEPExportOptions(os.path.join(out,'model.step'),root));em.execute(em.createSTLExportOptions(root,os.path.join(out,'model.stl')))
   for occ in root.occurrences:em.execute(em.createSTLExportOptions(occ,os.path.join(out,'meshes',occ.component.name+'.stl')))
   record.update(status='SUCCESS',component_count=root.occurrences.count,joint_count=root.asBuiltJoints.count,feature_count=sum(o.component.features.extrudeFeatures.count+o.component.features.filletFeatures.count for o in root.occurrences),rebuild_success=True,native_save_success=True,step_export_success=True,stl_export_success=True)
  except:record['errors'].append(traceback.format_exc())
  record['cad_execution_seconds']=time.perf_counter()-started;out=os.path.join(RUNS,job['version'],job['case_id']);os.makedirs(out,exist_ok=True);json.dump(record,open(os.path.join(out,'fusion_execution.json'),'w'),indent=2);results.append(record)
 json.dump(results,open(RESULTS,'w'),indent=2);app.userInterface.messageBox('Try-3 Fusion batch finished')
