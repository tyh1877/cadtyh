"""Canonical two-phase FreeCAD worker for Try-5A.4 completion.

Phase 1 replays the frozen A2/K1 CAD, evaluates M1, and freezes sampled swept
occupancies. Phase 2 consumes those occupancies plus Repair Scope Arbiter output
to build M2. Formal collision decisions use exact B-Rep operations.
"""

import hashlib
import json
import math
import sys
from pathlib import Path

import FreeCAD as App
import Mesh
import Part

TOL = 1e-6


def dump(path, payload):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def box(x0, x1, y0, y1, z0, z1): return Part.makeBox(x1-x0, y1-y0, z1-z0, App.Vector(x0,y0,z0))
def cyl_y(radius, y0, y1): return Part.makeCylinder(radius, y1-y0, App.Vector(0,y0,0), App.Vector(0,1,0))


def union(shapes):
    result=shapes[0]
    for shape in shapes[1:]: result=result.fuse(shape)
    return result.removeSplitter()


def compound(shapes): return Part.makeCompound(shapes)
def common_volume(a,b):
    value=a.common(b); return 0.0 if value.isNull() else float(value.Volume)


def bounds(shape):
    b=shape.BoundBox
    return {"min_mm":[b.XMin,b.YMin,b.ZMin],"max_mm":[b.XMax,b.YMax,b.ZMax],"size_mm":[b.XLength,b.YLength,b.ZLength]}


def fc_matrix(payload):
    value=App.Matrix()
    for row in range(4):
        for column in range(4):
            item=payload[row][column]*(1000.0 if column==3 and row<3 else 1.0)
            setattr(value,"A{}{}".format(row+1,column+1),item)
    return value


def moved(shape, transform):
    result=shape.copy(); result.transformShape(fc_matrix(transform),True); return result


def rotate_y(shape,q):
    result=shape.copy(); result.Placement=App.Placement(App.Vector(),App.Rotation(App.Vector(0,1,0),math.degrees(q))); return result


def load_a2_link(root, link_id, target_joint):
    folder=Path(root)/link_id; ir_path=folder/'cad_ir.json'; model_path=folder/'model.FCStd'
    ir=json.loads(ir_path.read_text(encoding='utf-8'))
    feature={op['op_id']:op.get('feature_ref') for op in ir['operations']}
    doc=App.openDocument(str(model_path)); finals={name:doc.getObject(name).Shape.copy() for name in ir['final_objects']}; App.closeDocument(doc.Name)
    body_names=[name for name in finals if feature.get(name)=='BODY']
    interface_names=[name for name in finals if feature.get(name)=='IF_'+target_joint]
    body=compound([finals[name] for name in body_names]) if body_names else compound(list(finals.values()))
    interface=compound([finals[name] for name in interface_names]) if interface_names else Part.Shape()
    return {'group':compound(list(finals.values())),'body':body,'interface':interface,'final_object_names':list(finals),'body_names':body_names,'interface_names':interface_names,'ir_sha256':sha(ir_path),'model_sha256':sha(model_path),'ir_path':str(ir_path),'model_path':str(model_path)}


def interface_geometry(family, clearance):
    if family=='fork_pin_interface':
        pin_r=3.0; bore_r=pin_r+clearance
        parent=union([cyl_y(16,-12,-7),cyl_y(16,7,12),cyl_y(pin_r,-12,12)])
        child=cyl_y(10,-6,6).cut(cyl_y(bore_r,-7,7)).removeSplitter()
        topology={'parent':['fork_left','fork_right','cross_pin'],'child':['central_boss','pin_bore']}
    elif family=='coaxial_rotary_interface':
        rotor_r=9.5; bearing_bore=rotor_r+clearance
        left=cyl_y(16,-12,-7).cut(cyl_y(bearing_bore,-13,-6))
        right=cyl_y(16,7,12).cut(cyl_y(bearing_bore,6,13))
        parent=union([left,right])
        child=union([cyl_y(rotor_r,-9,9),cyl_y(11.5,-6.8,-5.8),cyl_y(11.5,5.8,6.8)])
        topology={'parent':['left_bearing','right_bearing'],'child':['inner_rotor','axial_shoulders']}
    else: raise ValueError('unsupported pilot family '+family)
    return parent,child,topology


def child_body(): return box(8,58,-6,6,-6,6)
def m1_parent_body(): return box(-58,-14,-8,8,-60,60)


def swept_shapes(child_group,child_interface,samples):
    return compound([rotate_y(child_group,q) for q in samples]),compound([rotate_y(child_interface,q) for q in samples])


