"""Execute precomputed Try-2 blueprints as native Fusion feature assemblies."""
import adsk.core, adsk.fusion, json, os, traceback
ROOT=r'D:\CADtest\papertest'; JOBS=os.path.join(ROOT,'try2','fusion_jobs.json')
def add_box(comp,p):
 sk=comp.sketches.add(comp.xYConstructionPlane); c=p['center'];s=p['size']; sk.sketchCurves.sketchLines.addTwoPointRectangle(adsk.core.Point3D.create((c[0]-s[0]/2)/10,(c[1]-s[1]/2)/10,0),adsk.core.Point3D.create((c[0]+s[0]/2)/10,(c[1]+s[1]/2)/10,0)); inp=comp.features.extrudeFeatures.createInput(sk.profiles.item(0),adsk.fusion.FeatureOperations.NewBodyFeatureOperation);inp.setDistanceExtent(False,adsk.core.ValueInput.createByReal(s[2]/10));comp.features.extrudeFeatures.add(inp)
def add_cylinder(comp,p):
 sk=comp.sketches.add(comp.xYConstructionPlane);c=p['center'];sk.sketchCurves.sketchCircles.addByCenterRadius(adsk.core.Point3D.create(c[0]/10,c[1]/10,0),p['radius']/10);inp=comp.features.extrudeFeatures.createInput(sk.profiles.item(0),adsk.fusion.FeatureOperations.NewBodyFeatureOperation);inp.setDistanceExtent(False,adsk.core.ValueInput.createByReal(p['height']/10));comp.features.extrudeFeatures.add(inp)
def run(context):
 results=[]
 try: jobs=json.load(open(JOBS,encoding='utf-8'))['jobs']
 except: jobs=[]
 app=adsk.core.Application.get()
 for job in jobs:
  out=os.path.join(ROOT,'try2','runs',job['target_condition'],job['case_id']);os.makedirs(out,exist_ok=True);record={'case_id':job['case_id'],'status':'FAILURE','fusion_operations':0,'errors':[]}
  try:
   doc=app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType);design=adsk.fusion.Design.cast(app.activeProduct);root=design.rootComponent
   for link in job['blueprint']['links']:
    occ=root.occurrences.addNewComponent(adsk.core.Matrix3D.create());comp=occ.component;comp.name=link['name']
    for primitive in link['primitives']:
     if primitive['type']=='box':add_box(comp,primitive)
     elif primitive['type']=='cylinder':add_cylinder(comp,primitive)
     else: continue
     record['fusion_operations']+=1
   em=design.exportManager;em.execute(em.createFusionArchiveExportOptions(os.path.join(out,'model.f3d'),root));em.execute(em.createSTEPExportOptions(os.path.join(out,'model.step'),root));em.execute(em.createSTLExportOptions(root,os.path.join(out,'model.stl')))
   record.update({'status':'SUCCESS','component_count':root.occurrences.count,'feature_count':sum(o.component.features.extrudeFeatures.count for o in root.occurrences),'native_save_success':True,'step_export_success':True,'stl_export_success':True})
  except: record['errors'].append(traceback.format_exc())
  json.dump(record,open(os.path.join(out,'fusion_execution.json'),'w'),indent=2);results.append(record)
 json.dump(results,open(os.path.join(ROOT,'try2','fusion_batch_results.json'),'w'),indent=2)
 app.userInterface.messageBox('Try-2 Fusion batch finished')
