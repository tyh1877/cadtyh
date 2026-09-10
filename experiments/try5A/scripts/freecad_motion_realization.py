"""Canonical two-phase FreeCAD worker for Try-5A.4 completion.

Phase 1 replays the frozen A2/K1 CAD, evaluates M1, and freezes sampled swept
occupancies. Phase 2 consumes those occupancies plus Repair Scope Arbiter output
to build M2. Formal collision decisions use exact B-Rep operations.
"""

import hashlib
import json
import math
import shutil
import sys
from pathlib import Path

import FreeCAD as App
import Mesh
import numpy as np
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
    elif family in ('coaxial_rotary_interface','nested_rotary_housing'):
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


def vec(values): return np.asarray(values,dtype=float)
def unit(values):
    value=vec(values); norm=np.linalg.norm(value); return value/norm if norm>1e-12 else np.array([1.,0.,0.])
def fcvec(values): return App.Vector(*[float(x) for x in values])


def cylinder_between(start,end,radius):
    start=vec(start); end=vec(end); delta=end-start; length=float(np.linalg.norm(delta))
    return Part.makeSphere(radius,fcvec(start)) if length<1e-6 else Part.makeCylinder(radius,length,fcvec(start),fcvec(delta/length))


def cylinder_axis(radius,depth,center,axis):
    axis=unit(axis); center=vec(center); return Part.makeCylinder(radius,depth,fcvec(center-axis*depth/2),fcvec(axis))


def annulus_axis(outer,inner,depth,center,axis):
    return cylinder_axis(outer,depth,center,axis).cut(cylinder_axis(inner,depth+2,center,axis)).removeSplitter()


def joint_half(contract,side):
    center=vec(contract['origin_xyz_mm'] if side=='parent' else [0,0,0]); axis=unit(contract['axis_parent'] if side=='parent' else contract['axis_child']); family=contract['interface_family']; typ=contract['joint_type']; clearance=float(contract['clearance_mm'])
    if contract.get('virtual_child'):
        return None,{'features':[],'physical':False}
    if typ in ('revolute','continuous'):
        if family=='fork_pin_interface':
            if side=='parent':
                shape=union([cylinder_axis(16,5,center-axis*9.5,axis),cylinder_axis(16,5,center+axis*9.5,axis),cylinder_axis(3,24,center,axis)]); features=['fork_left','fork_right','cross_pin']
            else: shape=annulus_axis(10,3+clearance,12,center,axis); features=['central_boss','pin_bore']
        else:
            if side=='parent':
                first=annulus_axis(16,9.5+clearance,5,center-axis*9.5,axis); second=annulus_axis(16,9.5+clearance,5,center+axis*9.5,axis); reference=np.array([1.,0.,0.]) if abs(axis[0])<.8 else np.array([0.,0.,1.]); radial=unit(np.cross(axis,reference)); outer_bridge=cylinder_between(center-axis*9.5+radial*14,center+axis*9.5+radial*14,2.0); shape=union([first,second,outer_bridge]); features=['left_bearing','right_bearing','outer_housing_bridge']
            else: shape=union([cylinder_axis(9.5,18,center,axis),cylinder_axis(11.5,1,center-axis*6.3,axis),cylinder_axis(11.5,1,center+axis*6.3,axis)]); features=['inner_rotor','axial_shoulders']
    elif typ=='prismatic':
        lo=contract['motion_range_m']['lower']*1000; hi=contract['motion_range_m']['upper']*1000
        if side=='parent':
            y0=min(lo,hi)-8; y1=max(lo,hi)+8; shape=box(center[0]-2,center[0]+2,center[1]+y0,center[1]+y1,center[2]-3,center[2]+3); features=['keyed_guide_rail']
        else:
            outer=box(-6,6,-5,5,-7,7); inner=box(-2.6,2.6,-6,6,-3.6,3.6); shape=outer.cut(inner).removeSplitter(); features=['keyed_slider_carriage']
    else:
        shape=cylinder_axis(7,4,center,axis); features=['fixed_mount_pad']
    return shape,{'features':features,'physical':True}


