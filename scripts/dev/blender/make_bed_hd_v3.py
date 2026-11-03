"""bed HD v3 — 簇绒压扣真变形+床品垂褶+包边+车削腿."""
import bpy, math, os, random
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "furnlib", "bed.glb")
os.makedirs(os.path.dirname(OUT), exist_ok=True)
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
for coll in (bpy.data.meshes, bpy.data.curves, bpy.data.materials):
    for x in list(coll):
        try: coll.remove(x)
        except: pass

def mat(name, hexc, rough=0.92, metal=0.0):
    m=bpy.data.materials.new(name=name); m.use_nodes=True
    bsdf=m.node_tree.nodes.get("Principled BSDF")
    r,g,b=tuple(int(hexc[i:i+2],16)/255 for i in (1,3,5))
    bsdf.inputs["Base Color"].default_value=(r,g,b,1.0)
    bsdf.inputs["Roughness"].default_value=rough
    if "Metallic" in bsdf.inputs: bsdf.inputs["Metallic"].default_value=metal
    try:
        bsdf.inputs["Sheen weight"].default_value=0.7
    except: pass
    # 布纹
    nt=m.node_tree
    tx=nt.nodes.new("ShaderNodeTexCoord")
    nz=nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value=120.0; nz.inputs["Detail"].default_value=2.0
    bp=nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value=0.18; bp.inputs["Distance"].default_value=0.0015
    nt.links.new(tx.outputs["UV"], nz.inputs["Vector"]); nt.links.new(nz.outputs["Fac"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], bsdf.inputs["Normal"])
    return m

M_FAB=mat("U_upholstery","#cbbfae",0.92); M_FAB2=mat("U_upholsterydk","#a89a86",0.9)
M_WHITE=mat("U_fabric","#f5f1e8",0.95); M_TERRA=mat("runner_terracotta","#c96f2e",0.95)
M_BLUE=mat("pillow_blue","#2f7fd0",0.95); M_WOOD=mat("U_wood","#4a3320",0.5)
M_SEAM=mat("U_dark","#35322e",0.6)

def dense_box(name,dims,loc,material,dense=3,bevel=0.02):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc)
    o=bpy.context.active_object; o.name=name
    o.dimensions=dims; bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    o.data.materials.append(material)
    md=o.modifiers.new("Dense",'SUBSURF'); md.levels=dense; md.render_levels=dense
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active=o
    bpy.ops.object.modifier_apply(modifier=md.name)
    for p in o.data.polygons: p.use_smooth=True
    if bevel>0:
        md=o.modifiers.new("Bevel",'BEVEL'); md.width=bevel; md.segments=3; md.limit_method='ANGLE'; md.angle_limit=math.radians(30)
    return o

def smart_uv(o):
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active=o
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=60, island_margin=0.02)
    bpy.ops.object.mode_set(mode='OBJECT')

def piping_rect(name,w,d,loc,material,r=0.009):
    cu=bpy.data.curves.new(name+"_curve",type='CURVE'); cu.dimensions='3D'; cu.resolution_u=10
    cu.bevel_depth=r; cu.bevel_resolution=3; cu.use_fill_caps=True
    spl=cu.splines.new('NURBS'); spl.points.add(3); spl.use_cyclic_u=True
    for i,(px,py,pz) in enumerate([(-w/2,-d/2,0),(w/2,-d/2,0),(w/2,d/2,0),(-w/2,d/2,0)]):
        spl.points[i].co=(px,py,pz,1.0)
    spl.order_u=3
    ob=bpy.data.objects.new(name,cu); bpy.context.collection.objects.link(ob)
    ob.location=loc; ob.data.materials.append(material)
    return ob

def crown_top(o,lift=0.02):
    for v in o.data.vertices:
        if v.co.z>0.03:
            fx=max(0.0,1.0-(v.co.x/0.9)**2); fy=max(0.0,1.0-(v.co.y/1.0)**2)
            v.co.z+=lift*min(fx,fy)

def wrinkle(o,amp=0.006,freq=24.0,seed=0):
    random.seed(seed); me=o.data
    for v in me.vertices:
        if v.co.z<-0.06: continue
        v.co.z+=(math.sin(v.co.x*freq+seed)*math.sin(v.co.y*freq*0.9+seed*1.7)*0.5+(random.random()-0.5)*0.6)*amp

