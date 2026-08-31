"""Run non-benchmark RobotCAD operation-skill smoke tests in Fusion."""
import adsk.core,json,os,time,traceback,sys,importlib
ROOT=r"D:\CADtest\papertest";OUT=os.path.join(ROOT,'try3','smoke','fusion_api_skill_smoke.json')
def run(context):
 result={'status':'FAILURE','backend':'FusionAPIBackend.v1.basic_operations','calls':[],'errors':[],'started_at':time.time()}
 app=None
 try:
  # A Fusion script can be launched with a working directory different from
  # its own folder. Resolve the generic backend explicitly inside the guarded
  # entry point so an import error is recorded rather than disappearing.
  here=os.path.dirname(os.path.abspath(__file__))
  if here not in sys.path:sys.path.insert(0,here)
  import FusionAPIBackend as backend_module
  importlib.reload(backend_module)
  FusionAPIBackend,make_design=backend_module.FusionAPIBackend,backend_module.make_design
  app,design,root=make_design();backend=FusionAPIBackend(design,root,result)
  calls=[
   ('CreateSketchProfile',{'profile_id':'base_box','shape':'rectangle','center':[0,0,0],'axis':[0,0,1],'plane_offset_mm':-9,'size_mm':[60,24]}),
   ('Extrude',{'profile_id':'base_box','distance_mm':18,'operation':'new_body'}),
   ('CreateSketchProfile',{'profile_id':'cross_cylinder','shape':'circle','center':[0,0,12],'axis':[1,0,0],'plane_offset_mm':-35,'radius_mm':10}),
   ('Extrude',{'profile_id':'cross_cylinder','distance_mm':70,'operation':'new_body'}),
   ('Loft',{'profile_id':'taper','center':[0,18,0],'axis':[0,0,1],'height_mm':18,'bottom_radius_mm':7,'top_radius_mm':3,'operation':'new_body'}),
   ('ApplyFillet',{'radius_mm':1}),
   ('ApplyChamfer',{'distance_mm':1}),
   ('CreateHole',{'center':[0,0,0],'axis':[0,0,1],'radius_mm':3,'depth_mm':30}),
   ('BooleanCut',{'center':[0,0,0],'axis':[0,0,1],'shape':'rectangle','size_mm':[20,4,30]}),
   ('CircularPattern',{'center':[0,0,12],'axis':[0,0,1],'radius_mm':14,'boss_radius_mm':2,'boss_height_mm':3,'count':4}),
  ]
  components={}
  for i,(name,params) in enumerate(calls):backend.execute({'call_id':'smoke-%02d'%(i+1),'skill':name,'version':'v1','target_component':'SMOKE_1','parameters':params,'calling_agent':'SmokeTest'}, components)
  out=os.path.join(ROOT,'try3','smoke','FusionAPIBackendSmoke');os.makedirs(os.path.dirname(out),exist_ok=True);backend.export(out);result.update({'status':'SUCCESS','rebuild_success':True,'f3d':out+'.f3d','step':out+'.step','stl':out+'.stl'})
 except: result['errors'].append(traceback.format_exc())
 result['elapsed_seconds']=time.time()-result['started_at'];os.makedirs(os.path.dirname(OUT),exist_ok=True);json.dump(result,open(OUT,'w'),indent=2)
 try:
  if app:app.userInterface.messageBox('RobotCAD Fusion API skill smoke: '+result['status'])
 except: pass