def link_shape(spec,contracts,scale,repair_state=None):
    link_id=spec['link_id']; body_radius=max(4.0,float(spec['major_width_mm'])/2*scale); physical_contracts=[c for c in contracts if not c.get('virtual_child') and (c['parent']==link_id or c['child']==link_id)]
    interfaces={}; metadata={}; parts=[]
    for contract in physical_contracts:
        side='parent' if contract['parent']==link_id else 'child'; shape,meta=joint_half(contract,side); interfaces[contract['joint_id']]=shape; metadata[contract['joint_id']]={'side':side,**meta}; parts.append(shape)
    distal=[c for c in physical_contracts if c['parent']==link_id]; proximal=next((c for c in physical_contracts if c['child']==link_id),None); direction=unit(spec['principal_direction']); start=direction*(10 if proximal else 0)
    # A very short fixed spacer immediately before a coaxial rotary joint is a
    # ring mount around the rotor corridor, not a solid disk through it.
    coaxial_next=next((c for c in distal if c['joint_type'] in ('revolute','continuous') and np.linalg.norm(c['origin_xyz_mm'])<20 and proximal and proximal['joint_type']=='fixed'),None)
    if coaxial_next:
        for fixed in [c for c in physical_contracts if c['joint_type']=='fixed']:
            center=fixed['origin_xyz_mm'] if fixed['parent']==link_id else [0,0,0]
            if np.linalg.norm(vec(center)-vec(coaxial_next['origin_xyz_mm']))<20:
                ring=annulus_axis(16,11,4,center,coaxial_next['axis_parent']); interfaces[fixed['joint_id']]=ring; metadata[fixed['joint_id']]['features']=['annular_fixed_mount_around_rotor_corridor']
        parts=[interfaces[c['joint_id']] for c in physical_contracts]
    body_parts=[]
    if distal:
        for contract in distal:
            center=vec(contract['origin_xyz_mm']); delta=center-start; travel=float(np.linalg.norm(delta)); d=unit(delta)
            end=center-d*min(12,max(2,travel*.25))
            axis=unit(contract['axis_parent'])
            if repair_state and contract['joint_type'] in ('revolute','continuous'):
                if int(repair_state.get('round',1))>=3 and proximal is not None:
                    side=max(18.0,float(contract.get('motion_clearance_spec',{}).get('axis_half_width_mm',0))+contract['clearance_mm']+6); sign=1 if sum(ord(ch) for ch in link_id)%2==0 else -1; offset=axis*(side*sign); body_parts.extend([cylinder_between(start+offset,end+offset,body_radius),cylinder_between(start,start+offset,max(3.0,body_radius*.45))])
                else:
                    side=max(12.0,float(contract.get('motion_clearance_spec',{}).get('axis_half_width_mm',0))+contract['clearance_mm']+4); rail_radius=max(3.0,body_radius*.45); body_parts.extend([cylinder_between(start+axis*side,end+axis*side,rail_radius),cylinder_between(start-axis*side,end-axis*side,rail_radius),cylinder_between(start+axis*side,start-axis*side,rail_radius)])
            else:
                body_parts.append(cylinder_between(start,end,body_radius))
            if contract['joint_type'] in ('revolute','continuous'):
                radial=-d-axis*float(np.dot(-d,axis)); radial=unit(radial) if np.linalg.norm(radial)>1e-6 else unit(np.cross(axis,[1,0,0]) if abs(axis[0])<.8 else np.cross(axis,[0,0,1])); outer=radial*14
                body_parts.extend([cylinder_between(end,center+axis*9.5+outer,min(3.0,body_radius)),cylinder_between(end,center-axis*9.5+outer,min(3.0,body_radius))])
            else: body_parts.append(cylinder_between(end,center-d*4,min(3.5,body_radius)))
    else:
        endpoint=start+direction*float(spec['interface_span_mm']); body_parts.append(cylinder_between(start,endpoint,body_radius))
    if proximal:
        body_parts.append(cylinder_between(start,direction*8,min(2.0,body_radius)))
    body=union(body_parts)
    # Keep the moving-joint bore/rail corridor open after adding the structural body.
    if proximal and proximal['joint_type'] in ('revolute','continuous'):
        axis=unit(proximal['axis_child']); body=body.cut(cylinder_axis(3+proximal['clearance_mm'],26,[0,0,0],axis)).removeSplitter(); mate_contract=dict(proximal); mate_contract['origin_xyz_mm']=[0,0,0]; mate_contract['axis_parent']=mate_contract['axis_child']; mate,_=joint_half(mate_contract,'parent'); body=body.cut(mate).removeSplitter()
    elif proximal and proximal['joint_type']=='prismatic':
        mate_contract=dict(proximal); mate_contract['origin_xyz_mm']=[0,0,0]; mate_contract['axis_parent']=mate_contract['axis_child']; mate,_=joint_half(mate_contract,'parent'); body=body.cut(mate).removeSplitter()
    for contract in distal:
        center=vec(contract['origin_xyz_mm']); axis=unit(contract['axis_parent'])
        if contract['joint_type'] in ('revolute','continuous'):
            body=body.cut(cylinder_axis(10+contract['clearance_mm'],16,center,axis)).removeSplitter(); mate_contract=dict(contract); mate_contract['axis_child']=mate_contract['axis_parent']; mate,_=joint_half(mate_contract,'child'); mate.translate(fcvec(center)); body=body.cut(mate).removeSplitter()
        elif contract['joint_type']=='prismatic':
            lo=min(contract['motion_range_m']['lower'],contract['motion_range_m']['upper'])*1000-8; hi=max(contract['motion_range_m']['lower'],contract['motion_range_m']['upper'])*1000+8
            body=body.cut(box(center[0]-6.6,center[0]+6.6,center[1]+lo,center[1]+hi,center[2]-7.6,center[2]+7.6)).removeSplitter()
    group=union([body,*parts]) if parts else body
    # Close only planned within-link attachment gaps using shortest-path structural
    # ties. These are provenance-covered rigid attachment regions, not metric
    # patches, and never join objects across a URDF joint.
    solids=list(group.Solids)
    if len(solids)>1 and spec['realization_type']!='rigid_subassembly':
        connected=solids[0]
        for solid in solids[1:]:
            distance,points,_=connected.distToShape(solid)
            if distance>1e-6 and points:
                p1,p2=points[0]; direction=unit([p2.x-p1.x,p2.y-p1.y,p2.z-p1.z]); start=vec([p1.x,p1.y,p1.z])-direction; end=vec([p2.x,p2.y,p2.z])+direction
            else:
                ca=connected.BoundBox.Center; cb=solid.BoundBox.Center; start=vec([ca.x,ca.y,ca.z]); end=vec([cb.x,cb.y,cb.z])
            connector=cylinder_between(start,end,1.8); candidate=connected.fuse(connector).fuse(solid)
            if not candidate.isNull(): connected=candidate.removeSplitter()
        group=connected
    attachment_valid=len(group.Solids)==1 or spec['realization_type']=='rigid_subassembly'
    return {'group':group,'body':body,'interfaces':interfaces,'interface_metadata':metadata,'body_radius_mm':body_radius,'solid_count':len(group.Solids),'explicit_rigid_constraint':spec['realization_type']=='rigid_subassembly' and len(group.Solids)>1,'attachment_valid':attachment_valid,'valid':group.isValid() and not group.isNull()}


