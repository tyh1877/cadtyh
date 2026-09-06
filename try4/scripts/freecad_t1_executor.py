"""Generic T1 CAD-IR executor; no robot/part-specific geometry dispatch."""
import json,sys,time,traceback
from pathlib import Path
import FreeCAD,FreeCADGui,Import,Mesh
FreeCADGui.showMainWindow()
VIEWS={'front':'viewFront','side':'viewRight','top':'viewTop','isometric':'viewAxonometric'};COLORS=[(0.20,0.48,0.72),(0.90,0.48,0.18),(0.20,0.65,0.42),(0.65,0.34,0.78)]
def dump(p,x):p.write_text(json.dumps(x,indent=2)+'\n',encoding='utf-8')
def stats(objs):
    valid=[o for o in objs if hasattr(o,'Shape')and not o.Shape.isNull()];boxes=[o.Shape.BoundBox for o in valid]
    return {'valid_objects':sum(o.Shape.isValid()for o in valid),'objects':len(objs),'volume':sum(float(o.Shape.Volume)for o in valid),'bbox':[max(b.XMax for b in boxes)-min(b.XMin for b in boxes),max(b.YMax for b in boxes)-min(b.YMin for b in boxes),max(b.ZMax for b in boxes)-min(b.ZMin for b in boxes)]if boxes else[]}
def main(job_path):
    job=json.loads(Path(job_path).read_text());root=Path(job['repo_root']);sys.path.insert(0,str(root));from robotcad.backends.freecad_api.FreeCADBackend import FreeCADBackend
    out=Path(job['output']);data=json.loads(Path(job['agent_output']).read_text());ir=data['cad_ir'];backend=FreeCADBackend('Try4T1_'+data['part_id']);result={'part_id':data['part_id'],'status':'FAILURE','error':'','fallback_count':0};started=time.time()
    try:
        for operation in ir['operations']:backend.execute(operation)
        finals=[backend.resolve(n)for n in ir['final_objects']]
        for obj in backend.doc.Objects:obj.ViewObject.Visibility=False
        for i,obj in enumerate(finals):obj.ViewObject.Visibility=True;obj.ViewObject.ShapeColor=COLORS[i%len(COLORS)]
        backend.doc.recompute();before=stats(finals)
        if before['valid_objects']!=len(finals):raise RuntimeError('invalid final B-Rep')
        fcstd=out/'model.FCStd';step=out/'model.step';stl=out/'model.stl';backend.doc.saveAs(str(fcstd));Import.export(finals,str(step));Mesh.export(finals,str(stl));(out/'renders').mkdir(exist_ok=True)
        view=FreeCADGui.activeDocument().activeView();view.setAnimationEnabled(False);view.setCameraType('Orthographic')
        for name,method in VIEWS.items():getattr(view,method)();view.fitAll();FreeCADGui.updateGui();view.saveImage(str(out/'renders'/(name+'.png')),1000,1000,'White')
        edit=ir['editable_parameter'];obj=backend.doc.getObject(edit['object_id'])
        if obj is None:raise RuntimeError('editable native object missing')
        actual=float(getattr(obj,edit['property']));baseline_match=math_close(actual,edit['baseline_value']);setattr(obj,edit['property'],actual*1.05);backend.doc.recompute();after=stats(finals);edit_ok=after['valid_objects']==len(finals)and(abs(after['volume']-before['volume'])>1e-6 or after['bbox']!=before['bbox'])
        setattr(obj,edit['property'],actual);backend.doc.recompute();restored=stats(finals);parameter_restored=math_close(float(getattr(obj,edit['property'])),actual);restore_ok=restored['valid_objects']==len(finals)and parameter_restored
        log=backend.execution_log;result.update({'status':'SUCCESS','bodies':len(finals),'operations':len(log),'native_operation_successes':sum(r['success']for r in log),'fallback_count':sum(r['fallback_used']for r in log),'before':before,'editability':{'object_id':edit['object_id'],'property':edit['property'],'baseline_value':actual,'requested_baseline_matches':baseline_match,'edit_fraction':.05,'edited_valid':edit_ok,'restored_valid':restore_ok,'parameter_restored':parameter_restored,'restored_volume_delta':restored['volume']-before['volume'],'unrelated_frozen_regions':'NOT_APPLICABLE_T1_ROUND0'},'exports':{'fcstd':fcstd.is_file(),'step':step.is_file(),'stl':stl.is_file()}})
        dump(out/'feature_tree.json',backend.feature_manifest());dump(out/'execution_log.json',log);dump(out/'cad_validity.json',result);dump(out/'part_state.json',{'part_id':data['part_id'],'state':'BUILT','repair_round':0,'condition':'T1','current_artifact':'model.FCStd','quality_gates':'NOT_RUN_UNTIL_PHASE5','repair_history':[]});backend.close()
        reopened=FreeCAD.openDocument(str(fcstd));reopened.recompute();result['reopen']={'status':'PASS'if all(not o.Shape.isNull()and o.Shape.isValid()for o in reopened.Objects if hasattr(o,'Shape')and len(o.Shape.Faces))else'FAIL','native_shape_objects':sum(hasattr(o,'Shape')and len(o.Shape.Faces)for o in reopened.Objects)};FreeCAD.closeDocument(reopened.Name);dump(out/'cad_validity.json',result)
        if result['fallback_count']or not edit_ok or not restore_ok or result['reopen']['status']!='PASS':raise RuntimeError('CAD validity/editability gate failed')
    except Exception as e:
        result.update({'status':'FAILURE','error':f'{type(e).__name__}: {e}','traceback':traceback.format_exc()});dump(out/'cad_validity.json',result)
        try:backend.close()
        except Exception:pass
    finally:result['elapsed_seconds']=time.time()-started;dump(out/'execution_result.json',result);FreeCADGui.getMainWindow().close()
    return 0 if result['status']=='SUCCESS'else 1
def math_close(a,b):return abs(a-b)<=max(1e-6,abs(a)*1e-6)
if __name__=='__main__':raise SystemExit(main(sys.argv[-1]))