def planned_m2_parent_body(swept_child,clearance):
    b=swept_child.BoundBox; inner=max(abs(b.YMin),abs(b.YMax))+clearance; outer=inner+7
    rear1=b.XMin-clearance-8; rear0=rear1-6
    left=box(rear0,-14,-outer,-inner,-12,12); right=box(rear0,-14,inner,outer,-12,12); rear=box(rear0,rear1,-outer,outer,-12,12)
    return union([left,right,rear]),{'swept_bbox_consumed':bounds(swept_child),'clearance_mm':clearance,'side_inner_mm':inner,'rear_bridge_x_mm':[rear0,rear1]}


def build_condition(family,condition,samples,clearance=.6,swept_override=None):
    pif,cif,topology=interface_geometry(family,clearance); cb=child_body(); cg=union([cb,cif]); swept_c,swept_i=swept_shapes(cg,cif,samples)
    if condition=='M1': pb=m1_parent_body(); planner={'strategy':'unreplanned_central_body','swept_bbox_consumed':None}
    elif condition=='M2': pb,planner=planned_m2_parent_body(swept_override or swept_c,clearance); planner['strategy']='swept_bbox_driven_U_body'
    else: raise ValueError(condition)
    pg=union([pb,pif])
    return {'parent_body':pb,'parent_interface':pif,'child_body':cb,'child_interface':cif,'parent_group':pg,'child_group':cg,'swept_child':swept_c,'swept_interface':swept_i,'planner':planner,'topology':topology,'clearance_mm':clearance}


def attachment(body,interface,group):
    distance=float(body.distToShape(interface)[0]); solids=len(group.Solids)
    return {'minimum_distance_mm':distance,'intersection_volume_mm3':common_volume(body,interface),'solid_count':solids,'pass':distance<=TOL and solids==1}


def aabb_overlap(a,b):
    x,y=a.BoundBox,b.BoundBox
    return not(x.XMax<y.XMin or y.XMax<x.XMin or x.YMax<y.YMin or y.YMax<x.YMin or x.ZMax<y.ZMin or y.ZMax<x.ZMin)


def export_shape(shape,path):
    doc=App.newDocument('export'); obj=doc.addObject('Part::Feature','Shape'); obj.Shape=shape; Part.export([obj],str(path)); App.closeDocument(doc.Name)


def export_base(target,pilot,condition,shapes):
    folder=Path(target)/'cad'/condition/pilot; folder.mkdir(parents=True,exist_ok=True)
    doc=App.newDocument(pilot+'_'+condition); objects=[]
    for name in ('parent_group','child_group','parent_body','parent_interface','child_body','child_interface'):
        shape=shapes.get(name)
        if shape is None or shape.isNull(): continue
        obj=doc.addObject('Part::Feature',name); obj.Shape=shape; objects.append(obj)
    doc.recompute(); fcstd=folder/'model.FCStd'; step=folder/'model.step'; parent_stl=folder/'parent.stl'; child_stl=folder/'child.stl'
    doc.saveAs(str(fcstd)); Part.export(objects[:2],str(step)); Mesh.export([objects[0]],str(parent_stl)); Mesh.export([objects[1]],str(child_stl)); App.closeDocument(doc.Name)
    return [str(fcstd),str(step),str(parent_stl),str(child_stl)]


def export_pose_meshes(target,pilot,condition,index,parent,child,neighbor=None):
    if condition!='M2' and index not in (0,4,8): return None
    folder=Path(target)/'pose_meshes'/condition/pilot/('pose_%02d'%index); folder.mkdir(parents=True,exist_ok=True)
    doc=App.newDocument('pose'); paths={}
    for name,shape in (('parent',parent),('child',child),('neighbor',neighbor)):
        if shape is None or shape.isNull(): continue
        obj=doc.addObject('Part::Feature',name); obj.Shape=shape; path=folder/(name+'.stl'); Mesh.export([obj],str(path)); paths[name]=str(path)
    App.closeDocument(doc.Name); return paths