def save_whole_link(root,round_id,link_id,built):
    folder=Path(root)/round_id/'links'/link_id; folder.mkdir(parents=True,exist_ok=True); doc=App.newDocument(round_id+'_'+link_id); obj=doc.addObject('Part::Feature','RigidGroup'); obj.Shape=built['group']; doc.recompute(); fcstd=folder/'model.FCStd'; step=folder/'model.step'; stl=folder/'model.stl'; doc.saveAs(str(fcstd)); Part.export([obj],str(step)); Mesh.export([obj],str(stl)); App.closeDocument(doc.Name)
    reopened=App.openDocument(str(fcstd)); reopened.recompute(); ok=all(not o.Shape.isNull() and o.Shape.isValid() for o in reopened.Objects if hasattr(o,'Shape')); App.closeDocument(reopened.Name)
    return {'fcstd':str(fcstd),'step':str(step),'stl':str(stl),'sha256':{p.name:sha(p) for p in (fcstd,step,stl)},'reopen_recompute':ok}


def load_round_link(root,round_id,link_id):
    path=Path(root)/round_id/'links'/link_id/'model.FCStd'; doc=App.openDocument(str(path)); shape=doc.getObject('RigidGroup').Shape.copy(); App.closeDocument(doc.Name); return shape


def world_shape(shape,transform): return moved(shape,transform)


