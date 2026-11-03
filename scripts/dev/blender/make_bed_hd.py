"""Blender 4.5 bed HD v2: tufted headboard, piping, duvet folds, 20-min class detail."""
import bpy, math, os, random
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "furnlib", "bed.glb")
os.makedirs(os.path.dirname(OUT), exist_ok=True)
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
for coll in (bpy.data.meshes, bpy.data.curves, bpy.data.materials):
    for x in list(coll):
        try: coll.remove(x)
        except: pass
def mat(name, hexc, rough=0.9, metal=0.0):
    m=bpy.data.materials.new(name=name); m.use_nodes=True
    bsdf=m.node_tree.nodes.get("Principled BSDF")
    r,g,b=tuple(int(hexc[i:i+2],16)/255 for i in (1,3,5))
    bsdf.inputs["Base Color"].default_value=(r,g,b,1.0)
    bsdf.inputs["Roughness"].default_value=rough
    if "Metallic" in bsdf.inputs: bsdf.inputs["Metallic"].default_value=metal
    return m
M_FAB=mat("U_upholstery","#cbbfae",0.92); M_FAB2=mat("U_upholsterydk","#a89a86",0.9)
M_WHITE=mat("U_fabric","#f5f1e8",0.95); M_TERRA=mat("runner_terracotta","#c96f2e",0.95)
M_BLUE=mat("pillow_blue","#2f7fd0",0.95); M_WOOD=mat("U_wood","#4a3320",0.5)
M_SEAM=mat("U_dark","#35322e",0.6)
def box(name,dims,loc,material,bevel=0.02,sub=3):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc)
    o=bpy.context.active_object; o.name=name
    o.dimensions=dims; bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    o.data.materials.append(material)
    for p in o.data.polygons: p.use_smooth=True
    if bevel>0:
        md=o.modifiers.new("Bevel",'BEVEL'); md.width=bevel; md.segments=5; md.limit_method='ANGLE'; md.angle_limit=math.radians(30)
    if sub>0:
        md=o.modifiers.new("Subsurf",'SUBSURF'); md.levels=sub; md.render_levels=sub
    return o
def wrinkle(o, amp=0.007, freq=24.0, seed=0):
    random.seed(seed); me=o.data
    for v in me.vertices:
        if v.co.z < -0.06: continue
        v.co.z += (math.sin(v.co.x*freq+seed)*math.sin(v.co.y*freq*0.9+seed*1.7)*0.5 + (random.random()-0.5)*0.6)*amp
        v.co.x += (random.random()-0.5)*amp*0.4; v.co.y += (random.random()-0.5)*amp*0.4
objs=[]
objs.append(box("frame",(1.9,2.15,0.28),(0,0,0.22),M_FAB2,bevel=0.03,sub=3))
# tufted headboard: base + 12 chesterfield puffs + buttons
objs.append(box("headboard",(1.9,0.10,0.95),(0,-1.02,0.55),M_FAB,bevel=0.045,sub=3))
for ix in range(4):
    for iy in range(3):
        cx=-0.66+ix*0.44; cy=0.30+iy*0.25
        pu=box(f"tuft_{ix}_{iy}",(0.36,0.07,0.20),(cx,-0.95,cy),M_FAB,bevel=0.04,sub=3)
        for v in pu.data.vertices:
            if v.co.z>0.05: v.co.z*=1.12
        objs.append(pu)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.018,location=(cx,-0.905,cy))
        btn=bpy.context.active_object; btn.name=f"btn_{ix}_{iy}"; btn.data.materials.append(M_SEAM); objs.append(btn)
objs.append(box("mattress",(1.8,2.0,0.24),(0,0.02,0.48),M_WHITE,bevel=0.05,sub=3))
objs.append(box("duvet",(1.86,1.35,0.15),(0,0.38,0.62),M_WHITE,bevel=0.06,sub=3))
objs.append(box("duvet_fold",(1.86,0.22,0.10),(0,-0.18,0.645),M_FAB,bevel=0.04,sub=3))
run=box("runner",(1.5,0.55,0.05),(0,0.55,0.705),M_TERRA,bevel=0.015,sub=2); run["noTheme"]=1; objs.append(run)
run2=box("runner_fold",(1.5,0.12,0.055),(0,0.30,0.705),M_BLUE,bevel=0.012,sub=2); run2["noTheme"]=1; objs.append(run2)
for k,cx in enumerate((-0.45,0.45)):
    p=box(f"sleep_{k}",(0.62,0.36,0.16),(cx,-0.62,0.66),M_WHITE,bevel=0.06,sub=3)
    p.rotation_euler=(math.radians(-8),0,0); objs.append(p)
for k,cx in enumerate((-0.45,0.45)):
    p=box(f"cush_{k}",(0.42,0.14,0.34),(cx,-0.42,0.79),M_BLUE if k==0 else M_TERRA,bevel=0.06,sub=3)
    p.rotation_euler=(math.radians(-20),math.radians(10 if k==0 else -10),0); p["noTheme"]=1; objs.append(p)
for sx in (-1,1):
    for sz in (-1,1):
        x,y=sx*0.85,sz*0.95
        for i,(rad,h) in enumerate([(0.032,0.0),(0.022,0.035),(0.030,0.07)]):
            bpy.ops.mesh.primitive_cylinder_add(radius=rad,depth=0.03,location=(x,y,h+0.02))
            seg=bpy.context.active_object; seg.name=f"leg_{sx}_{sz}_{i}"; seg.data.materials.append(M_WOOD); objs.append(seg)
for o in list(objs):
    if o.type!='MESH': continue
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active=o
    for md in [m.name for m in o.modifiers]:
        try: bpy.ops.object.modifier_apply(modifier=md)
        except: pass
for nm,amp,fr,sd in (("duvet",0.009,22,3),("mattress",0.005,26,4),("runner",0.006,30,5)):
    wrinkle(bpy.data.objects[nm],amp,fr,sd)
    bpy.context.view_layer.objects.active=bpy.data.objects[nm]
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=OUT,export_format='GLB',export_materials='EXPORT',export_extras=True,export_cameras=False,export_lights=False,use_selection=True)
print("OK bed hd v2",OUT)
