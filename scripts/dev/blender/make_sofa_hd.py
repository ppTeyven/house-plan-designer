"""Blender 4.5 sofa HD v2: rolled arms, piping curves, turned legs, sculpted wrinkles."""
import bpy, math, os, random
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "furnlib", "sofa.glb")
os.makedirs(os.path.dirname(OUT), exist_ok=True)
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
for coll in (bpy.data.meshes, bpy.data.curves, bpy.data.materials, bpy.data.textures):
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

M_UP=mat("U_upholstery","#cfc3b4",0.92); M_DK=mat("U_upholsterydk","#8f867c",0.9)
M_WOOD=mat("U_wood","#4a3320",0.45); M_SEAM=mat("U_dark","#35322e",0.6)
M_OR=mat("pillow_orange","#d96f2e",0.95); M_BL=mat("pillow_blue","#2f7fd0",0.95)

def box(name,dims,loc,material,bevel=0.03,sub=3):
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

def wrinkle(obj, amp=0.007, freq=22.0, seed=0):
    random.seed(seed); me=obj.data
    # multi-frequency sine folds + random, keep bottom ring stable
    for v in me.vertices:
        if v.co.z < -0.06: continue
        x,y,z=v.co.x,v.co.y,v.co.z
        d=(math.sin(x*freq+seed)*math.sin(y*(freq*0.9)+seed*1.7)*0.5
           + math.sin((x+y)*freq*1.7)*0.25 + (random.random()-0.5)*0.6)*amp
        # fade wrinkles at very center top to keep crown smooth
        v.co.z+=d*0.8; v.co.x+=(random.random()-0.5)*amp*0.4; v.co.y+=(random.random()-0.5)*amp*0.4

def piping_rect(name, w, d, loc, material, r=0.011):
    # closed rectangular piping cord using curve
    cu=bpy.data.curves.new(name+"_curve", type='CURVE'); cu.dimensions='3D'; cu.resolution_u=6
    cu.bevel_depth=r; cu.bevel_resolution=4; cu.use_fill_caps=True
    spl=cu.splines.new('NURBS'); spl.points.add(3); spl.use_cyclic_u=True
    pts=[(-w/2,-d/2,0),(w/2,-d/2,0),(w/2,d/2,0),(-w/2,d/2,0)]
    for i,(px,py,pz) in enumerate(pts):
        spl.points[i].co=(px,py,pz,1.0)
    spl.order_u=3
    ob=bpy.data.objects.new(name, cu); bpy.context.collection.objects.link(ob)
    ob.location=loc; ob.data.materials.append(material)
    return ob

objs=[]
# frame
objs.append(box("base",(2.1,0.95,0.30),(0,0,0.27),M_UP,bevel=0.035,sub=3))
objs.append(box("plinth",(1.96,0.81,0.07),(0,0,0.075),M_DK,bevel=0.012,sub=2))
for sx in (-1,1):
    # arm main + rolled front scroll (video 里的圆滚扶手头)
    a=box(f"arm_{'L' if sx<0 else 'R'}",(0.24,0.78,0.34),(sx*0.93, -0.06, 0.53),M_UP,bevel=0.055,sub=3)
    objs.append(a)
    bpy.ops.mesh.primitive_cylinder_add(radius=0.155, depth=0.24, location=(sx*0.93, 0.36, 0.52))
    sc=bpy.context.active_object; sc.name=f"scroll_{'L' if sx<0 else 'R'}"
    sc.rotation_euler.x=math.radians(90)
    for p in sc.data.polygons: p.use_smooth=True
    md=sc.modifiers.new("Subsurf",'SUBSURF'); md.levels=3; md.render_levels=3
    sc.data.materials.append(M_UP); objs.append(sc)
    # scroll front button cap
    bpy.ops.mesh.primitive_cylinder_add(radius=0.045, depth=0.012, location=(sx*0.93, 0.505, 0.52))
    cap=bpy.context.active_object; cap.name=f"cap_{'L' if sx<0 else 'R'}"
    cap.rotation_euler.x=math.radians(90); cap.data.materials.append(M_SEAM); objs.append(cap)
    objs.append(piping_rect(f"arm_pipe_{'L' if sx<0 else 'R'}",0.20,0.74,(sx*0.93,-0.06,0.705),M_SEAM,r=0.010))

