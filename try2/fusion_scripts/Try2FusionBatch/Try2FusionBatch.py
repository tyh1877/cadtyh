"""Execute precomputed Try-2 blueprints as native Fusion feature assemblies."""
import adsk.core, adsk.fusion, json, os, traceback
ROOT=r'D:\CADtest\papertest'; JOBS=os.path.join(ROOT,'try2','fusion_jobs.json')
def mmatrix(rpy,xyz):
 import math
 r,p,y=rpy;cr,sr=math.cos(r),math.sin(r);cp,sp=math.cos(p),math.sin(p);cy,sy=math.cos(y),math.sin(y)
 return [[cy*cp,cy*sp*sr-sy*cr,cy*sp*cr+sy*sr,xyz[0]/10],[sy*cp,sy*sp*sr+cy*cr,sy*sp*cr-cy*sr,xyz[1]/10],[-sp,cp*sr,cp*cr,xyz[2]/10],[0,0,0,1]]
def mul(a,b):return [[sum(a[i][k]*b[k][j] for k in range(4)) for j in range(4)] for i in range(4)]
def fusion_matrix(a):
 m=adsk.core.Matrix3D.create()
 for i in range(4):
  for j in range(4):m.setCell(i,j,a[i][j])
 return m
def add_box(comp,p):
 sk=comp.sketches.add(comp.xYConstructionPlane); c=p['center'];s=p['size']; sk.sketchCurves.sketchLines.addTwoPointRectangle(adsk.core.Point3D.create((c[0]-s[0]/2)/10,(c[1]-s[1]/2)/10,0),adsk.core.Point3D.create((c[0]+s[0]/2)/10,(c[1]+s[1]/2)/10,0)); inp=comp.features.extrudeFeatures.createInput(sk.profiles.item(0),adsk.fusion.FeatureOperations.NewBodyFeatureOperation);inp.setDistanceExtent(False,adsk.core.ValueInput.createByReal(s[2]/10));comp.features.extrudeFeatures.add(inp)
def add_cylinder(comp,p):
 sk=comp.sketches.add(comp.xYConstructionPlane);c=p['center'];sk.sketchCurves.sketchCircles.addByCenterRadius(adsk.core.Point3D.create(c[0]/10,c[1]/10,0),p['radius']/10);inp=comp.features.extrudeFeatures.createInput(sk.profiles.item(0),adsk.fusion.FeatureOperations.NewBodyFeatureOperation);inp.setDistanceExtent(False,adsk.core.ValueInput.createByReal(p['height']/10));comp.features.extrudeFeatures.add(inp)
def add_envelope(comp,p):
 if p['type']=='sphere': add_cylinder(comp,{'center':p['center'],'radius':p['radius'],'height':2*p['radius']})
 elif p['type']=='cone': add_cylinder(comp,{'center':p['center'],'radius':max(p['bottom_radius'],p['top_radius']),'height':p['height']})
def run(context):
 results=[]
 try: jobs=json.load(open(JOBS,encoding='utf-8'))['jobs']
 except: jobs=[]
 app=adsk.core.Application.get()
 for job in jobs:
  out=os.path.join(ROOT,'try2','runs',job['target_condition'],job['case_id']);os.makedirs(out,exist_ok=True);record={'case_id':job['case_id'],'status':'FAILURE','fusion_operations':0,'errors':[]}
  try:
   doc=app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType);design=adsk.fusion.Design.cast(app.activeProduct);root=design.rootComponent
   world={job['blueprint']['links'][0]['name']:[[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]]};pending=list(job['blueprint']['joints'])
   while pending:
    rest=[]
    for j in pending:
     if j['parent'] in world:world[j['child']]=mul(world[j['parent']],mmatrix(j['origin_rpy'],j['origin_xyz']))
     else:rest.append(j)
    if len(rest)==len(pending):raise RuntimeError('disconnected blueprint')
    pending=rest
   occs={}
   for link in job['blueprint']['links']:
    occ=root.occurrences.addNewComponent(adsk.core.Matrix3D.create());comp=occ.component;comp.name=link['name']
    occ.transform= fusion_matrix(world[link['name']]);occs[link['name']]=occ
    for primitive in link['primitives']:
     if primitive['type']=='box':add_box(comp,primitive)
     elif primitive['type']=='cylinder':add_cylinder(comp,primitive)
     else:add_envelope(comp,primitive)
     record['fusion_operations']+=1
   em=design.exportManager; mesh_dir=os.path.join(out,'meshes');os.makedirs(mesh_dir,exist_ok=True);em.execute(em.createFusionArchiveExportOptions(os.path.join(out,'model.f3d'),root));em.execute(em.createSTEPExportOptions(os.path.join(out,'model.step'),root));em.execute(em.createSTLExportOptions(root,os.path.join(out,'model.stl')))
   for occ in root.occurrences:
    em.execute(em.createSTLExportOptions(occ,os.path.join(mesh_dir,occ.component.name+'.stl')))
   joint_ok=0
   for j in job['blueprint']['joints']:
    try:
     b=occs[j['child']].component.bRepBodies.item(0).createForAssemblyContext(occs[j['child']]);geo=adsk.fusion.JointGeometry.createByPoint(b.vertices.item(0));inp=root.asBuiltJoints.createInput(occs[j['parent']],occs[j['child']],geo)
     if j['type']=='fixed':inp.setAsRigidJointMotion()
     else:inp.setAsRevoluteJointMotion(adsk.fusion.JointDirections.ZAxisJointDirection)
     root.asBuiltJoints.add(inp);joint_ok+=1
    except: record['errors'].append('joint '+j['name']+': '+traceback.format_exc())
   record.update({'status':'SUCCESS','component_count':root.occurrences.count,'feature_count':sum(o.component.features.extrudeFeatures.count for o in root.occurrences),'joint_count':joint_ok,'native_save_success':True,'step_export_success':True,'stl_export_success':True})
  except: record['errors'].append(traceback.format_exc())
  json.dump(record,open(os.path.join(out,'fusion_execution.json'),'w'),indent=2);results.append(record)
 json.dump(results,open(os.path.join(ROOT,'try2','fusion_batch_results.json'),'w'),indent=2)
 app.userInterface.messageBox('Try-2 Fusion batch finished')
