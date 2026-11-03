"""Blender 4.5 sofa HD v3 — Blender Guru William流程: 框架按蓝图比例/坐垫cloth-pressure鼓包/曲线包边/褶皱克制."""
import bpy, math, os, random
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "furnlib", "sofa.glb")
os.makedirs(os.path.dirname(OUT), exist_ok=True)
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
for coll in (bpy.data.meshes, bpy.data.curves, bpy.data.materials):
    for x in list(coll):
        try: coll.remove(x)
        except: pass

def fabric_mat(name, hexc):
    m = bpy.data.materials.new(name=name); m.use_nodes = True
    nt = m.node_tree; bsdf = nt.nodes.get("Principled BSDF")
    r,g,b = tuple(int(hexc[i:i+2],16)/255 for i in (1,3,5))
    bsdf.inputs["Base Color"].default_value = (r,g,b,1.0)
    bsdf.inputs["Roughness"].default_value = 0.92
    if "Sheen weight" in bsdf.inputs:
        bsdf.inputs["Sheen weight"].default_value = 0.6
    if "Sheen roughness" in bsdf.inputs:
        bsdf.inputs["Sheen roughness"].default_value = 0.5
    # 布纹 bump: Noise -> Bump, 强度小避免融化感
    tex = nt.nodes.new("ShaderNodeTexCoord")
    noise = nt.nodes.new("ShaderNodeTexNoise"); noise.inputs["Scale"].default_value = 90.0; noise.inputs["Detail"].default_value = 2.0
    bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.12; bump.inputs["Distance"].default_value = 0.002
    nt.links.new(tex.outputs["UV"], noise.inputs["Vector"])
    nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return m

def flat_mat(name, hexc, rough=0.6, metal=0.0):
    m = bpy.data.materials.new(name=name); m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    r,g,b = tuple(int(hexc[i:i+2],16)/255 for i in (1,3,5))
    bsdf.inputs["Base Color"].default_value = (r,g,b,1.0)
    bsdf.inputs["Roughness"].default_value = rough
    if "Metallic" in bsdf.inputs: bsdf.inputs["Metallic"].default_value = metal
    return m

M_UP = fabric_mat("U_upholstery", "#cfc3b4")
M_DK = flat_mat("U_upholsterydk", "#9a8d7c", 0.9)
M_WELT = flat_mat("U_dark", "#4a443c", 0.7)   # 包边绳: 同面料深15%
M_METAL = flat_mat("U_metal", "#2b2e33", 0.35, 0.9)  # William款金属脚
M_BRASS = flat_mat("U_brass", "#8a6a3a", 0.35, 1.0)
M_OR = fabric_mat("pillow_orange", "#d96f2e")
M_BL = fabric_mat("pillow_blue", "#2f7fd0")

def box(name, dims, loc, material, bevel=0.02, bev_seg=3, sub=2):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.active_object; o.name = name
    o.dimensions = dims; bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.data.materials.append(material)
    for p in o.data.polygons: p.use_smooth = True
    # 倒角只做小圆角, 段数少保住型
    if bevel > 0:
        md = o.modifiers.new("Bevel", 'BEVEL'); md.width = bevel; md.segments = bev_seg
        md.limit_method = 'ANGLE'; md.angle_limit = math.radians(35)
    if sub > 0:
        md = o.modifiers.new("Subsurf", 'SUBSURF'); md.levels = sub; md.render_levels = sub
    return o

def smart_uv(o):
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True)
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=66, island_margin=0.02)
    bpy.ops.object.mode_set(mode='OBJECT')

def piping_rect(name, w, d, loc, material, r=0.008):
    cu = bpy.data.curves.new(name+"_curve", type='CURVE'); cu.dimensions='3D'; cu.resolution_u=8
    cu.bevel_depth=r; cu.bevel_resolution=3; cu.use_fill_caps=True
    spl = cu.splines.new('NURBS'); spl.points.add(3); spl.use_cyclic_u=True
    for i,(px,py,pz) in enumerate([(-w/2,-d/2,0),(w/2,-d/2,0),(w/2,d/2,0),(-w/2,d/2,0)]):
        spl.points[i].co = (px,py,pz,1.0)
    spl.order_u = 3
    ob = bpy.data.objects.new(name, cu); bpy.context.collection.objects.link(ob)
    ob.location = loc; ob.data.materials.append(material)
    return ob

def cushion_crown(o, lift=0.02, pinch=0.985):
    """cloth-pressure鼓包: 顶面中央抬高, 中腰轻收(缝纫拉力), 底圈钉死不动"""
    me = o.data
    for v in me.vertices:
        if v.co.z > 0.04:
            fx = max(0.0, 1.0-(v.co.x/0.32)**2); fy = max(0.0, 1.0-(v.co.y/0.34)**2)
            v.co.z += lift*min(fx,fy)
        elif abs(v.co.z) < 0.04:
            v.co.x *= pinch; v.co.y *= pinch

