import adsk.core,adsk.fusion,json,os,traceback
OUT=r'D:\CADtest\papertest\try2\fusion_smoke\rebuild_smoke.json'
def run(context):
 r={'rebuild_success':False,'error':None}
 try:
  app=adsk.core.Application.get();doc=app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType);design=adsk.fusion.Design.cast(app.activeProduct);root=design.rootComponent;occ=root.occurrences.addNewComponent(adsk.core.Matrix3D.create());sk=occ.component.sketches.add(occ.component.xYConstructionPlane);sk.sketchCurves.sketchCircles.addByCenterRadius(adsk.core.Point3D.create(0,0,0),1);i=occ.component.features.extrudeFeatures.createInput(sk.profiles.item(0),adsk.fusion.FeatureOperations.NewBodyFeatureOperation);i.setDistanceExtent(False,adsk.core.ValueInput.createByReal(1));occ.component.features.extrudeFeatures.add(i);r['compute_all_return']=design.computeAll();r['rebuild_success']=True
 except Exception:r['error']=traceback.format_exc()
 os.makedirs(os.path.dirname(OUT),exist_ok=True);json.dump(r,open(OUT,'w'),indent=2);app.userInterface.messageBox('Rebuild smoke complete')