def evaluate(pilot,condition,shapes,target):
    rows=[]
    for pose in pilot['poses']:
        parent=moved(shapes['parent_group'],pose['parent_world'] if condition=='M0' else pose['joint_world'])
        child=moved(shapes['child_group'],pose['child_world'])
        pif=moved(shapes['parent_interface'],pose['parent_world'] if condition=='M0' else pose['joint_world'])
        cif=moved(shapes['child_interface'],pose['child_world'])
        pair=common_volume(parent,child); interface=common_volume(pif,cif); unintended=max(0.0,pair-interface)
        neighbor=None; nonadj=0.0
        if shapes.get('neighbor') is not None and pose.get('neighbor_world') is not None:
            neighbor=moved(shapes['neighbor'],pose['neighbor_world']); nonadj=common_volume(parent,neighbor)
        classes=[]
        if interface>TOL: classes.append('EXPECTED_INTERFACE_CONTACT')
        if unintended>TOL: classes.append('ADJACENT_UNINTENDED_COLLISION' if pose['sample_index']==4 else 'MOTION_INDUCED_COLLISION')
        if nonadj>TOL: classes.append('NONADJACENT_COLLISION')
        rows.append({'sample_index':pose['sample_index'],'q_rad':pose['q_rad'],'q_deg':math.degrees(pose['q_rad']),'aabb_overlap':aabb_overlap(parent,child),'exact_pair_common_mm3':pair,'expected_interface_common_mm3':interface,'unintended_common_mm3':unintended,'nonadjacent_common_mm3':nonadj,'minimum_clearance_mm':float(parent.distToShape(child)[0]),'classifications':classes or ['CLEAR'],'formal_collision_free':unintended<=TOL and nonadj<=TOL,'mesh_paths':export_pose_meshes(target,pilot['joint_id'],condition,pose['sample_index'],parent,child,neighbor),'ee_world':pose['ee_world']})
    return rows


def dof_audit(family,shapes):
    parent=shapes['parent_interface']; child=shapes['child_interface']
    intended=[common_volume(parent,rotate_y(child,q))<=TOL for q in (-1,-.5,0,.5,1)]
    perturb=[('translation_x',App.Placement(App.Vector(1,0,0),App.Rotation())),('translation_y',App.Placement(App.Vector(0,1.5,0),App.Rotation())),('translation_z',App.Placement(App.Vector(0,0,1),App.Rotation())),('rotation_x',App.Placement(App.Vector(),App.Rotation(App.Vector(1,0,0),6))),('rotation_z',App.Placement(App.Vector(),App.Rotation(App.Vector(0,0,1),6)))]
    tests=[]
    for name,place in perturb:
        candidate=child.copy(); candidate.Placement=place; volume=common_volume(parent,candidate); tests.append({'constrained_dof':name,'exact_common_mm3':volume,'rejected_by_geometry':volume>TOL})
    return {'family':family,'intended_rotation_samples_clear':all(intended),'constrained_dof_tests':tests,'pass':all(intended) and all(x['rejected_by_geometry'] for x in tests)}


def phase1(job):
    results=[]; sweeps=[]; replay=[]
    for pilot in job['pilots']:
        m1_ir=json.loads(Path(pilot['cad_ir_paths']['M1']).read_text(encoding='utf-8'))
        if m1_ir['joint_id']!=pilot['joint_id']: raise RuntimeError('M1 CAD IR joint mismatch')
        parent=load_a2_link(job['a2_root'],pilot['parent'],pilot['joint_id']); child=load_a2_link(job['a2_root'],pilot['child'],pilot['joint_id'])
        neighbor=load_a2_link(job['a2_root'],pilot['neighbor'],pilot['neighbor_joint'])['group'] if pilot.get('neighbor') else None
        m0={'parent_group':parent['group'],'child_group':child['group'],'parent_body':parent['body'],'child_body':child['body'],'parent_interface':parent['interface'],'child_interface':child['interface'],'neighbor':neighbor}
        results.append({'joint_id':pilot['joint_id'],'condition':'M0','rows':evaluate(pilot,'M0',m0,job['artifact_root'])}); export_base(job['artifact_root'],pilot['joint_id'],'M0',m0)
        replay.append({'joint_id':pilot['joint_id'],'parent':{k:parent[k] for k in ('ir_sha256','model_sha256','ir_path','model_path','final_object_names','interface_names')},'child':{k:child[k] for k in ('ir_sha256','model_sha256','ir_path','model_path','final_object_names','interface_names')},'consumed':True})
        m1=build_condition(m1_ir['interface_family'],'M1',m1_ir['sample_values_rad'],clearance=m1_ir['parameters']['clearance_mm']); m1['neighbor']=neighbor
        results.append({'joint_id':pilot['joint_id'],'condition':'M1','rows':evaluate(pilot,'M1',m1,job['artifact_root']),'attachment':{'parent':attachment(m1['parent_body'],m1['parent_interface'],m1['parent_group']),'child':attachment(m1['child_body'],m1['child_interface'],m1['child_group'])},'topology':m1['topology']}); export_base(job['artifact_root'],pilot['joint_id'],'M1',m1)
        folder=Path(job['artifact_root'])/'sweeps'/pilot['joint_id']; folder.mkdir(parents=True,exist_ok=True); child_step=folder/'child_swept.step'; interface_step=folder/'interface_swept.step'; export_shape(m1['swept_child'],child_step); export_shape(m1['swept_interface'],interface_step)
        sweeps.append({'joint_id':pilot['joint_id'],'child_swept_bbox':bounds(m1['swept_child']),'interface_swept_bbox':bounds(m1['swept_interface']),'child_swept_step':str(child_step),'interface_swept_step':str(interface_step),'child_swept_sha256':sha(child_step),'interface_swept_sha256':sha(interface_step),'generated_before_m2':True})
    dump(job['output'],{'status':'PASS','results':results,'m0_replay':replay,'pre_m2_sweeps':sweeps})