back=box("backrest",(1.86,0.22,0.58),(0,-0.375,0.66),M_UP,bevel=0.055,sub=3)
back.rotation_euler.x=math.radians(-8); objs.append(back)
objs.append(piping_rect("back_pipe_top",1.70,0.18,(0,-0.42,0.955),M_SEAM,r=0.010))

# seat cushions with crown + piping + wrinkles
for k,cx in enumerate((-0.62,0.0,0.62)):
    c=box(f"seat_{k}",(0.60,0.64,0.18),(cx,0.07,0.50),M_UP,bevel=0.06,sub=3)
    # crown: lift top center
    for v in c.data.vertices:
        if v.co.z>0.05:
            fall=1.0-min(1.0,(v.co.x/0.3)**2*0.7+(v.co.y/0.32)**2*0.7)
            v.co.z+=0.022*fall
    objs.append(c)
    objs.append(piping_rect(f"seat_pipe_{k}",0.56,0.60,(cx,0.07,0.425),M_SEAM,r=0.009))
# back cushions tilted, puffy
for k,cx in enumerate((-0.62,0.0,0.62)):
    c=box(f"backc_{k}",(0.60,0.17,0.46),(cx,-0.28,0.74),M_UP,bevel=0.065,sub=3)
    c.rotation_euler.x=math.radians(-12)
    for v in c.data.vertices:
        if v.co.z>0.1: v.co.z*=1.06
    objs.append(c)

# throw pillows: pinched corners
for nm,cx,col,rz in (("pillow_orange",-0.52,M_OR,0.15),("pillow_blue",0.52,M_BL,-0.15)):
    p=box(nm,(0.40,0.13,0.40),(cx,-0.12,0.73),col,bevel=0.075,sub=3)
    p.rotation_euler=(math.radians(-18),math.radians(12 if cx<0 else -12),rz)
    # pinch 4 corners inward for stuffed look
    for v in p.data.vertices:
        if abs(v.co.x)>0.12 and abs(v.co.z)>0.12:
            v.co.x*=0.88; v.co.z*=0.88
    p["noTheme"]=1; objs.append(p)

# turned wood legs: stacked tori/cylinders mimicking 车旋木腿
for sx in (-1,1):
    for sz in (-1,1):
        x,y=sx*0.90,sz*0.36
        prof=[(0.030,0.00),(0.032,0.02),(0.020,0.035),(0.028,0.055),(0.022,0.075),(0.030,0.10)]
        prev_z=0.0
        for i,(rad,h) in enumerate(prof):
            bpy.ops.mesh.primitive_cylinder_add(radius=rad, depth=0.022, location=(x,y,h))
            seg=bpy.context.active_object; seg.name=f"leg_{sx}_{sz}_{i}"
            seg.data.materials.append(M_WOOD); objs.append(seg)

# apply modifiers
for o in list(objs):
    if o.type!='MESH': continue
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active=o
    for md in [m.name for m in o.modifiers]:
        try: bpy.ops.object.modifier_apply(modifier=md)
        except Exception as e: print("apply fail",o.name,e)
# wrinkles AFTER apply so they survive
for nm,amp,fr,sd in (("seat_0",0.006,26,1),("seat_1",0.006,24,2),("seat_2",0.006,26,3),
                     ("backc_0",0.008,20,4),("backc_1",0.008,20,5),("backc_2",0.008,20,6),
                     ("pillow_orange",0.010,30,7),("pillow_blue",0.010,30,8)):
    wrinkle(bpy.data.objects[nm],amp,fr,sd)
    bpy.context.view_layer.objects.active=bpy.data.objects[nm]
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.normals_make_consistent(inside=False); bpy.ops.object.mode_set(mode='OBJECT')

print("exporting",OUT,"objects:",len(objs))
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', export_materials='EXPORT', export_extras=True,
    export_cameras=False, export_lights=False, use_selection=True)
print("OK sofa hd v2")
