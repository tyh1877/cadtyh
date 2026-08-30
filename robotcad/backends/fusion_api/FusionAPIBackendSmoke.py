"""Run the six non-benchmark RobotCAD composite-skill smoke tests in Fusion."""
import adsk.core,json,os,time,traceback
from FusionAPIBackend import FusionAPIBackend,make_design
ROOT=r"D:\CADtest\papertest";OUT=os.path.join(ROOT,'try3','smoke','fusion_api_skill_smoke.json')
def run(context):
 result={'status':'FAILURE','backend':'FusionAPIBackend.v1','calls':[],'errors':[],'started_at':time.time()}
 try:
  app,design,root=make_design();backend=FusionAPIBackend(design,root,result)
  base={'length_mm':50,'radius_mm':15,'fillet_radius_mm':2,'shell_thickness_mm':2}
  names=['CreateRotaryJointHousing','CreateLoftedLinkHousing','CreateRoundedLinkHousing','CreateFlangeInterface','CreateShellHousing','CreateJointTransition']
  for i,name in enumerate(names):backend.execute({'call_id':'smoke-%02d'%(i+1),'skill':name,'version':'v1','target_component':'SMOKE_'+str(i+1),'parameters':base,'calling_agent':'SmokeTest'}, {})
  out=os.path.join(ROOT,'try3','smoke','FusionAPIBackendSmoke');os.makedirs(os.path.dirname(out),exist_ok=True);backend.export(out);result.update({'status':'SUCCESS','rebuild_success':True,'f3d':out+'.f3d','step':out+'.step','stl':out+'.stl'})
 except: result['errors'].append(traceback.format_exc())
 result['elapsed_seconds']=time.time()-result['started_at'];os.makedirs(os.path.dirname(OUT),exist_ok=True);json.dump(result,open(OUT,'w'),indent=2)
 try: app.userInterface.messageBox('RobotCAD Fusion API skill smoke: '+result['status'])
 except: pass
