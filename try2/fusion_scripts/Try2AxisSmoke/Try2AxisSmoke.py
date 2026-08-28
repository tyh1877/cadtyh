"""Probe whether a parametric Fusion construction axis can define joint geometry."""
import adsk.core,adsk.fusion,json,os,traceback
OUT=r'D:\CADtest\papertest\try2\fusion_smoke\axis_smoke.json'
def run(context):
 r={'axis_created':False,'joint_geometry_created':False,'error':None}
 try:
  app=adsk.core.Application.get();doc=app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType);root=adsk.fusion.Design.cast(app.activeProduct).rootComponent
  inp=root.constructionAxes.createInput();inp.setByLine(adsk.core.InfiniteLine3D.create(adsk.core.Point3D.create(0,0,0),adsk.core.Vector3D.create(1,1,0)));axis=root.constructionAxes.add(inp);r['axis_created']=axis is not None
  try:r['joint_geometry_created']=adsk.fusion.JointGeometry.createByCurve(axis,adsk.fusion.JointKeyPointTypes.CenterKeyPoint) is not None
  except Exception:r['joint_geometry_error']=traceback.format_exc()
 except Exception:r['error']=traceback.format_exc()
 os.makedirs(os.path.dirname(OUT),exist_ok=True);json.dump(r,open(OUT,'w'),indent=2);app.userInterface.messageBox('Axis smoke complete')