def load_step_shape(path):
    shapes=Part.read(str(path)); return shapes


def phase2(job):
    p1=json.loads(Path(job['phase1_output']).read_text(encoding='utf-8')); sweep_by={x['joint_id']:x for x in p1['pre_m2_sweeps']}; decisions=json.loads(Path(job['repair_decisions']).read_text(encoding='utf-8'))['decisions']; decision_by={x['joint_id']:x for x in decisions}
    results=[]; dofs=[]; planners=[]; counter=[]
    for pilot in job['pilots']:
        m2_ir=json.loads(Path(pilot['cad_ir_paths']['M2']).read_text(encoding='utf-8'))
        if m2_ir['swept_input_sha256']!=sweep_by[pilot['joint_id']]['child_swept_sha256']: raise RuntimeError('M2 swept input hash mismatch')
        scope=decision_by[pilot['joint_id']]['decision']['repair_scope']
        if scope not in ('R1_LOCAL_FEATURE_REPAIR','R2_BODY_REGION_REPLAN'): raise RuntimeError('unexpected scope '+scope)
        swept=load_step_shape(sweep_by[pilot['joint_id']]['child_swept_step']); neighbor=load_a2_link(job['a2_root'],pilot['neighbor'],pilot['neighbor_joint'])['group'] if pilot.get('neighbor') else None
        m2=build_condition(m2_ir['interface_family'],'M2',m2_ir['sample_values_rad'],clearance=m2_ir['parameters']['clearance_mm'],swept_override=swept); m2['neighbor']=neighbor
        results.append({'joint_id':pilot['joint_id'],'condition':'M2','rows':evaluate(pilot,'M2',m2,job['artifact_root']),'attachment':{'parent':attachment(m2['parent_body'],m2['parent_interface'],m2['parent_group']),'child':attachment(m2['child_body'],m2['child_interface'],m2['child_group'])},'topology':m2['topology'],'planner':m2['planner'],'swept_input_sha256':sweep_by[pilot['joint_id']]['child_swept_sha256']}); export_base(job['artifact_root'],pilot['joint_id'],'M2',m2)
        dofs.append({'joint_id':pilot['joint_id'],**dof_audit(pilot['family'],m2)}); planners.append({'joint_id':pilot['joint_id'],**m2['planner'],'input_swept_sha256':sweep_by[pilot['joint_id']]['child_swept_sha256']})
        narrowed=pilot['sample_values_rad'][2:7]; narrow_src=build_condition(pilot['family'],'M1',narrowed); narrow=build_condition(pilot['family'],'M2',narrowed,swept_override=narrow_src['swept_child']); alternate='coaxial_rotary_interface' if pilot['family']=='fork_pin_interface' else 'fork_pin_interface'; alt=build_condition(alternate,'M2',pilot['sample_values_rad']); clear=build_condition(pilot['family'],'M2',pilot['sample_values_rad'],clearance=1.0)
        counter.append({'joint_id':pilot['joint_id'],'joint_limit':{'baseline_parent_bbox':bounds(m2['parent_group']),'counterfactual_parent_bbox':bounds(narrow['parent_group']),'pass':bounds(m2['parent_group'])!=bounds(narrow['parent_group'])},'knowledge_family':{'baseline':pilot['family'],'counterfactual':alternate,'baseline_topology':m2['topology'],'counterfactual_topology':alt['topology'],'pass':m2['topology']!=alt['topology']},'clearance':{'baseline_mm':.6,'counterfactual_mm':1.0,'baseline_parent_bbox':bounds(m2['parent_group']),'counterfactual_parent_bbox':bounds(clear['parent_group']),'pass':bounds(m2['parent_group'])!=bounds(clear['parent_group'])}})
    dump(job['output'],{'status':'PASS','results':results,'mechanical_dof_audit':dofs,'planner_records':planners,'counterfactuals':counter})


def main():
    job=json.loads(Path(sys.argv[-1]).read_text(encoding='utf-8'))
    (phase1 if job['phase']=='phase1' else phase2)(job)
    print(json.dumps({'status':'PASS','phase':job['phase']},indent=2))


if __name__=='__main__': main()