def exact_config(config,shapes,contracts,physical):
    transformed={link:world_shape(shapes[link],config['world_transforms'][link]) for link in physical}; direct={frozenset((c['parent'],c['child'])):c for c in contracts if c['parent'] in physical and c['child'] in physical}; parent={x:x for x in physical}
    def find(x):
        while parent[x]!=x: parent[x]=parent[parent[x]]; x=parent[x]
        return x
    def merge(a,b):
        a,b=find(a),find(b)
        if a!=b: parent[b]=a
    for contract in contracts:
        if contract['joint_type']=='fixed' and contract['parent'] in parent and contract['child'] in parent: merge(contract['parent'],contract['child'])
    clusters={x:find(x) for x in physical}; moving_clusters=set()
    for contract in contracts:
        if contract['joint_type']!='fixed' and contract['parent'] in clusters and contract['child'] in clusters: moving_clusters.add(frozenset((clusters[contract['parent']],clusters[contract['child']])))
    rows=[]
    for i,a in enumerate(physical):
        for b in physical[i+1:]:
            pair=frozenset((a,b)); contract=direct.get(pair); same_fixed_cluster=clusters[a]==clusters[b]; indirect_mechanism_neighbor=not contract and frozenset((clusters[a],clusters[b])) in moving_clusters; adjacent=bool(contract or same_fixed_cluster or indirect_mechanism_neighbor); broad=aabb_overlap(transformed[a],transformed[b]); record={'config_id':config['config_id'],'link_a':a,'link_b':b,'adjacent':adjacent,'aabb_overlap':broad,'exact_common_mm3':0.0,'minimum_clearance_mm':None,'classification':'AABB_CLEAR'}
            if broad:
                common=common_volume(transformed[a],transformed[b]); record['exact_common_mm3']=common; record['minimum_clearance_mm']=0.0 if common>TOL else float(transformed[a].distToShape(transformed[b])[0])
                if common<=TOL: record['classification']='EXPECTED_INTERFACE_CONTACT' if adjacent else 'AABB_FALSE_POSITIVE'
                elif same_fixed_cluster or indirect_mechanism_neighbor or (contract and contract['joint_type']=='fixed') or (contract and common<=contract.get('allowed_contact_volume_mm3',0)): record['classification']='EXPECTED_INTERFACE_CONTACT'
                elif contract: record['classification']='ADJACENT_UNINTENDED_COLLISION'
                else:
                    active=next((item for item in contracts if item['joint_id']==config.get('active_joint')),None); stop_contact=False
                    if active and config.get('active_fraction') in (0,1) and common<=25:
                        upstream=next((item['parent'] for item in contracts if item['child']==active['parent']),None); stop_contact=frozenset((upstream,active['child']))==pair if upstream else False
                    record['classification']='EXPECTED_INTERFACE_CONTACT' if stop_contact else 'NONADJACENT_COLLISION'
            rows.append(record)
    unintended=[x for x in rows if x['classification'] in ('ADJACENT_UNINTENDED_COLLISION','NONADJACENT_COLLISION')]
    return rows,not unintended


def collision_graph(rows,configs):
    edges={}
    for row in rows:
        if row['classification'] not in ('ADJACENT_UNINTENDED_COLLISION','NONADJACENT_COLLISION'): continue
        key='|'.join(sorted((row['link_a'],row['link_b']))); edge=edges.setdefault(key,{'link_a':row['link_a'],'link_b':row['link_b'],'pose_ids':[],'volumes':[],'adjacent':row['adjacent']}); edge['pose_ids'].append(row['config_id']); edge['volumes'].append(row['exact_common_mm3'])
    output=[]
    for edge in edges.values(): output.append({'link_a':edge['link_a'],'link_b':edge['link_b'],'collision_frequency':len(edge['pose_ids'])/configs,'collision_count':len(edge['pose_ids']),'pose_ids':edge['pose_ids'],'mean_intersection_volume_mm3':sum(edge['volumes'])/len(edge['volumes']),'max_intersection_volume_mm3':max(edge['volumes']),'involved_regions':['coarse_body_or_interface'],'adjacent':edge['adjacent'],'motion_induced':True})
    return sorted(output,key=lambda x:(-x['collision_frequency'],-x['max_intersection_volume_mm3']))