def crease(o, x0,y0, dx,dy, width=0.05, depth=0.006, seed=0):
    """按视频cloth-brush思路: 沿一条线压出一道自然折痕, 两侧轻鼓"""
    random.seed(seed)
    for v in o.data.vertices:
        if v.co.z < 0.0: continue
        # 点到直线距离
        px,py = v.co.x-x0, v.co.y-y0
        t = px*dx+py*dy
        dist = abs(px*(-dy)+py*dx)
        if dist < width and -0.3 < t < 0.3:
            fall = math.cos(dist/width*math.pi/2)**2
            v.co.z -= depth*fall*(0.8+0.4*random.random())

objs = []
# ---- 框架: William款直线条, 底座+避光内收底脚 ----
objs.append(box("base",(2.10,0.90,0.30),(0,0,0.28),M_UP,bevel=0.025,sub=2))
objs.append(box("plinth",(1.94,0.78,0.07),(0,0,0.075),M_DK,bevel=0.008,bev_seg=2,sub=1))
# ---- Track扶手: 干净直线, 前端圆角大一点 ----
for sx in (-1,1):
    a = box(f"arm_{'L' if sx<0 else 'R'}",(0.24,0.90,0.34),(sx*0.93,0,0.53),M_UP,bevel=0.045,sub=2)
    objs.append(a)
    objs.append(piping_rect(f"arm_pipe_{'L' if sx<0 else 'R'}",0.20,0.86,(sx*0.93,0,0.705),M_WELT,r=0.008))
# ---- 靠背微后倾 ----
back = box("backrest",(1.86,0.20,0.56),(0,-0.36,0.65),M_UP,bevel=0.045,sub=2)
back.rotation_euler.x = math.radians(-8); objs.append(back)
objs.append(piping_rect("back_pipe_top",1.70,0.16,(0,-0.415,0.935),M_WELT,r=0.008))

# ---- 坐垫x3: 鼓包+包边正好压在接缝上+两道自然折痕 ----
for k,cx in enumerate((-0.62,0.0,0.62)):
    c = box(f"seat_{k}",(0.60,0.62,0.18),(cx,0.06,0.50),M_UP,bevel=0.035,bev_seg=3,sub=2)
    cushion_crown(c, lift=0.022)
    crease(c, -0.18,-0.15, 0.7,0.7, width=0.05, depth=0.005, seed=11+k)
    crease(c, 0.15,-0.2, -0.6,0.8, width=0.04, depth=0.004, seed=21+k)
    smart_uv(c); objs.append(c)
    # 包边坐在垫子腰线, 不悬空
    objs.append(piping_rect(f"seat_pipe_{k}",0.575,0.595,(cx,0.06,0.50),M_WELT,r=0.008))
# ---- 靠垫x3 ----
for k,cx in enumerate((-0.62,0.0,0.62)):
    c = box(f"backc_{k}",(0.60,0.16,0.44),(cx,-0.26,0.72),M_UP,bevel=0.04,bev_seg=3,sub=2)
    c.rotation_euler.x = math.radians(-12)
    cushion_crown(c, lift=0.015)
    smart_uv(c); objs.append(c)

# ---- 抱枕: 对角捏角, 幅度小 ----
for nm,cx,col,rz in (("pillow_orange",-0.52,M_OR,0.15),("pillow_blue",0.52,M_BL,-0.15)):
    p = box(nm,(0.38,0.12,0.38),(cx,-0.10,0.72),col,bevel=0.05,bev_seg=3,sub=2)
    p.rotation_euler = (math.radians(-16),math.radians(10 if cx<0 else -10),rz)
    for v in p.data.vertices:
        if abs(v.co.x)>0.11 and abs(v.co.z)>0.11:
            v.co.x *= 0.93; v.co.z *= 0.93
    smart_uv(p); p["noTheme"]=1; objs.append(p)

# ---- William金属锥腿+黄铜脚 ----
for sx in (-1,1):
    for sz in (-1,1):
        x,y = sx*0.88, sz*0.33
        bpy.ops.mesh.primitive_cylinder_add(radius=0.028, depth=0.10, location=(x,y,0.06))
        leg = bpy.context.active_object; leg.name=f"leg_{sx}_{sz}"
        leg.data.materials.append(M_METAL)
        leg.scale.x = 0.8; leg.scale.y = 0.8
        objs.append(leg)
        bpy.ops.mesh.primitive_cylinder_add(radius=0.020, depth=0.018, location=(x,y,0.012))
        foot = bpy.context.active_object; foot.name=f"foot_{sx}_{sz}"
        foot.data.materials.append(M_BRASS); objs.append(foot)

for o in list(objs):
    if o.type != 'MESH': continue
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
    for md in [m.name for m in o.modifiers]:
        try: bpy.ops.object.modifier_apply(modifier=md)
        except Exception as e: print("apply fail", o.name, e)

print("exporting", OUT, "objects:", len(objs))
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', export_materials='EXPORT', export_extras=True,
    export_cameras=False, export_lights=False, use_selection=True)
print("OK sofa hd v3")
