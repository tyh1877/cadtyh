"""Run non-benchmark RobotCAD operation-skill smoke tests in Fusion."""
import adsk.core,json,os,time,traceback,sys
ROOT=r"D:\CADtest\papertest";OUT=os.path.join(ROOT,'try3','smoke','fusion_api_skill_smoke.json')
def run(context):
 result={'status':'FAILURE','backend':'FusionAPIBackend.v1','calls':[],'errors':[],'started_at':time.time()}
 app=None
 try:
  # A Fusion script can be launched with a working directory different from
  # its own folder. Resolve the generic backend explicitly inside the guarded
  # entry point so an import error is recorded rather than disappearing.
  here=os.path.dirname(os.path.abspath(__file__))
  if here not in sys.path:sys.path.insert(0,here)
  from FusionAPIBackend import FusionAPIBackend,make_design
  app,design,root=make_design();backend=FusionAPIBackend(design,root,result)
  calls=[
   ('CreateCompositeLinkGeometry',{'primitives':[{'type':'box','center':[0,0,0],'size':[60,24,18]},{'type':'cylinder','center':[0,0,12],'axis':[1,0,0],'radius':10,'height':70}]}),
   ('ApplyFillet',{'radius_mm':1}),
   ('ApplyChamfer',{'distance_mm':1}),
   ('CreateGroove',{'center':[0,0,12],'axis':[1,0,0],'radius_mm':8,'width_mm':3,'depth_mm':1}),
   ('CreateHole',{'center':[0,0,0],'axis':[0,0,1],'radius_mm':3,'depth_mm':30}),
   ('CreateSlot',{'center':[0,0,0],'axis':[0,0,1],'size_mm':[20,4,30]}),
   ('CreateRib',{'center':[0,0,10],'size_mm':[45,3,8]}),
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