objs=[]
objs.append(dense_box("frame",(1.9,2.15,0.28),(0,0,0.22),M_FAB2,dense=2,bevel=0.03))
# 床框包边
objs.append(piping_rect("frame_pipe",1.86,2.11,(0,0,0.365),M_SEAM,r=0.008))
objs.append(dense_box("headboard",(1.9,0.10,0.95),(0,-1.02,0.55),M_FAB,dense=3,bevel=0.045))
objs.append(piping_rect("hb_pipe",1.8,0.08,(0,-1.02,1.0),M_SEAM,r=0.008))
# 12簇绒：中央鼓+纽扣真压陷+四周缝沟
for ix in range(4):
    for iy in range(3):
        cx=-0.66+ix*0.44; cy=0.30+iy*0.25
        pu=dense_box(f"tuft_{ix}_{iy}",(0.36,0.075,0.20),(cx,-0.945,cy),M_FAB,dense=2,bevel=0.04)
        for v in pu.data.vertices:
            # 中央鼓
            if v.co.z>0.04: v.co.z*=1.14
            # 纽扣坑：靠近中心的顶面往里压
            d=math.sqrt(v.co.x**2+(v.co.z-0.02)**2)
            if v.co.y>0.02 and d<0.09:
                v.co.y-=0.022*math.cos(d/0.09*math.pi/2)**2
            # 四边缝沟往里收
            if abs(v.co.x)>0.15 or abs(v.co.z-0.02)>0.085:
                v.co.y-=0.006
        objs.append(pu)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.017,location=(cx,-0.90,cy))
        btn=bpy.context.active_object; btn.name=f"btn_{ix}_{iy}"; btn.data.materials.append(M_SEAM); objs.append(btn)
objs.append(dense_box("mattress",(1.8,2.0,0.24),(0,0.02,0.48),M_WHITE,dense=3,bevel=0.05))
objs.append(piping_rect("matt_pipe",1.76,1.96,(0,0.02,0.60),M_SEAM,r=0.008))
# 被子：高密平面垂盖+波浪褶
bpy.ops.mesh.primitive_plane_add(size=1,location=(0,0.38,0.62))
dv=bpy.context.active_object; dv.name="duvet"
dv.dimensions=(1.94,1.42,1); bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.subdivide(number_cuts=22); bpy.ops.object.mode_set(mode='OBJECT')
for v in dv.data.vertices:
    ax=abs(v.co.x); ay=v.co.y
    if ax>0.93: v.co.z-=(ax-0.93)*1.3  # 两侧垂下
    if ay>0.65: v.co.z-=(ay-0.65)*1.1  # 尾部垂下
    v.co.z+=math.sin(v.co.x*16.0)*0.010+math.sin(v.co.y*21.0+v.co.x*6.0)*0.009
mod=dv.modifiers.new("Solid","SOLIDIFY"); mod.thickness=0.03
dv.data.materials.append(M_WHITE)
for p in dv.data.polygons: p.use_smooth=True
smart_uv(dv); objs.append(dv)
# 被头翻折
objs.append(dense_box("duvet_fold",(1.9,0.24,0.10),(0,-0.20,0.65),M_FAB,dense=2,bevel=0.04))
run=dense_box("runner",(1.5,0.55,0.05),(0,0.55,0.72),M_TERRA,dense=2,bevel=0.015); run["noTheme"]=1; objs.append(run)
run2=dense_box("runner_fold",(1.5,0.13,0.06),(0,0.30,0.72),M_BLUE,dense=1,bevel=0.012); run2["noTheme"]=1; objs.append(run2)
wrinkle(run,0.004,30,5); wrinkle(run2,0.004,34,6)
for k,cx in enumerate((-0.45,0.45)):
    p=dense_box(f"sleep_{k}",(0.62,0.36,0.16),(cx,-0.62,0.66),M_WHITE,dense=3,bevel=0.06)
    p.rotation_euler=(math.radians(-8),0,0); objs.append(p)
for k,cx in enumerate((-0.45,0.45)):
    p=dense_box(f"cush_{k}",(0.42,0.14,0.34),(cx,-0.42,0.80),M_BLUE if k==0 else M_TERRA,dense=3,bevel=0.06)
    p.rotation_euler=(math.radians(-20),math.radians(10 if k==0 else -10),0); p["noTheme"]=1
    for v in p.data.vertices:
        if abs(v.co.x)>0.15 and abs(v.co.z)>0.12: v.co.x*=0.92; v.co.z*=0.92
    objs.append(p)
for sx in (-1,1):
    for sz in (-1,1):
        x,y=sx*0.85,sz*0.95
        for i,(rad,h) in enumerate([(0.034,0.0),(0.024,0.035),(0.032,0.07)]):
            bpy.ops.mesh.primitive_cylinder_add(vertices=18,radius=rad,depth=0.032,location=(x,y,h+0.02))
            seg=bpy.context.active_object; seg.name=f"leg_{sx}_{sz}_{i}"; seg.data.materials.append(M_WOOD); objs.append(seg)
for o in list(objs):
    if o.type!='MESH': continue
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active=o
    for md in [m.name for m in o.modifiers]:
        try: bpy.ops.object.modifier_apply(modifier=md)
        except: pass
for nm,amp,fr,sd in (("duvet",0.0,22,3),("mattress",0.005,26,4)):
    if amp>0:
        wrinkle(bpy.data.objects[nm],amp,fr,sd)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=OUT,export_format='GLB',export_materials='EXPORT',export_extras=True,export_cameras=False,export_lights=False,use_selection=True)
print("OK bed hd v3",OUT)