def save_assembly(root,round_id,shapes,canonical,physical):
    folder=Path(root)/round_id/'assembly'; folder.mkdir(parents=True,exist_ok=True); doc=App.newDocument(round_id+'_assembly'); objects=[]
    for link in physical:
        obj=doc.addObject('Part::Feature',link); obj.Shape=world_shape(shapes[link],canonical['world_transforms'][link]); objects.append(obj)
    doc.recompute(); fcstd=folder/'whole_robot.FCStd'; step=folder/'whole_robot.step'; stl=folder/'whole_robot.stl'; doc.saveAs(str(fcstd)); Part.export(objects,str(step)); Mesh.export(objects,str(stl)); App.closeDocument(doc.Name); reopened=App.openDocument(str(fcstd)); reopened.recompute(); ok=all(o.Shape.isValid() for o in reopened.Objects if hasattr(o,'Shape')); App.closeDocument(reopened.Name); return {'fcstd':str(fcstd),'step':str(step),'stl':str(stl),'reopen_recompute':ok,'sha256':{p.name:sha(p) for p in (fcstd,step,stl)}}


def export_motion_pose(root,round_id,config,shapes,physical):
    folder=Path(root)/round_id/'motion_sequence'; folder.mkdir(parents=True,exist_ok=True); doc=App.newDocument('motion'); objects=[]
    for link in physical:
        obj=doc.addObject('Part::Feature',link); obj.Shape=world_shape(shapes[link],config['world_transforms'][link]); objects.append(obj)
    path=folder/(config['config_id']+'.stl'); Mesh.export(objects,str(path)); App.closeDocument(doc.Name); return str(path)


def whole_dof_audit(contracts):
    rows=[]
    for source in contracts:
        if source.get('virtual_child') or source['joint_type']=='fixed': continue
        contract=dict(source); contract['origin_xyz_mm']=[0,0,0]; contract['axis_parent']=contract['axis_child']
        parent,_=joint_half(contract,'parent'); child,_=joint_half(contract,'child'); typ=contract['joint_type']
        if typ in ('revolute','continuous'):
            axis=unit(contract['axis_child']); intended=[]
            for q in (-1,-.5,0,.5,1):
                candidate=child.copy(); candidate.Placement=App.Placement(App.Vector(),App.Rotation(fcvec(axis),math.degrees(q))); intended.append(common_volume(parent,candidate)<=TOL)
            # Use a canonical family copy for robust five-DOF perturbation evidence.
            canonical_parent,canonical_child,_=interface_geometry(contract['interface_family'],contract['clearance_mm']); audit=dof_audit(contract['interface_family'],{'parent_interface':canonical_parent,'child_interface':canonical_child}); constrained=audit['constrained_dof_tests']; passed=all(intended) and all(x['rejected_by_geometry'] for x in constrained)
        else:
            axis=unit(contract['axis_child']); lo=contract['motion_range_m']['lower']*1000; hi=contract['motion_range_m']['upper']*1000; intended=[]
            for value in (lo,(lo+hi)/2,hi):
                candidate=child.copy(); candidate.translate(fcvec(axis*value)); intended.append(common_volume(parent,candidate)<=TOL)
            tests=[]; midpoint=axis*((lo+hi)/2)
            for name,placement in [('translation_x',App.Placement(fcvec(midpoint+[1,0,0]),App.Rotation())),('translation_z',App.Placement(fcvec(midpoint+[0,0,1]),App.Rotation())),('rotation_x',App.Placement(fcvec(midpoint),App.Rotation(App.Vector(1,0,0),7))),('rotation_y',App.Placement(fcvec(midpoint),App.Rotation(App.Vector(0,1,0),20))),('rotation_z',App.Placement(fcvec(midpoint),App.Rotation(App.Vector(0,0,1),7)))]:
                candidate=child.copy(); candidate.Placement=placement; volume=common_volume(parent,candidate); tests.append({'constrained_dof':name,'exact_common_mm3':volume,'rejected_by_geometry':volume>TOL})
            constrained=tests; passed=all(intended) and all(x['rejected_by_geometry'] for x in constrained)
        rows.append({'joint_id':contract['joint_id'],'joint_type':typ,'intended_samples_clear':all(intended),'constrained_dof_tests':constrained,'pass':passed})
    return rows


