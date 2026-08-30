"""Generic formal executor: consumes frozen RobotCAD SkillCalls only."""
import adsk.core,json,os,time,traceback,sys,importlib
ROOT=r"D:\CADtest\papertest";JOBS=os.path.join(ROOT,'try3','fusion_api_jobs.json');OUT=os.path.join(ROOT,'try3','fusion_api_batch_results.json')
def run(context):
 here=os.path.dirname(os.path.abspath(__file__));sys.path.insert(0,here) if here not in sys.path else None
 # Fusion keeps imported modules alive between script invocations. Reload the
 # generic adapter so a user-run batch cannot silently use a pre-refactor class.
 import FusionAPIBackend as backend_module
 importlib.reload(backend_module)
 FusionAPIBackend,make_design=backend_module.FusionAPIBackend,backend_module.make_design
 results=[];app=None
 for job in json.load(open(JOBS))['jobs']:
  record={'case_id':job['case_id'],'version':job['version'],'status':'FAILURE','calls':[],'errors':[]};start=time.time();results.append(record)
  if job['status']!='READY':record['errors'].append(job['error']);continue
  try:
   app,design,root=make_design();backend=FusionAPIBackend(design,root,record);components={}
   for call in job['calls']:backend.execute(call,components)
   base=os.path.join(ROOT,'try3','runs',job['version'],job['case_id'],'fusion_api_model');os.makedirs(os.path.dirname(base),exist_ok=True);backend.export(base);record.update({'status':'SUCCESS','rebuild_success':True,'component_count':len(components),'f3d':base+'.f3d','step':base+'.step','stl':base+'.stl'})
  except:record['errors'].append(traceback.format_exc())
  record['elapsed_seconds']=time.time()-start
 json.dump(results,open(OUT,'w'),indent=2)
 try:
  if app:app.userInterface.messageBox('RobotCAD Fusion API formal batch complete')
 except:pass