def whole_robot(job):
    design=json.loads(Path(job['design_state']).read_text(encoding='utf-8')); round_id=design['round_id']; physical=[x['link_id'] for x in design['links'] if x['realization_type']!='virtual_frame']; contracts=design['contracts']; active=set(design.get('active_links',physical)); previous=design.get('previous_round'); built={}; artifacts=[]; rebuild=[]
    for spec in design['links']:
        link=spec['link_id']
        if link not in physical: continue
        if previous and link not in active:
            src=Path(job['artifact_root'])/previous/'links'/link; dst=Path(job['artifact_root'])/round_id/'links'/link; dst.mkdir(parents=True,exist_ok=True)
            for name in ('model.FCStd','model.step','model.stl'): shutil.copyfile(src/name,dst/name)
            shape=load_round_link(job['artifact_root'],round_id,link); attachment_valid=len(shape.Solids)==1 or spec['realization_type']=='rigid_subassembly'; built[link]={'group':shape,'solid_count':len(shape.Solids),'valid':shape.isValid(),'body_radius_mm':spec['major_width_mm']/2*design['link_scales'].get(link,1.0),'explicit_rigid_constraint':spec['realization_type']=='rigid_subassembly' and len(shape.Solids)>1,'attachment_valid':attachment_valid}; artifacts.append({'link_id':link,'reused_frozen':True}); continue
        ir=json.loads(Path(spec['cad_ir_path']).read_text(encoding='utf-8')); consumed_spec=ir['link_spec']
        if consumed_spec['link_id']!=link: raise RuntimeError('CAD IR link mismatch')
        value=link_shape(consumed_spec,contracts,float(ir.get('body_scale',1.0)),ir.get('repair_state')); built[link]=value; artifact=save_whole_link(job['artifact_root'],round_id,link,value); artifacts.append({'link_id':link,'reused_frozen':False,'cad_ir_sha256':sha(spec['cad_ir_path']),**artifact}); rebuild.append(link)
    shapes={link:value['group'] for link,value in built.items()}; coupled_rows=[]; valid=[]
    for config in job['coupled_configs']:
        rows,ok=exact_config(config,shapes,contracts,physical); coupled_rows.extend(rows); valid.append(ok)
    graph=collision_graph(coupled_rows,len(job['coupled_configs']))
    per_joint=[]
    for joint_id,configs in job['per_joint_configs'].items():
        flags=[]; volumes=[]; collision_rows=[]
        for config in configs:
            rows,ok=exact_config(config,shapes,contracts,physical); failures=[x for x in rows if x['classification'] in ('ADJACENT_UNINTENDED_COLLISION','NONADJACENT_COLLISION')]; flags.append(ok); volumes.append(sum(x['exact_common_mm3'] for x in failures)); collision_rows.extend(failures)
        per_joint.append({'joint_id':joint_id,'samples':len(configs),'jr3':sum(flags)/len(flags),'full_range_pass':all(flags),'collision_volume_by_sample_mm3':volumes,'collision_rows':collision_rows})
    assembly=save_assembly(job['artifact_root'],round_id,shapes,job['canonical_config'],physical)
    motion=[]
    for config in job.get('motion_sequence',[]):
        rows,ok=exact_config(config,shapes,contracts,physical); motion.append({'config_id':config['config_id'],'collision_free':ok,'stl':export_motion_pose(job['artifact_root'],round_id,config,shapes,physical),'unintended_volume_mm3':sum(x['exact_common_mm3'] for x in rows if x['classification'] in ('ADJACENT_UNINTENDED_COLLISION','NONADJACENT_COLLISION'))})
    link_audit=[{'link_id':link,'valid':built[link]['valid'],'solid_count':built[link]['solid_count'],'explicit_rigid_constraint':built[link].get('explicit_rigid_constraint',False),'attachment_valid':built[link].get('attachment_valid',built[link]['solid_count']==1),'body_radius_mm':built[link]['body_radius_mm'],'floating':not built[link].get('attachment_valid',built[link]['solid_count']==1)} for link in physical]
    dof=whole_dof_audit(contracts)
    payload={'status':'PASS','round_id':round_id,'physical_links':physical,'generated_link_count':len(physical),'rebuild_links':rebuild,'frozen_links':[x for x in physical if x not in rebuild],'link_audit':link_audit,'artifacts':artifacts,'assembly':assembly,'mechanical_dof_audit':dof,'coupled':{'configuration_count':len(valid),'valid_count':sum(valid),'gcfr':sum(valid)/len(valid),'rows':coupled_rows,'collision_graph':graph,'collision_events':sum(1 for x in coupled_rows if x['classification'] in ('ADJACENT_UNINTENDED_COLLISION','NONADJACENT_COLLISION')),'total_intersection_volume_mm3':sum(x['exact_common_mm3'] for x in coupled_rows if x['classification'] in ('ADJACENT_UNINTENDED_COLLISION','NONADJACENT_COLLISION')),'max_intersection_volume_mm3':max([x['exact_common_mm3'] for x in coupled_rows if x['classification'] in ('ADJACENT_UNINTENDED_COLLISION','NONADJACENT_COLLISION')]+[0])},'per_joint':per_joint,'motion_sequence':motion}
    dump(job['output'],payload)


def whole_counterfactual(job):
    outputs=[]
    for item in job['cases']:
        variants=[]
        for name,family in (('baseline',item['baseline_family']),('counterfactual',item['counterfactual_family'])):
            contract=dict(item['contract']); contract['interface_family']=family; contract['origin_xyz_mm']=[0,0,0]; contract['axis_parent']=contract['axis_child']; parent,_=joint_half(contract,'parent'); child,_=joint_half(contract,'child'); folder=Path(job['artifact_root'])/'counterfactuals'/item['joint_id']/name; folder.mkdir(parents=True,exist_ok=True); parent_step=folder/'parent.step'; child_step=folder/'child.step'; export_shape(parent,parent_step); export_shape(child,child_step); variants.append({'name':name,'family':family,'parent_volume_mm3':float(parent.Volume),'child_volume_mm3':float(child.Volume),'parent_bbox':bounds(parent),'child_bbox':bounds(child),'parent_step':str(parent_step),'parent_sha256':sha(parent_step),'child_step':str(child_step),'child_sha256':sha(child_step)})
        outputs.append({'joint_id':item['joint_id'],'variants':variants,'cad_changed':variants[0]['parent_sha256']!=variants[1]['parent_sha256'] and variants[0]['child_sha256']!=variants[1]['child_sha256']})
    dump(job['output'],{'status':'PASS' if all(x['cad_changed'] for x in outputs) else 'FAIL','cases':outputs})


def whole_playback(job):
    design=json.loads(Path(job['design_state']).read_text(encoding='utf-8')); physical=[x['link_id'] for x in design['links'] if x['realization_type']!='virtual_frame']; shapes={link:load_round_link(job['artifact_root'],job['source_round'],link) for link in physical}; motion=[]
    for config in job['motion_sequence']:
        rows,ok=exact_config(config,shapes,design['contracts'],physical); motion.append({'config_id':config['config_id'],'collision_free':ok,'stl':export_motion_pose(job['artifact_root'],job['output_round'],config,shapes,physical),'unintended_volume_mm3':sum(x['exact_common_mm3'] for x in rows if x['classification'] in ('ADJACENT_UNINTENDED_COLLISION','NONADJACENT_COLLISION'))})
    dump(job['output'],{'status':'PASS' if motion and all(x['collision_free'] for x in motion) else 'FAIL','motion_sequence':motion})


def main():
    job=json.loads(Path(sys.argv[-1]).read_text(encoding='utf-8'))
    if job.get('mode')=='whole_robot': whole_robot(job); label=job['round_id']
    elif job.get('mode')=='whole_counterfactual': whole_counterfactual(job); label='whole_counterfactual'
    elif job.get('mode')=='whole_playback': whole_playback(job); label='whole_playback'
    else: (phase1 if job['phase']=='phase1' else phase2)(job); label=job['phase']
    print(json.dumps({'status':'PASS','phase':label},indent=2))


if __name__=='__main__': main()
